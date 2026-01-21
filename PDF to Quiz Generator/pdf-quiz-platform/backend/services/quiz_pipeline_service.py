# import os
# import logging
# from typing import Dict, List, Any, Optional
# from datetime import datetime
# import json

# from sqlalchemy.orm import Session

# from core.pdf_ingestion import PDFIngestion, PDFMetadata
# from core.page_chunker import PageChunker, Chunk
# from core.embeddings import EmbeddingManager
# from core.entity_extraction import EntityExtractor
# from core.topic_normalization import TopicNormalizer
# from core.question_generation import QuestionGenerator
# from core.question_validation import QuestionValidator
# from core.deduplication import Deduplicator
# from core.quiz_formatter import QuizFormatter
# from agents.pdf_agent import PDFAgent
# from agents.topic_agent import TopicAgent
# from agents.question_agent import QuestionAgent
# from agents.validation_agent import ValidationAgent
# from agents.dedup_agent import DeduplicationAgent
# from agents.formatter_agent import FormatterAgent
# #updated imports (2):
# from agents.planner_agent import PlannerAgent 
# from agents.pdf_agent import PDFAgent

# from db.models import PDFDocument, Quiz, Question, Topic, Chunk as DBChunk
# from config.settings import settings


# logger = logging.getLogger(__name__)

# class QuizPipelineService:
#     def __init__(self, db: Session):
#         self.db = db
#         self.setup_directories()
        
#         # Initialize core components
#         self.pdf_ingestion = PDFIngestion(
#             upload_dir=settings.UPLOAD_DIR,
#             processed_dir=settings.PROCESSED_DIR
#         )
#         self.page_chunker = PageChunker(
#             overlap_ratio=settings.CHUNK_OVERLAP_RATIO,
#             max_chunk_size=settings.MAX_CHUNK_SIZE
#         )
#         self.embedding_manager = EmbeddingManager(
#             vector_index_dir=settings.VECTOR_INDEX_DIR
#         )
#         self.entity_extractor = EntityExtractor()
#         self.topic_normalizer = TopicNormalizer(
#             target_topic_count=settings.TARGET_TOPIC_COUNT
#         )
#         self.question_generator = QuestionGenerator()
#         self.question_validator = QuestionValidator(
#             validation_threshold=0.7
#         )
#         self.deduplicator = Deduplicator(
#             similarity_threshold=settings.SIMILARITY_THRESHOLD
#         )
#         self.quiz_formatter = QuizFormatter()
        
#         # Initialize agents
#         self.planner_agent = PlannerAgent()
#         self.pdf_agent = PDFAgent()
#         self.topic_agent = TopicAgent()
#         self.question_agent = QuestionAgent()
#         self.validation_agent = ValidationAgent()
#         self.dedup_agent = DeduplicationAgent(
#             similarity_threshold=settings.SIMILARITY_THRESHOLD
#         )
#         self.formatter_agent = FormatterAgent()
    
#     def setup_directories(self):
#         """Setup necessary directories"""
#         os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
#         os.makedirs(settings.PROCESSED_DIR, exist_ok=True)
#         os.makedirs(settings.CHUNKS_DIR, exist_ok=True)
#         os.makedirs(settings.QUIZZES_DIR, exist_ok=True)
#         os.makedirs(settings.VECTOR_INDEX_DIR, exist_ok=True)
    
#     def process_pdf(self, pdf_id: int, db: Session):
#         """
#         Process PDF through the full pipeline
        
#         Args:
#             pdf_id: ID of the PDF document
#             db: Database session
#         """
#         try:
#             # Get PDF document
#             pdf_doc = db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
#             if not pdf_doc:
#                 logger.error(f"PDF document {pdf_id} not found")
#                 return
            
#             # Update status
#             pdf_doc.status = "processing"
#             db.commit()
            
#             logger.info(f"Starting PDF processing for: {pdf_doc.filename}")
            
#             # Step 1: Extract text from PDF
#             logger.info("Step 1: Extracting text from PDF...")
#             pdf_metadata = self.pdf_ingestion.extract_metadata(pdf_doc.file_path)
#             pages = self.pdf_ingestion.extract_text_by_page(pdf_doc.file_path)
            
#             if not pages:
#                 raise ValueError("No text extracted from PDF")
            
#             # Save extraction results
#             extraction_path = self.pdf_ingestion.save_extraction_results(
#                 pdf_id, pdf_metadata, pages
#             )
            
#             # Step 2: Chunk pages with overlap
#             logger.info("Step 2: Chunking pages with overlap...")
#             chunks = self.page_chunker.chunk_pages_with_overlap(pages)
            
