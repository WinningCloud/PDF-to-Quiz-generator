from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class QuizStatus(str, Enum):
    GENERATING = "generating"
    GENERATED = "generated"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class QuestionType(str, Enum):
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"

class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class QuizCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    pdf_id: int

class QuizUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None

class QuizResponse(BaseModel):
    id: int
    pdf_id: int
    title: str
    description: Optional[str] = None
    status: str
    total_questions: int
    difficulty_distribution: Optional[Dict[str, float]] = None
    estimated_time: Optional[int] = None
    created_by: int
    created_at: datetime
    generated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    quiz_data_path: Optional[str] = None
    
    class Config:
        from_attributes = True

class QuestionBase(BaseModel):
    question_text: str
    question_type: str
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: Optional[str] = None
    difficulty: str = "medium"
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    page_reference: Optional[int] = None

class QuestionCreate(QuestionBase):
    quiz_id: int
    validation_score: Optional[float] = None
    confidence_score: Optional[float] = None
    chunk_id: Optional[str] = None

class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    is_active: Optional[bool] = None

class QuestionResponse(QuestionBase):
    id: int
    quiz_id: int
    validation_score: Optional[float] = None
    confidence_score: Optional[float] = None
    question_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    pdf_metadata: Optional[Dict] = Field(None, validation_alias="metadata", serialization_alias="metadata")
    
    class Config:
        from_attributes = True

# ADD THIS MISSING CLASS
class QuestionWithTopics(QuestionResponse):
    topics: List[str] = []  # List of topic names associated with this question
    
    class Config:
        from_attributes = True

class TopicResponse(BaseModel):
    id: int
    quiz_id: int
    topic_name: str
    subtopics: List[str]
    subtopic_count: int
    question_count: int
    average_difficulty: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class QuizWithQuestions(BaseModel):
    quiz: QuizResponse
    questions: List[QuestionResponse]  # Could also use List[QuestionWithTopics] if you want topics with questions
    topics: List[TopicResponse]
    
    class Config:
        from_attributes = True

class QuizSummary(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    total_questions: int
    difficulty_distribution: Dict[str, float]
    estimated_time: int
    published_at: Optional[datetime] = None
    previously_attempted: bool = False
    previous_score: Optional[float] = None
    statistics: Dict[str, Any]
    
    class Config:
        from_attributes = True

class QuizAttempt(BaseModel):
    attempt_id: int
    quiz: Dict[str, Any]
    questions: List[Dict[str, Any]]
    started_at: datetime
    time_limit_minutes: int
    
    class Config:
        from_attributes = True

class QuizResult(BaseModel):
    attempt_id: int
    quiz_id: int
    quiz_title: str
    student_id: int
    score: float
    correct_answers: int
    total_questions: int
    percentage: str
    completed_at: datetime
    time_taken_minutes: float
    topic_performance: List[Dict[str, Any]]
    recommendations: List[str]
    
    class Config:
        from_attributes = True

class StudentProgress(BaseModel):
    student_id: int
    statistics: Dict[str, Any]
    topic_mastery: List[Dict[str, Any]]
    progress_timeline: List[Dict[str, Any]]
    strengths: List[str]
    areas_for_improvement: List[str]
    recommendations: List[str]
    next_steps: List[str]
    
    class Config:
        from_attributes = True
