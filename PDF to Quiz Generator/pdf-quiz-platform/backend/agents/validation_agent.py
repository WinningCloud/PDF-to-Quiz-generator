import json
from typing import Dict, List, Any, Tuple
import logging
from config.llm_config import llm_client
from config.prompts import SystemPrompts, UserPrompts
from utils.similarity_utils import calculate_similarity

logger = logging.getLogger(__name__)

class ValidationAgent:
    def __init__(self):
        self.system_prompt = SystemPrompts.VALIDATOR_SYSTEM
    
    def validate_question(
        self, 
        question: Dict[str, Any], 
        source_text: str
    ) -> Dict[str, Any]:
        """
        Validate a single question against source text
        
        Args:
            question: Question dictionary
            source_text: Source text from chunk
            
        Returns:
            Validation results
        """
        try:
            prompt = UserPrompts.validate_question(question, source_text)
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            # Add question metadata
            response.update({
                "question_id": question.get("question_id"),
                "chunk_id": question.get("chunk_id"),
                "page_number": question.get("page_number"),
                "validation_timestamp": "now"
            })
            
            logger.info(f"Validated question: {question.get('question_id')}")
            return response
            
        except Exception as e:
            logger.error(f"Error validating question: {e}")
            return self._basic_validation(question, source_text)
    
    def validate_questions_batch(
        self, 
        questions: List[Dict[str, Any]], 
        chunks_data: Dict[str, str]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Validate multiple questions
        
        Args:
            questions: List of question dictionaries
            chunks_data: Dictionary mapping chunk_id to text
            
        Returns:
            Tuple of (validated_questions, failed_questions)
        """
        validated_questions = []
        failed_questions = []
        
        for question in questions:
            chunk_id = question.get("chunk_id")
            source_text = chunks_data.get(chunk_id, "")
            
            if not source_text:
                logger.warning(f"No source text found for chunk {chunk_id}")
                question["validation_status"] = "failed"
                question["validation_reason"] = "No source text available"
                failed_questions.append(question)
                continue
            
            validation_result = self.validate_question(question, source_text)
            
            # Check if question passed validation
            is_answerable = validation_result.get("is_answerable", False)
            answer_correctness = validation_result.get("answer_correctness_score", 0)
            overall_score = validation_result.get("overall_score", 0)
            
            threshold = 0.7  # Minimum validation score
            
            if is_answerable and overall_score >= threshold and answer_correctness >= 0.8:
                # Question passed validation
                question.update({
                    "validation_status": "validated",
                    "validation_score": overall_score,
                    "answer_correctness": answer_correctness,
                    "is_answerable": True,
                    "validation_feedback": validation_result.get("feedback", ""),
                    "clarity_score": validation_result.get("clarity_score", 0.5),
                    "difficulty_appropriate": validation_result.get("difficulty_appropriate", True)
                })
                validated_questions.append(question)
            else:
                # Question failed validation
                question.update({
                    "validation_status": "failed",
                    "validation_score": overall_score,
                    "validation_reason": validation_result.get("feedback", "Failed validation criteria"),
                    "is_answerable": is_answerable,
                    "answer_correctness": answer_correctness
                })
                failed_questions.append(question)
        
        logger.info(f"Validated {len(validated_questions)} questions, failed {len(failed_questions)}")
        return validated_questions, failed_questions
    
    def cross_reference_answer(
        self, 
        question: Dict[str, Any], 
        source_text: str
    ) -> Dict[str, Any]:
        """
        Cross-reference answer with source text using similarity
        
        Args:
            question: Question dictionary
            source_text: Source text
            
        Returns:
            Cross-reference results
        """
        answer = question.get("answer", "")
        question_text = question.get("question_text", "")
        
        # Calculate answer-source similarity
        answer_similarity = calculate_similarity(answer, source_text)
        
        # Calculate question-source relevance
        question_similarity = calculate_similarity(question_text, source_text)
        
        # Check if answer can be inferred from source
        can_be_inferred = self._check_answer_inference(answer, source_text)
        
        return {
            "answer_source_similarity": answer_similarity,
            "question_source_relevance": question_similarity,
            "answer_in_source": answer_similarity > 0.3,
            "can_be_inferred": can_be_inferred,
            "confidence": min(1.0, (answer_similarity + question_similarity) / 2)
        }
    
    def check_ambiguity(
        self, 
        question: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check question for ambiguity
        
        Args:
            question: Question dictionary
            
        Returns:
            Ambiguity analysis
        """
        question_text = question.get("question_text", "")
        options = question.get("options", [])
        answer = question.get("answer", "")
        
        ambiguity_issues = []
        
        # Check for vague terms
        vague_terms = ["often", "sometimes", "usually", "generally", "might", "could", "possibly"]
        for term in vague_terms:
            if term in question_text.lower():
                ambiguity_issues.append(f"Vague term '{term}' used")
        
        # Check for double negatives
        negations = ["not", "no", "never", "none"]
        negation_count = sum(1 for neg in negations if neg in question_text.lower())
        if negation_count > 1:
            ambiguity_issues.append("Multiple negations causing confusion")
        
        # For MCQs, check option quality
        if question.get("question_type") == "mcq" and options:
            # Check if answer is in options
            if answer not in options:
                ambiguity_issues.append("Correct answer not in options")
            
            # Check for similar options
            option_similarities = []
            for i in range(len(options)):
                for j in range(i+1, len(options)):
                    sim = calculate_similarity(options[i], options[j])
                    if sim > 0.8:
                        ambiguity_issues.append(f"Options {i+1} and {j+1} are too similar")
        
        # Check question clarity
        clarity_score = self._calculate_clarity(question_text)
        
        return {
            "ambiguity_issues": ambiguity_issues,
            "clarity_score": clarity_score,
            "is_ambiguous": len(ambiguity_issues) > 0 or clarity_score < 0.6,
            "issue_count": len(ambiguity_issues),
            "recommendations": self._get_ambiguity_recommendations(ambiguity_issues)
        }
    
    def validate_difficulty_level(
        self, 
        question: Dict[str, Any], 
        source_text: str
    ) -> Dict[str, Any]:
        """
        Validate if difficulty level matches question content
        
        Args:
            question: Question dictionary
            source_text: Source text
            
        Returns:
            Difficulty validation results
        """
        claimed_difficulty = question.get("difficulty", "medium")
        
        # Calculate actual difficulty factors
        text_complexity = self._calculate_text_complexity(source_text)
        question_complexity = self._calculate_question_complexity(question)
        answer_complexity = self._calculate_answer_complexity(question.get("answer", ""))
        
        # Determine actual difficulty
        overall_complexity = (text_complexity + question_complexity + answer_complexity) / 3
        
        if overall_complexity < 0.3:
            actual_difficulty = "easy"
        elif overall_complexity < 0.7:
            actual_difficulty = "medium"
        else:
            actual_difficulty = "hard"
        
        # Check match
        difficulty_match = (claimed_difficulty == actual_difficulty)
        
        return {
            "claimed_difficulty": claimed_difficulty,
            "calculated_difficulty": actual_difficulty,
            "difficulty_match": difficulty_match,
            "text_complexity": text_complexity,
            "question_complexity": question_complexity,
            "answer_complexity": answer_complexity,
            "overall_complexity": overall_complexity,
            "recommendation": f"Change to {actual_difficulty}" if not difficulty_match else "Keep as is"
        }
    
    def _basic_validation(self, question: Dict, source_text: str) -> Dict[str, Any]:
        """Basic validation fallback"""
        answer = question.get("answer", "")
        
        # Simple check: is answer in source text?
        answer_in_text = answer.lower() in source_text.lower() if answer else False
        
        # Calculate simple similarity
        answer_similarity = 0.0
        if answer and source_text:
            words_in_common = len(set(answer.lower().split()) & set(source_text.lower().split()))
            total_words = len(set(answer.lower().split()) | set(source_text.lower().split()))
            answer_similarity = words_in_common / total_words if total_words > 0 else 0
        
        return {
            "is_answerable": answer_in_text or answer_similarity > 0.3,
            "answer_correctness_score": 0.7 if answer_in_text else answer_similarity,
            "clarity_score": 0.5,
            "difficulty_appropriate": True,
            "overall_score": 0.6 if answer_in_text else 0.4,
            "feedback": "Basic validation performed",
            "validation_method": "fallback"
        }
    
    def _check_answer_inference(self, answer: str, source_text: str) -> bool:
        """Check if answer can be inferred from source text"""
        # Simple inference check
        answer_keywords = set(answer.lower().split()[:5])  # First 5 words as keywords
        source_words = set(source_text.lower().split())
        
        # Check if at least 2 keywords are in source
        matches = len(answer_keywords & source_words)
        return matches >= 2
    
    def _calculate_clarity(self, text: str) -> float:
        """Calculate clarity score of text"""
        # Simple clarity calculation
        words = text.split()
        if not words:
            return 0.0
        
        # Count complex words (more than 3 syllables)
        complex_words = 0
        for word in words:
            if len(word) > 8:  # Simple proxy for complexity
                complex_words += 1
        
        clarity = 1.0 - (complex_words / len(words))
        return max(0.1, min(1.0, clarity))
    
    def _calculate_text_complexity(self, text: str) -> float:
        """Calculate text complexity"""
        words = text.split()
        if not words:
            return 0.0
        
        # Average word length
        avg_word_len = sum(len(w) for w in words) / len(words)
        
        # Sentence count
        sentences = text.count('.') + text.count('!') + text.count('?')
        words_per_sentence = len(words) / max(1, sentences)
        
        # Complexity formula
        complexity = (avg_word_len / 10) * 0.3 + (words_per_sentence / 30) * 0.7
        return min(1.0, complexity)
    
    def _calculate_question_complexity(self, question: Dict) -> float:
        """Calculate question complexity"""
        question_text = question.get("question_text", "")
        options = question.get("options", [])
        q_type = question.get("question_type", "")
        
        base_complexity = self._calculate_text_complexity(question_text)
        
        # Adjust for question type
        if q_type == "mcq" and len(options) >= 4:
            base_complexity *= 0.8  # MCQs are generally easier
        
        # Adjust for question length
        word_count = len(question_text.split())
        if word_count > 25:
            base_complexity *= 1.2
        
        return min(1.0, base_complexity)
    
    def _calculate_answer_complexity(self, answer: str) -> float:
        """Calculate answer complexity"""
        return self._calculate_text_complexity(answer)
    
    def _get_ambiguity_recommendations(self, issues: List[str]) -> List[str]:
        """Get recommendations for fixing ambiguity issues"""
        recommendations = []
        
        for issue in issues:
            if "Vague term" in issue:
                recommendations.append("Replace vague terms with specific language")
            elif "Multiple negations" in issue:
                recommendations.append("Simplify sentence structure, avoid double negatives")
            elif "Correct answer not in options" in issue:
                recommendations.append("Add correct answer to options or verify answer")
            elif "too similar" in issue:
                recommendations.append("Make options more distinct")
        
        if not recommendations:
            recommendations.append("Question is clear and unambiguous")
        
        return recommendations