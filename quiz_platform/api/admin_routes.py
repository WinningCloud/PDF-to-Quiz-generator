from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import shutil
import os
import uuid
import json


from db.database import get_db
from db.models import User, PDFDocument, Quiz, Question, Topic, StudentAttempt
from schemas.pdf_schema import PDFUpload, PDFResponse, QuizCreate, QuizResponse, QuestionUpdate
from schemas.quiz_schema import QuizWithQuestions, QuestionWithTopics
from services.admin_service import AdminService
from services.quiz_pipeline_service import QuizPipelineService
from api.auth_routes import get_current_admin_user
from config.settings import settings

router = APIRouter()

@router.post("/pdf/upload", response_model=PDFResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Upload PDF and start processing"""
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create database record
    pdf_doc = PDFDocument(
        filename=filename,
        original_filename=file.filename,
        file_path=file_path,
        title=title,
        pdf_metadata={},
        description=description,
        uploaded_by=current_user.id,
        status="uploaded"
    )
    
    db.add(pdf_doc)
    db.commit()
    db.refresh(pdf_doc)
    
    # Start processing in background
    # background_tasks.add_task(
    #     QuizPipelineService.process_pdf,
    #     pdf_doc.id,
    #     db
    # )
    background_tasks.add_task(QuizPipelineService.process_pdf_background, pdf_doc.id)
    
    return pdf_doc

@router.get("/pdf/list", response_model=List[PDFResponse])
async def list_pdfs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all uploaded PDFs"""
    pdfs = db.query(PDFDocument).order_by(PDFDocument.created_at.desc()).offset(skip).limit(limit).all()
    for pdf in pdfs:
        if isinstance(pdf.pdf_metadata, str):
            try:
                pdf.pdf_metadata = json.loads(pdf.pdf_metadata)
            except Exception:
                pdf.pdf_metadata = {}
    return pdfs

@router.get("/pdf/{pdf_id}", response_model=PDFResponse)
async def get_pdf(
    pdf_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get PDF details"""
    pdf = db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")
    return pdf

@router.post("/quiz/generate/{pdf_id}")
async def generate_quiz(
    pdf_id: int,
    quiz_data: QuizCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Generate quiz from PDF"""
    pdf = db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    if pdf.status != "processed":
        raise HTTPException(status_code=400, detail="PDF not yet processed")
    
    # Create quiz record
    quiz = Quiz(
        pdf_id=pdf_id,
        title=quiz_data.title,
        description=quiz_data.description,
        created_by=current_user.id,
        status="generating",
        total_questions=0,
        difficulty_distribution={}
    )
    
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    
    # Start quiz generation in background
    background_tasks.add_task(
        QuizPipelineService.generate_quiz_background, #changed from process quiz background
        pdf_id,
        quiz.id
    )
    
    return {"message": "Quiz generation started", "quiz_id": quiz.id}

@router.get("/quiz/list", response_model=List[QuizResponse])
async def list_quizzes(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all quizzes"""
    quizzes = db.query(Quiz).order_by(Quiz.created_at.desc()).offset(skip).limit(limit).all()
    return quizzes

@router.get("/quiz/{quiz_id}")
async def get_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Manually get questions
    questions = db.query(Question).filter(Question.quiz_id == quiz_id).all()
    
    # Build a clean response dictionary
    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "status": quiz.status,
        "questions": questions # Pydantic will serialize this list
    }

@router.put("/question/{question_id}")
async def update_question(
    question_id: int,
    question_data: QuestionUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update question (admin can amend)"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Update fields
    for field, value in question_data.dict(exclude_unset=True).items():
        setattr(question, field, value)
    
    question.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(question)
    
    return question

@router.delete("/question/{question_id}")
async def delete_question(
    question_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete question"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    db.delete(question)
    db.commit()
    
    return {"message": "Question deleted"}

@router.post("/quiz/{quiz_id}/publish")
async def publish_quiz(
    quiz_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Publish quiz for students"""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    quiz.status = "published"
    quiz.published_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Quiz published"}

@router.get("/analytics/overview")
async def get_analytics_overview(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get system analytics overview"""
    service = AdminService(db)
    return service.get_system_overview()  #changed from get analytycs overview

@router.get("/analytics/quiz/{quiz_id}")
async def get_quiz_analytics(
    quiz_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get analytics for specific quiz"""
    service = AdminService(db)
    return service.get_quiz_analytics(quiz_id)