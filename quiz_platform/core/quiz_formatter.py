import json
import random
from typing import Dict, List, Any, Tuple
import logging
from datetime import datetime
import hashlib
from config.llm_config import llm_client

logger = logging.getLogger(__name__)

class QuizFormatter:
    def __init__(self):
        self.question_types = ["mcq", "short_answer"]
    
    def format_quiz(
        self, 
        questions: List[Dict[str, Any]], 
        quiz_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Format questions into a complete quiz
        
        Args:
            questions: List of validated questions
            quiz_config: Quiz configuration (optional)
            
        Returns:
            Formatted quiz structure
        """
        if not questions:
            return self._create_empty_quiz()
        
        # Apply default config if not provided
        if not quiz_config:
            quiz_config = self._get_default_config()
        
        try:
            # Sort and select questions based on config
            selected_questions = self._select_questions(questions, quiz_config)
            
            # Apply question order
            ordered_questions = self._apply_question_order(selected_questions, quiz_config)
            
            # Create quiz sections
            quiz_sections = self._create_quiz_sections(ordered_questions)
            
            # Generate quiz metadata
            quiz_metadata = self._generate_quiz_metadata(ordered_questions, quiz_config)
            
            # Calculate statistics
            quiz_stats = self._calculate_quiz_statistics(ordered_questions)
            
            # Create different output formats
            output_formats = {
                "internal": self._format_for_internal(ordered_questions, quiz_metadata),
                "student": self._format_for_student(ordered_questions, quiz_metadata),
                "admin": self._format_for_admin(ordered_questions, quiz_metadata)
            }
            
            quiz = {
                "id": self._generate_quiz_id(),
                "metadata": quiz_metadata,
                "sections": quiz_sections,
                "questions": ordered_questions,
                "statistics": quiz_stats,
                "formats": output_formats,
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
            
            logger.info(f"Formatted quiz with {len(ordered_questions)} questions")
            return quiz
            
        except Exception as e:
            logger.error(f"Error formatting quiz: {e}")
            return self._format_fallback_quiz(questions, quiz_config)
    
    def _select_questions(
        self, 
        questions: List[Dict], 
        config: Dict[str, Any]
    ) -> List[Dict]:
        """Select questions based on configuration"""
        max_questions = config.get("max_questions", 20)
        
        if len(questions) <= max_questions:
            return questions
        
        # Apply selection criteria
        selected = []
        
        # 1. Ensure topic coverage
        topic_distribution = config.get("topic_distribution", {})
        if topic_distribution:
            selected = self._select_by_topic_distribution(questions, topic_distribution, max_questions)
        
        # 2. If not enough questions from topic distribution, add random ones
        if len(selected) < max_questions:
            remaining = [q for q in questions if q not in selected]
            needed = max_questions - len(selected)
            selected.extend(random.sample(remaining, min(needed, len(remaining))))
        
        # 3. Ensure difficulty distribution
        difficulty_distribution = config.get("difficulty_distribution", {
            "easy": 0.3, "medium": 0.5, "hard": 0.2
        })
        
        selected = self._adjust_difficulty_distribution(selected, difficulty_distribution)
        
        return selected[:max_questions]
    
    def _select_by_topic_distribution(
        self, 
        questions: List[Dict], 
        distribution: Dict[str, float], 
        total_needed: int
    ) -> List[Dict]:
        """Select questions based on topic distribution"""
        selected = []
        
        # Group questions by topic
        topics = {}
        for question in questions:
            topic = question.get("normalized_topic", "General")
            if topic not in topics:
                topics[topic] = []
            topics[topic].append(question)
        
        # Select questions for each topic based on distribution
        for topic, percentage in distribution.items():
            if topic not in topics:
                continue
            
            topic_questions = topics[topic]
            needed_for_topic = int(total_needed * percentage)
            
            # Sort by quality score and select
            topic_questions.sort(
                key=lambda q: q.get("validation_score", 0), 
                reverse=True
            )
            selected.extend(topic_questions[:needed_for_topic])
        
        return selected
    
    def _adjust_difficulty_distribution(
        self, 
        questions: List[Dict], 
        distribution: Dict[str, float]
    ) -> List[Dict]:
        """Adjust questions to match difficulty distribution"""
        total = len(questions)
        if total == 0:
            return questions
        
        # Count current distribution
        current_counts = {"easy": 0, "medium": 0, "hard": 0}
        for question in questions:
            difficulty = question.get("difficulty", "medium")
            if difficulty in current_counts:
                current_counts[difficulty] += 1
        
        # Calculate target counts
        target_counts = {}
        for difficulty, percentage in distribution.items():
            target_counts[difficulty] = int(total * percentage)
        
        # Adjust if needed
        questions_by_difficulty = {}
        for difficulty in ["easy", "medium", "hard"]:
            questions_by_difficulty[difficulty] = [
                q for q in questions if q.get("difficulty") == difficulty
            ]
        
        adjusted = []
        
        # Add questions to meet targets
        for difficulty in ["easy", "medium", "hard"]:
            current = questions_by_difficulty[difficulty]
            target = target_counts.get(difficulty, 0)
            
            if len(current) > target:
                # Take only needed amount, sorted by quality
                current.sort(key=lambda q: q.get("validation_score", 0), reverse=True)
                adjusted.extend(current[:target])
            else:
                # Take all available
                adjusted.extend(current)
        
        # If still need more questions, add from other difficulties
        if len(adjusted) < total:
            remaining_needed = total - len(adjusted)
            all_questions = [q for q in questions if q not in adjusted]
            all_questions.sort(key=lambda q: q.get("validation_score", 0), reverse=True)
            adjusted.extend(all_questions[:remaining_needed])
        
        return adjusted
    
    def _apply_question_order(
        self, 
        questions: List[Dict], 
        config: Dict[str, Any]
    ) -> List[Dict]:
        """Apply question ordering"""
        order_strategy = config.get("order_strategy", "topic_difficulty")
        
        if order_strategy == "random":
            random.shuffle(questions)
        elif order_strategy == "difficulty_ascending":
            questions.sort(key=lambda q: {"easy": 1, "medium": 2, "hard": 3}.get(q.get("difficulty", "medium"), 2))
        elif order_strategy == "difficulty_descending":
            questions.sort(key=lambda q: {"easy": 3, "medium": 2, "hard": 1}.get(q.get("difficulty", "medium"), 2))
        elif order_strategy == "topic_difficulty":
            # Group by topic, then sort by difficulty within each topic
            questions_by_topic = {}
            for question in questions:
                topic = question.get("normalized_topic", "General")
                if topic not in questions_by_topic:
                    questions_by_topic[topic] = []
                questions_by_topic[topic].append(question)
            
            # Sort topics alphabetically
            sorted_topics = sorted(questions_by_topic.keys())
            
            # Sort questions within each topic by difficulty
            ordered_questions = []
            for topic in sorted_topics:
                topic_questions = questions_by_topic[topic]
                topic_questions.sort(key=lambda q: {"easy": 1, "medium": 2, "hard": 3}.get(q.get("difficulty", "medium"), 2))
                ordered_questions.extend(topic_questions)
            
            return ordered_questions
        
        # Assign question numbers
        for i, question in enumerate(questions, 1):
            question["question_number"] = i
        
        return questions
    
    def _create_quiz_sections(self, questions: List[Dict]) -> List[Dict]:
        """Create quiz sections based on topics"""
        sections = []
        current_topic = None
        current_section = None
        
        for question in questions:
            topic = question.get("normalized_topic", "General")
            
            if topic != current_topic:
                # Start new section
                if current_section:
                    sections.append(current_section)
                
                current_topic = topic
                current_section = {
                    "id": f"section_{len(sections) + 1}",
                    "title": f"Section: {topic}",
                    "description": f"Questions related to {topic}",
                    "topic": topic,
                    "questions": [],
                    "question_count": 0,
                    "instructions": "Answer all questions in this section."
                }
            
            # Add question to current section
            question_summary = {
                "question_number": question.get("question_number"),
                "question_text": question.get("question_text", "")[:100] + "...",
                "question_type": question.get("question_type"),
                "difficulty": question.get("difficulty")
            }
            current_section["questions"].append(question_summary)
            current_section["question_count"] += 1
        
        # Add the last section
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _generate_quiz_metadata(
        self, 
        questions: List[Dict], 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate quiz metadata"""
        # Calculate topic coverage
        topics = set()
        difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}
        type_counts = {"mcq": 0, "short_answer": 0}
        
        for question in questions:
            topics.add(question.get("normalized_topic", "General"))
            
            difficulty = question.get("difficulty", "medium")
            if difficulty in difficulty_counts:
                difficulty_counts[difficulty] += 1
            
            q_type = question.get("question_type", "mcq")
            if q_type in type_counts:
                type_counts[q_type] += 1
        
        # Calculate estimated time (1.5 minutes per MCQ, 3 minutes per short answer)
        estimated_time = (
            type_counts.get("mcq", 0) * 1.5 +
            type_counts.get("short_answer", 0) * 3
        )
        
        metadata = {
            "title": config.get("title", "Generated Quiz"),
            "description": config.get("description", "Quiz generated from PDF content"),
            "instructions": config.get("instructions", "Answer all questions. Time limit: {} minutes.".format(int(estimated_time))),
            "total_questions": len(questions),
            "topic_count": len(topics),
            "topics_covered": list(topics),
            "difficulty_distribution": difficulty_counts,
            "question_type_distribution": type_counts,
            "estimated_time_minutes": int(estimated_time),
            "passing_score": config.get("passing_score", 70),
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
        
        return metadata
    
    def _calculate_quiz_statistics(self, questions: List[Dict]) -> Dict[str, Any]:
        """Calculate quiz statistics"""
        total_questions = len(questions)
        
        # Difficulty statistics
        difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}
        validation_scores = []
        confidence_scores = []
        
        for question in questions:
            difficulty = question.get("difficulty", "medium")
            if difficulty in difficulty_counts:
                difficulty_counts[difficulty] += 1
            
            validation_score = question.get("validation_score", 0.5)
            validation_scores.append(validation_score)
            
            confidence_score = question.get("confidence_score", 0.5)
            confidence_scores.append(confidence_score)
        
        # Calculate averages
        avg_validation = sum(validation_scores) / total_questions if validation_scores else 0
        avg_confidence = sum(confidence_scores) / total_questions if confidence_scores else 0
        
        # Topic diversity
        topics = set(q.get("normalized_topic", "General") for q in questions)
        
        # Calculate question quality
        quality_scores = []
        for question in questions:
            validation = question.get("validation_score", 0.5)
            confidence = question.get("confidence_score", 0.5)
            quality_scores.append((validation + confidence) / 2)
        
        avg_quality = sum(quality_scores) / total_questions if quality_scores else 0
        
        return {
            "total_questions": total_questions,
            "difficulty_distribution": difficulty_counts,
            "topic_count": len(topics),
            "average_validation_score": round(avg_validation, 3),
            "average_confidence_score": round(avg_confidence, 3),
            "average_quality_score": round(avg_quality, 3),
            "estimated_completion_time": total_questions * 2,  # 2 minutes per question average
            "quality_rating": self._get_quality_rating(avg_quality)
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
    
    def _format_for_internal(
        self, 
        questions: List[Dict], 
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format quiz for internal use (full details)"""
        return {
            "metadata": metadata,
            "questions": [
                {
                    "question_number": q.get("question_number"),
                    "question_text": q.get("question_text"),
                    "question_type": q.get("question_type"),
                    "options": q.get("options", []),
                    "correct_answer": q.get("answer"),
                    "explanation": q.get("explanation"),
                    "difficulty": q.get("difficulty"),
                    "topic": q.get("normalized_topic"),
                    "subtopic": q.get("subtopic"),
                    "page_reference": q.get("page_number"),
                    "validation_score": q.get("validation_score"),
                    "confidence_score": q.get("confidence_score"),
                    "metadata": {
                        "chunk_id": q.get("chunk_id"),
                        "generation_source": q.get("generation_source")
                    }
                }
                for q in questions
            ]
        }
    
    def _format_for_student(
        self, 
        questions: List[Dict], 
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format quiz for student attempt"""
        student_questions = []
        
        for question in questions:
            student_question = {
                "question_number": question.get("question_number"),
                "question_text": question.get("question_text"),
                "question_type": question.get("question_type"),
                "difficulty": question.get("difficulty"),
                "topic": question.get("normalized_topic")
            }
            
            # Add options for MCQs (shuffled for student)
            if question.get("question_type") == "mcq":
                options = question.get("options", [])
                shuffled_options = options.copy()
                random.shuffle(shuffled_options)
                student_question["options"] = shuffled_options
            
            student_questions.append(student_question)
        
        return {
            "metadata": {
                "title": metadata.get("title"),
                "description": metadata.get("description"),
                "instructions": metadata.get("instructions"),
                "total_questions": metadata.get("total_questions"),
                "estimated_time_minutes": metadata.get("estimated_time_minutes"),
                "passing_score": metadata.get("passing_score")
            },
            "questions": student_questions
        }
    
    def _format_for_admin(
        self, 
        questions: List[Dict], 
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format quiz for admin review"""
        admin_questions = []
        
        for question in questions:
            admin_question = {
                "question_number": question.get("question_number"),
                "question_text": question.get("question_text"),
                "question_type": question.get("question_type"),
                "correct_answer": question.get("answer"),
                "explanation": question.get("explanation"),
                "difficulty": question.get("difficulty"),
                "topic": question.get("normalized_topic"),
                "subtopic": question.get("subtopic"),
                "page_reference": question.get("page_number"),
                "validation_score": question.get("validation_score"),
                "validation_status": question.get("validation_status", "validated")
            }
            
            # Add options for MCQs
            if question.get("question_type") == "mcq":
                admin_question["options"] = question.get("options", [])
            
            admin_questions.append(admin_question)
        
        return {
            "metadata": metadata,
            "questions": admin_questions,
            "statistics": self._calculate_quiz_statistics(questions),
            "edit_notes": "Admin can edit questions as needed"
        }
    
    def _generate_quiz_id(self) -> str:
        """Generate unique quiz ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        random_str = hashlib.md5(timestamp.encode()).hexdigest()[:8]
        return f"quiz_{timestamp}_{random_str}"
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default quiz configuration"""
        return {
            "title": "Generated Quiz",
            "description": "Quiz generated from PDF content",
            "max_questions": 20,
            "order_strategy": "topic_difficulty",
            "difficulty_distribution": {
                "easy": 0.3,
                "medium": 0.5,
                "hard": 0.2
            },
            "passing_score": 70,
            "shuffle_options": True
        }
    
    def _create_empty_quiz(self) -> Dict[str, Any]:
        """Create empty quiz structure"""
        return {
            "id": self._generate_quiz_id(),
            "metadata": {
                "title": "Empty Quiz",
                "description": "No questions available",
                "total_questions": 0,
                "created_at": datetime.utcnow().isoformat()
            },
            "sections": [],
            "questions": [],
            "statistics": {
                "total_questions": 0,
                "quality_rating": "No Data"
            },
            "formats": {
                "internal": {"questions": []},
                "student": {"questions": []},
                "admin": {"questions": []}
            }
        }
    
    def _format_fallback_quiz(
        self, 
        questions: List[Dict], 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback quiz formatting"""
        return {
            "id": self._generate_quiz_id(),
            "metadata": {
                "title": config.get("title", "Quiz"),
                "description": "Quiz generated with fallback formatting",
                "total_questions": len(questions),
                "created_at": datetime.utcnow().isoformat()
            },
            "questions": questions,
            "statistics": {
                "total_questions": len(questions),
                "warning": "Fallback formatting used"
            }
        }
    
    def generate_quiz_summary(self, quiz: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of the quiz"""
        metadata = quiz.get("metadata", {})
        statistics = quiz.get("statistics", {})
        
        summary = {
            "quiz_id": quiz.get("id"),
            "title": metadata.get("title"),
            "description": metadata.get("description"),
            "total_questions": metadata.get("total_questions", 0),
            "topic_count": statistics.get("topic_count", 0),
            "estimated_time": metadata.get("estimated_time_minutes", 0),
            "quality_rating": statistics.get("quality_rating", "Unknown"),
            "average_validation_score": statistics.get("average_validation_score", 0),
            "difficulty_breakdown": statistics.get("difficulty_distribution", {}),
            "created_at": metadata.get("created_at")
        }
        
        return summary