#             # Save chunks
#             chunks_path = os.path.join(
#                 settings.CHUNKS_DIR, 
#                 f"pdf_{pdf_id}_chunks.json"
#             )
#             self.page_chunker.save_chunks_to_file(chunks, chunks_path)
            
#             # Step 3: Generate embeddings
#             logger.info("Step 3: Generating embeddings...")
#             chunks_with_embeddings = self.embedding_manager.generate_embeddings(
#                 [chunk.__dict__ for chunk in chunks]
#             )
            
#             # Create vector index
#             index_path = self.embedding_manager.create_vector_index(
#                 chunks_with_embeddings,
#                 f"pdf_{pdf_id}"
#             )
            
#             # Step 4: Extract entities and topics
#             logger.info("Step 4: Extracting entities and topics...")
#             entity_extractions = []
#             for chunk in chunks:
#                 extraction = self.entity_extractor.extract_entities_from_chunk(
#                     chunk.__dict__
#                 )
#                 entity_extractions.append(extraction)
            
#             # Consolidate entities
#             consolidated_entities = self.entity_extractor.consolidate_entities_across_chunks(
#                 entity_extractions
#             )
            
#             # Extract subtopics
#             all_subtopics = []
#             for extraction in entity_extractions:
#                 subtopics = self.entity_extractor.extract_subtopics_from_entities(
#                     consolidated_entities,
#                     extraction.get("chunk_text", "")
#                 )
#                 all_subtopics.extend(subtopics)
            
#             # Step 5: Normalize topics
#             logger.info("Step 5: Normalizing topics...")
#             normalized_topics = self.topic_normalizer.normalize_topics(all_subtopics)
            
#             # Save processing results
#             processing_results = {
#                 "pdf_id": pdf_id,
#                 "metadata": pdf_metadata.__dict__,
#                 "page_count": len(pages),
#                 "chunk_count": len(chunks),
#                 "entity_extractions": entity_extractions,
#                 "consolidated_entities": consolidated_entities,
#                 "normalized_topics": normalized_topics,
#                 "paths": {
#                     "extraction": extraction_path,
#                     "chunks": chunks_path,
#                     "index": index_path
#                 },
#                 "processed_at": datetime.utcnow().isoformat()
#             }
            
#             # Save results to file
#             results_path = os.path.join(
#                 settings.PROCESSED_DIR, 
#                 f"pdf_{pdf_id}_processing_results.json"
#             )
#             with open(results_path, 'w', encoding='utf-8') as f:
#                 json.dump(processing_results, f, indent=2, ensure_ascii=False)
            
#             # Update PDF document status
#             pdf_doc.status = "processed"
#             pdf_doc.processed_at = datetime.utcnow()
#             pdf_doc.pdf_metadata = json.dumps({  #changed from .metadata to .pfd_metadata to match with db model
#                 "page_count": len(pages),
#                 "chunk_count": len(chunks),
#                 "topic_count": len(normalized_topics.get("normalized_topics", [])),
#                 "processing_results_path": results_path
#             })
#             db.commit()
            
#             logger.info(f"PDF processing complete: {pdf_doc.filename}")
            
#         except Exception as e:
#             logger.error(f"Error processing PDF {pdf_id}: {e}")
            
#             # Update status to failed
#             pdf_doc = db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
#             if pdf_doc:
#                 pdf_doc.status = "failed"
#                 pdf_doc.error_message = str(e)
#                 db.commit()
    
#     def generate_quiz_from_pdf(self, pdf_id: int, quiz_id: int, db: Session):
#         """
#         Generate quiz from processed PDF
        
#         Args:
#             pdf_id: ID of the PDF document
#             quiz_id: ID of the quiz record
#             db: Database session
#         """
#         try:
#             # Get PDF document
#             pdf_doc = db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
#             if not pdf_doc or pdf_doc.status != "processed":
#                 raise ValueError("PDF not processed or not found")
            
#             # Get quiz record
#             quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
#             if not quiz:
#                 raise ValueError("Quiz not found")
            
#             # Update quiz status
#             quiz.status = "generating"
#             db.commit()
            
#             logger.info(f"Starting quiz generation for PDF: {pdf_doc.filename}")
            
#             # Load processing results
#             processing_results_path = os.path.join(
#                 settings.PROCESSED_DIR, 
#                 f"pdf_{pdf_id}_processing_results.json"
#             )
            
#             with open(processing_results_path, 'r', encoding='utf-8') as f:
#                 processing_results = json.load(f)
            
