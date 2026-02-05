from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class AttemptCreate(BaseModel):
    quiz_id: int

class AnswerSubmit(BaseModel):
    question_id: int
    selected_option: Optional[str] = None
    answer_text: Optional[str] = None

class AnswerResponse(BaseModel):
    id: int
    attempt_id: int
    question_id: int
    selected_option: Optional[str] = None
    answer_text: Optional[str] = None
    is_correct: bool
    answered_at: datetime
    
    class Config:
        from_attributes = True

class AttemptResponse(BaseModel):
    id: int
    quiz_id: int
    student_id: int
    status: str
    score: Optional[float] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    time_taken_seconds: Optional[int] = None
    
    class Config:
        from_attributes = True

class TopicPerformance(BaseModel):
    topic: str
    total_questions: int
    correct_answers: int
    accuracy: float
    performance: str
    
    class Config:
        from_attributes = True

class ProgressTimeline(BaseModel):
    attempt_number: int
    attempt_id: int
    score: float
    completed_at: datetime
    trend: str
    
    class Config:
        from_attributes = True

class TopicMastery(BaseModel):
    topic: str
    total_questions: int
    correct_answers: int
    accuracy: float
    mastery_level: str
    confidence: float
    
    class Config:
        from_attributes = True

class StudentDashboard(BaseModel):
    student_id: int
    total_attempts: int
    average_score: float
    best_score: float
    recent_attempts: List[Dict[str, Any]]
    weak_topics: List[str]
    strong_topics: List[str]
    recommended_quizzes: List[Dict[str, Any]]
    study_plan: List[str]
    
    class Config:
        from_attributes = True

class Recommendation(BaseModel):
    type: str  # "for_improvement", "for_practice", "for_challenge"
    quizzes: List[Dict[str, Any]]
    reason: str
    
    class Config:
        from_attributes = True

class PersonalizedRecommendations(BaseModel):
    student_id: int
    total_recommendations: int
    recommendations: Dict[str, List[Dict[str, Any]]]
    based_on: Dict[str, Any]
    
    class Config:
        from_attributes = True