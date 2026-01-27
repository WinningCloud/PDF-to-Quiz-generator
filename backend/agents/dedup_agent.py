import json
from typing import Dict, List, Any, Tuple, Set
import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from config.llm_config import embedding_model
from config.prompts import SystemPrompts, UserPrompts
from utils.similarity_utils import calculate_similarity, jaccard_similarity

logger = logging.getLogger(__name__)

class DeduplicationAgent:
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.system_prompt = SystemPrompts.DEDUP_SYSTEM
    
    def deduplicate_questions(
        self, 
        questions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Remove duplicate or highly similar questions
        
        Args:
            questions: List of question dictionaries
            
        Returns:
            Tuple of (unique_questions, duplicates)
        """
        if len(questions) <= 1:
            return questions, []
        
        # Generate embeddings for all questions
        question_texts = [q.get("question_text", "") for q in questions]
        question_embeddings = embedding_model.embed_batch(question_texts)
        
        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(question_embeddings)
        
        # Find duplicates
        unique_indices = []
        duplicate_indices = []
        processed = set()
        
        for i in range(len(questions)):
            if i in processed:
                continue
            
            unique_indices.append(i)
            processed.add(i)
            
            # Find similar questions to i
            for j in range(i + 1, len(questions)):
                if j in processed:
                    continue
                
                similarity = similarity_matrix[i][j]
                
                # Check if questions are similar enough to be duplicates
                if similarity >= self.similarity_threshold:
                    # Additional semantic check
                    if self._are_questions_semantic_duplicates(questions[i], questions[j]):
                        duplicate_indices.append(j)
                        processed.add(j)
                        logger.info(f"Found duplicate: {j} similar to {i} (score: {similarity:.3f})")
        
        # Separate unique and duplicate questions
        unique_questions = [questions[i] for i in unique_indices]
        duplicate_questions = [questions[i] for i in duplicate_indices]
        
        # Add deduplication metadata
        for i, question in enumerate(unique_questions):
            question["is_unique"] = True
            question["duplicate_count"] = 0
        
        for question in duplicate_questions:
            question["is_unique"] = False
            question["duplicate_of"] = "similar_question"
        
        logger.info(f"Deduplication: {len(unique_questions)} unique, {len(duplicate_questions)} duplicates")
        return unique_questions, duplicate_questions
    
    def find_semantic_duplicates(
        self, 
        question1: Dict[str, Any], 
        question2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if two questions are semantic duplicates
        
        Args:
            question1: First question
            question2: Second question
            
        Returns:
            Duplicate analysis results
        """
        # Get question texts
        text1 = question1.get("question_text", "")
        text2 = question2.get("question_text", "")
        
        # Calculate multiple similarity metrics
        embedding_similarity = self._calculate_embedding_similarity(text1, text2)
        jaccard_sim = jaccard_similarity(text1, text2)
        word_overlap = self._calculate_word_overlap(text1, text2)
        
        # Check answer similarity
        answer1 = question1.get("answer", "")
        answer2 = question2.get("answer", "")
        answer_similarity = calculate_similarity(answer1, answer2) if answer1 and answer2 else 0
        
        # Check if they test the same concept
        same_concept = self._check_same_concept(question1, question2)
        
        # Calculate overall duplicate score
        duplicate_score = (
            embedding_similarity * 0.4 +
            jaccard_sim * 0.2 +
            word_overlap * 0.2 +
            answer_similarity * 0.1 +
            (1.0 if same_concept else 0.0) * 0.1
        )
        
        is_duplicate = duplicate_score >= self.similarity_threshold
        
        return {
            "is_duplicate": is_duplicate,
            "duplicate_score": duplicate_score,
            "embedding_similarity": embedding_similarity,
            "jaccard_similarity": jaccard_sim,
            "word_overlap": word_overlap,
            "answer_similarity": answer_similarity,
            "tests_same_concept": same_concept,
            "reasoning": self._get_duplicate_reasoning(
                is_duplicate, embedding_similarity, same_concept
            )
        }
    
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
        if not questions:
            return []
        
        # Group questions by topic
        topics = {}
        for question in questions:
            topic = question.get("normalized_topic", "General")
            if topic not in topics:
                topics[topic] = []
            topics[topic].append(question)
        
        # Select best questions from each topic
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
        
        # Update topic distribution
        topic_distribution = {}
        for question in selected_questions:
            topic = question.get("normalized_topic", "General")
            topic_distribution[topic] = topic_distribution.get(topic, 0) + 1
        
        logger.info(f"Topic-based deduplication: Selected {len(selected_questions)} questions")
        logger.info(f"Topic distribution: {topic_distribution}")
        
        return selected_questions
    
    def find_near_duplicates(
        self, 
        questions: List[Dict[str, Any]], 
        threshold: float = 0.75
    ) -> List[Tuple[int, int, float]]:
        """
        Find near-duplicate question pairs
        
        Args:
            questions: List of questions
            threshold: Similarity threshold for near-duplicates
            
        Returns:
            List of (index1, index2, similarity) tuples
        """
        near_duplicates = []
        
        # Generate embeddings
        question_texts = [q.get("question_text", "") for q in questions]
        embeddings = embedding_model.embed_batch(question_texts)
        
        # Compare each pair
        for i in range(len(questions)):
            for j in range(i + 1, len(questions)):
                similarity = cosine_similarity(
                    [embeddings[i]], 
                    [embeddings[j]]
                )[0][0]
                
                if threshold <= similarity < self.similarity_threshold:
                    near_duplicates.append((i, j, similarity))
        
        return near_duplicates
    
    def _calculate_embedding_similarity(
        self, 
        text1: str, 
        text2: str
    ) -> float:
        """Calculate embedding similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        embedding1 = embedding_model.embed(text1)
        embedding2 = embedding_model.embed(text2)
        
        similarity = cosine_similarity([embedding1], [embedding2])[0][0]
        return float(similarity)
    
    def _calculate_word_overlap(
        self, 
        text1: str, 
        text2: str
    ) -> float:
        """Calculate word overlap between two texts"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _check_same_concept(
        self, 
        question1: Dict, 
        question2: Dict
    ) -> bool:
        """Check if two questions test the same concept"""
        # Check subtopic
        subtopic1 = question1.get("subtopic", "").lower()
        subtopic2 = question2.get("subtopic", "").lower()
        
        if subtopic1 and subtopic2:
            if subtopic1 == subtopic2:
                return True
            
            # Check if one subtopic contains the other
            if subtopic1 in subtopic2 or subtopic2 in subtopic1:
                return True
        
        # Check normalized topic
        topic1 = question1.get("normalized_topic", "").lower()
        topic2 = question2.get("normalized_topic", "").lower()
        
        if topic1 and topic2 and topic1 == topic2:
            return True
        
        # Check keywords overlap
        text1 = question1.get("question_text", "").lower()
        text2 = question2.get("question_text", "").lower()
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        # Remove common words
        common_words = {"the", "and", "is", "in", "to", "of", "a", "that", "it", "with"}
        keywords1 = words1 - common_words
        keywords2 = words2 - common_words
        
        # Check if they share significant keywords
        shared_keywords = keywords1 & keywords2
        if len(shared_keywords) >= 2:  # At least 2 significant keywords in common
            return True
        
        return False
    
    def _are_questions_semantic_duplicates(
        self, 
        question1: Dict, 
        question2: Dict
    ) -> bool:
        """Check if questions are semantic duplicates using multiple criteria"""
        # Quick checks first
        if question1.get("question_type") != question2.get("question_type"):
            return False
        
        # Check if answers are very different
        answer1 = question1.get("answer", "")
        answer2 = question2.get("answer", "")
        
        if answer1 and answer2:
            answer_sim = calculate_similarity(answer1, answer2)
            if answer_sim < 0.3:  # Very different answers
                return False
        
        # Perform comprehensive duplicate check
        duplicate_analysis = self.find_semantic_duplicates(question1, question2)
        return duplicate_analysis["is_duplicate"]
    
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
    
    def _get_duplicate_reasoning(
        self, 
        is_duplicate: bool, 
        similarity: float, 
        same_concept: bool
    ) -> str:
        """Get reasoning for duplicate decision"""
        if is_duplicate:
            reasons = []
            if similarity >= 0.9:
                reasons.append("Very high semantic similarity")
            elif similarity >= 0.85:
                reasons.append("High semantic similarity")
            
            if same_concept:
                reasons.append("Tests the same core concept")
            
            return f"Duplicate: {', '.join(reasons)}"
        else:
            reasons = []
            if similarity < 0.7:
                reasons.append("Low semantic similarity")
            if not same_concept:
                reasons.append("Different concepts tested")
            
            return f"Not duplicate: {', '.join(reasons)}"