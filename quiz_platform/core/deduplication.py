import numpy as np
from collections import Counter
from typing import Dict, List, Any, Tuple, Set
import logging
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity
from quiz_platform.config.llm_config import embedding_model
from quiz_platform.utils.similarity_utils import jaccard_similarity, calculate_similarity

logger = logging.getLogger(__name__)

class Deduplicator:
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize deduplicator
        
        Args:
            similarity_threshold: Threshold for considering questions as duplicates
        """
        self.similarity_threshold = similarity_threshold
    
    def deduplicate_questions(
        self, 
        questions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict], List[Dict], Dict[str, Any]]:
        """
        Remove duplicate questions
        
        Args:
            questions: List of question dictionaries
            
        Returns:
            Tuple of (unique_questions, duplicates, statistics)
        """
        if len(questions) <= 1:
            return questions, [], {"total_questions": len(questions), "duplicates_removed": 0}
        
        # Generate embeddings for all questions
        question_texts = [q.get("question_text", "") for q in questions]
        question_embeddings = self._generate_embeddings(question_texts)
        
        # Find duplicates
        duplicates = self._find_duplicates(questions, question_embeddings)
        
        # Separate unique questions
        unique_questions = self._get_unique_questions(questions, duplicates)
        
        # Calculate statistics
        stats = self._calculate_deduplication_stats(questions, unique_questions, duplicates)
        
        # Add deduplication metadata
        unique_questions = self._add_deduplication_metadata(unique_questions, duplicates)
        
        logger.info(f"Deduplication: {len(unique_questions)} unique, {len(duplicates)} duplicates")
        
        return unique_questions, duplicates, stats
    
    def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts"""
        try:
            embeddings = embedding_model.embed_batch(texts)
            return np.array(embeddings, dtype=np.float32)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Return zero embeddings as fallback
            return np.zeros((len(texts), 384))  # Default dimension
    
    def _find_duplicates(
        self, 
        questions: List[Dict[str, Any]], 
        embeddings: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Find duplicate questions using multiple criteria"""
        duplicates = []
        processed = set()
        
        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(embeddings)
        
        for i in range(len(questions)):
            if i in processed:
                continue
            
            current_duplicates = []
            for j in range(i + 1, len(questions)):
                if j in processed:
                    continue
                
                # Check multiple similarity measures
                is_duplicate = self._are_questions_duplicate(
                    questions[i], 
                    questions[j], 
                    similarity_matrix[i][j]
                )
                
                if is_duplicate:
                    current_duplicates.append(j)
                    processed.add(j)
            
            if current_duplicates:
                # Mark all duplicates
                for dup_idx in current_duplicates:
                    duplicates.append({
                        "question": questions[dup_idx],
                        "duplicate_of": questions[i]["question_id"],
                        "similarity_score": float(similarity_matrix[i][dup_idx]),
                        "duplicate_reason": "semantic_similarity"
                    })
        
        return duplicates
    
    def _are_questions_duplicate(
        self, 
        question1: Dict[str, Any], 
        question2: Dict[str, Any], 
        embedding_similarity: float
    ) -> bool:
        """Check if two questions are duplicates"""
        # Quick checks first
        if question1.get("question_type") != question2.get("question_type"):
            return False
        
        # Check embedding similarity
        if embedding_similarity < self.similarity_threshold:
            return False
        
        # Check text similarity
        text1 = question1.get("question_text", "")
        text2 = question2.get("question_text", "")
        
        jaccard_sim = jaccard_similarity(text1, text2)
        if jaccard_sim < 0.3:  # Very different word sets
            return False
        
        # Check answer similarity
        answer1 = question1.get("answer", "")
        answer2 = question2.get("answer", "")
        
        if answer1 and answer2:
            answer_sim = calculate_similarity(answer1, answer2)
            if answer_sim < 0.5:  # Different answers
                return False
        
        # Check if they test the same concept
        same_concept = self._check_same_concept(question1, question2)
        if not same_concept:
            return False
        
        return True
    
    def _check_same_concept(
        self, 
        question1: Dict[str, Any], 
        question2: Dict[str, Any]
    ) -> bool:
        """Check if questions test the same concept"""
        # Check subtopic
        subtopic1 = question1.get("subtopic", "").lower()
        subtopic2 = question2.get("subtopic", "").lower()
        
        if subtopic1 and subtopic2 and subtopic1 == subtopic2:
            return True
        
        # Check normalized topic
        topic1 = question1.get("normalized_topic", "").lower()
        topic2 = question2.get("normalized_topic", "").lower()
        
        if topic1 and topic2 and topic1 == topic2:
            return True
        
        # Check for keyword overlap
        text1 = question1.get("question_text", "").lower()
        text2 = question2.get("question_text", "").lower()
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        # Remove common words
        common_words = {"the", "and", "is", "in", "to", "of", "a", "that", "it", "with"}
        keywords1 = words1 - common_words
        keywords2 = words2 - common_words
        
        # Check for significant keyword overlap
        overlap = keywords1 & keywords2
        if len(overlap) >= 2:  # At least 2 significant keywords in common
            return True
        
        return False
    
    def _get_unique_questions(
        self, 
        questions: List[Dict[str, Any]], 
        duplicates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get unique questions by removing duplicates"""
        duplicate_ids = {dup["question"]["question_id"] for dup in duplicates}
        unique_questions = [q for q in questions if q["question_id"] not in duplicate_ids]
        return unique_questions
    
    def _calculate_deduplication_stats(
        self, 
        original_questions: List[Dict], 
        unique_questions: List[Dict], 
        duplicates: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate deduplication statistics"""
        total_original = len(original_questions)
        total_unique = len(unique_questions)
        total_duplicates = len(duplicates)
        
        # Calculate similarity scores for duplicates
        similarity_scores = [dup["similarity_score"] for dup in duplicates]
        
        # Group duplicates by reason
        duplicate_reasons = defaultdict(int)
        for dup in duplicates:
            reason = dup.get("duplicate_reason", "unknown")
            duplicate_reasons[reason] += 1
        
        # Calculate topic distribution changes
        original_topics = Counter(q.get("normalized_topic", "General") for q in original_questions)
        unique_topics = Counter(q.get("normalized_topic", "General") for q in unique_questions)
        
        return {
            "total_original_questions": total_original,
            "total_unique_questions": total_unique,
            "total_duplicates_removed": total_duplicates,
            "deduplication_rate": total_duplicates / total_original if total_original > 0 else 0,
            "average_similarity_score": np.mean(similarity_scores) if similarity_scores else 0,
            "duplicate_reasons": dict(duplicate_reasons),
            "topic_distribution_original": dict(original_topics),
            "topic_distribution_unique": dict(unique_topics),
            "topic_preservation_rate": self._calculate_topic_preservation(
                original_topics, 
                unique_topics
            )
        }
    
    def _calculate_topic_preservation(
        self, 
        original_topics: Counter, 
        unique_topics: Counter
    ) -> float:
        """Calculate how well topic distribution is preserved"""
        if not original_topics:
            return 0.0
        
        # Calculate proportion of questions kept per topic
        preservation_scores = []
        for topic, original_count in original_topics.items():
            unique_count = unique_topics.get(topic, 0)
            if original_count > 0:
                preservation_scores.append(unique_count / original_count)
        
        return np.mean(preservation_scores) if preservation_scores else 0.0
    
    def _add_deduplication_metadata(
        self, 
        questions: List[Dict[str, Any]], 
        duplicates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add deduplication metadata to questions"""
        # Count how many duplicates each question had
        duplicate_counts = defaultdict(int)
        for dup in duplicates:
            duplicate_of = dup["duplicate_of"]
            duplicate_counts[duplicate_of] += 1
        
        for question in questions:
            question_id = question["question_id"]
            count = duplicate_counts.get(question_id, 0)
            question["duplicate_count"] = count
            question["is_unique_after_dedup"] = True
        
        return questions
    
    def find_near_duplicates(
        self, 
        questions: List[Dict[str, Any]], 
        threshold: float = 0.75
    ) -> List[Tuple[int, int, float, str]]:
        """
        Find near-duplicate question pairs
        
        Args:
            questions: List of questions
            threshold: Similarity threshold for near-duplicates
            
        Returns:
            List of (index1, index2, similarity, reason) tuples
        """
        near_duplicates = []
        
        # Generate embeddings
        question_texts = [q.get("question_text", "") for q in questions]
        embeddings = self._generate_embeddings(question_texts)
        
        # Compare each pair
        for i in range(len(questions)):
            for j in range(i + 1, len(questions)):
                similarity = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
                
                if threshold <= similarity < self.similarity_threshold:
                    reason = self._get_near_duplicate_reason(questions[i], questions[j], similarity)
                    near_duplicates.append((i, j, similarity, reason))
        
        return near_duplicates
    
    def _get_near_duplicate_reason(
        self, 
        question1: Dict, 
        question2: Dict, 
        similarity: float
    ) -> str:
        """Get reason for near-duplicate classification"""
        reasons = []
        
        # Check question type
        if question1.get("question_type") != question2.get("question_type"):
            reasons.append("different_question_type")
        
        # Check topic
        topic1 = question1.get("normalized_topic", "")
        topic2 = question2.get("normalized_topic", "")
        if topic1 != topic2:
            reasons.append("different_topic")
        
        # Check answer similarity
        answer1 = question1.get("answer", "")
        answer2 = question2.get("answer", "")
        if answer1 and answer2:
            answer_sim = calculate_similarity(answer1, answer2)
            if answer_sim < 0.7:
                reasons.append("different_answers")
        
        if not reasons:
            reasons.append("high_semantic_similarity")
        
        return "; ".join(reasons)
    
    def deduplicate_by_topic(
        self, 
        questions: List[Dict[str, Any]], 
        max_per_topic: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate questions within the same topic
        
        Args:
            questions: List of questions
            max_per_topic: Maximum questions per topic
            
        Returns:
            Deduplicated questions
        """
        # Group questions by topic
        topics = defaultdict(list)
        for question in questions:
            topic = question.get("normalized_topic", "General")
            topics[topic].append(question)
        
        # Select questions from each topic
        selected_questions = []
        
        for topic, topic_questions in topics.items():
            if len(topic_questions) <= max_per_topic:
                selected_questions.extend(topic_questions)
            else:
                # Select diverse questions from this topic
                diverse_questions = self._select_diverse_questions(
                    topic_questions, 
                    max_per_topic
                )
                selected_questions.extend(diverse_questions)
        
        logger.info(f"Topic-based deduplication: Selected {len(selected_questions)} questions")
        return selected_questions
    
    def _select_diverse_questions(
        self, 
        questions: List[Dict], 
        max_count: int
    ) -> List[Dict]:
        """Select diverse questions from a set"""
        if len(questions) <= max_count:
            return questions
        
        # Score questions by quality and diversity
        scored_questions = []
        for question in questions:
            score = self._calculate_question_score(question)
            scored_questions.append((score, question))
        
        # Sort by score (descending)
        scored_questions.sort(key=lambda x: x[0], reverse=True)
        
        # Select diverse questions
        selected = []
        selected_embeddings = []
        
        for score, question in scored_questions:
            if len(selected) >= max_count:
                break
            
            question_text = question.get("question_text", "")
            embedding = embedding_model.embed(question_text)
            
            # Check diversity with already selected questions
            is_diverse = True
            for sel_embedding in selected_embeddings:
                similarity = cosine_similarity([embedding], [sel_embedding])[0][0]
                if similarity > 0.7:  # Too similar to existing question
                    is_diverse = False
                    break
            
            if is_diverse:
                selected.append(question)
                selected_embeddings.append(embedding)
        
        # If we still need more questions, take highest scoring ones
        if len(selected) < max_count:
            remaining = [q for _, q in scored_questions if q not in selected]
            selected.extend(remaining[:max_count - len(selected)])
        
        return selected
    
    def _calculate_question_score(self, question: Dict) -> float:
        """Calculate overall score for question selection"""
        score = 0.0
        
        # Validation score
        validation_score = question.get("validation_score", 0.5)
        score += validation_score * 0.4
        
        # Confidence score
        confidence = question.get("confidence_score", 0.5)
        score += confidence * 0.3
        
        # Question length (moderate length is best)
        text = question.get("question_text", "")
        word_count = len(text.split())
        if 10 <= word_count <= 25:
            score += 0.2
        elif 5 <= word_count < 10 or 25 < word_count <= 40:
            score += 0.1
        
        # Question type diversity bonus
        q_type = question.get("question_type", "")
        if q_type == "short_answer":
            score += 0.1  # Favor short answers for diversity
        
        return min(1.0, score)
    
    def create_deduplication_report(
        self, 
        original_count: int, 
        unique_count: int, 
        duplicates_count: int, 
        stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create deduplication report
        
        Args:
            original_count: Original number of questions
            unique_count: Number of unique questions after deduplication
            duplicates_count: Number of duplicates removed
            stats: Additional statistics
            
        Returns:
            Deduplication report
        """
        report = {
            "summary": {
                "original_question_count": original_count,
                "unique_question_count": unique_count,
                "duplicates_removed": duplicates_count,
                "deduplication_rate": duplicates_count / original_count if original_count > 0 else 0,
                "unique_question_percentage": (unique_count / original_count * 100) if original_count > 0 else 0
            },
            "statistics": stats,
            "impact_analysis": self._analyze_deduplication_impact(
                original_count, 
                unique_count, 
                stats
            ),
            "recommendations": self._generate_deduplication_recommendations(
                duplicates_count, 
                original_count
            )
        }
        
        return report
    
    def _analyze_deduplication_impact(
        self, 
        original_count: int, 
        unique_count: int, 
        stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze the impact of deduplication"""
        if original_count == 0:
            return {"message": "No questions to analyze"}
        
        reduction_rate = 1 - (unique_count / original_count)
        
        impact = {
            "reduction_percentage": reduction_rate * 100,
            "efficiency_gain": f"{reduction_rate:.1%} reduction in question count",
            "topic_coverage_preserved": stats.get("topic_preservation_rate", 0) * 100,
            "quality_impact": "Positive - removed redundant questions" if reduction_rate > 0.1 else "Minimal - few duplicates found"
        }
        
        # Assess if too many questions were removed
        if reduction_rate > 0.5:
            impact["warning"] = "High reduction rate - may have removed too many questions"
        elif reduction_rate < 0.1:
            impact["note"] = "Low reduction rate - good question diversity"
        
        return impact
    
    def _generate_deduplication_recommendations(
        self, 
        duplicates_count: int, 
        original_count: int
    ) -> List[str]:
        """Generate recommendations based on deduplication results"""
        recommendations = []
        
        duplicate_ratio = duplicates_count / original_count if original_count > 0 else 0
        
        if duplicate_ratio > 0.3:
            recommendations.append("Review question generation process to reduce duplicates")
            recommendations.append("Consider increasing diversity in question generation")
        elif duplicate_ratio > 0.1:
            recommendations.append("Moderate duplicate rate - current process is acceptable")
        else:
            recommendations.append("Low duplicate rate - good question diversity")
        
        if duplicates_count > 0:
            recommendations.append(f"Removed {duplicates_count} duplicate questions to improve quality")
        
        return recommendations