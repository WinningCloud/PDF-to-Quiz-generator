from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import os
from .models import (
    User, PDFDocument, Quiz, Question, 
    Topic, StudentAttempt, StudentAnswer,
    Chunk, VectorIndex, SystemLog
)

# User CRUD operations
class UserCRUD:
    @staticmethod
    def get_user(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def create_user(db: Session, user_data: Dict[str, Any]) -> User:
        db_user = User(**user_data)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def update_user(db: Session, user_id: int, update_data: Dict[str, Any]) -> Optional[User]:
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            for key, value in update_data.items():
                setattr(db_user, key, value)
            db.commit()
            db.refresh(db_user)
        return db_user
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            db.delete(db_user)
            db.commit()
            return True
        return False

# PDF Document CRUD operations
class PDFDocumentCRUD:
    @staticmethod
    def get_pdf(db: Session, pdf_id: int) -> Optional[PDFDocument]:
        return db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
    
    @staticmethod
    def get_pdfs(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        user_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[PDFDocument]:
        query = db.query(PDFDocument)
        
        if user_id:
            query = query.filter(PDFDocument.uploaded_by == user_id)
        
        if status:
            query = query.filter(PDFDocument.status == status)
        
        return query.order_by(desc(PDFDocument.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def create_pdf(db: Session, pdf_data: Dict[str, Any]) -> PDFDocument:
        db_pdf = PDFDocument(**pdf_data)
        db.add(db_pdf)
        db.commit()
        db.refresh(db_pdf)
        return db_pdf
    
    @staticmethod
    def update_pdf(db: Session, pdf_id: int, update_data: Dict[str, Any]) -> Optional[PDFDocument]:
        db_pdf = db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
        if db_pdf:
            for key, value in update_data.items():
                setattr(db_pdf, key, value)
            db.commit()
            db.refresh(db_pdf)
        return db_pdf
    
    @staticmethod
    def delete_pdf(db: Session, pdf_id: int) -> bool:
        db_pdf = db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
        if db_pdf:
            db.delete(db_pdf)
            db.commit()
            return True
        return False

# Quiz CRUD operations
class QuizCRUD:
    @staticmethod
    def get_quiz(db: Session, quiz_id: int) -> Optional[Quiz]:
        return db.query(Quiz).filter(Quiz.id == quiz_id).first()
    
    @staticmethod
    def get_quizzes(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        pdf_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Quiz]:
        query = db.query(Quiz)
        
        if pdf_id:
            query = query.filter(Quiz.pdf_id == pdf_id)
        
        if user_id:
            query = query.filter(Quiz.created_by == user_id)
        
        if status:
            query = query.filter(Quiz.status == status)
        
        return query.order_by(desc(Quiz.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def create_quiz(db: Session, quiz_data: Dict[str, Any]) -> Quiz:
        db_quiz = Quiz(**quiz_data)
        db.add(db_quiz)
        db.commit()
        db.refresh(db_quiz)
        return db_quiz
    
    @staticmethod
    def update_quiz(db: Session, quiz_id: int, update_data: Dict[str, Any]) -> Optional[Quiz]:
        db_quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if db_quiz:
            for key, value in update_data.items():
                setattr(db_quiz, key, value)
            db.commit()
            db.refresh(db_quiz)
        return db_quiz
    
    @staticmethod
    def delete_quiz(db: Session, quiz_id: int) -> bool:
        db_quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if db_quiz:
            db.delete(db_quiz)
            db.commit()
            return True
        return False

# Question CRUD operations
class QuestionCRUD:
    @staticmethod
    def get_question(db: Session, question_id: int) -> Optional[Question]:
        return db.query(Question).filter(Question.id == question_id).first()
    
    @staticmethod
    def get_questions_by_quiz(
        db: Session, 
        quiz_id: int,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True
    ) -> List[Question]:
        query = db.query(Question).filter(Question.quiz_id == quiz_id)
        
        if active_only:
            query = query.filter(Question.is_active == True)
        
        return query.order_by(Question.question_order).offset(skip).limit(limit).all()
    
    @staticmethod
    def create_question(db: Session, question_data: Dict[str, Any]) -> Question:
        db_question = Question(**question_data)
        db.add(db_question)
        db.commit()
        db.refresh(db_question)
        return db_question
    
    @staticmethod
    def create_questions_batch(db: Session, questions_data: List[Dict[str, Any]]) -> List[Question]:
        questions = []
        for q_data in questions_data:
            db_question = Question(**q_data)
            db.add(db_question)
            questions.append(db_question)
        
        db.commit()
        
        # Refresh all questions to get IDs
        for q in questions:
            db.refresh(q)
        
        return questions
    
    @staticmethod
    def update_question(db: Session, question_id: int, update_data: Dict[str, Any]) -> Optional[Question]:
        db_question = db.query(Question).filter(Question.id == question_id).first()
        if db_question:
            for key, value in update_data.items():
                setattr(db_question, key, value)
            db.commit()
            db.refresh(db_question)
        return db_question
    
    @staticmethod
    def delete_question(db: Session, question_id: int) -> bool:
        db_question = db.query(Question).filter(Question.id == question_id).first()
        if db_question:
            db.delete(db_question)
            db.commit()
            return True
        return False

# Student Attempt CRUD operations
class StudentAttemptCRUD:
    @staticmethod
    def get_attempt(db: Session, attempt_id: int) -> Optional[StudentAttempt]:
        return db.query(StudentAttempt).filter(StudentAttempt.id == attempt_id).first()
    
    @staticmethod
    def get_attempts_by_student(
        db: Session,
        student_id: int,
        skip: int = 0,
        limit: int = 100,
        completed_only: bool = False
    ) -> List[StudentAttempt]:
        query = db.query(StudentAttempt).filter(StudentAttempt.student_id == student_id)
        
        if completed_only:
            query = query.filter(StudentAttempt.completed_at.isnot(None))
        
        return query.order_by(desc(StudentAttempt.started_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_attempts_by_quiz(
        db: Session,
        quiz_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[StudentAttempt]:
        return db.query(StudentAttempt).filter(
            StudentAttempt.quiz_id == quiz_id
        ).order_by(desc(StudentAttempt.started_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def create_attempt(db: Session, attempt_data: Dict[str, Any]) -> StudentAttempt:
        db_attempt = StudentAttempt(**attempt_data)
        db.add(db_attempt)
        db.commit()
        db.refresh(db_attempt)
        return db_attempt
    
    @staticmethod
    def update_attempt(db: Session, attempt_id: int, update_data: Dict[str, Any]) -> Optional[StudentAttempt]:
        db_attempt = db.query(StudentAttempt).filter(StudentAttempt.id == attempt_id).first()
        if db_attempt:
            for key, value in update_data.items():
                setattr(db_attempt, key, value)
            db.commit()
            db.refresh(db_attempt)
        return db_attempt
    
    @staticmethod
    def delete_attempt(db: Session, attempt_id: int) -> bool:
        db_attempt = db.query(StudentAttempt).filter(StudentAttempt.id == attempt_id).first()
        if db_attempt:
            db.delete(db_attempt)
            db.commit()
            return True
        return False

# Topic CRUD operations
class TopicCRUD:
    @staticmethod
    def get_topics_by_quiz(db: Session, quiz_id: int) -> List[Topic]:
        return db.query(Topic).filter(Topic.quiz_id == quiz_id).all()
    
    @staticmethod
    def create_topic(db: Session, topic_data: Dict[str, Any]) -> Topic:
        db_topic = Topic(**topic_data)
        db.add(db_topic)
        db.commit()
        db.refresh(db_topic)
        return db_topic
    
    @staticmethod
    def create_topics_batch(db: Session, topics_data: List[Dict[str, Any]]) -> List[Topic]:
        topics = []
        for t_data in topics_data:
            db_topic = Topic(**t_data)
            db.add(db_topic)
            topics.append(db_topic)
        
        db.commit()
        
        # Refresh all topics to get IDs
        for t in topics:
            db.refresh(t)
        
        return topics

# Chunk CRUD operations
class ChunkCRUD:
    @staticmethod
    def get_chunks_by_pdf(db: Session, pdf_id: int) -> List[Chunk]:
        return db.query(Chunk).filter(Chunk.pdf_id == pdf_id).all()
    
    @staticmethod
    def create_chunks_batch(db: Session, chunks_data: List[Dict[str, Any]]) -> List[Chunk]:
        chunks = []
        for c_data in chunks_data:
            db_chunk = Chunk(**c_data)
            db.add(db_chunk)
            chunks.append(db_chunk)
        
        db.commit()
        
        # Refresh all chunks to get IDs
        for c in chunks:
            db.refresh(c)
        
        return chunks

# System Log CRUD operations
class SystemLogCRUD:
    @staticmethod
    def create_log(db: Session, log_data: Dict[str, Any]) -> SystemLog:
        db_log = SystemLog(**log_data)
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return db_log
    
    @staticmethod
    def get_logs(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        level: Optional[str] = None,
        component: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[SystemLog]:
        query = db.query(SystemLog)
        
        if level:
            query = query.filter(SystemLog.level == level)
        
        if component:
            query = query.filter(SystemLog.component == component)
        
        if start_date:
            query = query.filter(SystemLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(SystemLog.created_at <= end_date)
        
        return query.order_by(desc(SystemLog.created_at)).offset(skip).limit(limit).all()