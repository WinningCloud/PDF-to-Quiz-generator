import json
from typing import Dict, List, Any, Tuple
import logging
from config.llm_config import llm_client
from config.prompts import SystemPrompts

logger = logging.getLogger(__name__)

class PDFAgent:
    def __init__(self):
        self.system_prompt = SystemPrompts.PDF_ANALYZER_SYSTEM
    
    def analyze_chunk(self, chunk: Dict) -> Dict[str, Any]:
        """
        Analyze a single chunk of text from PDF
        
        Args:
            chunk: Dictionary containing chunk info and text
            
        Returns:
            Analysis results including key information
        """
        try:
            chunk_text = chunk.get("text", "")
            page_num = chunk.get("page_number", 1)
            
            prompt = f"""Analyze the following text from page {page_num}:

            Text:
            {chunk_text}

            Extract:
            1. Key concepts and entities (list)
            2. Important facts or definitions (list)
            3. Main ideas or themes (1-3)
            4. Relationships between concepts if any
            5. Technical terms or jargon
            
            Return as JSON with these keys:
            - concepts: list of key concepts
            - facts: list of important facts
            - main_ideas: list of main ideas
            - relationships: list of relationships
            - technical_terms: list of technical terms
            - summary: brief summary of chunk
            """
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            # Add chunk metadata to response
            response.update({
                "chunk_id": chunk.get("chunk_id"),
                "page_number": page_num,
                "text_length": len(chunk_text),
                "word_count": len(chunk_text.split())
            })
            
            logger.info(f"Analyzed chunk {chunk.get('chunk_id')} from page {page_num}")
            return response
            
        except Exception as e:
            logger.error(f"Error analyzing chunk: {e}")
            return self._get_basic_analysis(chunk)
    
    def extract_key_information(self, chunks: List[Dict]) -> Dict[str, Any]:
        """
        Extract key information from all chunks
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Consolidated key information
        """
        all_concepts = []
        all_facts = []
        all_ideas = []
        all_terms = []
        
        for chunk in chunks:
            analysis = self.analyze_chunk(chunk)
            
            all_concepts.extend(analysis.get("concepts", []))
            all_facts.extend(analysis.get("facts", []))
            all_ideas.extend(analysis.get("main_ideas", []))
            all_terms.extend(analysis.get("technical_terms", []))
        
        # Remove duplicates while preserving order
        all_concepts = list(dict.fromkeys(all_concepts))
        all_facts = list(dict.fromkeys(all_facts))
        all_ideas = list(dict.fromkeys(all_ideas))
        all_terms = list(dict.fromkeys(all_terms))
        
        # Identify most frequent concepts
        from collections import Counter
        concept_counter = Counter(all_concepts)
        top_concepts = concept_counter.most_common(10)
        
        return {
            "total_chunks_analyzed": len(chunks),
            "unique_concepts": all_concepts,
            "unique_facts": all_facts,
            "main_ideas": all_ideas,
            "technical_terms": all_terms,
            "top_concepts": [concept for concept, count in top_concepts],
            "concept_frequencies": dict(top_concepts),
            "summary": f"Extracted {len(all_concepts)} concepts, {len(all_facts)} facts from {len(chunks)} chunks"
        }
    
    def identify_content_structure(self, chunks: List[Dict]) -> Dict[str, Any]:
        """
        Identify the overall structure of the content
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Content structure analysis
        """
        # Group chunks by page
        pages = {}
        for chunk in chunks:
            page_num = chunk.get("page_number", 1)
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(chunk)
        
        # Analyze progression across pages
        page_analyses = []
        for page_num in sorted(pages.keys()):
            page_chunks = pages[page_num]
            page_text = " ".join([chunk.get("text", "") for chunk in page_chunks])
            
            # Simple analysis of page content
            word_count = len(page_text.split())
            sentences = page_text.count('.') + page_text.count('!') + page_text.count('?')
            
            page_analyses.append({
                "page_number": page_num,
                "chunk_count": len(page_chunks),
                "word_count": word_count,
                "sentence_count": sentences,
                "density": word_count / max(1, sentences)
            })
        
        # Calculate progression metrics
        total_pages = len(pages)
        avg_words_per_page = sum([p["word_count"] for p in page_analyses]) / max(1, total_pages)
        
        return {
            "total_pages": total_pages,
            "total_chunks": len(chunks),
            "pages": page_analyses,
            "average_words_per_page": avg_words_per_page,
            "content_progression": self._analyze_progression(page_analyses)
        }
    
    def _analyze_progression(self, page_analyses: List[Dict]) -> Dict[str, Any]:
        """Analyze how content progresses across pages"""
        if len(page_analyses) < 2:
            return {"pattern": "single_page", "consistency": "high"}
        
        word_counts = [p["word_count"] for p in page_analyses]
        densities = [p["density"] for p in page_analyses]
        
        # Calculate trends
        from scipy import stats
        word_trend = stats.linregress(range(len(word_counts)), word_counts).slope
        density_trend = stats.linregress(range(len(densities)), densities).slope
        
        # Determine pattern
        if abs(word_trend) < 10 and abs(density_trend) < 0.1:
            pattern = "consistent"
        elif word_trend > 10:
            pattern = "increasing_density"
        elif word_trend < -10:
            pattern = "decreasing_density"
        else:
            pattern = "variable"
        
        return {
            "pattern": pattern,
            "word_count_trend": word_trend,
            "density_trend": density_trend,
            "consistency": "high" if pattern == "consistent" else "medium"
        }
    
    def _get_basic_analysis(self, chunk: Dict) -> Dict[str, Any]:
        """Fallback analysis if AI fails"""
        text = chunk.get("text", "")
        words = text.split()
        
        # Simple keyword extraction (top 5 words by TF-IDF like score)
        from collections import Counter
        word_freq = Counter(words)
        common_words = set(["the", "and", "is", "in", "to", "of", "a", "that", "it", "with"])
        keywords = [word for word, freq in word_freq.most_common(20) 
                   if word.lower() not in common_words and len(word) > 3][:5]
        
        return {
            "chunk_id": chunk.get("chunk_id"),
            "page_number": chunk.get("page_number", 1),
            "concepts": keywords,
            "facts": [],
            "main_ideas": ["Extracted from text"],
            "relationships": [],
            "technical_terms": keywords,
            "summary": "Basic analysis: " + text[:100] + "...",
            "text_length": len(text),
            "word_count": len(words)
        }