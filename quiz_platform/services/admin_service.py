import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
import os
from quiz_platform.db.models import (
    User, PDFDocument, Quiz, Question, Topic, 
    StudentAttempt, StudentAnswer
)
from quiz_platform.schemas.pdf_schema import PDFResponse, QuizResponse
from quiz_platform.schemas.quiz_schema import QuizWithQuestions
from quiz_platform.config.settings import settings

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get system overview statistics"""
        try:
            # Count users
            total_users = self.db.query(User).count()
            admin_users = self.db.query(User).filter(User.is_admin == True).count()
            student_users = total_users - admin_users
            
            # Count PDFs
            total_pdfs = self.db.query(PDFDocument).count()
            processed_pdfs = self.db.query(PDFDocument).filter(
                PDFDocument.status == "processed"
            ).count()
            
            # Count quizzes
            total_quizzes = self.db.query(Quiz).count()
            published_quizzes = self.db.query(Quiz).filter(
                Quiz.status == "published"
            ).count()
            
            # Count questions
            total_questions = self.db.query(Question).count()
            
            # Count attempts
            total_attempts = self.db.query(StudentAttempt).count()
            completed_attempts = self.db.query(StudentAttempt).filter(
                StudentAttempt.completed_at.isnot(None)
            ).count()
            
            # Recent activity
            recent_pdfs = self.db.query(PDFDocument).order_by(
                desc(PDFDocument.created_at)
            ).limit(5).all()
            
            recent_quizzes = self.db.query(Quiz).order_by(
                desc(Quiz.created_at)
            ).limit(5).all()
            
            # Calculate statistics
            pdf_processing_rate = (processed_pdfs / total_pdfs * 100) if total_pdfs > 0 else 0
            quiz_completion_rate = (completed_attempts / total_attempts * 100) if total_attempts > 0 else 0
            
            return {
                "user_statistics": {
                    "total_users": total_users,
                    "admin_users": admin_users,
                    "student_users": student_users,
                    "new_users_today": self._count_new_users_today()
                },
                "pdf_statistics": {
                    "total_pdfs": total_pdfs,
                    "processed_pdfs": processed_pdfs,
                    "processing_rate": f"{pdf_processing_rate:.1f}%",
                    "failed_pdfs": self.db.query(PDFDocument).filter(
                        PDFDocument.status == "failed"
                    ).count()
                },
                "quiz_statistics": {
                    "total_quizzes": total_quizzes,
                    "published_quizzes": published_quizzes,
                    "generating_quizzes": self.db.query(Quiz).filter(
                        Quiz.status == "generating"
                    ).count(),
                    "average_questions_per_quiz": total_questions / total_quizzes if total_quizzes > 0 else 0
                },
                "activity_statistics": {
                    "total_attempts": total_attempts,
                    "completed_attempts": completed_attempts,
                    "completion_rate": f"{quiz_completion_rate:.1f}%",
                    "average_score": self._calculate_average_score()
                },
                "recent_activity": {
                    "recent_pdfs": [
                        {
                            "id": pdf.id,
                            "filename": pdf.filename,
                            "status": pdf.status,
                            "uploaded_at": pdf.created_at.isoformat() if pdf.created_at else None
                        }
                        for pdf in recent_pdfs
                    ],
                    "recent_quizzes": [
                        {
                            "id": quiz.id,
                            "title": quiz.title,
                            "status": quiz.status,
                            "question_count": quiz.total_questions
                        }
                        for quiz in recent_quizzes
                    ]
                },
                "system_health": {
                    "database": "healthy",
                    "storage": self._check_storage_health(),
                    "api": "healthy",
                    "last_updated": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            return {"error": str(e)}
    
    def _count_new_users_today(self) -> int:
        """Count new users registered today"""
        today = datetime.utcnow().date()
        return self.db.query(User).filter(
            func.date(User.created_at) == today
        ).count()
    
    def _calculate_average_score(self) -> float:
        """Calculate average quiz score"""
        completed_attempts = self.db.query(StudentAttempt).filter(
            StudentAttempt.completed_at.isnot(None),
            StudentAttempt.score.isnot(None)
        ).all()
        
        if not completed_attempts:
            return 0.0
        
        total_score = sum(attempt.score for attempt in completed_attempts)
        return total_score / len(completed_attempts)
    
    def _check_storage_health(self) -> Dict[str, Any]:
        """Check storage health"""
        import os
        import shutil
        
        total, used, free = shutil.disk_usage("/")
        
        return {
            "total_gb": total // (2**30),
            "used_gb": used // (2**30),
            "free_gb": free // (2**30),
            "usage_percentage": (used / total) * 100
        }
    
    def get_pdf_analytics(self, pdf_id: Optional[int] = None) -> Dict[str, Any]:
        """Get PDF analytics"""
        try:
            if pdf_id:
                # Get specific PDF analytics
                pdf = self.db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
                if not pdf:
                    return {"error": "PDF not found"}
                
                quizzes = self.db.query(Quiz).filter(Quiz.pdf_id == pdf_id).all()
                
                return {
                    "pdf_id": pdf.id,
                    "filename": pdf.filename,
                    "title": pdf.title,
                    "status": pdf.status,
                    "uploaded_at": pdf.created_at.isoformat() if pdf.created_at else None,
                    "quiz_count": len(quizzes),
                    "quizzes": [
                        {
                            "id": quiz.id,
                            "title": quiz.title,
                            "status": quiz.status,
                            "question_count": quiz.total_questions,
                            "attempt_count": self.db.query(StudentAttempt).filter(
                                StudentAttempt.quiz_id == quiz.id
                            ).count()
                        }
                        for quiz in quizzes
                    ],
                    "processing_metadata": json.loads(pdf.metadata) if pdf.metadata else {}
                }
            else:
                # Get all PDFs analytics
                pdfs = self.db.query(PDFDocument).all()
                
                analytics = []
                for pdf in pdfs:
                    quiz_count = self.db.query(Quiz).filter(Quiz.pdf_id == pdf.id).count()
                    attempt_count = self.db.query(StudentAttempt).join(Quiz).filter(
                        Quiz.pdf_id == pdf.id
                    ).count()
                    
                    analytics.append({
                        "id": pdf.id,
                        "filename": pdf.filename,
                        "title": pdf.title,
                        "status": pdf.status,
                        "uploaded_at": pdf.created_at.isoformat() if pdf.created_at else None,
                        "quiz_count": quiz_count,
                        "attempt_count": attempt_count,
                        "size_mb": os.path.getsize(pdf.file_path) / (1024 * 1024) if os.path.exists(pdf.file_path) else 0
                    })
                
                # Calculate statistics
                status_distribution = {}
                for pdf in pdfs:
                    status_distribution[pdf.status] = status_distribution.get(pdf.status, 0) + 1
                
                return {
                    "total_pdfs": len(pdfs),
                    "status_distribution": status_distribution,
                    "average_quizzes_per_pdf": sum(a["quiz_count"] for a in analytics) / len(analytics) if analytics else 0,
                    "analytics": sorted(analytics, key=lambda x: x["uploaded_at"] or "", reverse=True)
                }
                
        except Exception as e:
            logger.error(f"Error getting PDF analytics: {e}")
            return {"error": str(e)}
    
    def get_quiz_analytics(self, quiz_id: int) -> Dict[str, Any]:
        """Get quiz analytics"""
        try:
            quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
            if not quiz:
                return {"error": "Quiz not found"}
            
            # Get quiz details
            questions = self.db.query(Question).filter(Question.quiz_id == quiz_id).all()
            
            # Get attempts
            attempts = self.db.query(StudentAttempt).filter(
                StudentAttempt.quiz_id == quiz_id
            ).all()
            
            # Calculate statistics
            completed_attempts = [a for a in attempts if a.completed_at]
            
            if completed_attempts:
                scores = [a.score for a in completed_attempts if a.score is not None]
                avg_score = sum(scores) / len(scores) if scores else 0
                max_score = max(scores) if scores else 0
                min_score = min(scores) if scores else 0
            else:
                avg_score = max_score = min_score = 0
            
            # Calculate question difficulty analysis
            question_stats = []
            for question in questions:
                answers = self.db.query(StudentAnswer).join(StudentAttempt).filter(
                    StudentAnswer.question_id == question.id,
                    StudentAttempt.quiz_id == quiz_id,
                    StudentAttempt.completed_at.isnot(None)
                ).all()
                
                if answers:
                    correct = sum(1 for a in answers if a.is_correct)
                    total = len(answers)
                    accuracy = (correct / total) * 100 if total > 0 else 0
                else:
                    correct = total = accuracy = 0
                
                question_stats.append({
                    "question_id": question.id,
                    "question_text": question.question_text[:100] + "...",
                    "difficulty": question.difficulty,
                    "attempts": total,
                    "correct": correct,
                    "accuracy": accuracy
                })
            
            # Time analysis
            completion_times = []
            for attempt in completed_attempts:
                if attempt.started_at and attempt.completed_at:
                    time_taken = (attempt.completed_at - attempt.started_at).total_seconds() / 60
                    completion_times.append(time_taken)
            
            avg_time = sum(completion_times) / len(completion_times) if completion_times else 0
            
            return {
                "quiz_id": quiz.id,
                "title": quiz.title,
                "status": quiz.status,
                "total_questions": len(questions),
                "published_at": quiz.published_at.isoformat() if quiz.published_at else None,
                "attempt_statistics": {
                    "total_attempts": len(attempts),
                    "completed_attempts": len(completed_attempts),
                    "completion_rate": (len(completed_attempts) / len(attempts) * 100) if attempts else 0,
                    "average_score": avg_score,
                    "max_score": max_score,
                    "min_score": min_score
                },
                "time_statistics": {
                    "average_completion_time_minutes": avg_time,
                    "fastest_completion": min(completion_times) if completion_times else 0,
                    "slowest_completion": max(completion_times) if completion_times else 0
                },
                "question_statistics": {
                    "total_questions": len(questions),
                    "by_difficulty": {
                        "easy": len([q for q in questions if q.difficulty == "easy"]),
                        "medium": len([q for q in questions if q.difficulty == "medium"]),
                        "hard": len([q for q in questions if q.difficulty == "hard"])
                    },
                    "question_performance": question_stats
                },
                "student_performance": self._get_student_performance(quiz_id)
            }
            
        except Exception as e:
            logger.error(f"Error getting quiz analytics: {e}")
            return {"error": str(e)}
    
    def _get_student_performance(self, quiz_id: int) -> List[Dict[str, Any]]:
        """Get student performance for a quiz"""
        attempts = self.db.query(
            StudentAttempt,
            User.username,
            User.email
        ).join(
            User, StudentAttempt.student_id == User.id
        ).filter(
            StudentAttempt.quiz_id == quiz_id,
            StudentAttempt.completed_at.isnot(None)
        ).all()
        
        performance = []
        for attempt, username, email in attempts:
            # Get answers for this attempt
            answers = self.db.query(StudentAnswer).filter(
                StudentAnswer.attempt_id == attempt.id
            ).all()
            
            correct = sum(1 for a in answers if a.is_correct)
            total = len(answers)
            
            performance.append({
                "student_id": attempt.student_id,
                "username": username,
                "email": email,
                "attempt_id": attempt.id,
                "score": attempt.score,
                "correct_answers": correct,
                "total_answers": total,
                "accuracy": (correct / total * 100) if total > 0 else 0,
                "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
                "time_taken_minutes": (
                    (attempt.completed_at - attempt.started_at).total_seconds() / 60
                    if attempt.completed_at and attempt.started_at else 0
                )
            })
        
        return sorted(performance, key=lambda x: x.get("score", 0), reverse=True)
    
    def update_question(self, question_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update question (admin can amend)"""
        try:
            question = self.db.query(Question).filter(Question.id == question_id).first()
            if not question:
                return {"error": "Question not found"}
            
            # Update fields
            for field, value in update_data.items():
                if hasattr(question, field):
                    setattr(question, field, value)
            
            question.updated_at = datetime.utcnow()
            self.db.commit()
            
            return {
                "success": True,
                "message": "Question updated successfully",
                "question_id": question.id
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating question: {e}")
            return {"error": str(e)}
    
    def delete_question(self, question_id: int) -> Dict[str, Any]:
        """Delete question"""
        try:
            question = self.db.query(Question).filter(Question.id == question_id).first()
            if not question:
                return {"error": "Question not found"}
            
            self.db.delete(question)
            self.db.commit()
            
            return {
                "success": True,
                "message": "Question deleted successfully"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting question: {e}")
            return {"error": str(e)}
    
    def publish_quiz(self, quiz_id: int) -> Dict[str, Any]:
        """Publish quiz for students"""
        try:
            quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
            if not quiz:
                return {"error": "Quiz not found"}
            
            # Check if quiz has questions
            question_count = self.db.query(Question).filter(Question.quiz_id == quiz_id).count()
            if question_count == 0:
                return {"error": "Quiz has no questions"}
            
            quiz.status = "published"
            quiz.published_at = datetime.utcnow()
            self.db.commit()
            
            return {
                "success": True,
                "message": "Quiz published successfully",
                "quiz_id": quiz.id,
                "published_at": quiz.published_at.isoformat()
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error publishing quiz: {e}")
            return {"error": str(e)}
    
    def get_user_management_data(self) -> Dict[str, Any]:
        """Get user management data"""
        try:
            users = self.db.query(User).all()
            
            user_data = []
            for user in users:
                # Get user activity
                attempts = self.db.query(StudentAttempt).filter(
                    StudentAttempt.student_id == user.id
                ).count()
                
                completed = self.db.query(StudentAttempt).filter(
                    StudentAttempt.student_id == user.id,
                    StudentAttempt.completed_at.isnot(None)
                ).count()
                
                avg_score = self.db.query(func.avg(StudentAttempt.score)).filter(
                    StudentAttempt.student_id == user.id,
                    StudentAttempt.score.isnot(None)
                ).scalar() or 0
                
                user_data.append({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "activity": {
                        "total_attempts": attempts,
                        "completed_attempts": completed,
                        "average_score": float(avg_score)
                    }
                })
            
            return {
                "total_users": len(users),
                "users": sorted(user_data, key=lambda x: x["created_at"] or "", reverse=True)
            }
            
        except Exception as e:
            logger.error(f"Error getting user management data: {e}")
            return {"error": str(e)}
    
    def get_storage_analytics(self) -> Dict[str, Any]:
        """Get storage analytics"""
        import os
        import shutil
        
        try:
            # Calculate directory sizes
            directories = {
                "uploads": settings.UPLOAD_DIR,
                "processed": settings.PROCESSED_DIR,
                "chunks": settings.CHUNKS_DIR,
                "quizzes": settings.QUIZZES_DIR,
                "vector_index": settings.VECTOR_INDEX_DIR
            }
            
            sizes = {}
            for name, path in directories.items():
                if os.path.exists(path):
                    total_size = 0
                    for dirpath, dirnames, filenames in os.walk(path):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            if os.path.exists(fp):
                                total_size += os.path.getsize(fp)
                    sizes[name] = total_size / (1024 * 1024)  # Convert to MB
                else:
                    sizes[name] = 0
            
            # Get file counts
            file_counts = {}
            for name, path in directories.items():
                if os.path.exists(path):
                    file_count = 0
                    for _, _, filenames in os.walk(path):
                        file_count += len(filenames)
                    file_counts[name] = file_count
                else:
                    file_counts[name] = 0
            
            # Get disk usage
            total, used, free = shutil.disk_usage("/")
            
            return {
                "directory_sizes_mb": sizes,
                "file_counts": file_counts,
                "total_storage_mb": {
                    "total": total // (1024 * 1024),
                    "used": used // (1024 * 1024),
                    "free": free // (1024 * 1024),
                    "usage_percentage": (used / total) * 100
                },
                "recommendations": self._generate_storage_recommendations(sizes)
            }
            
        except Exception as e:
            logger.error(f"Error getting storage analytics: {e}")
            return {"error": str(e)}
    
    def _generate_storage_recommendations(self, sizes: Dict[str, float]) -> List[str]:
        """Generate storage recommendations"""
        recommendations = []
        
        # Check if any directory is getting too large
        for directory, size_mb in sizes.items():
            if size_mb > 1000:  # More than 1GB
                recommendations.append(
                    f"Consider cleaning up {directory} directory (current size: {size_mb:.1f} MB)"
                )
        
        # Overall storage warning
        total_size = sum(sizes.values())
        if total_size > 5000:  # More than 5GB total
            recommendations.append(
                f"Total storage usage is high: {total_size:.1f} MB. Consider implementing cleanup policies."
            )
        
        if not recommendations:
            recommendations.append("Storage usage is within normal limits.")
        
        return recommendations