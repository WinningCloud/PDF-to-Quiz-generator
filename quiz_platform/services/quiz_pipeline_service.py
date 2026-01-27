import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from sqlalchemy.orm import Session

# Core Components
from quiz_platform.core.pdf_ingestion import PDFIngestion, PDFMetadata
from quiz_platform.core.page_chunker import PageChunker, Chunk
from quiz_platform.core.embeddings import EmbeddingManager
from quiz_platform.core.entity_extraction import EntityExtractor
from quiz_platform.core.topic_normalization import TopicNormalizer
from quiz_platform.core.question_generation import QuestionGenerator
from quiz_platform.core.question_validation import QuestionValidator
from quiz_platform.core.deduplication import Deduplicator
from quiz_platform.core.quiz_formatter import QuizFormatter

# Agents
from quiz_platform.agents.pdf_agent import PDFAgent
from quiz_platform.agents.topic_agent import TopicAgent
from quiz_platform.agents.question_agent import QuestionAgent
from quiz_platform.agents.validation_agent import ValidationAgent
from quiz_platform.agents.dedup_agent import DeduplicationAgent
from quiz_platform.agents.formatter_agent import FormatterAgent
from quiz_platform.agents.planner_agent import PlannerAgent 

# Models
from quiz_platform.db.models import PDFDocument, Quiz, Question, Topic, Chunk as DBChunk
from quiz_platform.config.settings import settings

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


            # temp logs 
            logger.info(f"[DEBUG] Total chunks loaded from JSON: {len(chunks_data)}")

            if chunks_data:
                sample = chunks_data[0]
                logger.info(
                    f"[DEBUG] Sample chunk -> id={sample.get('chunk_id')}, page={sample.get('page_number')}, "
                    f"text_len={len(sample.get('text') or '')}"
                )
                logger.info(f"[DEBUG] Sample chunk preview:\n{(sample.get('text') or '')[:600]}")
            else:
                logger.error("[DEBUG] chunks_data is EMPTY after loading chunk file!")


            # --- STEP 1: PLANNING ---
            logger.info("Step 1: Planning quiz generation...")
            chunk_summaries = []
            for chunk in chunks_data:
                try:
                    # Strip to just text for agent safety
                    analysis = self.pdf_agent.extract_key_information([{"text": chunk["text"]}])
                    summary_val = str(analysis.get("summary", analysis)) if isinstance(analysis, dict) else str(analysis)
                    chunk_summaries.append(summary_val)
                    # temp logs 
                    logger.info(
                        f"[DEBUG] Sending chunk to pdf_agent -> id={chunk.get('chunk_id')}, "
                        f"page={chunk.get('page_number')}, text_len={len(chunk.get('text') or '')}"
                    )
                    logger.info(f"[DEBUG] Chunk preview to pdf_agent:\n{(chunk.get('text') or '')[:400]}")

                except: continue
                time.sleep(3.5)
            
            full_content_summary = "\n".join(chunk_summaries)
            quiz_plan = self.planner_agent.plan_quiz_generation(len(chunks_data), full_content_summary)
            chunk_assignments = self.planner_agent.assign_questions_to_chunks(chunks_data, quiz_plan)
            logger.info(f"[DEBUG] Quiz plan returned type={type(quiz_plan)} preview={str(quiz_plan)[:800]}")
            logger.info(f"[DEBUG] Total chunk_assignments = {len(chunk_assignments)}")

            if chunk_assignments:
                logger.info(f"[DEBUG] First assignment keys: {list(chunk_assignments[0].keys())}")
                logger.info(f"[DEBUG] First assignment preview:\n{json.dumps(chunk_assignments[0], indent=2)[:1200]}")


            # --- STEP 2: GENERATION & NORMALIZATION ---
            logger.info("Step 2: Generating questions...")
            generated_questions = []
            for assignment in chunk_assignments:
                try:
                    chunk_qs = self.question_agent.generate_questions_batch([assignment], processing_results["normalized_topics"])
                    logger.info("[DEBUG] ------------------ QUESTION GEN INPUT ------------------")
                    logger.info(f"[DEBUG] assignment chunk_id={assignment.get('chunk_id')}")
                    logger.info(f"[DEBUG] assignment keys={list(assignment.keys())}")
                    logger.info(f"[DEBUG] assignment preview:\n{json.dumps(assignment, indent=2)[:1500]}")
                    logger.info(f"[DEBUG] normalized_topics keys={list(processing_results['normalized_topics'].keys())}")
                    logger.info("[DEBUG] --------------------------------------------------------")

                    if chunk_qs:
                        for q in chunk_qs:

                            # ✅ Robustly extract chunk_id from assignment (no more None)
                            assigned_chunk_id = (
                                assignment.get("chunk_id")
                                or (assignment.get("chunk") or {}).get("chunk_id")
                                or (assignment.get("chunk_data") or {}).get("chunk_id")
                                or (assignment.get("chunk_info") or {}).get("chunk_id")
                            )

                

                            q_text = (
                                q.get("question_text")
                                or q.get("question")
                                or q.get("prompt")
                                or q.get("text")
                                or "Empty Question?"
                            )

                            q_type = (q.get("question_type") or q.get("type") or "mcq").strip().lower()
                            if "short" in q_type:
                                q_type = "short_answer"
                            elif "mcq" in q_type:
                                q_type = "mcq"

                           # ---------------- CLEAN OPTIONS ----------------
                            raw_options = q.get("options") or []
                            cleaned_options = []

                            if isinstance(raw_options, dict):
                                raw_options = list(raw_options.values())

                            if isinstance(raw_options, list):
                                for opt in raw_options:
                                    if isinstance(opt, str):
                                        cleaned_options.append(opt.strip())
                                    elif isinstance(opt, dict) and "text" in opt:
                                        cleaned_options.append(opt["text"].strip())

                            # ---------------- NORMALIZE ANSWER ----------------
                            # ---------------- NORMALIZE ANSWER ----------------
                            # ------------------ ANSWER NORMALIZATION ------------------

                            raw_answer = (
                                q.get("answer")
                                or q.get("correct_answer")
                                or q.get("correct")
                                or q.get("correctAnswer")
                            )

                            answer_text = None

                            if q_type == "mcq":
                                # If answer is a letter like A/B/C/D → map to option text
                                if isinstance(raw_answer, str) and raw_answer.strip().upper() in ["A", "B", "C", "D"]:
                                    idx = ["A", "B", "C", "D"].index(raw_answer.strip().upper())
                                    if idx < len(cleaned_options):
                                        answer_text = cleaned_options[idx]
                                # If answer already matches an option string
                                elif raw_answer in cleaned_options:
                                    answer_text = raw_answer

                            else:
                                # Short answer — just use text directly
                                answer_text = raw_answer

                            # ------------------ HARD VALIDATION ------------------

                            if q_type == "mcq":
                                if not cleaned_options:
                                    logger.warning(f"[DROP] MCQ has no options: {q_text}")
                                    continue
                                if not answer_text:
                                    logger.warning(f"[DROP] MCQ answer invalid or unmapped: {q}")
                                    continue

                            if q_type == "short_answer" and not answer_text:
                                logger.warning(f"[DROP] Short answer missing answer: {q_text}")
                                continue




                            normalized_q = {
                                "question_text": q_text,
                                "question_type": q_type,
                                "options": cleaned_options,
                                "answer": answer_text,   # ✅ USE THE FIXED ANSWER
                                "explanation": q.get("explanation") or q.get("hint") or "",
                                "difficulty": (q.get("difficulty") or "medium").lower(),
                                "chunk_id": str(assigned_chunk_id),
                            }





                            generated_questions.append(normalized_q)

                            if len(generated_questions) <= 3:
                                logger.info(
                                    f"[DEBUG] Normalized question sample:\n{json.dumps(normalized_q, indent=2)[:1200]}"
                                )


                    logger.info(f"[DEBUG] question_agent returned type={type(chunk_qs)} count={len(chunk_qs or [])}")
                    if chunk_qs:
                        logger.info(f"[DEBUG] First generated Q raw:\n{json.dumps(chunk_qs[0], indent=2)[:1200]}")

                except: pass
                time.sleep(7) 

            if not generated_questions:
                raise ValueError("AI failed to generate any questions. Check PDF content.")

            # --- STEP 3 & 4: VALIDATION (Throttled & Non-Fatal) ---
            logger.info(f"Step 4: Validating {len(generated_questions)} questions...")

            # chunk_id -> chunk_text
            chunks_lookup = {str(c["chunk_id"]): str(c["text"]) for c in chunks_data}
            validated_questions = []

            for i, q in enumerate(generated_questions, 1):
                try:
                    # ✅ Ensure chunk_id is valid
                    chunk_id_key = str(q.get("chunk_id")) if q.get("chunk_id") is not None else None
                    chunk_text = chunks_lookup.get(chunk_id_key)

                    # ✅ Debug logging (only first few to avoid spam)
                    if i <= 5:
                        logger.info(
                            f"[DEBUG] Validating Q{i}: chunk_id={chunk_id_key}, "
                            f"chunk_found={'YES' if chunk_text else 'NO'}, "
                            f"q_preview={(q.get('question_text') or '')[:120]}, "
                            f"ans_preview={(q.get('answer') or '')[:120]}"
                        )

                    # ✅ If chunk is missing, skip AI validation and keep question
                    if not chunk_text:
                        q["validation_status"] = "needs_review"
                        q["validation_reason"] = "missing_chunk_text"
                        validated_questions.append(q)
                        continue

                    # ✅ Run validation normally
                    v_results = self.validation_agent.validate_questions_batch([q], chunks_lookup)

                    # ✅ Make result handling safer (avoid v_results[0] assumptions)
                    if v_results and isinstance(v_results, list) and len(v_results) > 0:
                        if isinstance(v_results[0], list) and len(v_results[0]) > 0:
                            validated_questions.append(v_results[0][0])
                        elif isinstance(v_results[0], dict):
                            validated_questions.append(v_results[0])
                        else:
                            q["validation_status"] = "needs_review"
                            q["validation_reason"] = "unexpected_validation_output"
                            validated_questions.append(q)
                    else:
                        q["validation_status"] = "needs_review"
                        q["validation_reason"] = "empty_validation_output"
                        validated_questions.append(q)

                except Exception as ve:
                    logger.warning(f"[DEBUG] Validation skipped due to error: {ve}")
                    q["validation_status"] = "needs_review"
                    q["validation_reason"] = f"exception:{type(ve).__name__}"
                    validated_questions.append(q)

                time.sleep(4)


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

            # 🚨 FINAL SAFETY FILTER BEFORE DB SAVE
            clean_questions = []

            for q in formatted_quiz["questions"]:
                # 🔥 Accept ANY possible answer field and normalize
                final_answer = (
                    q.get("correct_answer")
                    or q.get("answer")
                    or q.get("correct")
                    or q.get("correctAnswer")
                )

                if not final_answer:
                    logger.warning(f"[FILTER] Dropping question with missing answer: {q.get('question_text')}")
                    continue

                # Standardize field so rest of system is consistent
                q["correct_answer"] = final_answer

                # ✅ MCQ safety checks
                if q.get("question_type") == "mcq":
                    opts = q.get("options") or []

                    if len(opts) != 4:
                        logger.warning(f"[FILTER] Dropping MCQ with invalid options: {q.get('question_text')}")
                        continue

                    if final_answer not in opts:
                        logger.warning(f"[FILTER] MCQ answer not in options: {q.get('question_text')}")
                        continue

                clean_questions.append(q)
                formatted_quiz["questions"] = clean_questions



            formatted_quiz["questions"] = clean_questions
            logger.info(f"[FILTER] Questions after final safety check: {len(clean_questions)}")


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
        from quiz_platform.db.database import SessionLocal
        db = SessionLocal()
        try:
            print(f"🚀 [AI] Background process starting for PDF: {pdf_id}", flush=True)
            service = QuizPipelineService(db)
            service.process_pdf(pdf_id)
        finally:
            db.close()

    @staticmethod
    def generate_quiz_background(pdf_id: int, quiz_id: int):
        from quiz_platform.db.database import SessionLocal
        db = SessionLocal()
        try:
            print(f"🚀 [AI] Background quiz generation starting for ID: {quiz_id}", flush=True)
            service = QuizPipelineService(db)
            service.generate_quiz_from_pdf(pdf_id, quiz_id)
        finally:
            db.close()