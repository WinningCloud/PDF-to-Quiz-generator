import json
from typing import Dict, List, Any, Tuple
import logging
from datetime import datetime
import random
from config.llm_config import llm_client

logger = logging.getLogger(__name__)

class FormatterAgent:
    def __init__(self):
        self.question_types = ["mcq", "short_answer"]
    
    def format_quiz(
        self, 
        questions: List[Dict[str, Any]], 
        quiz_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format questions into a complete quiz
        
        Args:
            questions: List of validated questions
            quiz_config: Quiz configuration
            
        Returns:
            Formatted quiz structure
        """
        try:
            # Sort questions by topic and difficulty
            sorted_questions = self._sort_questions(questions)
            
            # Apply quiz configuration
            formatted_questions = self._apply_quiz_config(sorted_questions, quiz_config)
            
            # Generate quiz metadata
            quiz_metadata = self._generate_quiz_metadata(formatted_questions, quiz_config)
            
            # Create quiz sections by topic
            quiz_sections = self._create_quiz_sections(formatted_questions)
            
            # Calculate statistics
            quiz_stats = self._calculate_quiz_statistics(formatted_questions)
            
            # Format for different outputs
            output_formats = {
                "json": self._format_as_json(formatted_questions, quiz_metadata),
                "html": self._format_as_html(formatted_questions, quiz_metadata),
                "markdown": self._format_as_markdown(formatted_questions, quiz_metadata)
            }
            
            quiz = {
                "metadata": quiz_metadata,
                "sections": quiz_sections,
                "questions": formatted_questions,
                "statistics": quiz_stats,
                "formats": output_formats,
                "generated_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
            
            logger.info(f"Formatted quiz with {len(formatted_questions)} questions")
            return quiz
            
        except Exception as e:
            logger.error(f"Error formatting quiz: {e}")
            return self._format_fallback_quiz(questions, quiz_config)
    
    def format_questions_for_database(
        self, 
        questions: List[Dict[str, Any]], 
        quiz_id: int
    ) -> List[Dict[str, Any]]:
        """
        Format questions for database storage
        
        Args:
            questions: List of questions
            quiz_id: ID of the quiz
            
        Returns:
            Questions formatted for database
        """
        db_questions = []
        
        for i, question in enumerate(questions):
            db_question = {
                "quiz_id": quiz_id,
                "question_text": question.get("question_text", ""),
                "question_type": question.get("question_type", "mcq"),
                "options": json.dumps(question.get("options", [])),
                "correct_answer": question.get("answer", ""),
                "explanation": question.get("explanation", ""),
                "difficulty": question.get("difficulty", "medium"),
                "topic": question.get("normalized_topic", "General"),
                "subtopic": question.get("subtopic", ""),
                "page_reference": question.get("page_number", 1),
                "validation_score": question.get("validation_score", 0.0),
                "question_order": i + 1,
                "metadata": json.dumps({
                    "chunk_id": question.get("chunk_id"),
                    "confidence_score": question.get("confidence_score", 0.5),
                    "generation_source": question.get("generation_source", "llm"),
                    "original_data": {
                        key: value for key, value in question.items()
                        if key not in ["question_text", "options", "answer", "explanation", "difficulty"]
                    }
                })
            }
            db_questions.append(db_question)
        
        return db_questions
    
    def create_quiz_summary(
        self, 
        quiz_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a summary of the quiz
        
        Args:
            quiz_data: Complete quiz data
            
        Returns:
            Quiz summary
        """
        questions = quiz_data.get("questions", [])
        metadata = quiz_data.get("metadata", {})
        
        # Calculate topic distribution
        topic_distribution = {}
        difficulty_distribution = {"easy": 0, "medium": 0, "hard": 0}
        type_distribution = {"mcq": 0, "short_answer": 0}
        
        for question in questions:
            topic = question.get("topic", "General")
            topic_distribution[topic] = topic_distribution.get(topic, 0) + 1
            
            difficulty = question.get("difficulty", "medium")
            difficulty_distribution[difficulty] = difficulty_distribution.get(difficulty, 0) + 1
            
            q_type = question.get("question_type", "mcq")
            type_distribution[q_type] = type_distribution.get(q_type, 0) + 1
        
        # Calculate estimated time (1 minute per MCQ, 2 minutes per short answer)
        estimated_time = (
            type_distribution.get("mcq", 0) * 1 +
            type_distribution.get("short_answer", 0) * 2
        )
        
        summary = {
            "quiz_id": metadata.get("quiz_id"),
            "title": metadata.get("title", "Generated Quiz"),
            "description": metadata.get("description", ""),
            "total_questions": len(questions),
            "topic_count": len(topic_distribution),
            "topic_distribution": topic_distribution,
            "difficulty_distribution": difficulty_distribution,
            "type_distribution": type_distribution,
            "estimated_time_minutes": estimated_time,
            "average_difficulty": self._calculate_average_difficulty(difficulty_distribution),
            "coverage_score": self._calculate_coverage_score(topic_distribution, len(questions)),
            "quality_score": self._calculate_quality_score(questions)
        }
        
        return summary
    
    def format_for_student_view(
        self, 
        quiz_data: Dict[str, Any], 
        include_answers: bool = False
    ) -> Dict[str, Any]:
        """
        Format quiz for student viewing
        
        Args:
            quiz_data: Complete quiz data
            include_answers: Whether to include answers
            
        Returns:
            Student-friendly quiz format
        """
        questions = quiz_data.get("questions", [])
        
        student_questions = []
        for question in questions:
            student_question = {
                "question_id": question.get("question_id"),
                "question_text": question.get("question_text", ""),
                "question_type": question.get("question_type", "mcq"),
                "difficulty": question.get("difficulty", "medium"),
                "topic": question.get("topic", "General"),
                "question_order": question.get("question_order", 0)
            }
            
            # Add options for MCQs
            if question.get("question_type") == "mcq":
                options = question.get("options", [])
                # Shuffle options for student view
                shuffled_options = options.copy()
                random.shuffle(shuffled_options)
                student_question["options"] = shuffled_options
            
            # Add answer if requested
            if include_answers:
                student_question["correct_answer"] = question.get("answer", "")
                student_question["explanation"] = question.get("explanation", "")
            
            student_questions.append(student_question)
        
        return {
            "quiz_id": quiz_data.get("metadata", {}).get("quiz_id"),
            "title": quiz_data.get("metadata", {}).get("title", "Quiz"),
            "description": quiz_data.get("metadata", {}).get("description", ""),
            "instructions": "Answer all questions. For MCQs, select the best answer.",
            "questions": student_questions,
            "total_questions": len(student_questions),
            "estimated_time": self._calculate_estimated_time(student_questions)
        }
    
    def _sort_questions(self, questions: List[Dict]) -> List[Dict]:
        """Sort questions by topic and difficulty"""
        # First, sort by topic
        questions_by_topic = {}
        for question in questions:
            topic = question.get("normalized_topic", "General")
            if topic not in questions_by_topic:
                questions_by_topic[topic] = []
            questions_by_topic[topic].append(question)
        
        # Sort topics alphabetically
        sorted_topics = sorted(questions_by_topic.keys())
        
        # Within each topic, sort by difficulty (easy -> medium -> hard)
        sorted_questions = []
        for topic in sorted_topics:
            topic_questions = questions_by_topic[topic]
            # Define difficulty order
            difficulty_order = {"easy": 1, "medium": 2, "hard": 3}
            topic_questions.sort(
                key=lambda q: difficulty_order.get(q.get("difficulty", "medium"), 2)
            )
            sorted_questions.extend(topic_questions)
        
        return sorted_questions
    
    def _apply_quiz_config(
        self, 
        questions: List[Dict], 
        config: Dict
    ) -> List[Dict]:
        """Apply quiz configuration to questions"""
        max_questions = config.get("max_questions", 20)
        difficulty_distribution = config.get("difficulty_distribution", {
            "easy": 0.3, "medium": 0.5, "hard": 0.2
        })
        
        if len(questions) <= max_questions:
            return questions
        
        # Select questions based on configuration
        selected_questions = []
        counts = {"easy": 0, "medium": 0, "hard": 0}
        targets = {
            "easy": int(max_questions * difficulty_distribution.get("easy", 0.3)),
            "medium": int(max_questions * difficulty_distribution.get("medium", 0.5)),
            "hard": int(max_questions * difficulty_distribution.get("hard", 0.2))
        }
        
        for question in questions:
            difficulty = question.get("difficulty", "medium")
            
            if counts[difficulty] < targets[difficulty]:
                selected_questions.append(question)
                counts[difficulty] += 1
            
            if len(selected_questions) >= max_questions:
                break
        
        # If we still need more questions, fill with whatever is available
        if len(selected_questions) < max_questions:
            remaining = [q for q in questions if q not in selected_questions]
            selected_questions.extend(remaining[:max_questions - len(selected_questions)])
        
        # Assign question order
        for i, question in enumerate(selected_questions):
            question["question_order"] = i + 1
        
        return selected_questions
    
    def _generate_quiz_metadata(
        self, 
        questions: List[Dict], 
        config: Dict
    ) -> Dict[str, Any]:
        """Generate quiz metadata"""
        # Calculate topic coverage
        topics = set()
        for question in questions:
            topic = question.get("normalized_topic", "General")
            topics.add(topic)
        
        # Calculate difficulty breakdown
        difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}
        for question in questions:
            difficulty = question.get("difficulty", "medium")
            if difficulty in difficulty_counts:
                difficulty_counts[difficulty] += 1
        
        metadata = {
            "title": config.get("title", "Generated Quiz"),
            "description": config.get("description", "Quiz generated from PDF content"),
            "total_questions": len(questions),
            "topic_count": len(topics),
            "topics_covered": list(topics),
            "difficulty_breakdown": difficulty_counts,
            "generation_date": datetime.utcnow().isoformat(),
            "quiz_id": config.get("quiz_id", f"quiz_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"),
            "source_pdf": config.get("source_pdf", "Unknown"),
            "version": "1.0"
        }
        
        return metadata
    
    def _create_quiz_sections(self, questions: List[Dict]) -> List[Dict]:
        """Create quiz sections by topic"""
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
                    "section_title": f"Section: {topic}",
                    "topic": topic,
                    "instructions": "Answer the following questions:",
                    "questions": [],
                    "question_count": 0,
                    "difficulty_breakdown": {"easy": 0, "medium": 0, "hard": 0}
                }
            
            # Add question to current section
            current_section["questions"].append({
                "question_id": question.get("question_id"),
                "question_text": question.get("question_text"),
                "question_type": question.get("question_type"),
                "difficulty": question.get("difficulty", "medium")
            })
            current_section["question_count"] += 1
            
            difficulty = question.get("difficulty", "medium")
            if difficulty in current_section["difficulty_breakdown"]:
                current_section["difficulty_breakdown"][difficulty] += 1
        
        # Add the last section
        if current_section:
            sections.append(current_section)
        
        return sections
    
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
        
        return {
            "total_questions": total_questions,
            "difficulty_distribution": difficulty_counts,
            "topic_count": len(topics),
            "average_validation_score": round(avg_validation, 3),
            "average_confidence_score": round(avg_confidence, 3),
            "estimated_completion_time": total_questions * 1.5,  # 1.5 minutes per question
            "quality_rating": self._calculate_quality_rating(avg_validation, avg_confidence)
        }
    
    def _format_as_json(
        self, 
        questions: List[Dict], 
        metadata: Dict
    ) -> Dict[str, Any]:
        """Format quiz as JSON"""
        return {
            "metadata": metadata,
            "questions": [
                {
                    "id": q.get("question_id"),
                    "text": q.get("question_text"),
                    "type": q.get("question_type"),
                    "options": q.get("options", []),
                    "correct_answer": q.get("answer"),
                    "explanation": q.get("explanation"),
                    "difficulty": q.get("difficulty"),
                    "topic": q.get("normalized_topic"),
                    "page_reference": q.get("page_number")
                }
                for q in questions
            ]
        }
    
    def _format_as_html(
        self, 
        questions: List[Dict], 
        metadata: Dict
    ) -> str:
        """Format quiz as HTML"""
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<title>" + metadata.get("title", "Quiz") + "</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 40px; }",
            ".question { margin-bottom: 30px; padding: 15px; border: 1px solid #ddd; }",
            ".options { margin-left: 20px; }",
            ".option { margin: 5px 0; }",
            ".correct { color: green; font-weight: bold; }",
            ".explanation { margin-top: 10px; font-style: italic; color: #666; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{metadata.get('title', 'Quiz')}</h1>",
            f"<p>{metadata.get('description', '')}</p>",
            f"<p><strong>Total Questions:</strong> {metadata.get('total_questions', 0)}</p>"
        ]
        
        for i, question in enumerate(questions, 1):
            html_parts.extend([
                f'<div class="question" id="q{i}">',
                f'<h3>Question {i}: {question.get("difficulty", "").capitalize()} Difficulty</h3>',
                f'<p><strong>Topic:</strong> {question.get("normalized_topic", "General")}</p>',
                f'<p>{question.get("question_text", "")}</p>'
            ])
            
            if question.get("question_type") == "mcq":
                html_parts.append('<div class="options">')
                for j, option in enumerate(question.get("options", []), 1):
                    html_parts.append(f'<div class="option">{chr(64+j)}. {option}</div>')
                html_parts.append('</div>')
            
            html_parts.extend([
                f'<p class="correct"><strong>Answer:</strong> {question.get("answer", "")}</p>',
                f'<p class="explanation"><strong>Explanation:</strong> {question.get("explanation", "")}</p>',
                '</div>'
            ])
        
        html_parts.extend([
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_parts)
    
    def _format_as_markdown(
        self, 
        questions: List[Dict], 
        metadata: Dict
    ) -> str:
        """Format quiz as Markdown"""
        markdown_parts = [
            f"# {metadata.get('title', 'Quiz')}",
            f"\n{metadata.get('description', '')}",
            f"\n**Total Questions:** {metadata.get('total_questions', 0)}",
            "\n---\n"
        ]
        
        for i, question in enumerate(questions, 1):
            markdown_parts.extend([
                f"\n## Question {i}: {question.get('difficulty', '').capitalize()}",
                f"\n**Topic:** {question.get('normalized_topic', 'General')}",
                f"\n{question.get('question_text', '')}"
            ])
            
            if question.get("question_type") == "mcq":
                markdown_parts.append("\n**Options:**")
                for j, option in enumerate(question.get("options", []), 1):
                    markdown_parts.append(f"{chr(96+j)}) {option}")
            
            markdown_parts.extend([
                f"\n**Answer:** {question.get('answer', '')}",
                f"\n*Explanation:* {question.get('explanation', '')}",
                "\n---"
            ])
        
        return "\n".join(markdown_parts)
    
    def _format_fallback_quiz(
        self, 
        questions: List[Dict], 
        config: Dict
    ) -> Dict[str, Any]:
        """Fallback quiz formatting"""
        return {
            "metadata": {
                "title": config.get("title", "Quiz"),
                "description": "Quiz generated with fallback formatting",
                "total_questions": len(questions),
                "generation_date": datetime.utcnow().isoformat()
            },
            "questions": questions,
            "formats": {
                "json": {"questions": questions},
                "html": "<html><body>Fallback format</body></html>",
                "markdown": "# Fallback Quiz"
            }
        }
    
    def _calculate_average_difficulty(self, distribution: Dict) -> str:
        """Calculate average difficulty"""
        total = sum(distribution.values())
        if total == 0:
            return "medium"
        
        # Weight difficulties
        weight = (
            distribution.get("easy", 0) * 1 +
            distribution.get("medium", 0) * 2 +
            distribution.get("hard", 0) * 3
        ) / total
        
        if weight < 1.5:
            return "easy"
        elif weight < 2.5:
            return "medium"
        else:
            return "hard"
    
    def _calculate_coverage_score(
        self, 
        distribution: Dict, 
        total_questions: int
    ) -> float:
        """Calculate topic coverage score"""
        if total_questions == 0:
            return 0.0
        
        # Ideal: 3-5 questions per topic
        ideal_per_topic = 4
        topic_count = len(distribution)
        
        if topic_count == 0:
            return 0.0
        
        ideal_total = topic_count * ideal_per_topic
        coverage = min(1.0, total_questions / ideal_total)
        
        return coverage
    
    def _calculate_quality_score(self, questions: List[Dict]) -> float:
        """Calculate overall quiz quality score"""
        if not questions:
            return 0.0
        
        scores = []
        for question in questions:
            validation = question.get("validation_score", 0.5)
            confidence = question.get("confidence_score", 0.5)
            scores.append((validation + confidence) / 2)
        
        return sum(scores) / len(scores)
    
    def _calculate_estimated_time(self, questions: List[Dict]) -> int:
        """Calculate estimated completion time"""
        time_per_question = {
            "mcq": 1,  # 1 minute per MCQ
            "short_answer": 2  # 2 minutes per short answer
        }
        
        total_time = 0
        for question in questions:
            q_type = question.get("question_type", "mcq")
            total_time += time_per_question.get(q_type, 1)
        
        return total_time
    
    def _calculate_quality_rating(
        self, 
        avg_validation: float, 
        avg_confidence: float
    ) -> str:
        """Calculate quality rating"""
        avg_score = (avg_validation + avg_confidence) / 2
        
        if avg_score >= 0.8:
            return "Excellent"
        elif avg_score >= 0.7:
            return "Good"
        elif avg_score >= 0.6:
            return "Fair"
        else:
            return "Needs Improvement"