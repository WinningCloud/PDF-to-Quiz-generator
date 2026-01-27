import pytest
import numpy as np
from unittest.mock import Mock, patch

from quiz_platform.core.deduplication import Deduplicator
from quiz_platform.utils.similarity_utils import calculate_similarity


class TestDeduplicator:
    def setup_method(self):
        """Setup test environment"""
        self.deduplicator = Deduplicator(similarity_threshold=0.85)
        
        # Create test questions
        self.test_questions = [
            {
                "question_id": "q1",
                "question_text": "What is machine learning?",
                "answer": "Machine learning is a subset of AI.",
                "question_type": "short_answer",
                "difficulty": "medium",
                "normalized_topic": "Machine Learning",
                "subtopic": "basics",
                "validation_score": 0.8,
                "confidence_score": 0.7
            },
            {
                "question_id": "q2",
                "question_text": "Define machine learning.",
                "answer": "Machine learning is part of artificial intelligence.",
                "question_type": "short_answer",
                "difficulty": "medium",
                "normalized_topic": "Machine Learning",
                "subtopic": "basics",
                "validation_score": 0.8,
                "confidence_score": 0.7
            },
            {
                "question_id": "q3",
                "question_text": "What are neural networks?",
                "answer": "Neural networks are computing systems.",
                "question_type": "short_answer",
                "difficulty": "hard",
                "normalized_topic": "Deep Learning",
                "subtopic": "neural networks",
                "validation_score": 0.9,
                "confidence_score": 0.8
            },
            {
                "question_id": "q4",
                "question_text": "Explain supervised learning.",
                "answer": "Supervised learning uses labeled data.",
                "question_type": "short_answer",
                "difficulty": "medium",
                "normalized_topic": "Machine Learning",
                "subtopic": "supervised learning",
                "validation_score": 0.7,
                "confidence_score": 0.6
            }
        ]
    
    def test_deduplicate_questions(self):
        """Test question deduplication"""
        unique, duplicates, stats = self.deduplicator.deduplicate_questions(
            self.test_questions
        )
        
        # Should have at least some unique questions
        assert len(unique) > 0
        assert len(unique) <= len(self.test_questions)
        
        # Check unique questions have metadata
        for question in unique:
            assert "is_unique_after_dedup" in question
            assert question["is_unique_after_dedup"] is True
            assert "duplicate_count" in question
        
        # Check duplicates have metadata
        for duplicate in duplicates:
            assert "is_unique" in duplicate["question"]
            assert duplicate["question"]["is_unique"] is False
            assert "duplicate_of" in duplicate
        
        # Check statistics
        assert "total_original_questions" in stats
        assert "total_unique_questions" in stats
        assert "total_duplicates_removed" in stats
        assert "deduplication_rate" in stats
        assert stats["total_original_questions"] == len(self.test_questions)
        assert stats["total_unique_questions"] == len(unique)
        assert stats["total_duplicates_removed"] == len(duplicates)
    
    @patch('core.deduplication.embedding_model.embed_batch')
    def test_generate_embeddings(self, mock_embed):
        """Test embedding generation"""
        mock_embed.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ]
        
        texts = ["text1", "text2", "text3"]
        embeddings = self.deduplicator._generate_embeddings(texts)
        
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape[0] == len(texts)
        assert embeddings.shape[1] == 3
    
    @patch('core.deduplication.embedding_model.embed_batch')
    def test_find_duplicates(self, mock_embed):
        """Test finding duplicates"""
        # Create embeddings that will make q1 and q2 similar
        mock_embed.return_value = [
            [0.1, 0.2, 0.3],  # q1
            [0.1, 0.2, 0.3],  # q2 (same as q1)
            [0.7, 0.8, 0.9],  # q3
            [0.4, 0.5, 0.6]   # q4
        ]
        
        duplicates = self.deduplicator._find_duplicates(
            self.test_questions,
            np.array(mock_embed.return_value)
        )
        
        # q1 and q2 should be marked as duplicates
        assert len(duplicates) >= 1
    
    def test_are_questions_duplicate(self):
        """Test duplicate detection logic"""
        # Test with same question type and high similarity
        question1 = self.test_questions[0]
        question2 = self.test_questions[1]
        
        # Mock high similarity
        with patch('core.deduplication.cosine_similarity') as mock_cosine:
            mock_cosine.return_value = np.array([[0.9]])
            
            is_duplicate = self.deduplicator._are_questions_duplicate(
                question1, question2, 0.9
            )
            
            # These should be duplicates
            assert is_duplicate is True
        
        # Test with different question types
        mcq_question = {"question_type": "mcq", "question_text": "Test?", "answer": "A"}
        sa_question = {"question_type": "short_answer", "question_text": "Test?", "answer": "Answer"}
        
        is_duplicate = self.deduplicator._are_questions_duplicate(
            mcq_question, sa_question, 0.95
        )
        
        assert is_duplicate is False
    
    def test_check_same_concept(self):
        """Test concept similarity checking"""
        # Same subtopic
        question1 = {"subtopic": "machine learning", "normalized_topic": "AI"}
        question2 = {"subtopic": "machine learning", "normalized_topic": "AI"}
        
        assert self.deduplicator._check_same_concept(question1, question2) is True
        
        # Same normalized topic
        question3 = {"subtopic": "deep learning", "normalized_topic": "AI"}
        question4 = {"subtopic": "machine learning", "normalized_topic": "AI"}
        
        assert self.deduplicator._check_same_concept(question3, question4) is True
        
        # Different topics
        question5 = {"subtopic": "ml", "normalized_topic": "AI"}
        question6 = {"subtopic": "physics", "normalized_topic": "Science"}
        
        assert self.deduplicator._check_same_concept(question5, question6) is False
        
        # Keyword overlap
        question7 = {"question_text": "Explain neural networks in deep learning"}
        question8 = {"question_text": "What are neural networks?"}
        
        assert self.deduplicator._check_same_concept(question7, question8) is True
    
    def test_get_unique_questions(self):
        """Test getting unique questions"""
        duplicates = [
            {
                "question": {"question_id": "q2"},
                "duplicate_of": "q1",
                "similarity_score": 0.9
            }
        ]
        
        unique = self.deduplicator._get_unique_questions(
            self.test_questions,
            duplicates
        )
        
        # q2 should be removed
        question_ids = [q["question_id"] for q in unique]
        assert "q2" not in question_ids
        assert "q1" in question_ids
    
    def test_calculate_deduplication_stats(self):
        """Test deduplication statistics calculation"""
        original = self.test_questions
        unique = self.test_questions[:2]  # First 2 as unique
        duplicates = [
            {"question": self.test_questions[2], "similarity_score": 0.9},
            {"question": self.test_questions[3], "similarity_score": 0.8}
        ]
        
        stats = self.deduplicator._calculate_deduplication_stats(
            original, unique, duplicates
        )
        
        assert stats["total_original_questions"] == len(original)
        assert stats["total_unique_questions"] == len(unique)
        assert stats["total_duplicates_removed"] == len(duplicates)
        assert "average_similarity_score" in stats
        assert "duplicate_reasons" in stats
        assert "topic_distribution_original" in stats
        assert "topic_distribution_unique" in stats
        assert "topic_preservation_rate" in stats
    
    def test_calculate_topic_preservation(self):
        """Test topic preservation calculation"""
        from collections import Counter
        
        original = Counter({"AI": 5, "Science": 3, "Math": 2})
        unique = Counter({"AI": 3, "Science": 2, "Math": 1})
        
        preservation = self.deduplicator._calculate_topic_preservation(original, unique)
        
        assert 0 <= preservation <= 1
        # Should be less than 1 because we removed questions
        assert preservation < 1.0
    
    def test_add_deduplication_metadata(self):
        """Test adding deduplication metadata"""
        questions = [self.test_questions[0], self.test_questions[1]]
        duplicates = [
            {
                "question": self.test_questions[1],
                "duplicate_of": "q1",
                "similarity_score": 0.9
            }
        ]
        
        updated = self.deduplicator._add_deduplication_metadata(questions, duplicates)
        
        # q1 should have duplicate count
        for question in updated:
            if question["question_id"] == "q1":
                assert question["duplicate_count"] == 1
                assert question["is_unique_after_dedup"] is True
    
    def test_find_near_duplicates(self):
        """Test finding near-duplicates"""
        with patch('core.deduplication.embedding_model.embed_batch') as mock_embed:
            mock_embed.return_value = [
                [0.1, 0.2, 0.3],
                [0.15, 0.25, 0.35],  # Similar to first
                [0.7, 0.8, 0.9],
                [0.75, 0.85, 0.95]   # Similar to third
            ]
            
            near_duplicates = self.deduplicator.find_near_duplicates(
                self.test_questions,
                threshold=0.8
            )
            
            # Should find some near-duplicates
            assert isinstance(near_duplicates, list)
            for dup in near_duplicates:
                assert len(dup) == 4  # (index1, index2, similarity, reason)
                assert 0.8 <= dup[2] < 0.85  # Near duplicate threshold
    
    def test_get_near_duplicate_reason(self):
        """Test getting near-duplicate reason"""
        question1 = {
            "question_type": "mcq",
            "normalized_topic": "AI",
            "answer": "Answer A"
        }
        
        question2 = {
            "question_type": "mcq",
            "normalized_topic": "AI",
            "answer": "Answer B"
        }
        
        reason = self.deduplicator._get_near_duplicate_reason(
            question1, question2, 0.8
        )
        
        assert "different_answers" in reason
    
    def test_deduplicate_by_topic(self):
        """Test topic-based deduplication"""
        # Create questions with topic distribution
        questions = []
        for i in range(10):
            questions.append({
                "question_id": f"q{i}",
                "normalized_topic": "AI" if i < 7 else "Science",
                "validation_score": 0.5 + (i * 0.05)
            })
        
        deduplicated = self.deduplicator.deduplicate_by_topic(
            questions,
            max_per_topic=3
        )
        
        # Should have max 3 per topic
        ai_count = sum(1 for q in deduplicated if q["normalized_topic"] == "AI")
        science_count = sum(1 for q in deduplicated if q["normalized_topic"] == "Science")
        
        assert ai_count <= 3
        assert science_count <= 3
    
    def test_select_diverse_questions(self):
        """Test diverse question selection"""
        # Create similar questions
        similar_questions = []
        for i in range(5):
            similar_questions.append({
                "question_id": f"q{i}",
                "question_text": f"What is AI? Version {i}",
                "validation_score": 0.8,
                "confidence_score": 0.7
            })
        
        with patch('core.deduplication.embedding_model.embed') as mock_embed:
            # Make all embeddings similar
            mock_embed.return_value = [0.1, 0.2, 0.3]
            
            selected = self.deduplicator._select_diverse_questions(
                similar_questions,
                max_count=2
            )
            
            # Should select fewer due to similarity
            assert len(selected) <= 2
    
    def test_calculate_question_score(self):
        """Test question scoring"""
        good_question = {
            "validation_score": 0.9,
            "confidence_score": 0.8,
            "question_text": "Good question with appropriate length?",
            "question_type": "short_answer"
        }
        
        bad_question = {
            "validation_score": 0.3,
            "confidence_score": 0.4,
            "question_text": "Bad",
            "question_type": "mcq"
        }
        
        good_score = self.deduplicator._calculate_question_score(good_question)
        bad_score = self.deduplicator._calculate_question_score(bad_question)
        
        assert good_score > bad_score
        assert 0 <= good_score <= 1
        assert 0 <= bad_score <= 1
    
    def test_create_deduplication_report(self):
        """Test deduplication report creation"""
        original_count = 100
        unique_count = 70
        duplicates_count = 30
        stats = {
            "average_similarity_score": 0.88,
            "topic_preservation_rate": 0.85
        }
        
        report = self.deduplicator.create_deduplication_report(
            original_count,
            unique_count,
            duplicates_count,
            stats
        )
        
        assert "summary" in report
        assert "statistics" in report
        assert "impact_analysis" in report
        assert "recommendations" in report
        
        summary = report["summary"]
        assert summary["original_question_count"] == original_count
        assert summary["unique_question_count"] == unique_count
        assert summary["duplicates_removed"] == duplicates_count
        assert summary["deduplication_rate"] == duplicates_count / original_count
    
    def test_analyze_deduplication_impact(self):
        """Test impact analysis"""
        impact = self.deduplicator._analyze_deduplication_impact(
            original_count=100,
            unique_count=70,
            stats={"topic_preservation_rate": 0.85}
        )
        
        assert "reduction_percentage" in impact
        assert "efficiency_gain" in impact
        assert "topic_coverage_retained" in impact
        assert "quality_improvement_score" in impact
        
        # Verify calculations
        assert impact["reduction_percentage"] == 30  # 100-70 = 30%
        assert impact["efficiency_gain"] > 0
        assert impact["topic_coverage_retained"] == 0.85  # From stats
    
    def test_empty_questions(self):
        """Test deduplication with empty input"""
        unique, duplicates, stats = self.deduplicator.deduplicate_questions([])
        
        assert len(unique) == 0
        assert len(duplicates) == 0
        assert stats["total_original_questions"] == 0
        assert stats["total_unique_questions"] == 0
        assert stats["total_duplicates_removed"] == 0
        assert stats["deduplication_rate"] == 0.0
    
    def test_single_question(self):
        """Test deduplication with single question"""
        single_question = [self.test_questions[0]]
        unique, duplicates, stats = self.deduplicator.deduplicate_questions(single_question)
        
        assert len(unique) == 1
        assert len(duplicates) == 0
        assert stats["total_original_questions"] == 1
        assert stats["total_unique_questions"] == 1
        assert stats["deduplication_rate"] == 0.0
    
    def test_all_duplicates(self):
        """Test when all questions are duplicates"""
        # Create 5 identical questions
        identical_questions = []
        for i in range(5):
            q = self.test_questions[0].copy()
            q["question_id"] = f"q{i}"
            identical_questions.append(q)
        
        with patch('core.deduplication.embedding_model.embed_batch') as mock_embed:
            # All embeddings are identical
            identical_embedding = [0.1, 0.2, 0.3]
            mock_embed.return_value = [identical_embedding] * 5
            
            unique, duplicates, stats = self.deduplicator.deduplicate_questions(
                identical_questions
            )
            
            # Should have only 1 unique question
            assert len(unique) == 1
            assert len(duplicates) == 4
            assert stats["deduplication_rate"] == 0.8  # 4/5 = 80%
    
    def test_no_duplicates(self):
        """Test when no questions are duplicates"""
        # Create questions on completely different topics
        diverse_questions = [
            {
                "question_id": "q1",
                "question_text": "What is photosynthesis?",
                "normalized_topic": "Biology",
                "question_type": "short_answer"
            },
            {
                "question_id": "q2",
                "question_text": "Solve: 2x + 3 = 11",
                "normalized_topic": "Mathematics",
                "question_type": "short_answer"
            },
            {
                "question_id": "q3",
                "question_text": "Who was Shakespeare?",
                "normalized_topic": "Literature",
                "question_type": "short_answer"
            }
        ]
        
        with patch('core.deduplication.embedding_model.embed_batch') as mock_embed:
            # Very different embeddings
            mock_embed.return_value = [
                [0.1, 0.2, 0.3],  # Biology
                [0.8, 0.7, 0.6],  # Math
                [0.3, 0.9, 0.2]   # Literature
            ]
            
            unique, duplicates, stats = self.deduplicator.deduplicate_questions(
                diverse_questions
            )
            
            # Should have all questions as unique
            assert len(unique) == 3
            assert len(duplicates) == 0
            assert stats["deduplication_rate"] == 0.0
    
    def test_mixed_duplicate_types(self):
        """Test different types of duplicates"""
        # Create questions with various duplicate scenarios
        mixed_questions = [
            {
                "question_id": "q1",
                "question_text": "What is AI?",
                "question_type": "short_answer",
                "answer": "Artificial Intelligence",
                "normalized_topic": "Computer Science"
            },
            {
                "question_id": "q2",
                "question_text": "Define Artificial Intelligence",
                "question_type": "short_answer",
                "answer": "AI is machine intelligence",
                "normalized_topic": "Computer Science"
            },
            {
                "question_id": "q3",
                "question_text": "What is Artificial Intelligence?",
                "question_type": "mcq",
                "answer": "A",
                "normalized_topic": "Computer Science"
            },
            {
                "question_id": "q4",
                "question_text": "What is AI?",
                "question_type": "short_answer",
                "answer": "Artificial Intelligence",
                "normalized_topic": "Technology"
            }
        ]
        
        # q1 and q2 should be duplicates (same meaning)
        # q1 and q3 should NOT be duplicates (different question types)
        # q1 and q4 might be near duplicates (different topics)
        
        unique, duplicates, stats = self.deduplicator.deduplicate_questions(
            mixed_questions
        )
        
        # Basic assertions
        assert len(unique) > 0
        assert len(unique) < len(mixed_questions)
        assert "duplicate_reasons" in stats
    
    def test_duplicate_with_different_metadata(self):
        """Test deduplication when questions have different metadata but same content"""
        question1 = {
            "question_id": "q1",
            "question_text": "What is machine learning?",
            "answer": "A subset of AI",
            "difficulty": "easy",
            "validation_score": 0.9,
            "confidence_score": 0.8
        }
        
        question2 = {
            "question_id": "q2",
            "question_text": "What is machine learning?",
            "answer": "A subset of AI",
            "difficulty": "hard",  # Different difficulty
            "validation_score": 0.7,  # Different score
            "confidence_score": 0.6
        }
        
        # These should be duplicates despite different metadata
        with patch('core.deduplication.cosine_similarity') as mock_cosine:
            mock_cosine.return_value = np.array([[1.0]])  # Perfect similarity
            
            is_duplicate = self.deduplicator._are_questions_duplicate(
                question1, question2, 0.9
            )
            
            assert is_duplicate is True
    
    def test_threshold_adjustment(self):
        """Test deduplication with different similarity thresholds"""
        # Test with strict threshold
        strict_deduplicator = Deduplicator(similarity_threshold=0.95)
        
        # Test with lenient threshold
        lenient_deduplicator = Deduplicator(similarity_threshold=0.7)
        
        with patch('core.deduplication.embedding_model.embed_batch') as mock_embed:
            # Embeddings with moderate similarity
            mock_embed.return_value = [
                [0.1, 0.2, 0.3],
                [0.15, 0.25, 0.35],  # ~0.98 similarity with first
                [0.7, 0.8, 0.9]
            ]
            
            # With strict threshold, fewer duplicates
            unique_strict, _, stats_strict = strict_deduplicator.deduplicate_questions(
                self.test_questions[:3]
            )
            
            # With lenient threshold, more duplicates
            unique_lenient, _, stats_lenient = lenient_deduplicator.deduplicate_questions(
                self.test_questions[:3]
            )
            
            # Lenient should find more duplicates (fewer unique questions)
            assert len(unique_lenient) <= len(unique_strict)
    
    def test_deduplication_performance(self):
        """Test performance with large dataset"""
        # Create many similar questions
        n_questions = 100
        similar_questions = []
        
        for i in range(n_questions):
            question = self.test_questions[0].copy()
            question["question_id"] = f"q{i}"
            question["question_text"] = f"What is machine learning? Variation {i}"
            similar_questions.append(question)
        
        # Time the deduplication
        import time
        start_time = time.time()
        
        unique, duplicates, stats = self.deduplicator.deduplicate_questions(
            similar_questions
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time
        assert execution_time < 10.0  # Should complete within 10 seconds
        
        # Should have significantly reduced count
        assert len(unique) < n_questions
        assert stats["deduplication_rate"] > 0.5  # At least 50% reduction
    
    def test_invalid_question_format(self):
        """Test handling of invalid question formats"""
        invalid_questions = [
            {"question_text": "What is AI?"},  # Missing required fields
            {},  # Empty dict
            {"question_id": "q1", "answer": "Yes"}  # Missing question_text
        ]
        
        # Should handle gracefully
        unique, duplicates, stats = self.deduplicator.deduplicate_questions(
            invalid_questions
        )
        
        # Should still return results
        assert "total_original_questions" in stats
        assert stats["total_original_questions"] == len(invalid_questions)
    
    def test_question_with_special_characters(self):
        """Test deduplication with special characters in questions"""
        question1 = {
            "question_id": "q1",
            "question_text": "What is AI? (Artificial Intelligence)",
            "answer": "AI stands for Artificial Intelligence."
        }
        
        question2 = {
            "question_id": "q2",
            "question_text": "What is AI? [Artificial Intelligence]",
            "answer": "AI means Artificial Intelligence."
        }
        
        question3 = {
            "question_id": "q3",
            "question_text": "What is AI? - Artificial Intelligence",
            "answer": "Artificial Intelligence is AI."
        }
        
        similar_questions = [question1, question2, question3]
        
        # These should be identified as near duplicates
        near_duplicates = self.deduplicator.find_near_duplicates(
            similar_questions,
            threshold=0.8
        )
        
        assert len(near_duplicates) > 0
    
    def test_batch_deduplication(self):
        """Test deduplication in batches"""
        # Create a large set of questions
        large_question_set = []
        for i in range(50):
            question = self.test_questions[i % 4].copy()
            question["question_id"] = f"batch_q{i}"
            large_question_set.append(question)
        
        unique, duplicates, stats = self.deduplicator.deduplicate_questions(
            large_question_set
        )
        
        # Verify batch processing worked
        assert len(unique) < len(large_question_set)
        assert stats["total_original_questions"] == len(large_question_set)
        assert stats["total_unique_questions"] == len(unique)
        assert stats["total_duplicates_removed"] == len(duplicates)