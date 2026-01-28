import re
from typing import Dict, List, Any, Tuple, Set
import logging
from collections import Counter
import spacy
from config.llm_config import llm_client

logger = logging.getLogger(__name__)

class EntityExtractor:
    def __init__(self):
        try:
            # Try to load spaCy model
            self.nlp = spacy.load("en_core_web_sm")
            self.use_spacy = True
            logger.info("Loaded spaCy model for entity extraction")
        except:
            self.use_spacy = False
            logger.warning("spaCy model not available, using rule-based extraction")
    
    def extract_entities_from_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract entities from a chunk
        
        Args:
            chunk: Chunk dictionary with text
            
        Returns:
            Entity extraction results
        """
        text = chunk.get("text", "")
        chunk_id = chunk.get("chunk_id", "")
        page_number = chunk.get("page_number", 1)
        
        if not text:
            return {
                "chunk_id": chunk_id,
                "page_number": page_number,
                "entities": [],
                "entity_count": 0,
                "extraction_method": "none"
            }
        
        try:
            if self.use_spacy:
                return self._extract_with_spacy(text, chunk_id, page_number)
            else:
                return self._extract_with_rules(text, chunk_id, page_number)
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return self._extract_with_llm_fallback(text, chunk_id, page_number)
    
    def _extract_with_spacy(self, text: str, chunk_id: str, page_num: int) -> Dict[str, Any]:
        """Extract entities using spaCy"""
        doc = self.nlp(text[:1000000])  # Limit text length
        
        entities_by_type = {}
        all_entities = []
        
        for ent in doc.ents:
            entity_data = {
                "text": ent.text,
                "label": ent.label_,
                "start_char": ent.start_char,
                "end_char": ent.end_char
            }
            
            if ent.label_ not in entities_by_type:
                entities_by_type[ent.label_] = []
            entities_by_type[ent.label_].append(entity_data)
            all_entities.append(entity_data)
        
        # Extract noun phrases
        noun_phrases = [chunk.text for chunk in doc.noun_chunks]
        
        # Extract key terms (nouns and proper nouns)
        key_terms = []
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN"] and len(token.text) > 2:
                key_terms.append(token.text)
        
        # Get most frequent terms
        term_frequencies = Counter(key_terms)
        top_terms = term_frequencies.most_common(20)
        
        return {
            "chunk_id": chunk_id,
            "page_number": page_num,
            "entities": all_entities,
            "entities_by_type": entities_by_type,
            "entity_count": len(all_entities),
            "noun_phrases": noun_phrases,
            "key_terms": key_terms,
            "top_terms": top_terms,
            "extraction_method": "spacy"
        }
    
    def _extract_with_rules(self, text: str, chunk_id: str, page_num: int) -> Dict[str, Any]:
        """Extract entities using rule-based methods"""
        # Simple entity extraction patterns
        patterns = {
            "PERSON": r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # Simple name pattern
            "ORG": r'\b([A-Z][a-z]+ (?:Corporation|Company|Inc|LLC|Ltd))\b',
            "DATE": r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4})\b',
            "NUMERIC": r'\b(\d+[,.]?\d*)\b',
            "ACRONYM": r'\b([A-Z]{2,})\b'
        }
        
        entities_by_type = {}
        all_entities = []
        
        for label, pattern in patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                entity_data = {
                    "text": match.group(),
                    "label": label,
                    "start_char": match.start(),
                    "end_char": match.end()
                }
                
                if label not in entities_by_type:
                    entities_by_type[label] = []
                entities_by_type[label].append(entity_data)
                all_entities.append(entity_data)
        
        # Extract noun phrases (simple heuristic)
        sentences = re.split(r'[.!?]+', text)
        noun_phrases = []
        
        for sentence in sentences:
            words = sentence.split()
            if len(words) >= 2:
                # Simple noun phrase detection
                for i in range(len(words) - 1):
                    if words[i][0].isupper() and words[i+1][0].isupper():
                        noun_phrases.append(f"{words[i]} {words[i+1]}")
        
        # Extract key terms (capitalized words)
        key_terms = re.findall(r'\b[A-Z][a-z]+\b', text)
        term_frequencies = Counter(key_terms)
        top_terms = term_frequencies.most_common(20)
        
        return {
            "chunk_id": chunk_id,
            "page_number": page_num,
            "entities": all_entities,
            "entities_by_type": entities_by_type,
            "entity_count": len(all_entities),
            "noun_phrases": noun_phrases[:20],  # Limit
            "key_terms": key_terms,
            "top_terms": top_terms,
            "extraction_method": "rule_based"
        }
    
    def _extract_with_llm_fallback(self, text: str, chunk_id: str, page_num: int) -> Dict[str, Any]:
        """Extract entities using LLM as fallback"""
        try:
            prompt = f"""Extract important entities and concepts from the following text:

            Text:
            {text[:2000]}  # Limit text length

            Extract:
            1. Named entities (people, organizations, locations)
            2. Key concepts and topics
            3. Technical terms
            4. Important dates and numbers

            Return as JSON with these keys:
            - entities: list of entities with text and type
            - concepts: list of key concepts
            - technical_terms: list of technical terms
            - summary: brief summary
            """
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt="You are an entity extraction expert. Extract important entities and concepts from text."
            )
            
            return {
                "chunk_id": chunk_id,
                "page_number": page_num,
                "entities": response.get("entities", []),
                "concepts": response.get("concepts", []),
                "technical_terms": response.get("technical_terms", []),
                "summary": response.get("summary", ""),
                "extraction_method": "llm_fallback"
            }
            
        except Exception as e:
            logger.error(f"LLM entity extraction failed: {e}")
            return {
                "chunk_id": chunk_id,
                "page_number": page_num,
                "entities": [],
                "error": str(e),
                "extraction_method": "failed"
            }
    
    def consolidate_entities_across_chunks(
        self, 
        entity_extractions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Consolidate entities from multiple chunks
        
        Args:
            entity_extractions: List of entity extraction results
            
        Returns:
            Consolidated entity analysis
        """
        all_entities = []
        all_concepts = []
        all_technical_terms = []
        
        for extraction in entity_extractions:
            # Collect entities
            entities = extraction.get("entities", [])
            if isinstance(entities, list):
                all_entities.extend(entities)
            
            # Collect concepts
            concepts = extraction.get("concepts", [])
            if isinstance(concepts, list):
                all_concepts.extend(concepts)
            
            # Collect technical terms
            terms = extraction.get("technical_terms", [])
            if isinstance(terms, list):
                all_technical_terms.extend(terms)
        
        # Count entity frequencies
        entity_texts = [e.get("text", "") for e in all_entities if isinstance(e, dict)]
        entity_counter = Counter(entity_texts)
        top_entities = entity_counter.most_common(50)
        
        # Count concept frequencies
        concept_counter = Counter(all_concepts)
        top_concepts = concept_counter.most_common(50)
        
        # Count term frequencies
        term_counter = Counter(all_technical_terms)
        top_terms = term_counter.most_common(50)
        
        # Analyze entity types
        entity_types = {}
        for entity in all_entities:
            if isinstance(entity, dict):
                entity_type = entity.get("label", "UNKNOWN")
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        # Calculate coverage
        total_chunks = len(entity_extractions)
        chunks_with_entities = sum(1 for e in entity_extractions if e.get("entity_count", 0) > 0)
        
        return {
            "total_chunks_analyzed": total_chunks,
            "chunks_with_entities": chunks_with_entities,
            "entity_coverage": chunks_with_entities / total_chunks if total_chunks > 0 else 0,
            "total_entities": len(all_entities),
            "total_concepts": len(all_concepts),
            "total_technical_terms": len(all_technical_terms),
            "top_entities": top_entities,
            "top_concepts": top_concepts,
            "top_technical_terms": top_terms,
            "entity_type_distribution": dict(sorted(entity_types.items(), key=lambda x: x[1], reverse=True)),
            "entity_density": len(all_entities) / total_chunks if total_chunks > 0 else 0
        }
    
    def extract_subtopics_from_entities(
        self, 
        consolidated_entities: Dict[str, Any], 
        chunk_text: str = ""
    ) -> List[str]:
        """
        Extract subtopics from entities and concepts
        
        Args:
            consolidated_entities: Consolidated entity analysis
            chunk_text: Optional chunk text for context
            
        Returns:
            List of subtopics
        """
        subtopics = set()
        
        # Add top concepts as subtopics
        top_concepts = consolidated_entities.get("top_concepts", [])
        for concept, _ in top_concepts[:10]:
            if concept and len(concept) > 2:
                subtopics.add(concept.strip())
        
        # Add top entities as subtopics
        top_entities = consolidated_entities.get("top_entities", [])
        for entity, _ in top_entities[:10]:
            if entity and len(entity) > 2:
                subtopics.add(entity.strip())
        
        # Use LLM to generate subtopics from chunk text if available
        if chunk_text:
            try:
                llm_subtopics = self._extract_subtopics_with_llm(chunk_text)
                subtopics.update(llm_subtopics)
            except Exception as e:
                logger.warning(f"LLM subtopic extraction failed: {e}")
        
        # Clean and filter subtopics
        cleaned_subtopics = []
        for subtopic in subtopics:
            if subtopic and len(subtopic) > 2 and len(subtopic.split()) <= 5:
                cleaned_subtopics.append(subtopic)
        
        return cleaned_subtopics[:20]  # Limit to 20 subtopics
    
    def _extract_subtopics_with_llm(self, text: str) -> List[str]:
        """Extract subtopics using LLM"""
        prompt = f"""Extract 5-10 key subtopics from the following text:

        Text:
        {text[:1500]}

        Return as a JSON list of subtopics."""
        
        response = llm_client.generate_json(
            prompt=prompt,
            system_prompt="Extract key subtopics from text. Be concise and specific."
        )
        
        if isinstance(response, list):
            return response
        elif isinstance(response, dict) and "subtopics" in response:
            return response["subtopics"]
        else:
            return []
    
    def create_entity_graph(
        self, 
        entity_extractions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a graph of entity relationships
        
        Args:
            entity_extractions: Entity extraction results
            
        Returns:
            Entity graph structure
        """
        # This is a simplified version
        # In production, you might use more sophisticated co-occurrence analysis
        
        nodes = set()
        edges = []
        
        for extraction in entity_extractions:
            entities = extraction.get("entities", [])
            if not entities:
                continue
            
            # Extract entity texts
            entity_texts = []
            for entity in entities:
                if isinstance(entity, dict):
                    text = entity.get("text", "")
                    if text:
                        entity_texts.append(text)
                        nodes.add(text)
            
            # Create edges based on co-occurrence in same chunk
            for i in range(len(entity_texts)):
                for j in range(i + 1, len(entity_texts)):
                    edges.append({
                        "source": entity_texts[i],
                        "target": entity_texts[j],
                        "weight": 1,
                        "chunk_id": extraction.get("chunk_id", "")
                    })
        
        # Aggregate edge weights
        edge_dict = {}
        for edge in edges:
            key = (edge["source"], edge["target"])
            if key in edge_dict:
                edge_dict[key]["weight"] += 1
            else:
                edge_dict[key] = edge
        
        # Create final graph
        graph = {
            "nodes": [{"id": node, "label": node} for node in nodes],
            "edges": list(edge_dict.values()),
            "total_nodes": len(nodes),
            "total_edges": len(edge_dict),
            "density": len(edge_dict) / (len(nodes) * (len(nodes) - 1)) if len(nodes) > 1 else 0
        }
        
        return graph
    
    def analyze_entity_distribution(
        self, 
        entity_extractions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze entity distribution across pages
        
        Args:
            entity_extractions: Entity extraction results
            
        Returns:
            Distribution analysis
        """
        page_entities = {}
        
        for extraction in entity_extractions:
            page_num = extraction.get("page_number", 0)
            entities = extraction.get("entities", [])
            
            if page_num not in page_entities:
                page_entities[page_num] = []
            
            for entity in entities:
                if isinstance(entity, dict):
                    page_entities[page_num].append(entity.get("text", ""))
        
        # Calculate statistics per page
        page_stats = {}
        for page_num, entities in page_entities.items():
            unique_entities = set(entities)
            page_stats[page_num] = {
                "total_entities": len(entities),
                "unique_entities": len(unique_entities),
                "entity_density": len(entities) / 1000 if entities else 0,  # per 1000 chars
                "top_entities": Counter(entities).most_common(5)
            }
        
        # Overall statistics
        all_entities = [e for entities in page_entities.values() for e in entities]
        entity_counter = Counter(all_entities)
        
        return {
            "page_statistics": page_stats,
            "overall_statistics": {
                "total_pages": len(page_stats),
                "total_entities": len(all_entities),
                "unique_entities": len(entity_counter),
                "most_common_entities": entity_counter.most_common(20),
                "entity_richness": len(entity_counter) / len(page_stats) if page_stats else 0
            }
        }