#             # Load chunks
#             chunks_path = processing_results["paths"]["chunks"]
#             with open(chunks_path, 'r', encoding='utf-8') as f:
#                 chunk_dicts = json.load(f)
            
#             chunks = [Chunk(**chunk_dict) for chunk_dict in chunk_dicts]
            
#             # Step 1: Plan quiz generation
#             logger.info("Step 1: Planning quiz generation...")
#             content_summary = self.pdf_agent.extract_key_information(
#                 [chunk.__dict__ for chunk in chunks]
#             )
            
#             quiz_plan = self.planner_agent.plan_quiz_generation(
#                 len(chunks),
#                 content_summary.get("summary", "")
#             )
            
#             chunk_assignments = self.planner_agent.assign_questions_to_chunks(
#                 [chunk.__dict__ for chunk in chunks],
#                 quiz_plan
#             )
            
#             # Step 2: Generate questions
#             logger.info("Step 2: Generating questions...")
#             generated_questions = self.question_agent.generate_questions_batch(
#                 chunk_assignments,
#                 processing_results["normalized_topics"]
#             )
            
#             # Step 3: Enrich questions with topics
#             logger.info("Step 3: Enriching questions with topics...")
#             enriched_questions = self.question_agent.enrich_questions_with_metadata(
#                 generated_questions,
#                 processing_results["normalized_topics"]
#             )
            
#             # Step 4: Validate questions
#             logger.info("Step 4: Validating questions...")
#             chunks_dict = {chunk.chunk_id: chunk.text for chunk in chunks}
#             validated_questions, needs_review, invalid_questions = \
#                 self.validation_agent.validate_questions_batch(
#                     enriched_questions,
#                     chunks_dict
#                 )
            
#             # Step 5: Regenerate failed questions
#             logger.info("Step 5: Regenerating failed questions...")
#             regenerated_questions = self.question_validator.regenerate_failed_questions(
#                 invalid_questions,
#                 [chunk.__dict__ for chunk in chunks]
#             )
            
#             # Re-validate regenerated questions
#             if regenerated_questions:
#                 revalidated, _, _ = self.validation_agent.validate_questions_batch(
#                     regenerated_questions,
#                     chunks_dict
#                 )
#                 validated_questions.extend(revalidated)
            
#             # Step 6: Deduplicate questions
#             logger.info("Step 6: Deduplicating questions...")
#             unique_questions, duplicates, dedup_stats = self.dedup_agent.deduplicate_questions(
#                 validated_questions
#             )
            
#             # Step 7: Map questions to normalized topics
#             logger.info("Step 7: Mapping questions to topics...")
#             topic_mapping = processing_results["normalized_topics"].get("topic_mapping", {})
#             questions_with_topics = self.topic_normalizer.map_questions_to_normalized_topics(
#                 unique_questions,
#                 topic_mapping
#             )
            
#             # Step 8: Format quiz
#             logger.info("Step 8: Formatting quiz...")
#             quiz_config = {
#                 "title": quiz.title or f"Quiz from {pdf_doc.title}",
#                 "description": quiz.description or f"Quiz generated from {pdf_doc.filename}",
#                 "max_questions": 20,
#                 "difficulty_distribution": {
#                     "easy": 0.3,
#                     "medium": 0.5,
#                     "hard": 0.2
#                 }
#             }
            
#             formatted_quiz = self.formatter_agent.format_quiz(
#                 questions_with_topics,
#                 quiz_config
#             )
            
#             # Step 9: Save quiz
#             logger.info("Step 9: Saving quiz...")
#             self._save_quiz_to_database(
#                 quiz_id,
#                 formatted_quiz,
#                 processing_results["normalized_topics"],
#                 db
#             )
            
#             # Save quiz to file
#             quiz_path = os.path.join(
#                 settings.QUIZZES_DIR,
#                 f"quiz_{quiz_id}.json"
#             )
#             with open(quiz_path, 'w', encoding='utf-8') as f:
#                 json.dump(formatted_quiz, f, indent=2, ensure_ascii=False)
            
#             # Update quiz record
#             quiz.status = "generated"
#             quiz.total_questions = len(questions_with_topics)
#             quiz.difficulty_distribution = json.dumps(
#                 formatted_quiz["statistics"]["difficulty_distribution"]
#             )
#             quiz.quiz_data_path = quiz_path
#             quiz.generated_at = datetime.utcnow()
#             db.commit()
            
#             logger.info(f"Quiz generation complete: {quiz.title}")
            
