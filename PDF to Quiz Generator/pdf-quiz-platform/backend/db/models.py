from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime

from .database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STUDENT = "student"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    uploaded_pdfs = relationship("PDFDocument", back_populates="uploader")
    created_quizzes = relationship("Quiz", back_populates="creator")
    attempts = relationship("StudentAttempt", back_populates="student")

class PDFDocument(Base):
    __tablename__ = "pdf_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    title = Column(String(200))
    description = Column(Text)
    
    # Processing status
    status = Column(String(50), default="uploaded")  # uploaded, processing, processed, failed
    error_message = Column(Text)
    
    # Metadata (renamed to avoid SQLAlchemy conflict)
    page_count = Column(Integer)
    word_count = Column(Integer)
    # metadata = Column(JSON, nullable=True)  # Stores processing metadata (renamed from metadata)
    pdf_metadata = Column("metadata", JSON, nullable=True)

    # Relationships
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploader = relationship("User", back_populates="uploaded_pdfs")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    quizzes = relationship("Quiz", back_populates="pdf_document")

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    pdf_id = Column(Integer, ForeignKey("pdf_documents.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Quiz status
    status = Column(String(50), default="generating")  # generating, generated, published, archived
    error_message = Column(Text)
    
    # Quiz properties
    total_questions = Column(Integer, default=0)
    difficulty_distribution = Column(JSON)  # {"easy": 0.3, "medium": 0.5, "hard": 0.2}
    estimated_time = Column(Integer)  # in minutes
    
    # Storage
    quiz_data_path = Column(String(500))  # Path to generated quiz JSON
    
    # Relationships
    created_by = Column(Integer, ForeignKey("users.id"))
    creator = relationship("User", back_populates="created_quizzes")
    pdf_document = relationship("PDFDocument", back_populates="quizzes")
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    generated_at = Column(DateTime)
    published_at = Column(DateTime)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("StudentAttempt", back_populates="quiz", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    
    # Question content
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), default="mcq")  # mcq, short_answer
    options = Column(JSON)  # For MCQs: ["option1", "option2", ...]
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text)
    
    # Metadata
    difficulty = Column(String(20), default="medium")  # easy, medium, hard
    topic = Column(String(100))
    subtopic = Column(String(100))
    page_reference = Column(Integer)  # Page number in PDF
    
    # Generation info
    validation_score = Column(Float)  # 0.0 - 1.0
    confidence_score = Column(Float)  # 0.0 - 1.0
    chunk_id = Column(String(100))  # Reference to source chunk
    generation_source = Column(String(50))  # llm, fallback, regenerated
    
    # Display order
    question_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Metadata (renamed to avoid SQLAlchemy conflict)
    meta_data = Column(JSON)  # Additional metadata (renamed from metadata)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    answers = relationship("StudentAnswer", back_populates="question", cascade="all, delete-orphan")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    
    # Topic info
    topic_name = Column(String(200), nullable=False)
    subtopics = Column(JSON)  # List of subtopics
    subtopic_count = Column(Integer, default=0)
    
    # Statistics
    question_count = Column(Integer, default=0)
    average_difficulty = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    quiz = relationship("Quiz", back_populates="topics")

class StudentAttempt(Base):
    __tablename__ = "student_attempts"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Attempt status
    status = Column(String(20), default="in_progress")  # in_progress, completed, abandoned
    score = Column(Float)  # Percentage score
    
    # Timestamps
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)
    
    # Time tracking
    time_taken_seconds = Column(Integer)  # Total time taken
    
    # Metadata (renamed to avoid SQLAlchemy conflict)
    meta_data = Column(JSON)  # Additional attempt data (renamed from metadata)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")
    student = relationship("User", back_populates="attempts")
    answers = relationship("StudentAnswer", back_populates="attempt", cascade="all, delete-orphan")

class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("student_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    
    # Answer content
    selected_option = Column(String(500))  # For MCQs
    answer_text = Column(Text)  # For short answers
    is_correct = Column(Boolean)
    
    # Timestamps
    answered_at = Column(DateTime, default=func.now())
    
    # Relationships
    attempt = relationship("StudentAttempt", back_populates="answers")
    question = relationship("Question", back_populates="answers")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    pdf_id = Column(Integer, ForeignKey("pdf_documents.id"), nullable=False)
    
    # Chunk content
    chunk_id = Column(String(100), unique=True, index=True)
    text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=False)
    
    # Position info
    start_char = Column(Integer)
    end_char = Column(Integer)
    word_count = Column(Integer)
    
    # Context info
    previous_page_ref = Column(String(100))
    next_page_ref = Column(String(100))
    
    # Embeddings
    embedding = Column(JSON)  # Vector embedding
    embedding_dim = Column(Integer)
    
    # Metadata (renamed to avoid SQLAlchemy conflict)
    meta_data = Column(JSON)  # Renamed from metadata
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    pdf_document = relationship("PDFDocument")

class VectorIndex(Base):
    __tablename__ = "vector_indices"

    id = Column(Integer, primary_key=True, index=True)
    pdf_id = Column(Integer, ForeignKey("pdf_documents.id"), nullable=False)
    
    # Index info
    index_name = Column(String(200), unique=True, index=True)
    index_type = Column(String(50), default="faiss")  # faiss, pinecone, etc.
    
    # Storage
    index_path = Column(String(500))
    metadata_path = Column(String(500))
    
    # Statistics
    vector_count = Column(Integer)
    embedding_dim = Column(Integer)
    
    # Metadata (renamed to avoid SQLAlchemy conflict)
    meta_data = Column(JSON)  # Renamed from metadata
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    pdf_document = relationship("PDFDocument")

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Log info
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, DEBUG
    component = Column(String(100))  # Module/component name
    message = Column(Text, nullable=False)
    details = Column(JSON)
    
    # Context
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    pdf_id = Column(Integer, ForeignKey("pdf_documents.id"), nullable=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Relationships
    user = relationship("User")
    pdf_document = relationship("PDFDocument")
    quiz = relationship("Quiz")