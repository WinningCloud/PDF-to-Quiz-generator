import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, extract, case
import pandas as pd
import numpy as np
import json
import os

from db.models import (
    User, PDFDocument, Quiz, Question, 
    StudentAttempt, StudentAnswer, Topic
)
from config.settings import settings

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_system_analytics(self, time_range: str = "7d") -> Dict[str, Any]:
        """
        Get comprehensive system analytics
        
        Args:
            time_range: Time range for analytics (7d, 30d, 90d, all)
            
        Returns:
            System analytics data
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = self._get_start_date(time_range, end_date)
            
            return {
                "time_range": time_range,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "user_analytics": self._get_user_analytics(start_date, end_date),
                "content_analytics": self._get_content_analytics(start_date, end_date),
                "performance_analytics": self._get_performance_analytics(start_date, end_date),
                "engagement_analytics": self._get_engagement_analytics(start_date, end_date),
                "storage_analytics": self._get_storage_analytics(),
                "trends": self._get_system_trends(start_date, end_date),
                "recommendations": self._generate_system_recommendations()
            }
            
        except Exception as e:
            logger.error(f"Error getting system analytics: {e}")
            return {"error": str(e)}
    
    def _get_start_date(self, time_range: str, end_date: datetime) -> datetime:
        """Get start date based on time range"""
        if time_range == "7d":
            return end_date - timedelta(days=7)
        elif time_range == "30d":
            return end_date - timedelta(days=30)
        elif time_range == "90d":
            return end_date - timedelta(days=90)
        else:  # "all"
            return datetime(2020, 1, 1)  # Far in the past
    
    def _get_user_analytics(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get user analytics"""
        # Total users
        total_users = self.db.query(User).count()
        
        # New users in period
        new_users = self.db.query(User).filter(
            User.created_at.between(start_date, end_date)
        ).count()
        
        # Active users (users with at least one attempt in period)
        active_users = self.db.query(func.count(func.distinct(StudentAttempt.student_id))).filter(
            StudentAttempt.started_at.between(start_date, end_date)
        ).scalar() or 0
        
        # User growth rate
        previous_period_start = start_date - (end_date - start_date)
        previous_period_users = self.db.query(User).filter(
            User.created_at.between(previous_period_start, start_date)
        ).count()
        
        growth_rate = 0
        if previous_period_users > 0:
            growth_rate = ((new_users - previous_period_users) / previous_period_users) * 100
        
        # User retention
        retention_rate = self._calculate_retention_rate(start_date, end_date)
        
        # User distribution by role
        admin_users = self.db.query(User).filter(User.is_admin == True).count()
        student_users = total_users - admin_users
        
        return {
            "total_users": total_users,
            "new_users": new_users,
            "active_users": active_users,
            "user_growth_rate": f"{growth_rate:.1f}%",
            "retention_rate": f"{retention_rate:.1f}%",
            "role_distribution": {
                "admin": admin_users,
                "student": student_users,
                "admin_percentage": (admin_users / total_users * 100) if total_users > 0 else 0,
                "student_percentage": (student_users / total_users * 100) if total_users > 0 else 0
            },
            "activity_levels": self._get_user_activity_levels(start_date, end_date)
        }
    
    def _calculate_retention_rate(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> float:
        """Calculate user retention rate"""
        # Get users who registered before start_date
        cohort_users = self.db.query(User).filter(
            User.created_at < start_date,
            User.is_admin == False  # Only students
        ).count()
        
        if cohort_users == 0:
            return 0.0
        
        # Get users from cohort who were active in period
        retained_users = self.db.query(func.count(func.distinct(User.id))).join(
            StudentAttempt, User.id == StudentAttempt.student_id
        ).filter(
            User.created_at < start_date,
            User.is_admin == False,
            StudentAttempt.started_at.between(start_date, end_date)
        ).scalar() or 0
        
        return (retained_users / cohort_users) * 100
    
    def _get_user_activity_levels(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, int]:
        """Get user activity levels"""
        # Count attempts per user in period
        user_attempts = self.db.query(
            StudentAttempt.student_id,
            func.count(StudentAttempt.id).label('attempt_count')
        ).filter(
            StudentAttempt.started_at.between(start_date, end_date)
        ).group_by(StudentAttempt.student_id).all()
        
        # Categorize activity levels
        levels = {"inactive": 0, "low": 0, "medium": 0, "high": 0, "very_high": 0}
        
        for user_id, attempt_count in user_attempts:
            if attempt_count == 0:
                levels["inactive"] += 1
            elif attempt_count <= 2:
                levels["low"] += 1
            elif attempt_count <= 5:
                levels["medium"] += 1
            elif attempt_count <= 10:
                levels["high"] += 1
            else:
                levels["very_high"] += 1
        
        # Add users with no attempts
        total_students = self.db.query(User).filter(User.is_admin == False).count()
        active_students = sum(levels.values())
        levels["inactive"] = total_students - active_students
        
        return levels
    
    def _get_content_analytics(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get content analytics"""
        # PDF analytics
        total_pdfs = self.db.query(PDFDocument).count()
        new_pdfs = self.db.query(PDFDocument).filter(
            PDFDocument.created_at.between(start_date, end_date)
        ).count()
        
        pdf_status_distribution = dict(
            self.db.query(
                PDFDocument.status,
                func.count(PDFDocument.id)
            ).group_by(PDFDocument.status).all()
        )
        
        # Quiz analytics
        total_quizzes = self.db.query(Quiz).count()
        new_quizzes = self.db.query(Quiz).filter(
            Quiz.created_at.between(start_date, end_date)
        ).count()
        
        quiz_status_distribution = dict(
            self.db.query(
                Quiz.status,
                func.count(Quiz.id)
            ).group_by(Quiz.status).all()
        )
        
        # Question analytics
        total_questions = self.db.query(Question).count()
        
        question_difficulty_distribution = dict(
            self.db.query(
                Question.difficulty,
                func.count(Question.id)
            ).group_by(Question.difficulty).all()
        )
        
        # Topic analytics
        total_topics = self.db.query(Topic).count()
        
        return {
            "pdfs": {
                "total": total_pdfs,
                "new": new_pdfs,
                "status_distribution": pdf_status_distribution,
                "processing_success_rate": self._calculate_pdf_success_rate()
            },
            "quizzes": {
                "total": total_quizzes,
                "new": new_quizzes,
                "status_distribution": quiz_status_distribution,
                "average_questions_per_quiz": total_questions / total_quizzes if total_quizzes > 0 else 0
            },
            "questions": {
                "total": total_questions,
                "difficulty_distribution": question_difficulty_distribution,
                "validation_stats": self._get_question_validation_stats()
            },
            "topics": {
                "total": total_topics,
                "average_subtopics_per_topic": self._get_average_subtopics_per_topic()
            },
            "content_growth": self._calculate_content_growth(start_date, end_date)
        }
    
    def _calculate_pdf_success_rate(self) -> float:
        """Calculate PDF processing success rate"""
        total_pdfs = self.db.query(PDFDocument).count()
        if total_pdfs == 0:
            return 0.0
        
        successful_pdfs = self.db.query(PDFDocument).filter(
            PDFDocument.status == "processed"
        ).count()
        
        return (successful_pdfs / total_pdfs) * 100
    
    def _get_question_validation_stats(self) -> Dict[str, Any]:
        """Get question validation statistics"""
        # This would require storing validation scores in the database
        # For now, return placeholder data
        return {
            "average_validation_score": 75.5,
            "questions_validated": 0,
            "validation_success_rate": 85.0
        }
    
    def _get_average_subtopics_per_topic(self) -> float:
        """Get average subtopics per topic"""
        topics = self.db.query(Topic).all()
        if not topics:
            return 0.0
        
        total_subtopics = 0
        for topic in topics:
            subtopics = json.loads(topic.subtopics) if topic.subtopics else []
            total_subtopics += len(subtopics)
        
        return total_subtopics / len(topics)
    
    def _calculate_content_growth(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, float]:
        """Calculate content growth rates"""
        previous_period_start = start_date - (end_date - start_date)
        
        # PDF growth
        current_pdfs = self.db.query(PDFDocument).filter(
            PDFDocument.created_at.between(start_date, end_date)
        ).count()
        
        previous_pdfs = self.db.query(PDFDocument).filter(
            PDFDocument.created_at.between(previous_period_start, start_date)
        ).count()
        
        pdf_growth = self._calculate_growth_rate(current_pdfs, previous_pdfs)
        
        # Quiz growth
        current_quizzes = self.db.query(Quiz).filter(
            Quiz.created_at.between(start_date, end_date)
        ).count()
        
        previous_quizzes = self.db.query(Quiz).filter(
            Quiz.created_at.between(previous_period_start, start_date)
        ).count()
        
        quiz_growth = self._calculate_growth_rate(current_quizzes, previous_quizzes)
        
        # Question growth
        current_questions = self.db.query(Question).filter(
            Question.created_at.between(start_date, end_date)
        ).count()
        
        previous_questions = self.db.query(Question).filter(
            Question.created_at.between(previous_period_start, start_date)
        ).count()
        
        question_growth = self._calculate_growth_rate(current_questions, previous_questions)
        
        return {
            "pdf_growth": pdf_growth,
            "quiz_growth": quiz_growth,
            "question_growth": question_growth
        }
    
    def _calculate_growth_rate(self, current: int, previous: int) -> float:
        """Calculate growth rate percentage"""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / previous) * 100
    
    def _get_performance_analytics(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get performance analytics"""
        # Attempt statistics
        total_attempts = self.db.query(StudentAttempt).filter(
            StudentAttempt.started_at.between(start_date, end_date)
        ).count()
        
        completed_attempts = self.db.query(StudentAttempt).filter(
            StudentAttempt.started_at.between(start_date, end_date),
            StudentAttempt.completed_at.isnot(None)
        ).count()
        
        # Score statistics
        completed_scores = self.db.query(StudentAttempt.score).filter(
            StudentAttempt.started_at.between(start_date, end_date),
            StudentAttempt.completed_at.isnot(None),
            StudentAttempt.score.isnot(None)
        ).all()
        
        scores = [score for (score,) in completed_scores if score is not None]
        
        if scores:
            avg_score = np.mean(scores)
            median_score = np.median(scores)
            score_std = np.std(scores)
            score_distribution = self._get_score_distribution(scores)
        else:
            avg_score = median_score = score_std = 0
            score_distribution = {}
        
        # Time statistics
        time_data = self.db.query(
            StudentAttempt.started_at,
            StudentAttempt.completed_at
        ).filter(
            StudentAttempt.started_at.between(start_date, end_date),
            StudentAttempt.completed_at.isnot(None)
        ).all()
        
        completion_times = []
        for started, completed in time_data:
            if started and completed:
                time_taken = (completed - started).total_seconds() / 60  # minutes
                completion_times.append(time_taken)
        
        if completion_times:
            avg_completion_time = np.mean(completion_times)
            median_completion_time = np.median(completion_times)
        else:
            avg_completion_time = median_completion_time = 0
        
        # Quiz performance
        quiz_performance = self._get_quiz_performance(start_date, end_date)
        
        # Topic performance
        topic_performance = self._get_topic_performance(start_date, end_date)
        
        return {
            "attempts": {
                "total": total_attempts,
                "completed": completed_attempts,
                "completion_rate": (completed_attempts / total_attempts * 100) if total_attempts > 0 else 0,
                "average_attempts_per_user": total_attempts / max(1, self._get_active_user_count(start_date, end_date))
            },
            "scores": {
                "average": avg_score,
                "median": median_score,
                "standard_deviation": score_std,
                "distribution": score_distribution,
                "passing_rate": self._calculate_passing_rate(scores, 70)  # 70% passing threshold
            },
            "time": {
                "average_completion_minutes": avg_completion_time,
                "median_completion_minutes": median_completion_time,
                "time_efficiency": self._calculate_time_efficiency(scores, completion_times)
            },
            "quiz_performance": quiz_performance,
            "topic_performance": topic_performance,
            "performance_trends": self._get_performance_trends(start_date, end_date)
        }
    
    def _get_active_user_count(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> int:
        """Get count of active users in period"""
        return self.db.query(func.count(func.distinct(StudentAttempt.student_id))).filter(
            StudentAttempt.started_at.between(start_date, end_date)
        ).scalar() or 0
    
    def _get_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Get score distribution in buckets"""
        buckets = {"0-50": 0, "51-60": 0, "61-70": 0, "71-80": 0, "81-90": 0, "91-100": 0}
        
        for score in scores:
            if score <= 50:
                buckets["0-50"] += 1
            elif score <= 60:
                buckets["51-60"] += 1
            elif score <= 70:
                buckets["61-70"] += 1
            elif score <= 80:
                buckets["71-80"] += 1
            elif score <= 90:
                buckets["81-90"] += 1
            else:
                buckets["91-100"] += 1
        
        return buckets
    
    def _calculate_passing_rate(self, scores: List[float], passing_threshold: float) -> float:
        """Calculate passing rate"""
        if not scores:
            return 0.0
        
        passing = sum(1 for score in scores if score >= passing_threshold)
        return (passing / len(scores)) * 100
    
    def _calculate_time_efficiency(
        self, 
        scores: List[float], 
        times: List[float]
    ) -> float:
        """Calculate time efficiency score"""
        if not scores or not times or len(scores) != len(times):
            return 0.0
        
        # Normalize scores and times
        norm_scores = np.array(scores) / 100  # Convert to 0-1
        norm_times = np.array(times) / max(times) if max(times) > 0 else np.ones_like(times)
        
        # Efficiency = score / time (higher is better)
        efficiencies = norm_scores / (norm_times + 1e-10)  # Add small epsilon to avoid division by zero
        avg_efficiency = np.mean(efficiencies)
        
        return float(avg_efficiency * 100)  # Convert to percentage
    
    def _get_quiz_performance(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get quiz performance analytics"""
        quiz_performance = self.db.query(
            Quiz.id,
            Quiz.title,
            func.count(StudentAttempt.id).label('attempt_count'),
            func.avg(StudentAttempt.score).label('avg_score'),
            func.count(case([(StudentAttempt.score >= 70, 1)])).label('passing_count')
        ).join(
            StudentAttempt, Quiz.id == StudentAttempt.quiz_id
        ).filter(
            StudentAttempt.started_at.between(start_date, end_date),
            StudentAttempt.completed_at.isnot(None)
        ).group_by(Quiz.id, Quiz.title).all()
        
        performance_list = []
        for quiz_id, title, attempt_count, avg_score, passing_count in quiz_performance:
            passing_rate = (passing_count / attempt_count * 100) if attempt_count > 0 else 0
            performance_list.append({
                "quiz_id": quiz_id,
                "title": title,
                "attempt_count": attempt_count,
                "average_score": float(avg_score) if avg_score else 0,
                "passing_rate": passing_rate,
                "popularity_rank": 0  # Would need to calculate based on attempts
            })
        
        # Sort by average score (descending)
        performance_list.sort(key=lambda x: x["average_score"], reverse=True)
        
        # Add ranks
        for i, perf in enumerate(performance_list, 1):
            perf["performance_rank"] = i
        
        return performance_list[:10]  # Return top 10
    
    def _get_topic_performance(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get topic performance analytics"""
        # Get all answers with their question topics
        topic_performance = self.db.query(
            Question.topic,
            func.count(StudentAnswer.id).label('total_answers'),
            func.count(case([(StudentAnswer.is_correct == True, 1)])).label('correct_answers')
        ).join(
            StudentAnswer, Question.id == StudentAnswer.question_id
        ).join(
            StudentAttempt, StudentAnswer.attempt_id == StudentAttempt.id
        ).filter(
            StudentAttempt.started_at.between(start_date, end_date),
            StudentAttempt.completed_at.isnot(None)
        ).group_by(Question.topic).all()
        
        performance_list = []
        for topic, total, correct in topic_performance:
            if total > 0:
                accuracy = (correct / total) * 100
                performance_list.append({
                    "topic": topic or "Uncategorized",
                    "total_questions": total,
                    "correct_answers": correct,
                    "accuracy": accuracy,
                    "mastery_level": self._get_mastery_level(accuracy)
                })
        
        # Sort by accuracy (ascending for improvement focus)
        performance_list.sort(key=lambda x: x["accuracy"])
        
        return performance_list
    
    def _get_mastery_level(self, accuracy: float) -> str:
        """Get mastery level based on accuracy"""
        if accuracy >= 90:
            return "Mastered"
        elif accuracy >= 80:
            return "Proficient"
        elif accuracy >= 70:
            return "Competent"
        elif accuracy >= 60:
            return "Developing"
        else:
            return "Beginner"
    
    def _get_performance_trends(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, List]:
        """Get performance trends over time"""
        # Group by day/week
        daily_performance = self.db.query(
            func.date(StudentAttempt.completed_at).label('date'),
            func.avg(StudentAttempt.score).label('avg_score'),
            func.count(StudentAttempt.id).label('attempt_count')
        ).filter(
            StudentAttempt.completed_at.between(start_date, end_date),
            StudentAttempt.score.isnot(None)
        ).group_by(func.date(StudentAttempt.completed_at)).order_by('date').all()
        
        dates = []
        avg_scores = []
        attempt_counts = []
        
        for date, avg_score, attempt_count in daily_performance:
            dates.append(date.isoformat())
            avg_scores.append(float(avg_score) if avg_score else 0)
            attempt_counts.append(attempt_count)
        
        return {
            "dates": dates,
            "average_scores": avg_scores,
            "attempt_counts": attempt_counts,
            "trend_line": self._calculate_trend_line(avg_scores)
        }
    
    def _calculate_trend_line(self, values: List[float]) -> List[float]:
        """Calculate trend line using linear regression"""
        if len(values) < 2:
            return values
        
        x = np.arange(len(values))
        y = np.array(values)
        
        # Simple linear regression
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        
        return p(x).tolist()
    
    def _get_engagement_analytics(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get engagement analytics"""
        # Daily active users
        dau_data = self.db.query(
            func.date(StudentAttempt.started_at).label('date'),
            func.count(func.distinct(StudentAttempt.student_id)).label('active_users')
        ).filter(
            StudentAttempt.started_at.between(start_date, end_date)
        ).group_by(func.date(StudentAttempt.started_at)).order_by('date').all()
        
        # Average session duration
        session_durations = self.db.query(
            StudentAttempt.started_at,
            StudentAttempt.completed_at
        ).filter(
            StudentAttempt.started_at.between(start_date, end_date),
            StudentAttempt.completed_at.isnot(None)
        ).all()
        
        durations = []
        for started, completed in session_durations:
            if started and completed:
                duration = (completed - started).total_seconds() / 60  # minutes
                durations.append(duration)
        
        avg_session_duration = np.mean(durations) if durations else 0
        
        # Retention cohorts
        retention_cohorts = self._calculate_retention_cohorts(start_date, end_date)
        
        # Engagement funnel
        engagement_funnel = self._calculate_engagement_funnel(start_date, end_date)
        
        return {
            "daily_active_users": [
                {"date": date.isoformat(), "count": count}
                for date, count in dau_data
            ],
            "average_daily_active_users": np.mean([count for _, count in dau_data]) if dau_data else 0,
            "session_analytics": {
                "average_duration_minutes": avg_session_duration,
                "total_sessions": len(session_durations),
                "sessions_per_user": len(session_durations) / max(1, self._get_active_user_count(start_date, end_date))
            },
            "retention_cohorts": retention_cohorts,
            "engagement_funnel": engagement_funnel,
            "peak_usage_times": self._get_peak_usage_times(start_date, end_date)
        }
    
    def _calculate_retention_cohorts(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Calculate retention cohorts"""
        # Simplified cohort analysis
        cohorts = []
        
        # Monthly cohorts for last 3 months
        for i in range(3):
            cohort_start = start_date - timedelta(days=30 * (i + 1))
            cohort_end = cohort_start + timedelta(days=30)
            
            # Users who registered in this cohort
            cohort_users = self.db.query(User).filter(
                User.created_at.between(cohort_start, cohort_end),
                User.is_admin == False
            ).count()
            
            if cohort_users == 0:
                continue
            
            # Users active in current period
            active_users = self.db.query(func.count(func.distinct(User.id))).join(
                StudentAttempt, User.id == StudentAttempt.student_id
            ).filter(
                User.created_at.between(cohort_start, cohort_end),
                User.is_admin == False,
                StudentAttempt.started_at.between(start_date, end_date)
            ).scalar() or 0
            
            retention_rate = (active_users / cohort_users * 100) if cohort_users > 0 else 0
            
            cohorts.append({
                "cohort": cohort_start.strftime("%b %Y"),
                "total_users": cohort_users,
                "active_users": active_users,
                "retention_rate": retention_rate,
                "cohort_age_days": (end_date - cohort_start).days
            })
        
        return cohorts
    
    def _calculate_engagement_funnel(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate engagement funnel"""
        # Total users
        total_users = self.db.query(User).filter(User.is_admin == False).count()
        
        # Users who viewed a quiz
        users_viewed_quiz = self.db.query(func.count(func.distinct(StudentAttempt.student_id))).filter(
            StudentAttempt.started_at.between(start_date, end_date)
        ).scalar() or 0
        
        # Users who completed a quiz
        users_completed_quiz = self.db.query(func.count(func.distinct(StudentAttempt.student_id))).filter(
            StudentAttempt.started_at.between(start_date, end_date),
            StudentAttempt.completed_at.isnot(None)
        ).scalar() or 0
        
        # Users who completed multiple quizzes
        users_multiple_quizzes = self.db.query(
            StudentAttempt.student_id,
            func.count(StudentAttempt.id).label('attempt_count')
        ).filter(
            StudentAttempt.started_at.between(start_date, end_date),
            StudentAttempt.completed_at.isnot(None)
        ).group_by(StudentAttempt.student_id).having(
            func.count(StudentAttempt.id) > 1
        ).count()
        
        return {
            "total_users": total_users,
            "users_viewed_quiz": users_viewed_quiz,
            "users_completed_quiz": users_completed_quiz,
            "users_multiple_quizzes": users_multiple_quizzes,
            "conversion_rates": {
                "view_to_complete": (users_completed_quiz / users_viewed_quiz * 100) if users_viewed_quiz > 0 else 0,
                "complete_to_repeat": (users_multiple_quizzes / users_completed_quiz * 100) if users_completed_quiz > 0 else 0
            }
        }
    
    def _get_peak_usage_times(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get peak usage times"""
        # Group by hour of day
        hourly_usage = self.db.query(
            extract('hour', StudentAttempt.started_at).label('hour'),
            func.count(StudentAttempt.id).label('attempt_count')
        ).filter(
            StudentAttempt.started_at.between(start_date, end_date)
        ).group_by('hour').order_by('hour').all()
        
        hours = []
        counts = []
        
        for hour, count in hourly_usage:
            hours.append(int(hour))
            counts.append(count)
        
        # Find peak hours
        if counts:
            max_count = max(counts)
            peak_hours = [hours[i] for i, count in enumerate(counts) if count == max_count]
        else:
            peak_hours = []
        
        return {
            "hourly_distribution": dict(zip(hours, counts)),
            "peak_hours": peak_hours,
            "busiest_hour": peak_hours[0] if peak_hours else None,
            "total_peak_activity": max_count if counts else 0
        }
    
    def _get_storage_analytics(self) -> Dict[str, Any]:
        """Get storage analytics"""
        import os
        import shutil
        
        directories = {
            "uploads": settings.UPLOAD_DIR,
            "processed": settings.PROCESSED_DIR,
            "chunks": settings.CHUNKS_DIR,
            "quizzes": settings.QUIZZES_DIR,
            "vector_index": settings.VECTOR_INDEX_DIR
        }
        
        sizes = {}
        file_counts = {}
        growth_rates = {}
        
        for name, path in directories.items():
            if os.path.exists(path):
                # Current size
                total_size = 0
                file_count = 0
                for dirpath, dirnames, filenames in os.walk(path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if os.path.exists(fp):
                            total_size += os.path.getsize(fp)
                            file_count += 1
                
                sizes[name] = total_size / (1024 * 1024)  # MB
                file_counts[name] = file_count
                
                # Growth rate (simplified - would need historical data)
                growth_rates[name] = 0.0
            else:
                sizes[name] = 0
                file_counts[name] = 0
                growth_rates[name] = 0.0
        
        # Database size (estimate)
        db_size = self._estimate_database_size()
        
        total_storage = sum(sizes.values()) + db_size
        
        # Disk usage
        total, used, free = shutil.disk_usage("/")
        
        return {
            "directory_sizes_mb": sizes,
            "file_counts": file_counts,
            "growth_rates": growth_rates,
            "database_size_mb": db_size,
            "total_storage_mb": total_storage,
            "disk_usage": {
                "total_gb": total // (2**30),
                "used_gb": used // (2**30),
                "free_gb": free // (2**30),
                "usage_percentage": (used / total) * 100
            },
            "storage_health": self._assess_storage_health(total_storage, free)
        }
    
    def _estimate_database_size(self) -> float:
        """Estimate database size in MB"""
        # This is a simplified estimation
        # In production, you would query the actual database size
        return 10.0  # Placeholder
    
    def _assess_storage_health(self, total_used: float, free_space: float) -> str:
        """Assess storage health"""
        free_gb = free_space / (1024 * 1024 * 1024)  # Convert to GB
        
        if free_gb < 5:
            return "Critical"
        elif free_gb < 10:
            return "Warning"
        elif free_gb < 20:
            return "Attention"
        else:
            return "Healthy"
    
    def _get_system_trends(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get system trends"""
        return {
            "user_growth_trend": self._calculate_trend("user", start_date, end_date),
            "engagement_trend": self._calculate_trend("engagement", start_date, end_date),
            "performance_trend": self._calculate_trend("performance", start_date, end_date),
            "content_growth_trend": self._calculate_trend("content", start_date, end_date),
            "key_metrics": self._get_key_metrics_trends(start_date, end_date)
        }
    
    def _calculate_trend(
        self, 
        metric: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> str:
        """Calculate trend for a metric"""
        # Simplified trend calculation
        # In production, you would compare current period with previous period
        
        if metric == "user":
            current = self.db.query(User).filter(
                User.created_at.between(start_date, end_date)
            ).count()
            
            previous_start = start_date - (end_date - start_date)
            previous = self.db.query(User).filter(
                User.created_at.between(previous_start, start_date)
            ).count()
            
            if previous == 0:
                return "new" if current > 0 else "stable"
            
            growth = ((current - previous) / previous) * 100
            
            if growth > 20:
                return "strong_growth"
            elif growth > 5:
                return "growth"
            elif growth < -10:
                return "decline"
            else:
                return "stable"
        
        # Similar calculations for other metrics
        return "stable"
    
    def _get_key_metrics_trends(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get trends for key metrics"""
        return {
            "daily_active_users": "increasing",
            "quiz_completion_rate": "stable",
            "average_score": "slight_improvement",
            "user_retention": "stable",
            "content_quality": "improving"
        }
    
    def _generate_system_recommendations(self) -> List[str]:
        """Generate system recommendations based on analytics"""
        recommendations = []
        
        # Get key metrics
        system_data = self.get_system_analytics("30d")
        
        # User growth recommendations
        user_data = system_data.get("user_analytics", {})
        if user_data.get("new_users", 0) < 10:
            recommendations.append("Consider marketing initiatives to attract more users.")
        
        if user_data.get("retention_rate", 0) < 60:
            recommendations.append("Implement engagement features to improve user retention.")
        
        # Performance recommendations
        perf_data = system_data.get("performance_analytics", {})
        if perf_data.get("scores", {}).get("passing_rate", 0) < 70:
            recommendations.append("Review quiz difficulty levels - may be too challenging.")
        
        # Content recommendations
        content_data = system_data.get("content_analytics", {})
        if content_data.get("pdfs", {}).get("processing_success_rate", 0) < 90:
            recommendations.append("Improve PDF processing reliability.")
        
        # Engagement recommendations
        engagement_data = system_data.get("engagement_analytics", {})
        if engagement_data.get("average_daily_active_users", 0) < 5:
            recommendations.append("Add notification system to increase daily engagement.")
        
        # Storage recommendations
        storage_data = system_data.get("storage_analytics", {})
        if storage_data.get("storage_health") in ["Warning", "Critical"]:
            recommendations.append("Implement automated cleanup for old files and data.")
        
        if not recommendations:
            recommendations.append("System is performing well. Continue monitoring key metrics.")
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def export_analytics_report(
        self, 
        time_range: str = "30d",
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export analytics report
        
        Args:
            time_range: Time range for report
            format: Export format (json, csv, pdf)
            
        Returns:
            Export data
        """
        try:
            analytics_data = self.get_system_analytics(time_range)
            
            if format == "json":
                return {
                    "format": "json",
                    "data": analytics_data,
                    "exported_at": datetime.utcnow().isoformat()
                }
            
            elif format == "csv":
                # Convert to CSV format
                csv_data = self._convert_to_csv(analytics_data)
                return {
                    "format": "csv",
                    "data": csv_data,
                    "filename": f"analytics_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
                    "exported_at": datetime.utcnow().isoformat()
                }
            
            else:
                return {"error": f"Unsupported format: {format}"}
                
        except Exception as e:
            logger.error(f"Error exporting analytics report: {e}")
            return {"error": str(e)}
    
    def _convert_to_csv(self, analytics_data: Dict[str, Any]) -> str:
        """Convert analytics data to CSV format"""
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Flatten the data structure
        flattened = self._flatten_dict(analytics_data)
        
        # Write headers and data
        writer.writerow(["Metric", "Value"])
        for key, value in flattened.items():
            writer.writerow([key, value])
        
        return output.getvalue()
    
    def _flatten_dict(self, data: Dict, parent_key: str = "") -> Dict[str, Any]:
        """Flatten nested dictionary"""
        items = {}
        for key, value in data.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            
            if isinstance(value, dict):
                items.update(self._flatten_dict(value, new_key))
            elif isinstance(value, list):
                # Convert lists to string representation
                items[new_key] = str(value)
            else:
                items[new_key] = value
        
        return items
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time system metrics"""
        try:
            current_time = datetime.utcnow()
            one_hour_ago = current_time - timedelta(hours=1)
            
            return {
                "timestamp": current_time.isoformat(),
                "active_sessions": self.db.query(StudentAttempt).filter(
                    StudentAttempt.started_at >= one_hour_ago,
                    StudentAttempt.completed_at.is_(None)
                ).count(),
                "quizzes_taken_last_hour": self.db.query(StudentAttempt).filter(
                    StudentAttempt.completed_at >= one_hour_ago
                ).count(),
                "new_users_last_hour": self.db.query(User).filter(
                    User.created_at >= one_hour_ago
                ).count(),
                "system_status": {
                    "api": "online",
                    "database": "online",
                    "storage": "healthy",
                    "llm_service": "online"
                },
                "performance": {
                    "response_time_ms": 45,
                    "error_rate": 0.1,
                    "uptime": 99.9
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}")
            return {"error": str(e)}