#             # Create validation report
#             validation_report = self.question_validator.create_validation_report(
#                 validated_questions,
#                 needs_review,
#                 invalid_questions
#             )
            
#             # Create deduplication report
#             dedup_report = self.deduplicator.create_deduplication_report(
#                 len(validated_questions),
#                 len(unique_questions),
#                 len(duplicates),
#                 dedup_stats
#             )
            
#             # Save reports
#             reports = {
#                 "validation_report": validation_report,
#                 "deduplication_report": dedup_report,
#                 "generation_summary": {
#                     "total_generated": len(generated_questions),
#                     "validated": len(validated_questions),
#                     "needs_review": len(needs_review),
#                     "invalid": len(invalid_questions),
#                     "unique_after_dedup": len(unique_questions),
#                     "final_quiz_questions": len(questions_with_topics)
#                 }
#             }
            
#             reports_path = os.path.join(
#                 settings.QUIZZES_DIR,
#                 f"quiz_{quiz_id}_reports.json"
#             )
#             with open(reports_path, 'w', encoding='utf-8') as f:
#                 json.dump(reports, f, indent=2, ensure_ascii=False)
            
#         except Exception as e:
#             logger.error(f"Error generating quiz: {e}")
            
#             # Update quiz status to failed
#             quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
#             if quiz:
#                 quiz.status = "failed"
#                 quiz.error_message = str(e)
#                 db.commit()
    
#     def _save_quiz_to_database(
#         self, 
#         quiz_id: int, 
#         formatted_quiz: Dict[str, Any],
#         normalized_topics: Dict[str, Any],
#         db: Session
#     ):
#         """Save formatted quiz to database"""
#         try:
#             # Get quiz record
#             quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
#             if not quiz:
#                 raise ValueError("Quiz not found")
            
#             # Save topics
#             topic_objects = []
#             for topic_data in normalized_topics.get("normalized_topics", []):
#                 topic = Topic(
#                     quiz_id=quiz_id,
#                     topic_name=topic_data.get("topic_name"),
#                     subtopics=json.dumps(topic_data.get("subtopics", [])),
#                     subtopic_count=topic_data.get("subtopic_count", 0)
#                 )
#                 db.add(topic)
#                 topic_objects.append(topic)
            
#             db.flush()  # Get topic IDs
            
#             # Save questions
#             for i, question_data in enumerate(formatted_quiz.get("questions", []), 1):
#                 question = Question(
#                     quiz_id=quiz_id,
#                     question_text=question_data.get("question_text", ""),
#                     question_type=question_data.get("question_type", "mcq"),
#                     options=json.dumps(question_data.get("options", [])),
#                     correct_answer=question_data.get("answer", ""),
#                     explanation=question_data.get("explanation", ""),
#                     difficulty=question_data.get("difficulty", "medium"),
#                     topic=question_data.get("normalized_topic", "General"),
#                     subtopic=question_data.get("subtopic", ""),
#                     page_reference=question_data.get("page_number", 1),
#                     validation_score=question_data.get("validation_score", 0.0),
#                     question_order=i,
#                     metadata=json.dumps({
#                         "chunk_id": question_data.get("chunk_id"),
#                         "confidence_score": question_data.get("confidence_score", 0.5),
#                         "generation_source": question_data.get("generation_source", "llm")
#                     })
#                 )
#                 db.add(question)
            
#             db.commit()
#             logger.info(f"Saved quiz {quiz_id} to database")
            
#         except Exception as e:
#             logger.error(f"Error saving quiz to database: {e}")
#             db.rollback()
#             raise
    
#     def get_pipeline_status(self, pdf_id: int) -> Dict[str, Any]:
#         """
#         Get pipeline status for a PDF
        
#         Args:
#             pdf_id: PDF document ID
            
#         Returns:
#             Pipeline status information
#         """
#         pdf_doc = self.db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
#         if not pdf_doc:
#             return {"error": "PDF not found"}
        
#         status = {
#             "pdf_id": pdf_id,
#             "filename": pdf_doc.filename,
#             "status": pdf_doc.status,
#             "uploaded_at": pdf_doc.created_at.isoformat() if pdf_doc.created_at else None,
#             "processed_at": pdf_doc.processed_at.isoformat() if pdf_doc.processed_at else None,
#             "error": pdf_doc.error_message
#         }
        
#         # Add processing details if available
#         if pdf_doc.status == "processed" and pdf_doc.metadata:
#             try:
#                 metadata = json.loads(pdf_doc.metadata)
#                 status.update({
#                     "page_count": metadata.get("page_count"),
#                     "chunk_count": metadata.get("chunk_count"),
#                     "topic_count": metadata.get("topic_count")
#                 })
#             except:
#                 pass
        
