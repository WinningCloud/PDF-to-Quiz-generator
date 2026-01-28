import json
from typing import Dict, List, Any, Tuple
import logging
from config.llm_config import llm_client, embedding_model
from config.prompts import SystemPrompts, UserPrompts
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import pairwise_distances_argmin_min

logger = logging.getLogger(__name__)

class TopicAgent:
    def __init__(self):
        self.system_prompt = SystemPrompts.TOPIC_EXTRACTOR_SYSTEM
    
    def extract_topics_from_chunk(self, chunk: Dict) -> Dict[str, Any]:
        """
        Extract topics and subtopics from a single chunk
        
        Args:
            chunk: Dictionary containing chunk info and text
            
        Returns:
            Topics and subtopics for the chunk
        """
        try:
            chunk_text = chunk.get("text", "")
            page_num = chunk.get("page_number", 1)
            
            prompt = UserPrompts.extract_topics(chunk_text, page_num)
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            # Add metadata
            response.update({
                "chunk_id": chunk.get("chunk_id"),
                "page_number": page_num,
                "source": "llm_extraction"
            })
            
            logger.info(f"Extracted topics from chunk {chunk.get('chunk_id')}")
            return response
            
        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
            return self._extract_topics_fallback(chunk)
    
    def extract_topics_from_all_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Extract topics from all chunks
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List of topic extractions for each chunk
        """
        all_topics = []
        
        for chunk in chunks:
            topics = self.extract_topics_from_chunk(chunk)
            all_topics.append(topics)
        
        return all_topics
    
    def consolidate_topics(self, topic_extractions: List[Dict]) -> Dict[str, Any]:
        """
        Consolidate topics from multiple chunks
        
        Args:
            topic_extractions: List of topic extraction results
            
        Returns:
            Consolidated topics structure
        """
        all_main_topics = []
        all_subtopics = []
        all_concepts = []
        
        for extraction in topic_extractions:
            all_main_topics.extend(extraction.get("main_topics", []))
            all_subtopics.extend(extraction.get("subtopics", []))
            all_concepts.extend(extraction.get("key_concepts", []))
        
        # Clean and deduplicate
        all_main_topics = list(dict.fromkeys([t.strip() for t in all_main_topics if t.strip()]))
        all_subtopics = list(dict.fromkeys([t.strip() for t in all_subtopics if t.strip()]))
        all_concepts = list(dict.fromkeys([t.strip() for t in all_concepts if t.strip()]))
        
        # Group subtopics under main topics (simplified)
        topic_hierarchy = {}
        for main_topic in all_main_topics[:10]:  # Limit to top 10
            related_subtopics = []
            for subtopic in all_subtopics:
                if main_topic.lower() in subtopic.lower() or subtopic.lower() in main_topic.lower():
                    related_subtopics.append(subtopic)
            
            # Also find related concepts
            related_concepts = []
            for concept in all_concepts:
                if main_topic.lower() in concept.lower() or concept.lower() in main_topic.lower():
                    related_concepts.append(concept)
            
            topic_hierarchy[main_topic] = {
                "subtopics": list(dict.fromkeys(related_subtopics))[:5],
                "concepts": list(dict.fromkeys(related_concepts))[:10],
                "frequency": all_main_topics.count(main_topic)
            }
        
        return {
            "total_main_topics": len(all_main_topics),
            "total_subtopics": len(all_subtopics),
            "total_concepts": len(all_concepts),
            "main_topics": all_main_topics,
            "subtopics": all_subtopics,
            "concepts": all_concepts,
            "topic_hierarchy": topic_hierarchy,
            "topic_coverage": self._calculate_topic_coverage(topic_hierarchy)
        }
    
    def normalize_topics(self, subtopics: List[str], target_count: int = 10) -> Dict[str, Any]:
        """
        Normalize subtopics into main topics using clustering
        
        Args:
            subtopics: List of subtopic strings
            target_count: Target number of main topics
            
        Returns:
            Normalized topics structure
        """
        if not subtopics:
            return {"normalized_topics": [], "mapping": {}}
        
        # Generate embeddings for subtopics
        subtopic_embeddings = embedding_model.embed_batch(subtopics)
        embeddings_array = np.array(subtopic_embeddings)
        
        # Determine optimal number of clusters
        optimal_clusters = min(target_count, len(subtopics))
        
        # Cluster using KMeans
        kmeans = KMeans(n_clusters=optimal_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings_array)
        
        # Find centroid topics (closest to cluster center)
        centroids = kmeans.cluster_centers_
        closest_indices, _ = pairwise_distances_argmin_min(centroids, embeddings_array)
        
        # Create normalized topics
        normalized_topics = []
        mapping = {}
        
        for cluster_id in range(optimal_clusters):
            # Get subtopics in this cluster
            cluster_subtopic_indices = np.where(cluster_labels == cluster_id)[0]
            cluster_subtopics = [subtopics[i] for i in cluster_subtopic_indices]
            
            # Use centroid subtopic as main topic name
            centroid_idx = closest_indices[cluster_id]
            main_topic = subtopics[centroid_idx]
            
            # Get AI to generate better topic name
            try:
                prompt = f"""Given these related subtopics, suggest a comprehensive main topic name:
                
                Subtopic List:
                {cluster_subtopics}
                
                Current proposed name: {main_topic}
                
                Suggest a better, more comprehensive topic name that covers all these subtopics."""
                
                better_name = llm_client.generate(
                    prompt=prompt,
                    system_prompt="You are a topic naming expert. Suggest concise, descriptive topic names.",
                    max_tokens=50
                ).strip()
                
                if better_name and len(better_name) > 3:
                    main_topic = better_name
            except:
                pass  # Keep original name if AI fails
            
            normalized_topics.append({
                "topic_id": cluster_id + 1,
                "topic_name": main_topic,
                "subtopics": cluster_subtopics,
                "subtopic_count": len(cluster_subtopics),
                "representative_subtopic": main_topic
            })
            
            # Create mapping
            for subtopic in cluster_subtopics:
                mapping[subtopic] = main_topic
        
        return {
            "normalized_topics": normalized_topics,
            "mapping": mapping,
            "cluster_stats": {
                "total_clusters": optimal_clusters,
                "average_subtopics_per_cluster": len(subtopics) / optimal_clusters,
                "clustering_method": "kmeans"
            }
        }
    
    def assign_questions_to_topics(self, questions: List[Dict], topic_mapping: Dict) -> List[Dict]:
        """
        Assign questions to normalized topics
        
        Args:
            questions: List of question dictionaries
            topic_mapping: Mapping from subtopic to normalized topic
            
        Returns:
            Questions with assigned topics
        """
        for question in questions:
            subtopic = question.get("subtopic", "")
            if subtopic in topic_mapping:
                question["normalized_topic"] = topic_mapping[subtopic]
            else:
                # Find closest topic
                closest_topic = self._find_closest_topic(subtopic, list(topic_mapping.values()))
                question["normalized_topic"] = closest_topic
        
        return questions
    
    def _find_closest_topic(self, subtopic: str, topics: List[str]) -> str:
        """Find closest topic using embedding similarity"""
        if not topics:
            return "General"
        
        subtopic_embedding = embedding_model.embed(subtopic)
        topic_embeddings = embedding_model.embed_batch(topics)
        
        # Calculate cosine similarities
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity([subtopic_embedding], topic_embeddings)[0]
        
        max_idx = np.argmax(similarities)
        return topics[max_idx]
    
    def _calculate_topic_coverage(self, topic_hierarchy: Dict) -> Dict[str, float]:
        """Calculate coverage metrics for topics"""
        total_topics = len(topic_hierarchy)
        if total_topics == 0:
            return {"coverage": 0, "diversity": 0, "depth": 0}
        
        # Calculate average subtopics per topic
        subtopic_counts = [len(data["subtopics"]) for data in topic_hierarchy.values()]
        avg_subtopics = sum(subtopic_counts) / total_topics
        
        # Calculate concept diversity
        concept_counts = [len(data["concepts"]) for data in topic_hierarchy.values()]
        avg_concepts = sum(concept_counts) / total_topics
        
        return {
            "coverage": min(1.0, total_topics / 20),  # Normalize
            "diversity": min(1.0, avg_subtopics / 5),
            "depth": min(1.0, avg_concepts / 10),
            "richness": min(1.0, (avg_subtopics + avg_concepts) / 15)
        }
    
    def _extract_topics_fallback(self, chunk: Dict) -> Dict[str, Any]:
        """Fallback topic extraction using simple methods"""
        text = chunk.get("text", "")
        words = text.lower().split()
        
        # Remove common words
        common_words = set(["the", "and", "is", "in", "to", "of", "a", "that", "it", "with", "for", "on", "as", "by", "at"])
        content_words = [w for w in words if w not in common_words and len(w) > 3]
        
        # Simple frequency analysis
        from collections import Counter
        word_freq = Counter(content_words)
        top_words = [word for word, freq in word_freq.most_common(10)]
        
        # Use top words as topics
        main_topics = top_words[:3] if len(top_words) >= 3 else top_words
        subtopics = top_words[3:] if len(top_words) > 3 else []
        
        return {
            "chunk_id": chunk.get("chunk_id"),
            "page_number": chunk.get("page_number", 1),
            "main_topics": main_topics,
            "subtopics": subtopics,
            "key_concepts": top_words[:5],
            "source": "fallback_extraction"
        }