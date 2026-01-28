import json
import random
from typing import Dict, List, Any, Tuple
import logging
from datetime import datetime
from config.llm_config import llm_client
from config.prompts import SystemPrompts, UserPrompts
from config.settings import settings

logger = logging.getLogger(__name__)

class QuestionGenerator:
    def __init__(self):
        self.system_prompt = SystemPrompts.QUESTION_GENERATOR_SYSTEM
        
    def generate_questions_from_chunks(
        self, 
        chunks: List[Dict[str, Any]], 
        extracted_topics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate questions from chunks using extracted topics
        
        Args:
            chunks: List of chunk dictionaries
            extracted_topics: Topics extracted from chunks
            
        Returns:
            List of generated questions
        """
        all_questions = []
        
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", "")
            chunk_text = chunk.get("text", "")
            page_number = chunk.get("page_number", 1)
            
            if not chunk_text:
                continue
            
            # Get topics for this chunk
            chunk_topics = self._get_topics_for_chunk(
                chunk_id, 
                extracted_topics
            )
            
            if not chunk_topics:
                # Generate general questions if no specific topics
                general_questions = self._generate_general_questions(
                    chunk_text, 
                    chunk_id, 
                    page_number
                )
                all_questions.extend(general_questions)
                continue
            
            # Generate questions for each topic
            for topic in chunk_topics:
                topic_questions = self._generate_questions_for_topic(
                    chunk_text, 
                    topic, 
                    chunk_id, 
                    page_number
                )
                all_questions.extend(topic_questions)
        
        logger.info(f"Generated {len(all_questions)} questions from {len(chunks)} chunks")
        return all_questions
    
    def _get_topics_for_chunk(
        self, 
        chunk_id: str, 
        extracted_topics: Dict[str, Any]
    ) -> List[str]:
        """Get topics for a specific chunk"""
        # In a full implementation, this would map chunks to topics
        # For now, return a sampling of topics from the hierarchy
        
        topic_hierarchy = extracted_topics.get("topic_hierarchy", {})
        all_subtopics = []
        
        for topic_data in topic_hierarchy.values():
            all_subtopics.extend(topic_data.get("subtopics", []))
        
        if not all_subtopics:
            return []
        
        # Return random subtopics (in production, use actual mapping)
        sample_size = min(3, len(all_subtopics))
        return random.sample(all_subtopics, sample_size)
    
    def _generate_general_questions(
        self, 
        chunk_text: str, 
        chunk_id: str, 
        page_number: int
    ) -> List[Dict[str, Any]]:
        """Generate general questions from chunk text"""
        try:
            prompt = f"""Generate 2-3 questions based on the following text:

            Text:
            {chunk_text[:1500]}  # Limit text length

            Generate a mix of:
            1. Multiple choice questions (with 4 options)
            2. Short answer questions
            
            Include:
            - Clear question text
            - Correct answer
            - Explanation (for MCQ)
            - Difficulty level (Easy/Medium/Hard)
            
            Return as JSON with list of questions."""
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            questions = response.get("questions", [])
            
            # Add metadata
            for i, question in enumerate(questions):
                question.update({
                    "question_id": f"{chunk_id}_gen_{i}",
                    "chunk_id": chunk_id,
                    "page_number": page_number,
                    "subtopic": "General",
                    "generation_source": "llm_general",
                    "generated_at": datetime.utcnow().isoformat(),
                    "confidence_score": 0.7  # Default confidence
                })
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating general questions: {e}")
            return self._generate_fallback_questions(chunk_text, chunk_id, page_number)
    
    def _generate_questions_for_topic(
        self, 
        chunk_text: str, 
        topic: str, 
        chunk_id: str, 
        page_number: int
    ) -> List[Dict[str, Any]]:
        """Generate questions for a specific topic"""
        try:
            prompt = UserPrompts.generate_questions(chunk_text, topic, count=2)
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            questions = response.get("questions", [])
            
            # Add metadata
            for i, question in enumerate(questions):
                question.update({
                    "question_id": f"{chunk_id}_{topic[:10]}_{i}",
                    "chunk_id": chunk_id,
                    "page_number": page_number,
                    "subtopic": topic,
                    "generation_source": "llm_topic_based",
                    "generated_at": datetime.utcnow().isoformat(),
                    "confidence_score": 0.8  # Higher confidence for topic-based
                })
            
            logger.debug(f"Generated {len(questions)} questions for topic '{topic}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions for topic '{topic}': {e}")
            return []
    
    def _generate_fallback_questions(
        self, 
        chunk_text: str, 
        chunk_id: str, 
        page_number: int
    ) -> List[Dict[str, Any]]:
        """Generate fallback questions using simple methods"""
        questions = []
        
        # Split text into sentences
        sentences = self._split_into_sentences(chunk_text)
        
        for i, sentence in enumerate(sentences[:3]):  # Use first 3 sentences
            if len(sentence.split()) < 5:  # Skip very short sentences
                continue
            
            # Create MCQ
            mcq = self._create_simple_mcq(sentence, i)
            mcq.update({
                "question_id": f"{chunk_id}_fallback_mcq_{i}",
                "chunk_id": chunk_id,
                "page_number": page_number,
                "subtopic": "General",
                "generation_source": "fallback",
                "confidence_score": 0.5
            })
            questions.append(mcq)
            
            # Create short answer question
            saq = self._create_simple_short_answer(sentence, i)
            saq.update({
                "question_id": f"{chunk_id}_fallback_sa_{i}",
                "chunk_id": chunk_id,
                "page_number": page_number,
                "subtopic": "General",
                "generation_source": "fallback",
                "confidence_score": 0.5
            })
            questions.append(saq)
        
        return questions
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _create_simple_mcq(self, sentence: str, index: int) -> Dict[str, Any]:
        """Create a simple multiple choice question"""
        words = sentence.split()
        
        # Extract key term (assuming it's a noun)
        key_terms = [w for w in words if w[0].isupper() and len(w) > 3]
        key_term = key_terms[0] if key_terms else "concept"
        
        question_text = f"What is the main purpose of {key_term.lower()} as described?"
        
        # Create options
        options = [
            f"To enhance {key_term.lower()} efficiency",
            f"To reduce {key_term.lower()} complexity",
            f"To increase {key_term.lower()} scalability",
            f"To optimize {key_term.lower()} performance"
        ]
        
        # Random correct answer
        correct_answer = random.choice(options)
        
        return {
            "question_text": question_text,
            "question_type": "mcq",
            "options": options,
            "answer": correct_answer,
            "explanation": f"Based on the context: {sentence[:100]}...",
            "difficulty": random.choice(["easy", "medium"])
        }
    
    def _create_simple_short_answer(self, sentence: str, index: int) -> Dict[str, Any]:
        """Create a simple short answer question"""
        question_text = f"What is described in this sentence: '{sentence[:100]}...'?"
        
        # Create answer from sentence
        answer = f"The sentence describes: {sentence}"
        
        return {
            "question_text": question_text,
            "question_type": "short_answer",
            "answer": answer,
            "explanation": "Answer is based on the provided sentence.",
            "difficulty": "easy"
        }
    
    def generate_questions_with_planner(
        self, 
        chunks: List[Dict[str, Any]], 
        planner_assignments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate questions based on planner assignments
        
        Args:
            chunks: List of chunks
            planner_assignments: Assignments from planner agent
            
        Returns:
            Generated questions
        """
        all_questions = []
        
        # Create chunk lookup
        chunk_dict = {chunk["chunk_id"]: chunk for chunk in chunks}
        
        for assignment in planner_assignments:
            chunk_id = assignment.get("chunk_id")
            chunk = chunk_dict.get(chunk_id)
            
            if not chunk:
                logger.warning(f"Chunk {chunk_id} not found for assignment")
                continue
            
            chunk_text = chunk.get("text", "")
            page_number = chunk.get("page_number", 1)
            target_count = assignment.get("target_questions", 2)
            difficulty_mix = assignment.get("difficulty_mix", ["medium"])
            
            # Generate questions based on assignment
            questions = self._generate_questions_by_assignment(
                chunk_text, 
                chunk_id, 
                page_number, 
                target_count, 
                difficulty_mix
            )
            
            all_questions.extend(questions)
        
        logger.info(f"Generated {len(all_questions)} questions from planner assignments")
        return all_questions
    
    def _generate_questions_by_assignment(
        self, 
        chunk_text: str, 
        chunk_id: str, 
        page_number: int, 
        target_count: int, 
        difficulty_mix: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate questions based on assignment parameters"""
        questions = []
        
        # Determine question type distribution
        mcq_count = max(1, int(target_count * 0.7))  # 70% MCQs
        sa_count = target_count - mcq_count
        
        # Generate MCQs
        for i in range(mcq_count):
            difficulty = self._select_difficulty(difficulty_mix)
            mcq = self._generate_mcq(chunk_text, difficulty)
            
            if mcq:
                mcq.update({
                    "question_id": f"{chunk_id}_mcq_{i}",
                    "chunk_id": chunk_id,
                    "page_number": page_number,
                    "subtopic": "Assignment-based",
                    "generation_source": "planner_assignment",
                    "confidence_score": 0.75
                })
                questions.append(mcq)
        
        # Generate short answer questions
        for i in range(sa_count):
            difficulty = self._select_difficulty(difficulty_mix)
            saq = self._generate_short_answer(chunk_text, difficulty)
            
            if saq:
                saq.update({
                    "question_id": f"{chunk_id}_sa_{i}",
                    "chunk_id": chunk_id,
                    "page_number": page_number,
                    "subtopic": "Assignment-based",
                    "generation_source": "planner_assignment",
                    "confidence_score": 0.75
                })
                questions.append(saq)
        
        return questions
    
    def _generate_mcq(self, text: str, difficulty: str) -> Dict[str, Any]:
        """Generate a multiple choice question"""
        try:
            prompt = f"""Generate a {difficulty} difficulty multiple choice question from this text:

            Text:
            {text[:1000]}

            Requirements:
            - 4 options (A, B, C, D)
            - One correct answer
            - Plausible distractors
            - Clear explanation
            - Question should test understanding, not just recall
            
            Return as JSON with:
            - question_text
            - options (list of 4 strings)
            - answer (the correct option text)
            - explanation
            """
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            response["question_type"] = "mcq"
            response["difficulty"] = difficulty
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating MCQ: {e}")
            return None
    
    def _generate_short_answer(self, text: str, difficulty: str) -> Dict[str, Any]:
        """Generate a short answer question"""
        try:
            prompt = f"""Generate a {difficulty} difficulty short answer question from this text:

            Text:
            {text[:1000]}

            Requirements:
            - Open-ended question
            - Clear, specific answer
            - Explanation of why the answer is correct
            - Question should require analysis, not just recall
            
            Return as JSON with:
            - question_text
            - answer
            - explanation
            """
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            response["question_type"] = "short_answer"
            response["difficulty"] = difficulty
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating short answer: {e}")
            return None
    
    def _select_difficulty(self, difficulty_mix: List[str]) -> str:
        """Select difficulty based on mix"""
        if not difficulty_mix:
            return "medium"
        
        # Simple weighted random selection
        weights = {
            "easy": 0.3,
            "medium": 0.5,
            "hard": 0.2
        }
        
        # Filter to available difficulties
        available = [d for d in difficulty_mix if d in weights]
        if not available:
            return "medium"
        
        # Calculate weights
        weight_list = [weights[d] for d in available]
        total = sum(weight_list)
        normalized_weights = [w/total for w in weight_list]
        
        return random.choices(available, weights=normalized_weights, k=1)[0]
    
    def enrich_questions_with_context(
        self, 
        questions: List[Dict[str, Any]], 
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich questions with context from chunks
        
        Args:
            questions: List of questions
            chunks: List of chunks
            
        Returns:
            Enriched questions
        """
        chunk_dict = {chunk["chunk_id"]: chunk for chunk in chunks}
        
        for question in questions:
            chunk_id = question.get("chunk_id")
            chunk = chunk_dict.get(chunk_id)
            
            if chunk:
                # Add context information
                question["context"] = {
                    "page_number": chunk.get("page_number"),
                    "chunk_preview": chunk.get("text", "")[:200],
                    "word_count": chunk.get("word_count", 0),
                    "has_previous_context": bool(chunk.get("previous_page_ref")),
                    "has_next_context": bool(chunk.get("next_page_ref"))
                }
        
        return questions