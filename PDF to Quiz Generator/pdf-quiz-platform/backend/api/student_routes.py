from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from db.database import get_db
from db.models import User, Quiz, Question, StudentAttempt, StudentAnswer
from schemas.quiz_schema import QuizSummary, QuizAttempt, QuizResult, StudentProgress
from schemas.student_schema import AttemptCreate, AnswerSubmit
from services.student_service import StudentService
from api.auth_routes import get_current_user

router = APIRouter()

@router.get("/quizzes/available", response_model=List[QuizSummary])
async def get_available_quizzes(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of published quizzes available to student"""
    service = StudentService(db)
    quizzes = service.get_available_quizzes(current_user.id, skip, limit)
    return quizzes

@router.get("/quiz/{quiz_id}", response_model=QuizAttempt)
async def get_quiz_for_attempt(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get quiz questions for attempt"""
    # Check if quiz exists and is published
    quiz = db.query(Quiz).filter(
        Quiz.id == quiz_id,
        Quiz.status == "published"
    ).first()
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found or not published")
    
    # Check if already attempted
    existing_attempt = db.query(StudentAttempt).filter(
        StudentAttempt.quiz_id == quiz_id,
        StudentAttempt.student_id == current_user.id,
        StudentAttempt.completed_at.is_(None)
    ).first()
    
    if existing_attempt:
        # Return existing attempt
        attempt = existing_attempt
    else:
        # Create new attempt
        attempt = StudentAttempt(
            quiz_id=quiz_id,
            student_id=current_user.id,
            started_at=datetime.utcnow(),
            status="in_progress"
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    
    # Get quiz questions
    questions = db.query(Question).filter(
        Question.quiz_id == quiz_id,
        Question.is_active == True
    ).order_by(Question.question_order).all()
    
    return {
        "attempt_id": attempt.id,
        "quiz": quiz,
        "questions": questions,
        "started_at": attempt.started_at
    }

@router.post("/attempt/{attempt_id}/answer")
async def submit_answer(
    attempt_id: int,
    answer_data: AnswerSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit answer for a question in attempt"""
    # Verify attempt belongs to student
    attempt = db.query(StudentAttempt).filter(
        StudentAttempt.id == attempt_id,
        StudentAttempt.student_id == current_user.id
    ).first()
    
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    
    if attempt.completed_at:
        raise HTTPException(status_code=400, detail="Attempt already completed")
    
    # Check if answer already exists
    existing_answer = db.query(StudentAnswer).filter(
        StudentAnswer.attempt_id == attempt_id,
        StudentAnswer.question_id == answer_data.question_id
    ).first()
    
    if existing_answer:
        # Update existing answer
        existing_answer.selected_option = answer_data.selected_option
        existing_answer.answer_text = answer_data.answer_text
        existing_answer.answered_at = datetime.utcnow()
        db.commit()
        return existing_answer
    else:
        # Create new answer
        answer = StudentAnswer(
            attempt_id=attempt_id,
            question_id=answer_data.question_id,
            selected_option=answer_data.selected_option,
            answer_text=answer_data.answer_text,
            answered_at=datetime.utcnow()
        )
        db.add(answer)
        db.commit()
        db.refresh(answer)
        return answer

@router.post("/attempt/{attempt_id}/complete", response_model=QuizResult)
async def complete_attempt(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Complete the quiz attempt and get results"""
    service = StudentService(db)
    result = service.complete_attempt(attempt_id, current_user.id)
    return result

@router.get("/attempts/history", response_model=List[QuizResult])
async def get_attempt_history(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get student's quiz attempt history"""
    service = StudentService(db)
    attempts = service.get_attempt_history(current_user.id, skip, limit)
    return attempts

@router.get("/progress", response_model=StudentProgress)
async def get_student_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get student's learning progress and analytics"""
    service = StudentService(db)
    progress = service.get_student_progress(current_user.id)
    return progress

@router.get("/topic/performance")
async def get_topic_performance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get student's performance by topic"""
    service = StudentService(db)
    performance = service.get_topic_performance(current_user.id)
    return performance

@router.get("/recommendations")
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized quiz recommendations"""
    service = StudentService(db)
    recommendations = service.get_recommendations(current_user.id)
    return recommendations