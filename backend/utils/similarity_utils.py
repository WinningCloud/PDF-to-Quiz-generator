import numpy as np
from typing import List, Tuple, Dict, Any
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import logging
import os
logger = logging.getLogger(__name__)

class SimilarityUtils:
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )
    
    def calculate_cosine_similarity(
        self, 
        text1: str, 
        text2: str
    ) -> float:
        """
        Calculate cosine similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity (0-1)
        """
        if not text1 or not text2:
            return 0.0
        
        try:
            # Use TF-IDF for text similarity
            tfidf_matrix = self.tfidf_vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return self._calculate_simple_similarity(text1, text2)
    
    def _calculate_simple_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity as fallback"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_jaccard_similarity(
        self, 
        text1: str, 
        text2: str
    ) -> float:
        """
        Calculate Jaccard similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Jaccard similarity (0-1)
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_semantic_similarity(
        self, 
        embedding1: List[float], 
        embedding2: List[float]
    ) -> float:
        """
        Calculate semantic similarity between embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Semantic similarity (0-1)
        """
        if not embedding1 or not embedding2:
            return 0.0
        
        if len(embedding1) != len(embedding2):
            logger.warning(f"Embedding dimensions don't match: {len(embedding1)} vs {len(embedding2)}")
            return 0.0
        
        try:
            # Convert to numpy arrays
            emb1 = np.array(embedding1).reshape(1, -1)
            emb2 = np.array(embedding2).reshape(1, -1)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def find_similar_items(
        self, 
        query: str, 
        items: List[str], 
        threshold: float = 0.7,
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Find items similar to query
        
        Args:
            query: Query text
            items: List of items to search
            threshold: Similarity threshold
            top_k: Number of results to return
            
        Returns:
            List of (index, similarity) tuples
        """
        if not query or not items:
            return []
        
        try:
            # Calculate similarities
            similarities = []
            for i, item in enumerate(items):
                similarity = self.calculate_cosine_similarity(query, item)
                similarities.append((i, similarity))
            
            # Filter by threshold and sort
            filtered = [(i, sim) for i, sim in similarities if sim >= threshold]
            filtered.sort(key=lambda x: x[1], reverse=True)
            
            return filtered[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding similar items: {e}")
            return []
    
    def calculate_pairwise_similarities(
        self, 
        texts: List[str]
    ) -> np.ndarray:
        """
        Calculate pairwise similarities between texts
        
        Args:
            texts: List of texts
            
        Returns:
            Similarity matrix
        """
        if not texts or len(texts) < 2:
            return np.array([])
        
        try:
            # Create TF-IDF matrix
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # Calculate pairwise similarities
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            return similarity_matrix
            
        except Exception as e:
            logger.error(f"Error calculating pairwise similarities: {e}")
            return np.array([])
    
    def cluster_by_similarity(
        self, 
        texts: List[str], 
        threshold: float = 0.7
    ) -> List[List[int]]:
        """
        Cluster texts by similarity
        
        Args:
            texts: List of texts
            threshold: Similarity threshold for clustering
            
        Returns:
            List of clusters (each cluster is list of indices)
        """
        if not texts:
            return []
        
        # Calculate similarity matrix
        similarity_matrix = self.calculate_pairwise_similarities(texts)
        
        if similarity_matrix.size == 0:
            return []
        
        # Simple clustering (connected components)
        n = len(texts)
        visited = [False] * n
        clusters = []
        
        for i in range(n):
            if not visited[i]:
                # Start new cluster
                cluster = [i]
                visited[i] = True
                
                # Find all similar items
                stack = [i]
                while stack:
                    current = stack.pop()
                    for j in range(n):
                        if not visited[j] and similarity_matrix[current, j] >= threshold:
                            cluster.append(j)
                            visited[j] = True
                            stack.append(j)
                
                clusters.append(cluster)
        
        return clusters
    
    def calculate_text_diversity(
        self, 
        texts: List[str]
    ) -> float:
        """
        Calculate diversity score for a set of texts
        
        Args:
            texts: List of texts
            
        Returns:
            Diversity score (0-1, higher = more diverse)
        """
        if not texts or len(texts) < 2:
            return 0.0
        
        try:
            # Calculate pairwise similarities
            similarity_matrix = self.calculate_pairwise_similarities(texts)
            
            if similarity_matrix.size == 0:
                return 0.0
            
            # Get upper triangle (excluding diagonal)
            n = len(texts)
            similarities = []
            for i in range(n):
                for j in range(i + 1, n):
                    similarities.append(similarity_matrix[i, j])
            
            if not similarities:
                return 0.0
            
            # Diversity = 1 - average similarity
            avg_similarity = np.mean(similarities)
            diversity = 1.0 - avg_similarity
            
            return float(max(0.0, min(1.0, diversity)))
            
        except Exception as e:
            logger.error(f"Error calculating text diversity: {e}")
            return 0.0
    
    def calculate_similarity_distribution(
        self, 
        texts: List[str]
    ) -> Dict[str, Any]:
        """
        Calculate similarity distribution statistics
        
        Args:
            texts: List of texts
            
        Returns:
            Similarity distribution statistics
        """
        if not texts or len(texts) < 2:
            return {"error": "Not enough texts"}
        
        try:
            similarity_matrix = self.calculate_pairwise_similarities(texts)
            
            if similarity_matrix.size == 0:
                return {"error": "Could not calculate similarities"}
            
            # Get all pairwise similarities
            n = len(texts)
            similarities = []
            for i in range(n):
                for j in range(i + 1, n):
                    similarities.append(similarity_matrix[i, j])
            
            if not similarities:
                return {"error": "No similarities calculated"}
            
            # Calculate statistics
            stats = {
                "count": len(similarities),
                "mean": float(np.mean(similarities)),
                "median": float(np.median(similarities)),
                "std": float(np.std(similarities)),
                "min": float(np.min(similarities)),
                "max": float(np.max(similarities)),
                "q1": float(np.percentile(similarities, 25)),
                "q3": float(np.percentile(similarities, 75)),
                "diversity_score": 1.0 - float(np.mean(similarities))
            }
            
            # Distribution buckets
            buckets = {"0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, 
                      "0.6-0.8": 0, "0.8-1.0": 0}
            
            for sim in similarities:
                if sim <= 0.2:
                    buckets["0-0.2"] += 1
                elif sim <= 0.4:
                    buckets["0.2-0.4"] += 1
                elif sim <= 0.6:
                    buckets["0.4-0.6"] += 1
                elif sim <= 0.8:
                    buckets["0.6-0.8"] += 1
                else:
                    buckets["0.8-1.0"] += 1
            
            # Convert to percentages
            total = len(similarities)
            for key in buckets:
                buckets[key] = buckets[key] / total * 100
            
            stats["distribution"] = buckets
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating similarity distribution: {e}")
            return {"error": str(e)}

# Convenience functions
def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts"""
    utils = SimilarityUtils()
    return utils.calculate_cosine_similarity(text1, text2)

def jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts"""
    utils = SimilarityUtils()
    return utils.calculate_jaccard_similarity(text1, text2)

def semantic_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate semantic similarity between embeddings"""
    utils = SimilarityUtils()
    return utils.calculate_semantic_similarity(embedding1, embedding2)