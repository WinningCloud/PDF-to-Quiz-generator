from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class PDFStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

class PDFUpload(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None

class PDFUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None

class PDFResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: str
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    uploaded_by: int
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    # metadata: Optional[Dict[str, Any]] = None 
    metadata: Optional[Dict] = Field(None, validation_alias="pdf_metadata")
    # meta_data: Optional[dict] = Field(None, alias="metadata")
    
    class Config:
        from_attributes = True
        # populate_by_name = True

class PDFProcessingResult(BaseModel):
    pdf_id: int
    status: str
    page_count: int
    chunk_count: int
    topic_count: int
    processing_time_seconds: float
    extracted_text_length: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class PDFPage(BaseModel):
    page_number: int
    text: str
    word_count: int
    has_text: bool
    tables: List[Any] = []
    images: List[Any] = []
    extraction_method: str
    
    class Config:
        from_attributes = True

class PDFMetadata(BaseModel):
    filename: str
    total_pages: int
    author: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    
    class Config:
        from_attributes = True

# Quiz-related schemas
class QuizStatus(str, Enum):
    GENERATING = "generating"
    GENERATED = "generated"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class QuizCreate(BaseModel):
    pdf_id: int
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    difficulty_distribution: Optional[Dict[str, float]] = Field(
        default={"easy": 0.3, "medium": 0.5, "hard": 0.2}
    )
    total_questions: Optional[int] = Field(default=10, ge=1, le=100)
    estimated_time: Optional[int] = Field(default=30, ge=5, le=180)  # minutes
    
    class Config:
        from_attributes = True

class QuizUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[QuizStatus] = None

class QuizResponse(BaseModel):
    id: int
    pdf_id: int
    title: str
    description: Optional[str] = None
    status: str
    total_questions: int
    difficulty_distribution: Dict[str, float]
    estimated_time: Optional[int] = None
    created_by: int
    created_at: datetime
    generated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    error_message: Optional[str] = None
    quiz_data_path: Optional[str] = None
    
    class Config:
        from_attributes = True

class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    is_active: Optional[bool] = None
    validation_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    class Config:
        from_attributes = True
