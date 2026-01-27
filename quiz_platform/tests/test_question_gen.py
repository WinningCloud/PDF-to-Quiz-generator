import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from quiz_platform.core.question_generation import QuestionGenerator
from quiz_platform.config.llm_config import llm_client

class TestQuestionGenerator:
    def setup_method(self):
        """Setup test environment"""
        self.generator = QuestionGenerator()
        
        # Create test chunks
        self.test_chunks = [
            {
                "chunk_id": "chunk_1",
                "text": "Machine learning is a subset of artificial intelligence that focuses on building "
                        "systems that learn from data. These systems improve their performance as they are "
                        "exposed to more data over time.",
                "page_number": 1
            },
            {
                "chunk_id": "chunk_2",
                "text": "Deep learning is a type of machine learning that uses neural networks with multiple "
                        "layers. These neural networks can learn complex patterns from large amounts of data.",
                "page_number": 2
            }
        ]
        
        # Create test topics
        self.test_topics = {
            "topic_hierarchy": {
                "Machine Learning": {
                    "subtopics": ["supervised learning", "unsupervised learning", "reinforcement learning"],
                    "concepts": ["algorithms", "models", "training"],
                    "frequency": 5
                },
                "Deep Learning": {
                    "subtopics": ["neural networks", "convolutional networks", "recurrent networks"],
                    "concepts": ["layers", "activation functions", "backpropagation"],
                    "frequency": 3
                }
            }
        }
    
    @patch.object(llm_client, 'generate_json')
    def test_generate_questions_from_chunks(self, mock_generate):
        """Test generating questions from chunks"""
        # Mock LLM response
        mock_response = {
            "questions": [
                {
                    "question_text": "What is machine learning?",
                    "question_type": "short_answer",
                    "answer": "Machine learning is a subset of artificial intelligence.",
                    "explanation": "Based on the provided text.",
                    "difficulty": "medium"
                }
            ]
        }
        mock_generate.return_value = mock_response
        
        questions = self.generator.generate_questions_from_chunks(
            self.test_chunks,
            self.test_topics
        )
        
        assert len(questions) > 0
        assert all(isinstance(q, dict) for q in questions)
        
        # Check question structure
        for question in questions:
            assert "question_text" in question
            assert "answer" in question
            assert "question_type" in question
            assert "difficulty" in question
            assert "chunk_id" in question
            assert "page_number" in question
    
    @patch.object(llm_client, 'generate_json')
    def test_generate_questions_for_topic(self, mock_generate):
        """Test generating questions for specific topic"""
        mock_response = {
            "questions": [
                {
                    "question_text": "What are neural networks used for in deep learning?",
                    "question_type": "mcq",
                    "options": [
                        "Pattern recognition",
                        "Data storage",
                        "Network security",
                        "File compression"
                    ],
                    "answer": "Pattern recognition",
                    "explanation": "Neural networks learn complex patterns from data.",
                    "difficulty": "medium"
                }
            ]
        }
        mock_generate.return_value = mock_response
        
        questions = self.generator._generate_questions_for_topic(
            self.test_chunks[1]["text"],
            "neural networks",
            "chunk_2",
            2
        )
        
        assert len(questions) > 0
        
        # Check MCQ structure
        mcq = questions[0]
        if mcq["question_type"] == "mcq":
            assert "options" in mcq
            assert len(mcq["options"]) >= 4
            assert mcq["answer"] in mcq["options"]
    
    def test_generate_general_questions(self):
        """Test generating general questions"""
        # This might use LLM, so we test with mock
        with patch.object(self.generator, '_generate_general_questions') as mock_method:
            mock_method.return_value = [
                {
                    "question_text": "General question",
                    "question_type": "short_answer",
                    "answer": "General answer",
                    "difficulty": "easy"
                }
            ]
            
            questions = self.generator._generate_general_questions(
                self.test_chunks[0]["text"],
                "chunk_1",
                1
            )
            
            assert len(questions) > 0
    
    def test_generate_fallback_questions(self):
        """Test fallback question generation"""
        questions = self.generator._generate_fallback_questions(
            self.test_chunks[0]["text"],
            "chunk_1",
            1
        )
        
        assert len(questions) > 0
        
        # Check fallback questions have basic structure
        for question in questions:
            assert "question_text" in question
            assert "answer" in question
            assert "generation_source" in question
            assert question["generation_source"] == "fallback"
    
    def test_split_into_sentences(self):
        """Test sentence splitting"""
        text = "First sentence. Second sentence! Third sentence?"
        
        sentences = self.generator._split_into_sentences(text)
        
        assert len(sentences) == 3
        assert all(s.strip() for s in sentences)
    
    def test_create_simple_mcq(self):
        """Test creating simple MCQ"""
        sentence = "Neural networks are used for pattern recognition in deep learning."
        
        mcq = self.generator._create_simple_mcq(sentence, 1)
        
        assert "question_text" in mcq
        assert "options" in mcq
        assert "answer" in mcq
        assert "difficulty" in mcq
        
        assert len(mcq["options"]) == 4
        assert mcq["answer"] in mcq["options"]
    
    def test_create_simple_short_answer(self):
        """Test creating simple short answer question"""
        sentence = "Machine learning algorithms improve with more data."
        
        saq = self.generator._create_simple_short_answer(sentence, 1)
        
        assert "question_text" in saq
        assert "answer" in saq
        assert "difficulty" in saq
        assert "question_type" in saq
        assert saq["question_type"] == "short_answer"
    
    @patch.object(llm_client, 'generate_json')
    def test_generate_questions_with_planner(self, mock_generate):
        """Test generating questions with planner assignments"""
        mock_response = {
            "questions": [
                {
                    "question_text": "Planned question",
                    "question_type": "mcq",
                    "options": ["A", "B", "C", "D"],
                    "answer": "A",
                    "explanation": "Planned explanation",
                    "difficulty": "medium"
                }
            ]
        }
        mock_generate.return_value = mock_response
        
        planner_assignments = [
            {
                "chunk_id": "chunk_1",
                "text": self.test_chunks[0]["text"],
                "target_questions": 2,
                "difficulty_mix": ["easy", "medium"]
            }
        ]
        
        questions = self.generator.generate_questions_with_planner(
            self.test_chunks,
            planner_assignments
        )
        
        assert len(questions) > 0
        
        # Check assignment-based metadata
        for question in questions:
            assert "generation_source" in question
            assert question["generation_source"] == "planner_assignment"
    
    def test_select_difficulty(self):
        """Test difficulty selection"""
        # Test with mixed difficulties
        difficulty_mix = ["easy", "medium", "hard"]
        
        # Run multiple times to ensure all difficulties can be selected
        selected = set()
        for _ in range(100):
            difficulty = self.generator._select_difficulty(difficulty_mix)
            selected.add(difficulty)
        
        assert "easy" in selected
        assert "medium" in selected
        assert "hard" in selected
        
        # Test with single difficulty
        single_mix = ["hard"]
        assert self.generator._select_difficulty(single_mix) == "hard"
        
        # Test empty mix
        assert self.generator._select_difficulty([]) == "medium"
    
    def test_enrich_questions_with_context(self):
        """Test enriching questions with context"""
        questions = [
            {
                "question_id": "q1",
                "chunk_id": "chunk_1",
                "question_text": "Test question",
                "answer": "Test answer"
            }
        ]
        
        enriched = self.generator.enrich_questions_with_context(
            questions,
            self.test_chunks
        )
        
        assert len(enriched) == len(questions)
        
        # Check context was added
        for question in enriched:
            assert "context" in question
            context = question["context"]
            assert "page_number" in context
            assert "chunk_preview" in context
            assert "word_count" in context
    
    def test_get_topics_for_chunk(self):
        """Test getting topics for chunk"""
        # Mock the method since it uses random sampling
        with patch.object(self.generator, '_get_topics_for_chunk') as mock_method:
            mock_method.return_value = ["machine learning", "ai"]
            
            topics = self.generator._get_topics_for_chunk(
                "chunk_1",
                self.test_topics
            )
            
            assert len(topics) > 0
            assert all(isinstance(t, str) for t in topics)
    
    @patch.object(llm_client, 'generate_json')
    def test_generate_mcq(self, mock_generate):
        """Test generating MCQ"""
        mock_response = {
            "question_text": "What is deep learning?",
            "options": [
                "A type of machine learning",
                "A database system",
                "A programming language",
                "A hardware component"
            ],
            "answer": "A type of machine learning",
            "explanation": "Deep learning uses neural networks.",
            "difficulty": "medium"
        }
        mock_generate.return_value = mock_response
        
        mcq = self.generator._generate_mcq(
            self.test_chunks[1]["text"],
            "medium"
        )
        
        assert mcq is not None
        assert mcq["question_type"] == "mcq"
        assert mcq["difficulty"] == "medium"
    
    @patch.object(llm_client, 'generate_json')
    def test_generate_short_answer(self, mock_generate):
        """Test generating short answer question"""
        mock_response = {
            "question_text": "Explain neural networks.",
            "answer": "Neural networks are computing systems inspired by biological neural networks.",
            "explanation": "They consist of interconnected nodes that process information.",
            "difficulty": "hard"
        }
        mock_generate.return_value = mock_response
        
        saq = self.generator._generate_short_answer(
            self.test_chunks[1]["text"],
            "hard"
        )
        
        assert saq is not None
        assert saq["question_type"] == "short_answer"
        assert saq["difficulty"] == "hard"
    
    def test_question_generation_error_handling(self):
        """Test error handling in question generation"""
        # Test with empty text
        empty_questions = self.generator.generate_questions_from_chunks([], {})
        assert len(empty_questions) == 0
        
        # Test with None chunks
        none_questions = self.generator.generate_questions_from_chunks(None, {})
        assert len(none_questions) == 0
    
    def test_question_metadata(self):
        """Test question metadata structure"""
        question = {
            "question_id": "test_1",
            "question_text": "Test question?",
            "answer": "Test answer",
            "question_type": "short_answer",
            "difficulty": "easy",
            "chunk_id": "chunk_1",
            "page_number": 1,
            "subtopic": "test topic",
            "generation_source": "test",
            "confidence_score": 0.8
        }
        
        # Test all required fields
        required_fields = [
            "question_text", "answer", "question_type", 
            "difficulty", "chunk_id", "page_number"
        ]
        
        for field in required_fields:
            assert field in question
    
    def test_question_difficulty_validation(self):
        """Test question difficulty validation"""
        valid_difficulties = ["easy", "medium", "hard"]
        
        questions = self.generator._generate_fallback_questions(
            self.test_chunks[0]["text"],
            "chunk_1",
            1
        )
        
        for question in questions:
            assert question["difficulty"] in valid_difficulties