#         # Check for generated quizzes
#         quizzes = self.db.query(Quiz).filter(Quiz.pdf_id == pdf_id).all()
#         status["quizzes"] = [
#             {
#                 "id": quiz.id,
#                 "title": quiz.title,
#                 "status": quiz.status,
#                 "question_count": quiz.total_questions,
#                 "generated_at": quiz.generated_at.isoformat() if quiz.generated_at else None
#             }
#             for quiz in quizzes
#         ]
        
#         return status
    
#     def run_complete_pipeline(self, pdf_id: int):
#         """
#         Run complete pipeline from PDF processing to quiz generation
        
#         Args:
#             pdf_id: PDF document ID
#         """
#         try:
#             # Process PDF
#             self.process_pdf(pdf_id, self.db)
            
#             # Check if processing was successful
#             pdf_doc = self.db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
#             if pdf_doc.status != "processed":
#                 raise ValueError(f"PDF processing failed: {pdf_doc.error_message}")
            
#             # Create quiz record
#             quiz = Quiz(
#                 pdf_id=pdf_id,
#                 title=f"Quiz from {pdf_doc.title}",
#                 description=f"Auto-generated from {pdf_doc.filename}",
#                 status="generating",
#                 created_by=pdf_doc.uploaded_by
#             )
#             self.db.add(quiz)
#             self.db.commit()
            
#             # Generate quiz
#             self.generate_quiz_from_pdf(pdf_id, quiz.id, self.db)
            
#             return {"success": True, "quiz_id": quiz.id}
            
#         except Exception as e:
#             logger.error(f"Complete pipeline failed: {e}")
#             return {"success": False, "error": str(e)}
    
#     @staticmethod
#     def get_available_pipelines() -> Dict[str, Any]:
#         """Get available pipeline configurations"""
#         return {
#             "pipelines": {
#                 "full": {
#                     "description": "Complete pipeline from PDF to quiz",
#                     "steps": [
#                         "PDF ingestion and text extraction",
#                         "Page chunking with overlap",
#                         "Embedding generation",
#                         "Entity and topic extraction",
#                         "Topic normalization",
#                         "Question generation",
#                         "Question validation",
#                         "Deduplication",
#                         "Quiz formatting"
#                     ]
#                 },
#                 "processing_only": {
#                     "description": "PDF processing only (no quiz generation)",
#                     "steps": [
#                         "PDF ingestion and text extraction",
#                         "Page chunking with overlap",
#                         "Embedding generation",
#                         "Entity and topic extraction",
#                         "Topic normalization"
#                     ]
#                 },
#                 "quiz_generation": {
#                     "description": "Quiz generation from processed PDF",
#                     "steps": [
#                         "Question generation",
#                         "Question validation",
#                         "Deduplication",
#                         "Quiz formatting"
#                     ]
#                 }
#             },
#             "configurations": {
#                 "chunk_overlap_ratio": settings.CHUNK_OVERLAP_RATIO,
#                 "max_chunk_size": settings.MAX_CHUNK_SIZE,
#                 "target_topic_count": settings.TARGET_TOPIC_COUNT,
#                 "similarity_threshold": settings.SIMILARITY_THRESHOLD,
#                 "validation_threshold": 0.7
#             }
#         }
    
#     # Add this to the end of your QuizPipelineService class
#     @staticmethod
#     def process_pdf_background(pdf_id: int):
#         """
#         Static wrapper for background tasks to ensure 
#         a fresh DB session is used.
#         """
#         print(f"DEBUG: Background task started for PDF {pdf_id}", flush=True)
#         from db.database import SessionLocal
#         db = SessionLocal()
#         try:
#             # 1. Create a fresh instance of the service with its own DB session
#             service = QuizPipelineService(db)
#             print(f"DEBUG: Service initialized, starting process_pdf", flush=True)
#             # 2. Run the actual processing
#             service.process_pdf(pdf_id, db)
#         except Exception as e:
#             print(f"DEBUG: CRITICAL ERROR IN BACKGROUND: {e}", flush=True)
#             logger.error(f"Background Process Error: {e}")
#         finally:
#             db.close()
import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from sqlalchemy.orm import Session

# Core Components
from core.pdf_ingestion import PDFIngestion, PDFMetadata
from core.page_chunker import PageChunker, Chunk
from core.embeddings import EmbeddingManager
from core.entity_extraction import EntityExtractor
from core.topic_normalization import TopicNormalizer
from core.question_generation import QuestionGenerator
from core.question_validation import QuestionValidator
from core.deduplication import Deduplicator
from core.quiz_formatter import QuizFormatter

