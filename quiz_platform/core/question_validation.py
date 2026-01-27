import json
from typing import Dict, List, Any, Tuple
import logging
from quiz_platform.config.llm_config import llm_client
from quiz_platform.config.prompts import SystemPrompts, UserPrompts
from quiz_platform.utils.similarity_utils import calculate_similarity

logger = logging.getLogger(__name__)

class QuestionValidator:
    def __init__(self, validation_threshold: float = 0.7):
        """
        Initialize question validator
        
        Args:
            validation_threshold: Minimum score for validation
        """
        self.validation_threshold = validation_threshold
    
    def validate_question_batch(
        self, 
        questions: List[Dict[str, Any]], 
        chunks: List[Dict[str, Any]]
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Validate a batch of questions against source chunks
        
        Args:
            questions: List of question dictionaries
            chunks: List of chunk dictionaries (source text)
            
        Returns:
            Tuple of (valid_questions, needs_review, invalid_questions)
        """
        valid_questions = []
        needs_review = []
        invalid_questions = []
        
        # Create chunk lookup
        chunk_dict = {chunk["chunk_id"]: chunk for chunk in chunks}
        
        for question in questions:
            chunk_id = question.get("chunk_id")
            source_chunk = chunk_dict.get(chunk_id)
            
            if not source_chunk:
                logger.warning(f"Source chunk not found for question {question.get('question_id')}")
                question["validation_status"] = "failed"
                question["validation_reason"] = "Source chunk not found"
                invalid_questions.append(question)
                continue
            
            source_text = source_chunk.get("text", "")
            validation_result = self.validate_single_question(question, source_text)
            
            # Classify based on validation score
            validation_score = validation_result.get("overall_score", 0)
            
            if validation_score >= self.validation_threshold:
                question["validation_status"] = "validated"
                question["validation_score"] = validation_score
                question["validation_details"] = validation_result
                valid_questions.append(question)
            elif validation_score >= 0.5:  # Needs review
                question["validation_status"] = "needs_review"
                question["validation_score"] = validation_score
                question["validation_details"] = validation_result
                question["validation_issues"] = validation_result.get("issues", [])
                needs_review.append(question)
            else:  # Invalid
                question["validation_status"] = "failed"
                question["validation_score"] = validation_score
                question["validation_details"] = validation_result
                question["validation_issues"] = validation_result.get("issues", [])
                invalid_questions.append(question)
        
        logger.info(f"Validation complete: {len(valid_questions)} valid, "
                   f"{len(needs_review)} need review, {len(invalid_questions)} invalid")
        
        return valid_questions, needs_review, invalid_questions
    
    def validate_single_question(
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
            # First, perform quick checks
            quick_checks = self._perform_quick_checks(question, source_text)
            
            if not quick_checks["passed"]:
                return {
                    "overall_score": 0.3,
                    "passed_quick_checks": False,
                    "issues": quick_checks["issues"],
                    "validation_method": "quick_check_failed"
                }
            
            # Then, perform comprehensive validation with LLM
            llm_validation = self._validate_with_llm(question, source_text)
            
            # Combine results
            overall_score = self._calculate_overall_score(quick_checks, llm_validation)
            
            validation_result = {
                "overall_score": overall_score,
                "passed_quick_checks": True,
                "quick_checks": quick_checks,
                "llm_validation": llm_validation,
                "is_answerable": llm_validation.get("is_answerable", False),
                "answer_correctness": llm_validation.get("answer_correctness_score", 0),
                "clarity_score": llm_validation.get("clarity_score", 0),
                "difficulty_match": llm_validation.get("difficulty_appropriate", False),
                "issues": llm_validation.get("issues", []),
                "recommendations": llm_validation.get("recommendations", []),
                "validation_method": "comprehensive"
            }
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating question: {e}")
            return {
                "overall_score": 0.0,
                "error": str(e),
                "validation_method": "failed"
            }
    
    def _perform_quick_checks(
        self, 
        question: Dict[str, Any], 
        source_text: str
    ) -> Dict[str, Any]:
        """
        Perform quick validation checks
        
        Args:
            question: Question dictionary
            source_text: Source text
            
        Returns:
            Quick check results
        """
        issues = []
        checks_passed = 0
        total_checks = 0
        
        # Check 1: Question text not empty
        total_checks += 1
        question_text = question.get("question_text", "")
        if not question_text or len(question_text.strip()) < 10:
            issues.append("Question text too short or empty")
        else:
            checks_passed += 1
        
        # Check 2: Answer not empty
        total_checks += 1
        answer = question.get("answer", "")
        if not answer or len(answer.strip()) < 2:
            issues.append("Answer too short or empty")
        else:
            checks_passed += 1
        
        # Check 3: For MCQs, check options
        if question.get("question_type") == "mcq":
            total_checks += 1
            options = question.get("options", [])
            if len(options) < 4:
                issues.append(f"MCQ has only {len(options)} options (need 4)")
            else:
                checks_passed += 1
            
            # Check if answer is in options
            total_checks += 1
            if answer not in options:
                issues.append("Correct answer not in options")
            else:
                checks_passed += 1
        
        # Check 4: Answer similarity to source
        total_checks += 1
        if answer and source_text:
            similarity = calculate_similarity(answer, source_text)
            if similarity < 0.1:  # Very low similarity
                issues.append(f"Answer has low similarity to source ({similarity:.2f})")
            else:
                checks_passed += 1
        
        # Check 5: Question similarity to source
        total_checks += 1
        if question_text and source_text:
            similarity = calculate_similarity(question_text, source_text)
            if similarity < 0.05:  # Very low similarity
                issues.append(f"Question has low relevance to source ({similarity:.2f})")
            else:
                checks_passed += 1
        
        quick_check_score = checks_passed / total_checks if total_checks > 0 else 0
        
        return {
            "passed": quick_check_score >= 0.7,
            "score": quick_check_score,
            "checks_passed": checks_passed,
            "total_checks": total_checks,
            "issues": issues
        }
    
    def _validate_with_llm(
        self, 
        question: Dict[str, Any], 
        source_text: str
    ) -> Dict[str, Any]:
        """
        Validate question using LLM
        
        Args:
            question: Question dictionary
            source_text: Source text
            
        Returns:
            LLM validation results
        """
        try:
            prompt = UserPrompts.validate_question(question, source_text)
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt=SystemPrompts.VALIDATOR_SYSTEM
            )
            
            return response
            
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            return self._validate_with_rules(question, source_text)
    
    def _validate_with_rules(
        self, 
        question: Dict[str, Any], 
        source_text: str
    ) -> Dict[str, Any]:
        """
        Rule-based validation fallback
        
        Args:
            question: Question dictionary
            source_text: Source text
            
        Returns:
            Rule-based validation results
        """
        issues = []
        recommendations = []
        
        # Check answer presence in source
        answer = question.get("answer", "")
        answer_in_source = answer.lower() in source_text.lower() if answer else False
        
        # Check question clarity
        question_text = question.get("question_text", "")
        clarity_score = self._calculate_clarity_score(question_text)
        
        # Check for ambiguity
        is_ambiguous = self._check_ambiguity(question_text)
        if is_ambiguous:
            issues.append("Question may be ambiguous")
            recommendations.append("Clarify the question wording")
        
        # Check difficulty appropriateness
        difficulty = question.get("difficulty", "medium")
        difficulty_score = self._assess_difficulty(question, source_text)
        
        # Calculate overall score
        overall_score = (
            (1.0 if answer_in_source else 0.4) * 0.4 +
            clarity_score * 0.3 +
            difficulty_score * 0.2 +
            (0.8 if not is_ambiguous else 0.4) * 0.1
        )
        
        return {
            "is_answerable": answer_in_source,
            "answer_correctness_score": 1.0 if answer_in_source else 0.4,
            "clarity_score": clarity_score,
            "difficulty_appropriate": difficulty_score > 0.6,
            "overall_score": overall_score,
            "issues": issues,
            "recommendations": recommendations,
            "validation_method": "rule_based"
        }
    
    def _calculate_clarity_score(self, text: str) -> float:
        """Calculate clarity score of text"""
        if not text:
            return 0.0
        
        # Simple clarity heuristics
        score = 1.0
        
        # Penalize long sentences
        sentences = text.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_sentence_length > 25:
            score *= 0.8
        
        # Penalize complex words (more than 3 syllables)
        complex_words = self._count_complex_words(text)
        word_count = len(text.split())
        complex_ratio = complex_words / word_count if word_count > 0 else 0
        
        if complex_ratio > 0.3:
            score *= 0.7
        
        # Penalize passive voice
        passive_indicators = [" is ", " was ", " were ", " has been ", " have been "]
        passive_count = sum(text.lower().count(indicator) for indicator in passive_indicators)
        if passive_count > 2:
            score *= 0.9
        
        return max(0.1, min(1.0, score))
    
    def _count_complex_words(self, text: str) -> int:
        """Count complex words (simplified)"""
        words = text.lower().split()
        complex_count = 0
        
        for word in words:
            # Simple heuristic: long words are complex
            if len(word) > 8 and '-' not in word:
                complex_count += 1
        
        return complex_count
    
    def _check_ambiguity(self, text: str) -> bool:
        """Check if text is ambiguous"""
        ambiguity_indicators = [
            "might", "could", "possibly", "perhaps", "maybe",
            "sometimes", "often", "usually", "generally",
            "various", "several", "multiple", "some"
        ]
        
        text_lower = text.lower()
        indicator_count = sum(text_lower.count(indicator) for indicator in ambiguity_indicators)
        
        return indicator_count > 2
    
    def _assess_difficulty(
        self, 
        question: Dict[str, Any], 
        source_text: str
    ) -> float:
        """Assess if difficulty level is appropriate"""
        claimed_difficulty = question.get("difficulty", "medium")
        
        # Simple assessment based on text complexity
        question_complexity = self._calculate_text_complexity(question.get("question_text", ""))
        answer_complexity = self._calculate_text_complexity(question.get("answer", ""))
        source_complexity = self._calculate_text_complexity(source_text)
        
        avg_complexity = (question_complexity + answer_complexity + source_complexity) / 3
        
        # Map complexity to difficulty
        if avg_complexity < 0.3:
            appropriate_difficulty = "easy"
        elif avg_complexity < 0.7:
            appropriate_difficulty = "medium"
        else:
            appropriate_difficulty = "hard"
        
        # Score based on match
        if claimed_difficulty == appropriate_difficulty:
            return 1.0
        elif (claimed_difficulty == "easy" and appropriate_difficulty == "medium") or \
             (claimed_difficulty == "hard" and appropriate_difficulty == "medium"):
            return 0.7
        else:
            return 0.4
    
    def _calculate_text_complexity(self, text: str) -> float:
        """Calculate text complexity score"""
        if not text:
            return 0.0
        
        words = text.split()
        if not words:
            return 0.0
        
        # Average word length
        avg_word_len = sum(len(w) for w in words) / len(words)
        
        # Sentence complexity
        sentences = text.count('.') + text.count('!') + text.count('?')
        words_per_sentence = len(words) / max(1, sentences)
        
        # Complex word ratio
        complex_words = self._count_complex_words(text)
        complex_ratio = complex_words / len(words)
        
        # Calculate overall complexity
        complexity = (
            (avg_word_len / 10) * 0.3 +
            (words_per_sentence / 30) * 0.4 +
            complex_ratio * 0.3
        )
        
        return min(1.0, complexity)
    
    def _calculate_overall_score(
        self, 
        quick_checks: Dict[str, Any], 
        llm_validation: Dict[str, Any]
    ) -> float:
        """Calculate overall validation score"""
        quick_score = quick_checks.get("score", 0)
        llm_score = llm_validation.get("overall_score", 0)
        
        # Weight quick checks more if they failed
        if quick_score < 0.7:
            return quick_score * 0.7 + llm_score * 0.3
        else:
            return quick_score * 0.3 + llm_score * 0.7
    
    def regenerate_failed_questions(
        self, 
        invalid_questions: List[Dict[str, Any]], 
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Regenerate questions that failed validation
        
        Args:
            invalid_questions: List of invalid questions
            chunks: List of source chunks
            
        Returns:
            Regenerated questions
        """
        regenerated_questions = []
        
        chunk_dict = {chunk["chunk_id"]: chunk for chunk in chunks}
        
        for question in invalid_questions:
            chunk_id = question.get("chunk_id")
            chunk = chunk_dict.get(chunk_id)
            
            if not chunk:
                continue
            
            source_text = chunk.get("text", "")
            subtopic = question.get("subtopic", "General")
            
            # Try to regenerate with different approach
            regenerated = self._regenerate_single_question(
                source_text, 
                subtopic, 
                question.get("difficulty", "medium"),
                chunk_id,
                chunk.get("page_number", 1)
            )
            
            if regenerated:
                regenerated_questions.append(regenerated)
        
        logger.info(f"Regenerated {len(regenerated_questions)} questions")
        return regenerated_questions
    
    def _regenerate_single_question(
        self, 
        source_text: str, 
        subtopic: str, 
        difficulty: str, 
        chunk_id: str, 
        page_number: int
    ) -> Dict[str, Any]:
        """Regenerate a single question"""
        try:
            prompt = f"""Generate a different {difficulty} difficulty question about '{subtopic}' from this text:

            Text:
            {source_text[:1000]}

            Previous question had validation issues. Generate a new question that:
            1. Is clearly answerable from the text
            2. Has unambiguous answer
            3. Is at appropriate difficulty level
            4. Tests understanding, not just recall
            
            Return as JSON with question_text, answer, explanation, and question_type."""
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt=SystemPrompts.QUESTION_GENERATOR_SYSTEM
            )
            
            response.update({
                "question_id": f"{chunk_id}_regenerated",
                "chunk_id": chunk_id,
                "page_number": page_number,
                "subtopic": subtopic,
                "difficulty": difficulty,
                "generation_source": "regenerated",
                "validation_status": "pending",
                "confidence_score": 0.6
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to regenerate question: {e}")
            return None
    
    def create_validation_report(
        self, 
        valid_questions: List[Dict], 
        needs_review: List[Dict], 
        invalid_questions: List[Dict]
    ) -> Dict[str, Any]:
        """
        Create validation report
        
        Args:
            valid_questions: List of valid questions
            needs_review: List of questions needing review
            invalid_questions: List of invalid questions
            
        Returns:
            Validation report
        """
        total_questions = len(valid_questions) + len(needs_review) + len(invalid_questions)
        
        if total_questions == 0:
            return {
                "total_questions": 0,
                "validation_rate": 0.0,
                "quality_score": 0.0,
                "summary": "No questions to validate"
            }
        
        # Calculate statistics
        validation_rate = len(valid_questions) / total_questions
        
        # Calculate average validation scores
        valid_scores = [q.get("validation_score", 0) for q in valid_questions]
        review_scores = [q.get("validation_score", 0) for q in needs_review]
        
        avg_valid_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
        avg_review_score = sum(review_scores) / len(review_scores) if review_scores else 0
        
        # Calculate quality score
        quality_score = (
            validation_rate * 0.6 +
            avg_valid_score * 0.3 +
            (1.0 - (len(invalid_questions) / total_questions)) * 0.1
        )
        
        # Issue analysis
        all_issues = []
        for question in needs_review + invalid_questions:
            issues = question.get("validation_issues", [])
            all_issues.extend(issues)
        
        issue_counter = {}
        for issue in all_issues:
            issue_counter[issue] = issue_counter.get(issue, 0) + 1
        
        # Common issue types
        common_issues = sorted(issue_counter.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_questions": total_questions,
            "valid_count": len(valid_questions),
            "needs_review_count": len(needs_review),
            "invalid_count": len(invalid_questions),
            "validation_rate": validation_rate,
            "average_valid_score": avg_valid_score,
            "average_review_score": avg_review_score,
            "quality_score": quality_score,
            "quality_rating": self._get_quality_rating(quality_score),
            "common_issues": common_issues,
            "issue_summary": self._summarize_issues(common_issues),
            "recommendations": self._generate_recommendations(
                validation_rate, 
                common_issues
            )
        }
    
    def _get_quality_rating(self, score: float) -> str:
        """Get quality rating from score"""
        if score >= 0.8:
            return "Excellent"
        elif score >= 0.7:
            return "Good"
        elif score >= 0.6:
            return "Fair"
        else:
            return "Needs Improvement"
    
    def _summarize_issues(self, common_issues: List[Tuple[str, int]]) -> str:
        """Summarize common issues"""
        if not common_issues:
            return "No significant issues found"
        
        summaries = []
        for issue, count in common_issues[:3]:
            summaries.append(f"{issue} ({count} occurrences)")
        
        return "; ".join(summaries)
    
    def _generate_recommendations(
        self, 
        validation_rate: float, 
        common_issues: List[Tuple[str, int]]
    ) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        if validation_rate < 0.7:
            recommendations.append("Improve question generation to increase validation rate")
        
        for issue, count in common_issues[:3]:
            if "similarity" in issue.lower():
                recommendations.append("Ensure answers are directly supported by source text")
            elif "ambiguous" in issue.lower():
                recommendations.append("Clarify question wording to reduce ambiguity")
            elif "difficulty" in issue.lower():
                recommendations.append("Review and adjust difficulty levels")
            elif "options" in issue.lower():
                recommendations.append("Ensure MCQs have 4 distinct options with correct answer included")
        
        if not recommendations:
            recommendations.append("Maintain current quality standards")
        
        return recommendations