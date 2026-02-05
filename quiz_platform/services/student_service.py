import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
import os
from db.models import (
    User, Quiz, Question, StudentAttempt, StudentAnswer, Topic
)
from schemas.quiz_schema import QuizSummary, QuizAttempt, QuizResult, StudentProgress
from schemas.student_schema import AttemptCreate, AnswerSubmit
from config.settings import settings

logger = logging.getLogger(__name__)

class StudentService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_available_quizzes(
        self, 
        student_id: int, 
        skip: int = 0, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get quizzes available to student
        
        Args:
            student_id: Student ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of available quizzes
        """
        try:
            # Get published quizzes
            quizzes = (
                self.db.query(Quiz)
                .filter(Quiz.status == "published")
                .filter(Quiz.total_questions > 0)   # 👈 ADD THIS
                .order_by(desc(Quiz.published_at))
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            available_quizzes = []
            for quiz in quizzes:
                # Check if student has already attempted this quiz
                previous_attempt = self.db.query(StudentAttempt).filter(
                    StudentAttempt.quiz_id == quiz.id,
                    StudentAttempt.student_id == student_id,
                    StudentAttempt.completed_at.isnot(None)
                ).first()
                
                # Get quiz statistics
                total_attempts = self.db.query(StudentAttempt).filter(
                    StudentAttempt.quiz_id == quiz.id
                ).count()
                
                avg_score = self.db.query(func.avg(StudentAttempt.score)).filter(
                    StudentAttempt.quiz_id == quiz.id,
                    StudentAttempt.score.isnot(None)
                ).scalar() or 0
                
                quiz_summary = {
                    "id": quiz.id,
                    "title": quiz.title,
                    "description": quiz.description,
                    "total_questions": quiz.total_questions,
                    "difficulty_distribution": json.loads(quiz.difficulty_distribution) if quiz.difficulty_distribution else {},
                    "estimated_time": quiz.total_questions * 2,  # 2 minutes per question
                    "published_at": quiz.published_at.isoformat() if quiz.published_at else None,
                    "previously_attempted": previous_attempt is not None,
                    "previous_score": previous_attempt.score if previous_attempt else None,
                    "statistics": {
                        "total_attempts": total_attempts,
                        "average_score": float(avg_score)
                    }
                }
                
                available_quizzes.append(quiz_summary)
            
            return available_quizzes
            
        except Exception as e:
            logger.error(f"Error getting available quizzes: {e}")
            return []
    
    def start_quiz_attempt(
        self, 
        student_id: int, 
        quiz_id: int
    ) -> Dict[str, Any]:
        """
        Start a new quiz attempt
        
        Args:
            student_id: Student ID
            quiz_id: Quiz ID
            
        Returns:
            Attempt information
        """
        try:
            # Check if quiz exists and is published
            quiz = self.db.query(Quiz).filter(
                Quiz.id == quiz_id,
                Quiz.status == "published"
            ).first()
            
            if not quiz:
                return {"error": "Quiz not found or not published"}
            
            # Check for existing incomplete attempt
            existing_attempt = self.db.query(StudentAttempt).filter(
                StudentAttempt.quiz_id == quiz_id,
                StudentAttempt.student_id == student_id,
                StudentAttempt.completed_at.is_(None)
            ).first()
            
            if existing_attempt:
                # Return existing attempt
                return self._format_attempt_data(existing_attempt, quiz)
            
            # Create new attempt
            attempt = StudentAttempt(
                quiz_id=quiz_id,
                student_id=student_id,
                started_at=datetime.utcnow(),
                status="in_progress"
            )
            
            self.db.add(attempt)
            self.db.commit()
            self.db.refresh(attempt)
            
            return self._format_attempt_data(attempt, quiz)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error starting quiz attempt: {e}")
            return {"error": str(e)}
    
    def _format_attempt_data(
        self, 
        attempt: StudentAttempt, 
        quiz: Quiz
    ) -> Dict[str, Any]:
        """Format attempt data for response"""
        # Get quiz questions
        questions = self.db.query(Question).filter(
            Question.quiz_id == quiz.id,
            Question.is_active == True
        ).order_by(Question.question_order).all()
        
        # Format questions for attempt (without answers)
        attempt_questions = []
        for question in questions:
            q_data = {
                "id": question.id,
                "question_text": question.question_text,
                "question_type": question.question_type,
                "difficulty": question.difficulty,
                "topic": question.topic,
                "question_order": question.question_order
            }
            
            if question.question_type == "mcq":
                # Shuffle options for student
                options = json.loads(question.options) if question.options else []
                import random
                shuffled_options = options.copy()
                random.shuffle(shuffled_options)
                q_data["options"] = shuffled_options
            
            attempt_questions.append(q_data)
        
        return {
            "attempt_id": attempt.id,
            "quiz": {
                "id": quiz.id,
                "title": quiz.title,
                "description": quiz.description,
                "total_questions": len(questions)
            },
            "questions": attempt_questions,
            "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
            "time_limit_minutes": len(questions) * 2  # 2 minutes per question
        }
    
    def submit_answer(
        self, 
        attempt_id: int, 
        student_id: int, 
        answer_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit answer for a question
        
        Args:
            attempt_id: Attempt ID
            student_id: Student ID
            answer_data: Answer data
            
        Returns:
            Submission result
        """
        try:
            # Verify attempt belongs to student
            attempt = self.db.query(StudentAttempt).filter(
                StudentAttempt.id == attempt_id,
                StudentAttempt.student_id == student_id
            ).first()
            
            if not attempt:
                return {"error": "Attempt not found"}
            
            if attempt.completed_at:
                return {"error": "Attempt already completed"}
            
            question_id = answer_data.get("question_id")
            question = self.db.query(Question).filter(Question.id == question_id).first()
            
            if not question:
                return {"error": "Question not found"}
            
            # Check if answer already exists
            existing_answer = self.db.query(StudentAnswer).filter(
                StudentAnswer.attempt_id == attempt_id,
                StudentAnswer.question_id == question_id
            ).first()
            
            if existing_answer:
                # Update existing answer
                existing_answer.selected_option = answer_data.get("selected_option")
                existing_answer.answer_text = answer_data.get("answer_text")
                existing_answer.answered_at = datetime.utcnow()
                existing_answer.is_correct = self._check_answer_correctness(
                    question, 
                    answer_data
                )
            else:
                # Create new answer
                answer = StudentAnswer(
                    attempt_id=attempt_id,
                    question_id=question_id,
                    selected_option=answer_data.get("selected_option"),
                    answer_text=answer_data.get("answer_text"),
                    answered_at=datetime.utcnow(),
                    is_correct=self._check_answer_correctness(question, answer_data)
                )
                self.db.add(answer)
            
            self.db.commit()
            
            return {
                "success": True,
                "message": "Answer submitted successfully",
                "is_correct": self._check_answer_correctness(question, answer_data)
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error submitting answer: {e}")
            return {"error": str(e)}
    
    def _check_answer_correctness(
        self, 
        question: Question, 
        answer_data: Dict[str, Any]
    ) -> bool:
        """Check if answer is correct"""
        if question.question_type == "mcq":
            selected = answer_data.get("selected_option")
            correct = question.correct_answer
            return selected == correct
        else:  # short answer
            # For short answers, we might want to use similarity checking
            # For now, simple exact match
            student_answer = answer_data.get("answer_text", "").strip().lower()
            correct_answer = question.correct_answer.strip().lower()
            return student_answer == correct_answer
    
    def complete_attempt(
        self, 
        attempt_id: int, 
        student_id: int
    ) -> Dict[str, Any]:
        """
        Complete quiz attempt and calculate score
        
        Args:
            attempt_id: Attempt ID
            student_id: Student ID
            
        Returns:
            Quiz result
        """
        try:
            # Verify attempt belongs to student
            attempt = self.db.query(StudentAttempt).filter(
                StudentAttempt.id == attempt_id,
                StudentAttempt.student_id == student_id
            ).first()
            
            if not attempt:
                return {"error": "Attempt not found"}
            
            if attempt.completed_at:
                return {"error": "Attempt already completed"}
            
            # Get all answers for this attempt
            answers = self.db.query(StudentAnswer).filter(
                StudentAnswer.attempt_id == attempt_id
            ).all()
            
            # Calculate score
            total_questions = self.db.query(Question).filter(
                Question.quiz_id == attempt.quiz_id
            ).count()
            
            correct_answers = sum(1 for a in answers if a.is_correct)
            score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
            
            # Update attempt
            attempt.completed_at = datetime.utcnow()
            attempt.score = score
            attempt.status = "completed"
            
            self.db.commit()
            
            # Get quiz details
            quiz = self.db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()
            
            # Get topic-wise performance
            topic_performance = self._calculate_topic_performance(attempt_id)
            
            # Get time taken
            time_taken_minutes = 0
            if attempt.started_at and attempt.completed_at:
                time_taken_minutes = (attempt.completed_at - attempt.started_at).total_seconds() / 60
            
            return {
                "attempt_id": attempt.id,
                "quiz_id": quiz.id,
                "quiz_title": quiz.title,
                "student_id": student_id,
                "score": score,
                "correct_answers": correct_answers,
                "total_questions": total_questions,
                "percentage": f"{score:.1f}%",
                "completed_at": attempt.completed_at.isoformat(),
                "time_taken_minutes": time_taken_minutes,
                "topic_performance": topic_performance,
                "recommendations": self._generate_recommendations(topic_performance, score)
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error completing attempt: {e}")
            return {"error": str(e)}
    
    def _calculate_topic_performance(self, attempt_id: int) -> List[Dict[str, Any]]:
        """Calculate topic-wise performance"""
        # Get all questions and answers for this attempt
        answers = self.db.query(
            StudentAnswer,
            Question.topic
        ).join(
            Question, StudentAnswer.question_id == Question.id
        ).filter(
            StudentAnswer.attempt_id == attempt_id
        ).all()
        
        # Group by topic
        topic_stats = {}
        for answer, topic in answers:
            if topic not in topic_stats:
                topic_stats[topic] = {"total": 0, "correct": 0}
            
            topic_stats[topic]["total"] += 1
            if answer.is_correct:
                topic_stats[topic]["correct"] += 1
        
        # Format results
        performance = []
        for topic, stats in topic_stats.items():
            accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
            performance.append({
                "topic": topic,
                "total_questions": stats["total"],
                "correct_answers": stats["correct"],
                "accuracy": accuracy,
                "performance": self._get_performance_level(accuracy)
            })
        
        return sorted(performance, key=lambda x: x["accuracy"])
    
    def _get_performance_level(self, accuracy: float) -> str:
        """Get performance level based on accuracy"""
        if accuracy >= 80:
            return "Excellent"
        elif accuracy >= 70:
            return "Good"
        elif accuracy >= 60:
            return "Fair"
        else:
            return "Needs Improvement"
    
    def _generate_recommendations(
        self, 
        topic_performance: List[Dict[str, Any]], 
        overall_score: float
    ) -> List[str]:
        """Generate study recommendations"""
        recommendations = []
        
        # Overall performance
        if overall_score >= 80:
            recommendations.append("Excellent performance! Keep up the good work.")
        elif overall_score >= 70:
            recommendations.append("Good performance. Review areas for improvement.")
        else:
            recommendations.append("Focus on understanding key concepts. Practice more.")
        
        # Topic-specific recommendations
        weak_topics = [tp for tp in topic_performance if tp["accuracy"] < 70]
        if weak_topics:
            weak_topic_names = ", ".join([tp["topic"] for tp in weak_topics[:3]])
            recommendations.append(f"Focus on improving in: {weak_topic_names}")
        
        # Study tips
        recommendations.append("Review incorrect answers to understand mistakes.")
        recommendations.append("Practice regularly to improve retention.")
        
        return recommendations
    
    def get_attempt_history(
        self, 
        student_id: int, 
        skip: int = 0, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get student's quiz attempt history
        
        Args:
            student_id: Student ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of attempt history
        """
        try:
            attempts = self.db.query(
                StudentAttempt,
                Quiz.title,
                Quiz.total_questions
            ).join(
                Quiz, StudentAttempt.quiz_id == Quiz.id
            ).filter(
                StudentAttempt.student_id == student_id,
                StudentAttempt.completed_at.isnot(None)
            ).order_by(
                desc(StudentAttempt.completed_at)
            ).offset(skip).limit(limit).all()
            
            history = []
            for attempt, quiz_title, total_questions in attempts:
                # Get topic performance for this attempt
                topic_performance = self._calculate_topic_performance(attempt.id)
                
                history.append({
                    "attempt_id": attempt.id,
                    "quiz_id": attempt.quiz_id,
                    "quiz_title": quiz_title,
                    "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
                    "score": attempt.score,
                    "total_questions": total_questions,
                    "correct_answers": int((attempt.score or 0) / 100 * total_questions) if attempt.score else 0,
                    "time_taken_minutes": (
                        (attempt.completed_at - attempt.started_at).total_seconds() / 60
                        if attempt.completed_at and attempt.started_at else 0
                    ),
                    "topic_performance": topic_performance
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting attempt history: {e}")
            return []
    
    def get_student_progress(self, student_id: int) -> Dict[str, Any]:
        """
        Get student's overall progress
        
        Args:
            student_id: Student ID
            
        Returns:
            Student progress information
        """
        try:
            # Get all completed attempts
            attempts = self.db.query(StudentAttempt).filter(
                StudentAttempt.student_id == student_id,
                StudentAttempt.completed_at.isnot(None)
            ).all()
            
            if not attempts:
                return {
                    "student_id": student_id,
                    "total_attempts": 0,
                    "message": "No quiz attempts yet"
                }
            
            # Calculate statistics
            total_attempts = len(attempts)
            avg_score = sum(a.score for a in attempts if a.score) / total_attempts
            best_score = max(a.score for a in attempts if a.score)
            
            # Get topic mastery
            topic_mastery = self._calculate_topic_mastery(student_id)
            
            # Get progress over time
            progress_timeline = self._get_progress_timeline(student_id)
            
            # Calculate consistency
            consistency_score = self._calculate_consistency_score(attempts)
            
            # Get recommendations
            recommendations = self._get_progress_recommendations(
                avg_score, 
                topic_mastery, 
                consistency_score
            )
            
            return {
                "student_id": student_id,
                "statistics": {
                    "total_attempts": total_attempts,
                    "average_score": avg_score,
                    "best_score": best_score,
                    "consistency_score": consistency_score
                },
                "topic_mastery": topic_mastery,
                "progress_timeline": progress_timeline,
                "strengths": self._identify_strengths(topic_mastery),
                "areas_for_improvement": self._identify_weak_areas(topic_mastery),
                "recommendations": recommendations,
                "next_steps": self._suggest_next_steps(topic_mastery, attempts)
            }
            
        except Exception as e:
            logger.error(f"Error getting student progress: {e}")
            return {"error": str(e)}
    
    def _calculate_topic_mastery(self, student_id: int) -> List[Dict[str, Any]]:
        """Calculate topic mastery across all attempts"""
        # Get all questions answered by student
        answers = self.db.query(
            StudentAnswer,
            Question.topic
        ).join(
            Question, StudentAnswer.question_id == Question.id
        ).join(
            StudentAttempt, StudentAnswer.attempt_id == StudentAttempt.id
        ).filter(
            StudentAttempt.student_id == student_id,
            StudentAttempt.completed_at.isnot(None)
        ).all()
        
        # Group by topic
        topic_stats = {}
        for answer, topic in answers:
            if topic not in topic_stats:
                topic_stats[topic] = {"total": 0, "correct": 0}
            
            topic_stats[topic]["total"] += 1
            if answer.is_correct:
                topic_stats[topic]["correct"] += 1
        
        # Calculate mastery levels
        mastery_levels = []
        for topic, stats in topic_stats.items():
            accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
            
            if accuracy >= 90:
                mastery = "Mastered"
            elif accuracy >= 80:
                mastery = "Proficient"
            elif accuracy >= 70:
                mastery = "Competent"
            elif accuracy >= 60:
                mastery = "Developing"
            else:
                mastery = "Beginner"
            
            mastery_levels.append({
                "topic": topic,
                "total_questions": stats["total"],
                "correct_answers": stats["correct"],
                "accuracy": accuracy,
                "mastery_level": mastery,
                "confidence": min(100, stats["total"] * 2)  # More questions = more confidence
            })
        
        return sorted(mastery_levels, key=lambda x: x["accuracy"], reverse=True)
    
    def _get_progress_timeline(self, student_id: int) -> List[Dict[str, Any]]:
        """Get progress timeline (last 10 attempts)"""
        attempts = self.db.query(StudentAttempt).filter(
            StudentAttempt.student_id == student_id,
            StudentAttempt.completed_at.isnot(None)
        ).order_by(StudentAttempt.completed_at).limit(10).all()
        
        timeline = []
        for i, attempt in enumerate(attempts, 1):
            timeline.append({
                "attempt_number": i,
                "attempt_id": attempt.id,
                "score": attempt.score,
                "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
                "trend": "improving" if i > 1 and attempt.score > attempts[i-2].score else "stable"
            })
        
        return timeline
    
    def _calculate_consistency_score(self, attempts: List[StudentAttempt]) -> float:
        """Calculate consistency score (0-100)"""
        if len(attempts) < 2:
            return 50.0  # Default for single attempt
        
        scores = [a.score for a in attempts if a.score is not None]
        if not scores:
            return 50.0
        
        avg_score = sum(scores) / len(scores)
        variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
        
        # Convert to 0-100 scale (lower variance = higher consistency)
        max_variance = 2500  # Assuming max score variance
        consistency = max(0, 100 - (variance / max_variance * 100))
        
        return consistency
    
    def _identify_strengths(self, topic_mastery: List[Dict[str, Any]]) -> List[str]:
        """Identify student's strengths"""
        strengths = []
        for topic in topic_mastery:
            if topic["mastery_level"] in ["Mastered", "Proficient"] and topic["total_questions"] >= 5:
                strengths.append(topic["topic"])
        
        return strengths[:3]  # Return top 3 strengths
    
    def _identify_weak_areas(self, topic_mastery: List[Dict[str, Any]]) -> List[str]:
        """Identify areas for improvement"""
        weak_areas = []
        for topic in topic_mastery:
            if topic["mastery_level"] in ["Beginner", "Developing"] and topic["total_questions"] >= 3:
                weak_areas.append(topic["topic"])
        
        return weak_areas[:3]  # Return top 3 weak areas
    
    def _get_progress_recommendations(
        self, 
        avg_score: float, 
        topic_mastery: List[Dict[str, Any]], 
        consistency_score: float
    ) -> List[str]:
        """Get progress recommendations"""
        recommendations = []
        
        # Score-based recommendations
        if avg_score >= 80:
            recommendations.append("Excellent overall performance. Challenge yourself with harder quizzes.")
        elif avg_score >= 70:
            recommendations.append("Good performance. Focus on consistent improvement.")
        else:
            recommendations.append("Focus on foundational concepts. Practice regularly.")
        
        # Consistency recommendations
        if consistency_score >= 80:
            recommendations.append("Great consistency in performance.")
        elif consistency_score >= 60:
            recommendations.append("Work on maintaining consistent performance.")
        else:
            recommendations.append("Try to be more consistent in your preparation.")
        
        # Topic-based recommendations
        weak_topics = [t for t in topic_mastery if t["mastery_level"] in ["Beginner", "Developing"]]
        if weak_topics:
            recommendations.append(f"Focus on improving {len(weak_topics)} weak topic(s).")
        
        return recommendations
    
    def _suggest_next_steps(
        self, 
        topic_mastery: List[Dict[str, Any]], 
        attempts: List[StudentAttempt]
    ) -> List[str]:
        """Suggest next steps for the student"""
        next_steps = []
        
        # If fewer than 5 attempts, suggest more practice
        if len(attempts) < 5:
            next_steps.append("Complete more quizzes to establish a baseline.")
        
        # Suggest focusing on weak areas
        weak_topics = [t for t in topic_mastery if t["mastery_level"] in ["Beginner", "Developing"]]
        if weak_topics:
            next_steps.append(f"Take quizzes focusing on: {', '.join([t['topic'] for t in weak_topics[:2]])}")
        
        # Suggest review of previous attempts
        next_steps.append("Review your previous attempts to understand mistakes.")
        
        # Suggest setting goals
        next_steps.append("Set specific goals for your next quiz (e.g., improve by 5%).")
        
        return next_steps
    
    def get_personalized_recommendations(self, student_id: int) -> Dict[str, Any]:
        """
        Get personalized quiz recommendations
        
        Args:
            student_id: Student ID
            
        Returns:
            Personalized recommendations
        """
        try:
            # Get student's topic mastery
            topic_mastery = self._calculate_topic_mastery(student_id)
            
            # Get available quizzes
            available_quizzes = self.get_available_quizzes(student_id, 0, 100)
            
            # Score quizzes based on student's needs
            scored_quizzes = []
            for quiz in available_quizzes:
                score = self._score_quiz_for_student(quiz, topic_mastery, student_id)
                quiz["recommendation_score"] = score
                scored_quizzes.append(quiz)
            
            # Sort by recommendation score
            scored_quizzes.sort(key=lambda x: x["recommendation_score"], reverse=True)
            
            # Categorize recommendations
            recommendations = {
                "for_improvement": [],
                "for_practice": [],
                "for_challenge": []
            }
            
            for quiz in scored_quizzes[:9]:  # Top 9 quizzes
                score = quiz["recommendation_score"]
                
                if score >= 80:
                    recommendations["for_challenge"].append(quiz)
                elif score >= 60:
                    recommendations["for_practice"].append(quiz)
                else:
                    recommendations["for_improvement"].append(quiz)
            
            return {
                "student_id": student_id,
                "total_recommendations": len(scored_quizzes),
                "recommendations": recommendations,
                "based_on": {
                    "topic_mastery": topic_mastery[:5],
                    "attempt_history": len(self.get_attempt_history(student_id, 0, 1))
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {e}")
            return {"error": str(e)}
    
    def _score_quiz_for_student(
        self, 
        quiz: Dict[str, Any], 
        topic_mastery: List[Dict[str, Any]], 
        student_id: int
    ) -> float:
        """Score a quiz for recommendation to a student"""
        score = 50.0  # Base score
        
        # Check if already attempted
        if quiz["previously_attempted"]:
            score -= 20  # Penalize already attempted quizzes
        
        # Check difficulty match
        difficulty_dist = quiz.get("difficulty_distribution", {})
        easy_pct = difficulty_dist.get("easy", 0)
        hard_pct = difficulty_dist.get("hard", 0)
        
        # Get student's average score
        avg_score = self._get_student_average_score(student_id)
        
        if avg_score >= 80 and hard_pct > 0.3:
            score += 20  # Good challenge for high performers
        elif avg_score >= 70 and easy_pct < 0.5:
            score += 10  # Appropriate difficulty
        elif avg_score < 60 and easy_pct > 0.4:
            score += 15  # Good for improvement
        
        # Check topic alignment with weak areas
        # (This would require quiz topics, which we need to add to quiz model)
        # For now, use a simplified approach
        
        return min(100, max(0, score))
    
    def _get_student_average_score(self, student_id: int) -> float:
        """Get student's average score"""
        attempts = self.db.query(StudentAttempt).filter(
            StudentAttempt.student_id == student_id,
            StudentAttempt.score.isnot(None)
        ).all()
        
        if not attempts:
            return 50.0  # Default
        
        return sum(a.score for a in attempts) / len(attempts)