# Agents
from agents.pdf_agent import PDFAgent
from agents.topic_agent import TopicAgent
from agents.question_agent import QuestionAgent
from agents.validation_agent import ValidationAgent
from agents.dedup_agent import DeduplicationAgent
from agents.formatter_agent import FormatterAgent
from agents.planner_agent import PlannerAgent 

# Models
from db.models import PDFDocument, Quiz, Question, Topic, Chunk as DBChunk
from config.settings import settings

logger = logging.getLogger(__name__)

class QuizPipelineService:
    def __init__(self, db: Session):
        self.db = db
        self.setup_directories()
        
        # Initialize core components
        self.pdf_ingestion = PDFIngestion(
            upload_dir=settings.UPLOAD_DIR,
            processed_dir=settings.PROCESSED_DIR
        )
        self.page_chunker = PageChunker(
            overlap_ratio=settings.CHUNK_OVERLAP_RATIO,
            max_chunk_size=settings.MAX_CHUNK_SIZE
        )
        self.embedding_manager = EmbeddingManager(
            vector_index_dir=settings.VECTOR_INDEX_DIR
        )
        self.entity_extractor = EntityExtractor()
        self.topic_normalizer = TopicNormalizer(
            target_topic_count=settings.TARGET_TOPIC_COUNT
        )
        self.question_generator = QuestionGenerator()
        self.question_validator = QuestionValidator(
            validation_threshold=0.7
        )
        self.deduplicator = Deduplicator(
            similarity_threshold=settings.SIMILARITY_THRESHOLD
        )
        self.quiz_formatter = QuizFormatter()
        
        # Initialize agents
        self.planner_agent = PlannerAgent()
        self.pdf_agent = PDFAgent()
        self.topic_agent = TopicAgent()
        self.question_agent = QuestionAgent()
        self.validation_agent = ValidationAgent()
        self.dedup_agent = DeduplicationAgent(
            similarity_threshold=settings.SIMILARITY_THRESHOLD
        )
        self.formatter_agent = FormatterAgent()
    
    def setup_directories(self):
        """Setup necessary directories using absolute paths for Docker stability"""
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(settings.PROCESSED_DIR, exist_ok=True)
        os.makedirs(settings.CHUNKS_DIR, exist_ok=True)
        os.makedirs(settings.QUIZZES_DIR, exist_ok=True)
        os.makedirs(settings.VECTOR_INDEX_DIR, exist_ok=True)
    
    def process_pdf(self, pdf_id: int):
        """Process PDF - Uses self.db and includes safety checks"""
        try:
            pdf_doc = self.db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
            if not pdf_doc:
                logger.error(f"PDF document {pdf_id} not found")
                return
            
            pdf_doc.status = "processing"
            self.db.commit()
            
            logger.info(f"Starting PDF processing for: {pdf_doc.filename}")
            
            # Step 1: Extraction
            logger.info("Step 1: Extracting text from PDF...")
            pdf_metadata = self.pdf_ingestion.extract_metadata(pdf_doc.file_path)
            pages = self.pdf_ingestion.extract_text_by_page(pdf_doc.file_path)
            
            if not pages:
                raise ValueError("No text extracted from PDF. Check if PDF is scanned/image-only.")
            
            extraction_path = self.pdf_ingestion.save_extraction_results(pdf_id, pdf_metadata, pages)
            
            # Step 2: Chunking
            logger.info("Step 2: Chunking pages...")
            chunks = self.page_chunker.chunk_pages_with_overlap(pages)
            chunks_path = os.path.join(settings.CHUNKS_DIR, f"pdf_{pdf_id}_chunks.json")
            self.page_chunker.save_chunks_to_file(chunks, chunks_path)
            
            # Step 3: Embeddings (Local Math - No Sleep Needed)
            logger.info("Step 3: Generating embeddings...")
            chunks_with_embeddings = self.embedding_manager.generate_embeddings([chunk.__dict__ for chunk in chunks])
            index_path = self.embedding_manager.create_vector_index(chunks_with_embeddings, f"pdf_{pdf_id}")
            
            # Step 4: Analysis (Local Rule-based)
            entity_extractions = [self.entity_extractor.extract_entities_from_chunk(c.__dict__) for c in chunks]
            consolidated_entities = self.entity_extractor.consolidate_entities_across_chunks(entity_extractions)
            
            all_subtopics = []
            for extraction in entity_extractions:
                subtopics = self.entity_extractor.extract_subtopics_from_entities(consolidated_entities, extraction.get("chunk_text", ""))
                all_subtopics.extend(subtopics)
            
            normalized_topics = self.topic_normalizer.normalize_topics(all_subtopics)
            
            # Step 5: Save Results
            results_path = os.path.join(settings.PROCESSED_DIR, f"pdf_{pdf_id}_processing_results.json")
            processing_results = {
                "pdf_id": pdf_id,
                "metadata": pdf_metadata.__dict__,
                "normalized_topics": normalized_topics,
                "paths": {
                    "extraction": extraction_path,
                    "chunks": chunks_path,
                    "index": index_path
                },
                "processed_at": datetime.utcnow().isoformat()
            }
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(processing_results, f, indent=2, ensure_ascii=False)
            
            # Update PDF Status
            pdf_doc.status = "processed"
            pdf_doc.processed_at = datetime.utcnow()
            # Note: Matching your DB model naming convention 'pdf_metadata'
            pdf_doc.pdf_metadata = {
                "page_count": len(pages),
                "chunk_count": len(chunks),
                "topic_count": len(normalized_topics.get("normalized_topics", [])),
                "processing_results_path": results_path
            }
            self.db.commit()
            logger.info(f"✅ PDF processing complete: {pdf_doc.filename}")
            
        except Exception as e:
            logger.error(f"❌ Error processing PDF {pdf_id}: {e}")
            self.db.rollback()
            pdf_doc = self.db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
            if pdf_doc:
                pdf_doc.status = "failed"
                pdf_doc.error_message = str(e)
                self.db.commit()

    def generate_quiz_from_pdf(self, pdf_id: int, quiz_id: int):
        """Final Battle-Tested Version - Groq Free Tier Optimized"""
        import time
        try:
            pdf_doc = self.db.query(PDFDocument).filter(PDFDocument.id == pdf_id).first()
            quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
            if not pdf_doc or not quiz: raise ValueError("PDF or Quiz not found")
            
            quiz.status = "generating"
            self.db.commit()

            results_path = os.path.join(settings.PROCESSED_DIR, f"pdf_{pdf_id}_processing_results.json")
            with open(results_path, 'r', encoding='utf-8') as f:
                processing_results = json.load(f)
            with open(processing_results["paths"]["chunks"], 'r', encoding='utf-8') as f:
                chunk_dicts = json.load(f)
            
            chunks_data = [{"text": str(c["text"]), "chunk_id": str(c["chunk_id"]), "page_number": c.get("page_number")} for c in chunk_dicts]

            # --- STEP 1: PLANNING ---
            logger.info("Step 1: Planning quiz generation...")
            chunk_summaries = []
            for chunk in chunks_data:
                try:
                    # Strip to just text for agent safety
                    analysis = self.pdf_agent.extract_key_information([{"text": chunk["text"]}])
                    summary_val = str(analysis.get("summary", analysis)) if isinstance(analysis, dict) else str(analysis)
                    chunk_summaries.append(summary_val)
                    print(f"DEBUG: Analyzed page {chunk['page_number']}", flush=True)
                except: continue
                time.sleep(3.5)
            
            full_content_summary = "\n".join(chunk_summaries)
            quiz_plan = self.planner_agent.plan_quiz_generation(len(chunks_data), full_content_summary)
            chunk_assignments = self.planner_agent.assign_questions_to_chunks(chunks_data, quiz_plan)

            # --- STEP 2: GENERATION & NORMALIZATION ---
            logger.info("Step 2: Generating questions...")
            generated_questions = []
            for assignment in chunk_assignments:
                try:
                    chunk_qs = self.question_agent.generate_questions_batch([assignment], processing_results["normalized_topics"])
                    if chunk_qs:
                        for q in chunk_qs:
                            # CRITICAL: Normalize keys before anything else sees them
                            normalized_q = {
                                "question_text": q.get("question_text") or q.get("text") or "Empty Question?",
                                "question_type": q.get("question_type") or "mcq",
                                "options": q.get("options") or {},
                                "answer": q.get("answer") or q.get("correct_answer"),
                                "explanation": q.get("explanation") or "",
                                "difficulty": q.get("difficulty") or "medium",
                                "chunk_id": str(assignment.get("chunk_id"))
                            }
                            generated_questions.append(normalized_q)
                    print(f"DEBUG: Generated {len(chunk_qs or [])} questions", flush=True)
                except: pass
                time.sleep(4) 

            if not generated_questions:
                raise ValueError("AI failed to generate any questions. Check PDF content.")

            # --- STEP 3 & 4: VALIDATION (Throttled & Non-Fatal) ---
            logger.info(f"Step 4: Validating {len(generated_questions)} questions...")
            chunks_lookup = {str(c["chunk_id"]): str(c["text"]) for c in chunks_data}
            validated_questions = []
            
            for q in generated_questions:
                try:
                    # One-by-one validation
                    v_results = self.validation_agent.validate_questions_batch([q], chunks_lookup)
                    if v_results and len(v_results[0]) > 0:
                        validated_questions.append(v_results[0][0])
                    else:
                        # Fallback: If AI fails to validate, we KEEP the question but tag it
                        q["validation_status"] = "needs_review"
                        validated_questions.append(q)
                except Exception as ve:
                    print(f"DEBUG: Validation skipped for 1 question due to 429/Error: {ve}", flush=True)
                    q["validation_status"] = "needs_review"
                    validated_questions.append(q)
                
                time.sleep(4) # Stronger sleep for the busy validation phase

            # --- STEP 6: DEDUPLICATION ---
            logger.info("Step 6: Deduplicating...")
            dedup_res = self.dedup_agent.deduplicate_questions(validated_questions)
            unique_questions = dedup_res[0] if isinstance(dedup_res, tuple) and len(dedup_res) > 0 else validated_questions

            # --- STEP 7-9: SAVE ---
            logger.info("Step 9: Saving to Database...")
            topic_mapping = processing_results["normalized_topics"].get("topic_mapping", {})
            questions_with_topics = self.topic_normalizer.map_questions_to_normalized_topics(unique_questions, topic_mapping)

            quiz_config = {"title": str(quiz.title), "description": str(quiz.description), "max_questions": 20}
            formatted_quiz = self.formatter_agent.format_quiz(questions_with_topics, quiz_config)

            self._save_quiz_to_database(quiz_id, formatted_quiz, processing_results["normalized_topics"])

            quiz.status = "generated"
            quiz.total_questions = len(questions_with_topics)
            quiz.generated_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"✅ Quiz generation complete: {quiz.title}")
            
        except Exception as e:
            import traceback
            logger.error(f"❌ CRITICAL AI ERROR:\n{traceback.format_exc()}")
            self.db.rollback()
            quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
            if quiz:
                quiz.status = "failed"
                quiz.error_message = str(e)
                self.db.commit()

    def _save_quiz_to_database(self, quiz_id: int, formatted_quiz: Dict[str, Any], normalized_topics: Dict[str, Any]):
        """Saves final quiz items to DB using self.db"""
        try:
            for topic_data in normalized_topics.get("normalized_topics", []):
                topic = Topic(
                    quiz_id=quiz_id,
                    topic_name=topic_data.get("topic_name"),
                    subtopics=json.dumps(topic_data.get("subtopics", [])),
                    subtopic_count=topic_data.get("subtopic_count", 0)
                )
                self.db.add(topic)
            
            self.db.flush() 
            
            for i, q_data in enumerate(formatted_quiz.get("questions", []), 1):
                question = Question(
                    quiz_id=quiz_id,
                    question_text=q_data.get("question_text", ""),
                    question_type=q_data.get("question_type", "mcq"),
                    options=json.dumps(q_data.get("options", [])),
                    correct_answer=q_data.get("answer", ""),
                    explanation=q_data.get("explanation", ""),
                    difficulty=q_data.get("difficulty", "medium"),
                    topic=q_data.get("normalized_topic", "General"),
                    question_order=i,
                    metadata=json.dumps({"chunk_id": q_data.get("chunk_id")})
                )
                self.db.add(question)
            
            self.db.commit()
        except Exception as e:
            logger.error(f"Error saving to DB: {e}")
            self.db.rollback()
            raise

    @staticmethod
    def process_pdf_background(pdf_id: int):
        from db.database import SessionLocal
        db = SessionLocal()
        try:
            print(f"🚀 [AI] Background process starting for PDF: {pdf_id}", flush=True)
            service = QuizPipelineService(db)
            service.process_pdf(pdf_id)
        finally:
            db.close()

    @staticmethod
    def generate_quiz_background(pdf_id: int, quiz_id: int):
        from db.database import SessionLocal
        db = SessionLocal()
        try:
            print(f"🚀 [AI] Background quiz generation starting for ID: {quiz_id}", flush=True)
            service = QuizPipelineService(db)
            service.generate_quiz_from_pdf(pdf_id, quiz_id)
        finally:
            db.close()