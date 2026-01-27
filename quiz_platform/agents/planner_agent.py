import json
from typing import Dict, List, Any
import logging
from quiz_platform.config.llm_config import llm_client
from quiz_platform.config.prompts import SystemPrompts, UserPrompts

logger = logging.getLogger(__name__)

class PlannerAgent:
    def __init__(self):
        self.system_prompt = SystemPrompts.PLANNER_SYSTEM
    
    def plan_quiz_generation(self, chunk_count: int, content_summary: str) -> Dict[str, Any]:
        """
        Plan how to generate questions from PDF chunks
        
        Args:
            chunk_count: Number of content chunks
            content_summary: Summary of PDF content
            
        Returns:
            Dictionary with generation plan
        """
        try:
            prompt = UserPrompts.generate_quiz_plan(chunk_count, content_summary)
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            logger.info(f"Generated quiz plan for {chunk_count} chunks")
            return response
            
        except Exception as e:
            logger.error(f"Error in quiz planning: {e}")
            # Return default plan
            return self._get_default_plan(chunk_count)
    
    def _get_default_plan(self, chunk_count: int) -> Dict[str, Any]:
        """Get default plan if AI planning fails"""
        questions_per_chunk = min(2, max(1, 10 // max(1, chunk_count)))
        
        return {
            "total_chunks": chunk_count,
            "questions_per_chunk": questions_per_chunk,
            "estimated_total_questions": chunk_count * questions_per_chunk,
            "question_type_distribution": {
                "mcq": 0.7,
                "short_answer": 0.3
            },
            "difficulty_distribution": {
                "easy": 0.3,
                "medium": 0.5,
                "hard": 0.2
            },
            "strategy": "balanced_coverage"
        }
    
    def assign_questions_to_chunks(self, chunks: List[Dict], plan: Dict) -> List[Dict]:
        """
        Assign question generation parameters to each chunk based on plan
        
        Args:
            chunks: List of chunk dictionaries
            plan: Generation plan from planner
            
        Returns:
            List of chunks with assignment parameters
        """
        assignments = []
        
        for i, chunk in enumerate(chunks):
            # Determine questions for this chunk
            chunk_content = chunk.get("text", "")
            chunk_length = len(chunk_content.split())
            
            # Adjust based on content density
            if chunk_length < 100:
                questions_for_chunk = 1
            elif chunk_length < 300:
                questions_for_chunk = plan.get("questions_per_chunk", 2)
            else:
                questions_for_chunk = min(3, plan.get("questions_per_chunk", 2) + 1)
            
            assignment = {
                "chunk_id": chunk.get("chunk_id"),
                "page_number": chunk.get("page_number"),
                "text": chunk_content,
                "target_questions": questions_for_chunk,
                "question_types": ["mcq", "short_answer"],
                "difficulty_mix": ["easy", "medium", "hard"],
                "priority": "normal"
            }
            
            assignments.append(assignment)
        
        return assignments
    
    def analyze_content_density(self, chunks: List[Dict]) -> Dict[str, Any]:
        """
        Analyze content density across chunks
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Analysis results
        """
        if not chunks:
            return {"error": "No chunks provided"}
        
        total_words = 0
        chunks_by_density = {"low": 0, "medium": 0, "high": 0}
        
        for chunk in chunks:
            text = chunk.get("text", "")
            word_count = len(text.split())
            total_words += word_count
            
            if word_count < 150:
                chunks_by_density["low"] += 1
            elif word_count < 400:
                chunks_by_density["medium"] += 1
            else:
                chunks_by_density["high"] += 1
        
        avg_words_per_chunk = total_words / len(chunks)
        
        return {
            "total_chunks": len(chunks),
            "total_words": total_words,
            "average_words_per_chunk": avg_words_per_chunk,
            "chunks_by_density": chunks_by_density,
            "density_distribution": {
                "low": chunks_by_density["low"] / len(chunks),
                "medium": chunks_by_density["medium"] / len(chunks),
                "high": chunks_by_density["high"] / len(chunks)
            }
        }