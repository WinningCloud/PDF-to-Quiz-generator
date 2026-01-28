import pytest
from unittest.mock import Mock, patch
import numpy as np

from core.question_validation import QuestionValidator
from utils.similarity_utils import calculate_similarity

class TestQuestionValidator:
    def setup_method(self):
        """Setup test environment"""
        self.validator = QuestionValidator(validation_threshold=0.7)
        
        # Create test questions
        self.test_questions = [
            {
                "question_id": "q1",
                "question_text": "What is machine learning?",
                "answer": "Machine learning is a subset of artificial intelligence.",
                "question_type": "short_answer",
                "difficulty": "medium",
                "chunk_id": "chunk_1",
                "confidence_score": 0.8
            },
            {
                "question_id": "q2",
                "question_text": "Which of these is a type of machine learning?",
                "answer": "Supervised learning",
                "question_type": "mcq",
                "options": ["Supervised learning", "Database learning", "Network learning", "System learning"],
                "difficulty": "easy",
                "chunk_id": "chunk_1",
                "confidence_score": 0.9
            }
        ]
        
        # Create test chunks
        self.test_chunks = [
            {
                "chunk_id": "chunk_1",
                "text": "Machine learning is a subset of artificial intelligence that focuses on building "
                        "systems that learn from data. Types of machine learning include supervised learning, "
                        "unsupervised learning, and reinforcement learning.",
                "page_number": 1
            }
        ]
    
    def test_validate_question_batch(self):
        """Test batch question validation"""
        valid, needs_review, invalid = self.validator.validate_question_batch(
            self.test_questions,
            self.test_chunks
        )
        
        # All questions should pass basic validation
        assert len(valid) + len(needs_review) + len(invalid) == len(self.test_questions)
        
        # Check validation status
        for question in valid:
            assert question["validation_status"] == "validated"
        
        for question in needs_review:
            assert question["validation_status"] == "needs_review"
        
        for question in invalid:
            assert question["validation_status"] == "failed"
    
    def test_validate_single_question(self):
        """Test single question validation"""
        question = self.test_questions[0]
        source_text = self.test_chunks[0]["text"]
        
        result = self.validator.validate_single_question(question, source_text)
        
        assert "overall_score" in result
        assert "is_answerable" in result
        assert "answer_correctness" in result
        assert "clarity_score" in result
        
        # Score should be between 0 and 1
        assert 0 <= result["overall_score"] <= 1
        assert 0 <= result["answer_correctness"] <= 1
        assert 0 <= result["clarity_score"] <= 1
    
    def test_perform_quick_checks(self):
        """Test quick validation checks"""
        question = self.test_questions[0]
        source_text = self.test_chunks[0]["text"]
        
        quick_checks = self.validator._perform_quick_checks(question, source_text)
        
        assert "passed" in quick_checks
        assert "score" in quick_checks
        assert "issues" in quick_checks
        assert "checks_passed" in quick_checks
        assert "total_checks" in quick_checks
        
        # Score should be between 0 and 1
        assert 0 <= quick_checks["score"] <= 1
    
    def test_quick_checks_fail_empty_question(self):
        """Test quick checks with empty question"""
        empty_question = {
            "question_text": "",
            "answer": ""
        }
        
        quick_checks = self.validator._perform_quick_checks(empty_question, "source")
        
        assert not quick_checks["passed"]
        assert len(quick_checks["issues"]) > 0
    
    def test_quick_checks_mcq_options(self):
        """Test quick checks for MCQ options"""
        bad_mcq = {
            "question_text": "Test question?",
            "answer": "Correct",
            "question_type": "mcq",
            "options": ["A", "B"]  # Only 2 options
        }
        
        quick_checks = self.validator._perform_quick_checks(bad_mcq, "source")
        
        assert "options" in str(quick_checks["issues"])
    
    def test_quick_checks_answer_not_in_options(self):
        """Test quick checks when answer not in options"""
        bad_mcq = {
            "question_text": "Test question?",
            "answer": "Correct Answer",
            "question_type": "mcq",
            "options": ["A", "B", "C", "D"]  # Answer not in options
        }
        
        quick_checks = self.validator._perform_quick_checks(bad_mcq, "source")
        
        assert "Correct answer not in options" in quick_checks["issues"]
    
    @patch('core.question_validation.llm_client.generate_json')
    def test_validate_with_llm(self, mock_generate):
        """Test validation with LLM"""
        mock_response = {
            "is_answerable": True,
            "answer_correctness_score": 0.9,
            "clarity_score": 0.8,
            "difficulty_appropriate": True,
            "overall_score": 0.85,
            "issues": [],
            "recommendations": ["Good question"]
        }
        mock_generate.return_value = mock_response
        
        result = self.validator._validate_with_llm(
            self.test_questions[0],
            self.test_chunks[0]["text"]
        )
        
        assert result["is_answerable"] is True
        assert result["overall_score"] > 0.7
    
    def test_validate_with_rules(self):
        """Test rule-based validation fallback"""
        result = self.validator._validate_with_rules(
            self.test_questions[0],
            self.test_chunks[0]["text"]
        )
        
        assert "is_answerable" in result
        assert "answer_correctness_score" in result
        assert "clarity_score" in result
        assert "overall_score" in result
    
    def test_calculate_clarity_score(self):
        """Test clarity score calculation"""
        clear_text = "This is a clear and simple sentence."
        complex_text = "The multifaceted interdisciplinary conceptualization necessitates comprehensive comprehension."
        
        clear_score = self.validator._calculate_clarity_score(clear_text)
        complex_score = self.validator._calculate_clarity_score(complex_text)
        
        assert 0 <= clear_score <= 1
        assert 0 <= complex_score <= 1
        assert clear_score > complex_score
    
    def test_check_ambiguity(self):
        """Test ambiguity checking"""
        clear_text = "The algorithm always produces the correct result."
        ambiguous_text = "The algorithm might sometimes produce possibly correct results."
        
        clear_ambiguous = self.validator._check_ambiguity(clear_text)
        ambiguous = self.validator._check_ambiguity(ambiguous_text)
        
        assert not clear_ambiguous
        assert ambiguous
    
    def test_assess_difficulty(self):
        """Test difficulty assessment"""
        easy_question = {
            "question_text": "What is AI?",
            "answer": "Artificial Intelligence",
            "difficulty": "easy"
        }
        
        hard_question = {
            "question_text": "Explain the backpropagation algorithm with mathematical formulation.",
            "answer": "Detailed technical explanation...",
            "difficulty": "hard"
        }
        
        source_text = "Simple text about artificial intelligence."
        
        easy_score = self.validator._assess_difficulty(easy_question, source_text)
        hard_score = self.validator._assess_difficulty(hard_question, source_text)
        
        assert 0 <= easy_score <= 1
        assert 0 <= hard_score <= 1
    
    def test_calculate_text_complexity(self):
        """Test text complexity calculation"""
        simple_text = "The cat sat on the mat."
        complex_text = "The multidisciplinary conceptual framework necessitates comprehensive analysis."
        
        simple_score = self.validator._calculate_text_complexity(simple_text)
        complex_score = self.validator._calculate_text_complexity(complex_text)
        
        assert 0 <= simple_score <= 1
        assert 0 <= complex_score <= 1
        assert complex_score > simple_score
    
    def test_calculate_overall_score(self):
        """Test overall score calculation"""
        quick_checks = {
            "passed": True,
            "score": 0.8
        }
        
        llm_validation = {
            "overall_score": 0.9,
            "is_answerable": True,
            "answer_correctness_score": 0.95
        }
        
        overall_score = self.validator._calculate_overall_score(quick_checks, llm_validation)
        
        assert 0 <= overall_score <= 1
    
    def test_regenerate_failed_questions(self):
        """Test regenerating failed questions"""
        invalid_questions = [
            {
                "question_id": "q1",
                "question_text": "Bad question?",
                "answer": "Wrong answer",
                "difficulty": "medium",
                "subtopic": "AI",
                "chunk_id": "chunk_1",
                "page_number": 1
            }
        ]
        
        with patch.object(self.validator, '_regenerate_single_question') as mock_regenerate:
            mock_regenerate.return_value = {
                "question_text": "Regenerated question?",
                "answer": "Correct answer",
                "difficulty": "medium"
            }
            
            regenerated = self.validator.regenerate_failed_questions(
                invalid_questions,
                self.test_chunks
            )
            
            assert len(regenerated) > 0
    
    @patch('core.question_validation.llm_client.generate_json')
    def test_regenerate_single_question(self, mock_generate):
        """Test regenerating single question"""
        mock_response = {
            "question_text": "What is machine learning in AI?",
            "answer": "Machine learning is a subset of AI.",
            "explanation": "It focuses on learning from data.",
            "question_type": "short_answer"
        }
        mock_generate.return_value = mock_response
        
        regenerated = self.validator._regenerate_single_question(
            "Machine learning is...",
            "machine learning",
            "medium",
            "chunk_1",
            1
        )
        
        assert regenerated is not None
        assert "question_text" in regenerated
        assert "answer" in regenerated
    
    def test_create_validation_report(self):
        """Test creating validation report"""
        valid = [{"validation_score": 0.8}]
        needs_review = [{"validation_score": 0.6}]
        invalid = [{"validation_score": 0.4}]
        
        report = self.validator.create_validation_report(valid, needs_review, invalid)
        
        assert "total_questions" in report
        assert "validation_rate" in report
        assert "quality_score" in report
        assert "common_issues" in report
        assert "recommendations" in report
        
        assert report["total_questions"] == 3
        assert 0 <= report["validation_rate"] <= 1
        assert 0 <= report["quality_score"] <= 1
    
    def test_get_quality_rating(self):
        """Test quality rating calculation"""
        assert self.validator._get_quality_rating(0.9) == "Excellent"
        assert self.validator._get_quality_rating(0.75) == "Good"
        assert self.validator._get_quality_rating(0.65) == "Fair"
        assert self.validator._get_quality_rating(0.5) == "Needs Improvement"
    
    def test_summarize_issues(self):
        """Test issue summarization"""
        common_issues = [
            ("Answer not in source", 5),
            ("Question ambiguous", 3),
            ("Difficulty mismatch", 2)
        ]
        
        summary = self.validator._summarize_issues(common_issues)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
    
    def test_generate_recommendations(self):
        """Test recommendation generation"""
        # Test with low validation rate
        recommendations = self.validator._generate_recommendations(0.5, [])
        assert len(recommendations) > 0
        assert "improve" in recommendations[0].lower()
        
        # Test with common issues
        common_issues = [("similarity low", 3), ("ambiguous", 2)]
        recommendations = self.validator._generate_recommendations(0.8, common_issues)
        assert any("similarity" in r.lower() or "ambiguous" in r.lower() for r in recommendations)
    
    def test_validation_with_missing_chunk(self):
        """Test validation when chunk is missing"""
        questions = [{"chunk_id": "missing_chunk", "question_text": "Test?", "answer": "Test"}]
        chunks = [{"chunk_id": "different_chunk", "text": "Different text"}]
        
        valid, needs_review, invalid = self.validator.validate_question_batch(questions, chunks)
        
        # Question should fail because chunk not found
        assert len(invalid) == 1
        assert "Source chunk not found" in invalid[0].get("validation_reason", "")
    
    def test_validation_score_distribution(self):
        """Test validation score distribution"""
        # Create questions with different quality
        questions = [
            {"question_text": "Good question?", "answer": "Good answer", "chunk_id": "chunk_1"},
            {"question_text": "Bad question?", "answer": "Wrong", "chunk_id": "chunk_1"}
        ]
        
        valid, needs_review, invalid = self.validator.validate_question_batch(questions, self.test_chunks)
        
        # Good question should have higher score
        if valid and invalid:
            assert valid[0]["validation_score"] > invalid[0]["validation_score"]
    
    def test_count_complex_words(self):
        """Test complex word counting"""
        simple_text = "The cat sat on the mat."
        complex_text = "The interdisciplinary conceptualization necessitates comprehensive analysis."
        
        simple_count = self.validator._count_complex_words(simple_text)
        complex_count = self.validator._count_complex_words(complex_text)
        
        assert simple_count == 0  # All words are short
        assert complex_count > 0  # Has complex words