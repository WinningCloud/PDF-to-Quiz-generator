import json
import random
from typing import Dict, List, Any, Tuple
import logging
from config.llm_config import llm_client
from config.prompts import SystemPrompts, UserPrompts
from config.settings import settings

logger = logging.getLogger(__name__)

class QuestionAgent:
    def __init__(self):
        self.system_prompt = SystemPrompts.QUESTION_GENERATOR_SYSTEM
    
    def generate_questions_for_chunk(
        self, 
        chunk: Dict, 
        subtopic: str, 
        count: int = 2,
        difficulty: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        Generate questions for a specific chunk and subtopic
        
        Args:
            chunk: Chunk dictionary with text
            subtopic: Specific subtopic to focus on
            count: Number of questions to generate
            difficulty: Target difficulty level
            
        Returns:
            List of generated questions
        """
        try:
            chunk_text = chunk.get("text", "")
            chunk_id = chunk.get("chunk_id")
            page_num = chunk.get("page_number", 1)
            
            prompt = UserPrompts.generate_questions(chunk_text, subtopic, count)
            
            # Add difficulty hint
            prompt += f"\nTarget difficulty: {difficulty.capitalize()}"
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            questions = response.get("questions", [])
            
            # Add metadata to each question
            for i, question in enumerate(questions):
                question.update({
                    "chunk_id": chunk_id,
                    "page_number": page_num,
                    "subtopic": subtopic,
                    "difficulty": difficulty,
                    "question_id": f"{chunk_id}_{subtopic[:10]}_{i}",
                    "generation_source": "llm",
                    "confidence_score": 0.8  # Default confidence
                })
            
            logger.info(f"Generated {len(questions)} questions for subtopic '{subtopic}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return self._generate_fallback_questions(chunk, subtopic, count, difficulty)

    
    def generate_questions_batch(
        self, 
        chunk_assignments: List[Dict], 
        extracted_topics: Dict
    ) -> List[Dict[str, Any]]:
        """
        Generate questions for multiple chunks based on assignments
        
        Args:
            chunk_assignments: List of chunk assignments from planner
            extracted_topics: Topics extracted from chunks
            
        Returns:
            List of all generated questions
        """
        all_questions = []
        
        for assignment in chunk_assignments:
            chunk_id = assignment.get("chunk_id")
            chunk_text = assignment.get("text", "")
            target_count = assignment.get("target_questions", 2)
            
            # Find topics for this chunk
            chunk_topics = self._get_topics_for_chunk(chunk_id, extracted_topics)
            
            if not chunk_topics:
                # Generate general questions
                questions = self._generate_general_questions(
                    chunk_text, 
                    target_count,
                    assignment.get("difficulty_mix", ["medium"])
                )
                all_questions.extend(questions)
            else:
                # Generate questions for each subtopic
                for subtopic in chunk_topics[:1]:
                    # Determine difficulty for this question
                    difficulty = self._select_difficulty(assignment.get("difficulty_mix", ["medium"]))
                    
                    # Generate questions
                    questions = self.generate_questions_for_chunk(
                        chunk={"text": chunk_text, "chunk_id": chunk_id, "page_number": assignment.get("page_number", 1)},
                        subtopic=subtopic,
                        count=max(1, target_count // len(chunk_topics)),
                        difficulty=difficulty
                    )
                    all_questions.extend(questions)
        
        logger.info(f"Generated total {len(all_questions)} questions")
        return all_questions
    
    def _get_topics_for_chunk(self, chunk_id: str, extracted_topics: Dict) -> List[str]:
        """
        Use normalized_topics subtopics and filter junk like years, page numbers, ISSN, etc.
        """
        normalized_topics = extracted_topics.get("normalized_topics", [])
        all_subtopics = []

        for topic in normalized_topics:
            subs = topic.get("subtopics", [])
            if isinstance(subs, list):
                for s in subs:
                    if not isinstance(s, str):
                        continue
                    s_clean = s.strip()

                    # ❌ Reject numbers like 2014, 373, etc.
                    if s_clean.isdigit():
                        continue

                    # ❌ Reject very short terms
                    if len(s_clean) < 4:
                        continue

                    all_subtopics.append(s_clean)

        # return top 3-5 topics (stable)
        return all_subtopics[:5]


    
    def _select_difficulty(self, difficulty_mix: List[str]) -> str:
        """Select difficulty based on mix"""
        if not difficulty_mix:
            return "medium"
        
        weights = []
        difficulties = []
        
        # Assign weights based on typical distribution
        for diff in difficulty_mix:
            if diff == "easy":
                weights.append(0.3)
            elif diff == "medium":
                weights.append(0.5)
            elif diff == "hard":
                weights.append(0.2)
            difficulties.append(diff)
        
        # Normalize weights
        total = sum(weights)
        if total > 0:
            weights = [w/total for w in weights]
        
        return random.choices(difficulties, weights=weights, k=1)[0]
    
    def _generate_general_questions(self, text: str, count: int, difficulty_mix: List[str]) -> List[Dict[str, Any]]:
        """
        If no topics found, ask LLM to generate MCQs directly instead of sentence-meaning.
        """
        try:
            difficulty = self._select_difficulty(difficulty_mix)

            prompt = UserPrompts.generate_questions(
                chunk_text=text,
                subtopic="General Concepts",
                count=count
            )
            prompt += f"\nTarget difficulty: {difficulty.capitalize()}"
            prompt += "\nIMPORTANT: Generate MCQ questions only. Avoid 'What does this sentence mean' style."

            response = llm_client.generate_json(prompt=prompt, system_prompt=self.system_prompt)

            questions = response.get("questions", [])
            for q in questions:
                q["generation_source"] = "llm_general"
                q["difficulty"] = q.get("difficulty", difficulty)
                q["confidence_score"] = 0.75

            return questions

        except Exception as e:
            logger.error(f"General MCQ generation failed: {e}")
            return []

    
    def _generate_fallback_questions(
        self, 
        chunk: Dict, 
        subtopic: str, 
        count: int, 
        difficulty: str
    ) -> List[Dict[str, Any]]:
        """Fallback question generation"""
        text = chunk.get("text", "")
        sentences = self._split_into_sentences(text)
        
        questions = []
        for i in range(min(count, 2)):
            if i < len(sentences):
                question = {
                    "question_text": f"What is mentioned about '{subtopic}' in the text?",
                    "question_type": "short_answer",
                    "answer": f"The text discusses {subtopic} in the context: {sentences[i][:200]}",
                    "options": [],
                    "difficulty": difficulty,
                    "explanation": "Generated from text analysis.",
                    "generation_source": "fallback",
                    "confidence_score": 0.5,
                    "chunk_id": chunk.get("chunk_id"),
                    "subtopic": subtopic
                }
                questions.append(question)
        
        return questions
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Simple sentence splitting"""
        import re
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def enrich_questions_with_metadata(
        self, 
        questions: List[Dict], 
        topics_data: Dict
    ) -> List[Dict]:
        """
        Enrich questions with additional metadata
        
        Args:
            questions: List of question dictionaries
            topics_data: Topics data for enrichment
            
        Returns:
            Enriched questions
        """
        normalized_topics = topics_data.get("normalized_topics", [])
        topic_mapping = topics_data.get("mapping", {})
        
        for question in questions:
            # Add topic information
            subtopic = question.get("subtopic", "")
            if subtopic in topic_mapping:
                question["normalized_topic"] = topic_mapping[subtopic]
            else:
                question["normalized_topic"] = "General"
            
            # Add question order placeholder
            question["question_order"] = 0
            
            # Add validation status
            question["validation_status"] = "pending"
            
            # Calculate complexity score
            question["complexity_score"] = self._calculate_complexity(question)
        
        return questions
    
    def _calculate_complexity(self, question: Dict) -> float:
        """Calculate question complexity score"""
        complexity = 0.5  # Base
        
        # Adjust based on difficulty
        difficulty = question.get("difficulty", "medium")
        if difficulty == "easy":
            complexity -= 0.2
        elif difficulty == "hard":
            complexity += 0.2
        
        # Adjust based on question type
        q_type = question.get("question_type", "")
        if q_type == "mcq":
            complexity += 0.1  # MCQs are generally easier
        
        # Adjust based on text length
        question_text = question.get("question_text", "")
        if len(question_text.split()) > 25:
            complexity += 0.1
        
        return max(0.1, min(1.0, complexity))