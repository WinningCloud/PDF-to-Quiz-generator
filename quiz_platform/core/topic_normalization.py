import numpy as np
from typing import Dict, List, Any, Tuple, Set
import logging
from collections import Counter, defaultdict
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
from config.llm_config import llm_client, embedding_model
from config.settings import settings

logger = logging.getLogger(__name__)

class TopicNormalizer:
    def __init__(self, target_topic_count: int = 10):
        """
        Initialize topic normalizer
        
        Args:
            target_topic_count: Target number of normalized topics
        """
        self.target_topic_count = target_topic_count
    
    def normalize_topics(
        self, 
        subtopics: List[str], 
        topic_hierarchy: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Normalize subtopics into main topics
        
        Args:
            subtopics: List of subtopic strings
            topic_hierarchy: Optional existing topic hierarchy
            
        Returns:
            Normalized topics structure
        """
        if not subtopics:
            return self._create_empty_normalization()
        
        # Clean and filter subtopics
        cleaned_subtopics = self._clean_subtopics(subtopics)
        
        if len(cleaned_subtopics) <= self.target_topic_count:
            # Not enough subtopics to cluster
            return self._create_simple_normalization(cleaned_subtopics)
        
        try:
            # Generate embeddings for subtopics
            subtopic_embeddings = embedding_model.embed_batch(cleaned_subtopics)
            embeddings_array = np.array(subtopic_embeddings, dtype=np.float32)
            
            # Determine optimal number of clusters
            optimal_clusters = self._determine_optimal_clusters(
                embeddings_array, 
                cleaned_subtopics
            )
            
            # Cluster subtopics
            clusters = self._cluster_subtopics(
                cleaned_subtopics, 
                embeddings_array, 
                optimal_clusters
            )
            
            # Create normalized topics
            normalized_topics = self._create_normalized_topics(clusters, cleaned_subtopics)
            
            # Map subtopics to normalized topics
            topic_mapping = self._create_topic_mapping(normalized_topics)
            
            # Calculate statistics
            stats = self._calculate_normalization_stats(normalized_topics, cleaned_subtopics)
            
            result = {
                "normalized_topics": normalized_topics,
                "topic_mapping": topic_mapping,
                "original_subtopics": cleaned_subtopics,
                "statistics": stats,
                "clustering_method": "kmeans",
                "normalization_method": "embedding_clustering"
            }
            
            logger.info(f"Normalized {len(cleaned_subtopics)} subtopics into {len(normalized_topics)} topics")
            return result
            
        except Exception as e:
            logger.error(f"Error normalizing topics with clustering: {e}")
            return self._normalize_with_llm_fallback(cleaned_subtopics)
    
    def _determine_optimal_clusters(
        self, 
        embeddings: np.ndarray, 
        subtopics: List[str]
    ) -> int:
        """Determine optimal number of clusters"""
        max_clusters = min(self.target_topic_count * 2, len(subtopics) - 1)
        min_clusters = min(3, len(subtopics))
        
        if max_clusters <= min_clusters:
            return min_clusters
        
        # Try silhouette score for different cluster counts
        best_score = -1
        best_k = self.target_topic_count
        
        for k in range(min_clusters, max_clusters + 1):
            try:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(embeddings)
                
                # Calculate silhouette score
                if k > 1:
                    score = silhouette_score(embeddings, cluster_labels)
                else:
                    score = 0
                
                if score > best_score:
                    best_score = score
                    best_k = k
                    
                logger.debug(f"Cluster evaluation: k={k}, silhouette={score:.3f}")
                
            except Exception as e:
                logger.debug(f"Failed to evaluate k={k}: {e}")
                continue
        
        logger.info(f"Optimal cluster count: {best_k} (silhouette: {best_score:.3f})")
        return best_k
    
    def _cluster_subtopics(
        self, 
        subtopics: List[str], 
        embeddings: np.ndarray, 
        n_clusters: int
    ) -> Dict[int, List[str]]:
        """Cluster subtopics using KMeans"""
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # Organize subtopics by cluster
        clusters = defaultdict(list)
        for subtopic, label in zip(subtopics, cluster_labels):
            clusters[label].append(subtopic)
        
        return dict(clusters)
    
    def _create_normalized_topics(
        self, 
        clusters: Dict[int, List[str]], 
        all_subtopics: List[str]
    ) -> List[Dict[str, Any]]:
        """Create normalized topics from clusters"""
        normalized_topics = []
        
        for cluster_id, cluster_subtopics in clusters.items():
            if not cluster_subtopics:
                continue
            
            # Generate topic name using LLM
            topic_name = self._generate_topic_name(cluster_subtopics)
            
            # Find representative subtopic
            representative = self._find_representative_subtopic(
                cluster_subtopics, 
                all_subtopics
            )
            
            # Calculate cluster statistics
            cluster_stats = self._calculate_cluster_stats(cluster_subtopics)
            
            topic_data = {
                "topic_id": f"topic_{cluster_id + 1:03d}",
                "topic_name": topic_name,
                "subtopics": cluster_subtopics,
                "subtopic_count": len(cluster_subtopics),
                "representative_subtopic": representative,
                "cluster_id": cluster_id,
                "statistics": cluster_stats
            }
            
            normalized_topics.append(topic_data)
        
        # Sort topics by subtopic count (descending)
        normalized_topics.sort(key=lambda x: x["subtopic_count"], reverse=True)
        
        return normalized_topics
    
    def _generate_topic_name(self, subtopics: List[str]) -> str:
        """Generate descriptive topic name using LLM"""
        try:
            prompt = f"""Given these related subtopics, suggest a comprehensive, descriptive topic name that covers them all:

            Subtopics:
            {subtopics}

            Requirements:
            1. Be concise (2-5 words)
            2. Be descriptive and comprehensive
            3. Use academic/professional language
            4. Avoid being too general

            Return only the topic name."""
            
            topic_name = llm_client.generate(
                prompt=prompt,
                system_prompt="You are a topic naming expert. Create concise, descriptive topic names.",
                max_tokens=30
            ).strip()
            
            # Clean the response
            topic_name = topic_name.replace('"', '').replace("'", "").strip()
            
            if topic_name and len(topic_name.split()) <= 6:
                return topic_name
            
        except Exception as e:
            logger.warning(f"LLM topic naming failed: {e}")
        
        # Fallback: use most frequent words in subtopics
        return self._generate_fallback_topic_name(subtopics)
    
    def _generate_fallback_topic_name(self, subtopics: List[str]) -> str:
        """Generate topic name using word frequency"""
        # Extract all words
        all_words = []
        for subtopic in subtopics:
            words = subtopic.lower().split()
            # Filter out common words
            common_words = {"the", "and", "of", "in", "to", "for", "on", "with", "by", "at"}
            filtered_words = [w for w in words if w not in common_words and len(w) > 2]
            all_words.extend(filtered_words)
        
        if not all_words:
            return "General Topics"
        
        # Find most common words
        word_counter = Counter(all_words)
        top_words = [word for word, count in word_counter.most_common(3)]
        
        if top_words:
            return " ".join(word.capitalize() for word in top_words)
        else:
            return "General Topics"
    
    def _find_representative_subtopic(
        self, 
        cluster_subtopics: List[str], 
        all_subtopics: List[str]
    ) -> str:
        """Find representative subtopic for cluster"""
        if not cluster_subtopics:
            return ""
        
        # Use the subtopic with highest TF-IDF score
        # Simplified: use the most central subtopic by embedding
        try:
            # Generate embeddings for cluster subtopics
            cluster_embeddings = embedding_model.embed_batch(cluster_subtopics)
            cluster_center = np.mean(cluster_embeddings, axis=0)
            
            # Find subtopic closest to center
            distances = np.linalg.norm(cluster_embeddings - cluster_center, axis=1)
            closest_idx = np.argmin(distances)
            
            return cluster_subtopics[closest_idx]
        except:
            # Fallback: use first subtopic
            return cluster_subtopics[0]
    
    def _calculate_cluster_stats(self, cluster_subtopics: List[str]) -> Dict[str, Any]:
        """Calculate cluster statistics"""
        # Calculate average word count
        word_counts = [len(st.split()) for st in cluster_subtopics]
        avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
        
        # Calculate length statistics
        char_counts = [len(st) for st in cluster_subtopics]
        
        return {
            "subtopic_count": len(cluster_subtopics),
            "average_word_count": avg_words,
            "min_length": min(char_counts) if char_counts else 0,
            "max_length": max(char_counts) if char_counts else 0,
            "cohesion_score": self._calculate_cluster_cohesion(cluster_subtopics)
        }
    
    def _calculate_cluster_cohesion(self, subtopics: List[str]) -> float:
        """Calculate cluster cohesion score"""
        if len(subtopics) <= 1:
            return 1.0
        
        try:
            # Generate embeddings
            embeddings = embedding_model.embed_batch(subtopics)
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Calculate pairwise cosine similarities
            from sklearn.metrics.pairwise import cosine_similarity
            similarity_matrix = cosine_similarity(embeddings_array)
            
            # Average similarity (excluding self-similarity)
            np.fill_diagonal(similarity_matrix, 0)
            total_pairs = len(subtopics) * (len(subtopics) - 1)
            
            if total_pairs > 0:
                avg_similarity = np.sum(similarity_matrix) / total_pairs
                return float(avg_similarity)
            else:
                return 0.0
                
        except Exception as e:
            logger.debug(f"Could not calculate cohesion: {e}")
            return 0.5  # Default moderate cohesion
    
    def _create_topic_mapping(
        self, 
        normalized_topics: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Create mapping from subtopic to normalized topic"""
        mapping = {}
        
        for topic in normalized_topics:
            topic_name = topic["topic_name"]
            for subtopic in topic["subtopics"]:
                mapping[subtopic] = topic_name
        
        return mapping
    
    def _calculate_normalization_stats(
        self, 
        normalized_topics: List[Dict[str, Any]], 
        original_subtopics: List[str]
    ) -> Dict[str, Any]:
        """Calculate normalization statistics"""
        total_subtopics = len(original_subtopics)
        total_topics = len(normalized_topics)
        
        # Calculate coverage
        mapped_subtopics = set()
        for topic in normalized_topics:
            mapped_subtopics.update(topic["subtopics"])
        
        coverage = len(mapped_subtopics) / total_subtopics if total_subtopics > 0 else 0
        
        # Calculate distribution statistics
        subtopic_counts = [topic["subtopic_count"] for topic in normalized_topics]
        
        if subtopic_counts:
            avg_subtopics_per_topic = sum(subtopic_counts) / total_topics
            std_subtopics_per_topic = np.std(subtopic_counts)
        else:
            avg_subtopics_per_topic = 0
            std_subtopics_per_topic = 0
        
        # Calculate balance score (1.0 = perfect balance)
        if avg_subtopics_per_topic > 0:
            balance_score = 1.0 / (1.0 + std_subtopics_per_topic / avg_subtopics_per_topic)
        else:
            balance_score = 0.0
        
        # Calculate overall cohesion
        cohesion_scores = [topic["statistics"]["cohesion_score"] for topic in normalized_topics]
        avg_cohesion = sum(cohesion_scores) / total_topics if cohesion_scores else 0
        
        return {
            "total_original_subtopics": total_subtopics,
            "total_normalized_topics": total_topics,
            "coverage_percentage": coverage * 100,
            "average_subtopics_per_topic": avg_subtopics_per_topic,
            "subtopic_distribution_std": std_subtopics_per_topic,
            "balance_score": balance_score,
            "average_cohesion_score": avg_cohesion,
            "normalization_quality": self._assess_normalization_quality(
                coverage, balance_score, avg_cohesion
            )
        }
    
    def _assess_normalization_quality(
        self, 
        coverage: float, 
        balance: float, 
        cohesion: float
    ) -> str:
        """Assess overall normalization quality"""
        quality_score = (coverage * 0.4 + balance * 0.3 + cohesion * 0.3)
        
        if quality_score >= 0.8:
            return "Excellent"
        elif quality_score >= 0.7:
            return "Good"
        elif quality_score >= 0.6:
            return "Fair"
        else:
            return "Needs Improvement"
    
    def _clean_subtopics(self, subtopics: List[str]) -> List[str]:
        """Clean and filter subtopics"""
        cleaned = []
        seen = set()
        
        for subtopic in subtopics:
            if not isinstance(subtopic, str):
                continue
            
            # Clean subtopic
            st = subtopic.strip()
            st = ' '.join(st.split())  # Remove extra whitespace
            
            # Filter criteria
            if (st and 
                len(st) >= 2 and 
                len(st) <= 100 and 
                st.lower() not in seen):
                
                seen.add(st.lower())
                cleaned.append(st)
        
        return cleaned
    
    def _create_empty_normalization(self) -> Dict[str, Any]:
        """Create empty normalization result"""
        return {
            "normalized_topics": [],
            "topic_mapping": {},
            "original_subtopics": [],
            "statistics": {
                "total_original_subtopics": 0,
                "total_normalized_topics": 0,
                "coverage_percentage": 0,
                "normalization_quality": "No Data"
            }
        }
    
    def _create_simple_normalization(self, subtopics: List[str]) -> Dict[str, Any]:
        """Create simple normalization when there are few subtopics"""
        normalized_topics = []
        
        for i, subtopic in enumerate(subtopics):
            topic_data = {
                "topic_id": f"topic_{i+1:03d}",
                "topic_name": subtopic,
                "subtopics": [subtopic],
                "subtopic_count": 1,
                "representative_subtopic": subtopic,
                "statistics": {
                    "subtopic_count": 1,
                    "average_word_count": len(subtopic.split()),
                    "cohesion_score": 1.0
                }
            }
            normalized_topics.append(topic_data)
        
        # Create mapping
        topic_mapping = {st: st for st in subtopics}
        
        return {
            "normalized_topics": normalized_topics,
            "topic_mapping": topic_mapping,
            "original_subtopics": subtopics,
            "statistics": {
                "total_original_subtopics": len(subtopics),
                "total_normalized_topics": len(subtopics),
                "coverage_percentage": 100.0,
                "average_subtopics_per_topic": 1.0,
                "normalization_quality": "Perfect (1:1 mapping)"
            }
        }
    
    def _normalize_with_llm_fallback(self, subtopics: List[str]) -> Dict[str, Any]:
        """Normalize topics using LLM as fallback"""
        try:
            prompt = f"""Group these {len(subtopics)} subtopics into approximately {self.target_topic_count} main topics:

            Subtopics:
            {subtopics}

            Requirements:
            1. Group semantically similar subtopics together
            2. Create descriptive, comprehensive topic names
            3. Aim for {self.target_topic_count} topics (±2)
            4. Each subtopic should belong to exactly one topic

            Return JSON with:
            - normalized_topics: list of topics, each with topic_name and subtopics
            - topic_mapping: mapping from subtopic to topic_name
            """
            
            response = llm_client.generate_json(
                prompt=prompt,
                system_prompt="You are a topic normalization expert. Group subtopics into meaningful topics."
            )
            
            # Format response
            normalized_topics = []
            if "normalized_topics" in response:
                for i, topic in enumerate(response["normalized_topics"]):
                    if isinstance(topic, dict):
                        normalized_topics.append({
                            "topic_id": f"topic_{i+1:03d}",
                            "topic_name": topic.get("topic_name", f"Topic {i+1}"),
                            "subtopics": topic.get("subtopics", []),
                            "subtopic_count": len(topic.get("subtopics", [])),
                            "representative_subtopic": topic.get("subtopics", [""])[0],
                            "statistics": {
                                "subtopic_count": len(topic.get("subtopics", [])),
                                "average_word_count": 0,  # Would need calculation
                                "cohesion_score": 0.7  # Default
                            }
                        })
            
            topic_mapping = response.get("topic_mapping", {})
            
            return {
                "normalized_topics": normalized_topics,
                "topic_mapping": topic_mapping,
                "original_subtopics": subtopics,
                "statistics": {
                    "total_original_subtopics": len(subtopics),
                    "total_normalized_topics": len(normalized_topics),
                    "coverage_percentage": 100.0,  # Assuming full coverage
                    "normalization_quality": "LLM-based"
                },
                "normalization_method": "llm_fallback"
            }
            
        except Exception as e:
            logger.error(f"LLM normalization failed: {e}")
            return self._create_simple_normalization(subtopics)
    
    def map_questions_to_normalized_topics(
        self, 
        questions: List[Dict[str, Any]], 
        topic_mapping: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Map questions to normalized topics
        
        Args:
            questions: List of question dictionaries
            topic_mapping: Mapping from subtopic to normalized topic
            
        Returns:
            Questions with normalized topics
        """
        mapped_questions = []
        
        for question in questions:
            subtopic = question.get("subtopic", "")
            normalized_topic = topic_mapping.get(subtopic, "")
            
            if not normalized_topic and subtopic:
                # Try to find similar topic
                normalized_topic = self._find_similar_topic(subtopic, topic_mapping)
            
            question["normalized_topic"] = normalized_topic or "General"
            mapped_questions.append(question)
        
        # Calculate topic distribution
        topic_distribution = Counter(
            q["normalized_topic"] for q in mapped_questions
        )
        
        logger.info(f"Mapped questions to {len(set(topic_distribution.keys()))} topics")
        return mapped_questions
    
    def _find_similar_topic(
        self, 
        subtopic: str, 
        topic_mapping: Dict[str, str]
    ) -> str:
        """Find similar topic using embedding similarity"""
        if not subtopic or not topic_mapping:
            return "General"
        
        try:
            # Generate embedding for subtopic
            subtopic_embedding = embedding_model.embed(subtopic)
            
            # Generate embeddings for all mapped subtopics
            mapped_subtopics = list(topic_mapping.keys())
            mapped_embeddings = embedding_model.embed_batch(mapped_subtopics)
            
            # Calculate similarities
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity([subtopic_embedding], mapped_embeddings)[0]
            
            # Find most similar
            max_idx = np.argmax(similarities)
            if similarities[max_idx] > 0.6:  # Threshold
                return topic_mapping[mapped_subtopics[max_idx]]
            
        except Exception as e:
            logger.debug(f"Could not find similar topic: {e}")
        
        return "General"