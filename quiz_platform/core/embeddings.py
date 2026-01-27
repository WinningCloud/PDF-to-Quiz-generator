import numpy as np
from typing import List, Dict, Any, Tuple
import logging
import pickle
import os
from datetime import datetime
import json
from quiz_platform.config.llm_config import embedding_model

logger = logging.getLogger(__name__)

class EmbeddingManager:
    def __init__(self, vector_index_dir: str):
        """
        Initialize embedding manager
        
        Args:
            vector_index_dir: Directory to store vector indices
        """
        self.vector_index_dir = vector_index_dir
        os.makedirs(vector_index_dir, exist_ok=True)
        
    def generate_embeddings(
        self, 
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for chunks
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List of chunks with embeddings
        """
        if not chunks:
            return []
        
        # Extract texts
        texts = [chunk.get("text", "") for chunk in chunks]
        
        try:
            # Generate embeddings in batches
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = embedding_model.embed_batch(batch_texts)
                all_embeddings.extend(batch_embeddings)
                
                logger.debug(f"Generated embeddings for batch {i//batch_size + 1}")
            
            # Add embeddings to chunks
            for i, chunk in enumerate(chunks):
                if i < len(all_embeddings):
                    chunk["embedding"] = all_embeddings[i]
                    chunk["embedding_dim"] = len(all_embeddings[i])
                    chunk["embedding_generated_at"] = datetime.utcnow().isoformat()
                else:
                    logger.warning(f"No embedding generated for chunk {i}")
            
            logger.info(f"Generated embeddings for {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Return chunks without embeddings
            for chunk in chunks:
                chunk["embedding_error"] = str(e)
            return chunks
    
    def create_vector_index(
        self, 
        chunks_with_embeddings: List[Dict[str, Any]], 
        index_name: str
    ) -> str:
        """
        Create vector index from embeddings
        
        Args:
            chunks_with_embeddings: Chunks with embeddings
            index_name: Name for the index
            
        Returns:
            Path to saved index
        """
        try:
            # Extract embeddings and metadata
            embeddings = []
            metadata = []
            
            for chunk in chunks_with_embeddings:
                embedding = chunk.get("embedding")
                if embedding is not None:
                    embeddings.append(embedding)
                    
                    # Prepare metadata
                    chunk_meta = {
                        "chunk_id": chunk.get("chunk_id"),
                        "page_number": chunk.get("page_number"),
                        "text_preview": chunk.get("text", "")[:200],
                        "word_count": chunk.get("word_count", 0),
                        "previous_page_ref": chunk.get("previous_page_ref", ""),
                        "next_page_ref": chunk.get("next_page_ref", ""),
                        "metadata": chunk.get("metadata", {})
                    }
                    metadata.append(chunk_meta)
            
            if not embeddings:
                raise ValueError("No embeddings found in chunks")
            
            # Convert to numpy arrays
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Create index directory
            index_dir = os.path.join(self.vector_index_dir, index_name)
            os.makedirs(index_dir, exist_ok=True)
            
            # Save embeddings and metadata
            index_data = {
                "embeddings": embeddings_array,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat(),
                "total_vectors": len(embeddings),
                "embedding_dim": embeddings_array.shape[1]
            }
            
            index_path = os.path.join(index_dir, "vector_index.pkl")
            with open(index_path, 'wb') as f:
                pickle.dump(index_data, f)
            
            # Save metadata separately for easy access
            metadata_path = os.path.join(index_dir, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created vector index at {index_path} with {len(embeddings)} vectors")
            return index_path
            
        except Exception as e:
            logger.error(f"Error creating vector index: {e}")
            raise
    
    def load_vector_index(self, index_path: str) -> Dict[str, Any]:
        """
        Load vector index from file
        
        Args:
            index_path: Path to index file
            
        Returns:
            Loaded index data
        """
        try:
            with open(index_path, 'rb') as f:
                index_data = pickle.load(f)
            
            logger.info(f"Loaded vector index from {index_path}")
            return index_data
            
        except Exception as e:
            logger.error(f"Error loading vector index: {e}")
            raise
    
    def search_similar_chunks(
        self, 
        query: str, 
        index_data: Dict[str, Any], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using embeddings
        
        Args:
            query: Search query
            index_data: Loaded index data
            top_k: Number of results to return
            
        Returns:
            List of similar chunks with scores
        """
        try:
            # Generate embedding for query
            query_embedding = embedding_model.embed(query)
            
            # Get embeddings from index
            embeddings = index_data.get("embeddings")
            metadata = index_data.get("metadata", [])
            
            if embeddings is None or not metadata:
                raise ValueError("Invalid index data")
            
            # Calculate cosine similarities
            query_norm = np.linalg.norm(query_embedding)
            embeddings_norm = np.linalg.norm(embeddings, axis=1)
            
            # Avoid division by zero
            query_norm = max(query_norm, 1e-10)
            embeddings_norm = np.maximum(embeddings_norm, 1e-10)
            
            # Normalize embeddings
            embeddings_normalized = embeddings / embeddings_norm[:, np.newaxis]
            query_normalized = query_embedding / query_norm
            
            # Calculate similarities
            similarities = np.dot(embeddings_normalized, query_normalized)
            
            # Get top k indices
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            # Prepare results
            results = []
            for idx in top_indices:
                similarity = float(similarities[idx])
                chunk_meta = metadata[idx]
                
                result = {
                    "chunk_id": chunk_meta.get("chunk_id"),
                    "page_number": chunk_meta.get("page_number"),
                    "similarity_score": similarity,
                    "text_preview": chunk_meta.get("text_preview", ""),
                    "metadata": chunk_meta.get("metadata", {})
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} similar chunks for query")
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            return []
    
    def find_similar_questions(
        self, 
        question_text: str, 
        index_data: Dict[str, Any], 
        threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Find similar questions for deduplication
        
        Args:
            question_text: Question text
            index_data: Question embeddings index
            threshold: Similarity threshold
            
        Returns:
            List of similar questions
        """
        try:
            # Search for similar chunks
            similar_chunks = self.search_similar_chunks(
                question_text, 
                index_data, 
                top_k=10
            )
            
            # Filter by threshold
            similar_questions = [
                chunk for chunk in similar_chunks 
                if chunk.get("similarity_score", 0) >= threshold
            ]
            
            logger.info(f"Found {len(similar_questions)} similar questions above threshold {threshold}")
            return similar_questions
            
        except Exception as e:
            logger.error(f"Error finding similar questions: {e}")
            return []
    
    def cluster_chunks_by_topic(
        self, 
        chunks_with_embeddings: List[Dict[str, Any]], 
        n_clusters: int = 10
    ) -> Dict[str, Any]:
        """
        Cluster chunks by topic using embeddings
        
        Args:
            chunks_with_embeddings: Chunks with embeddings
            n_clusters: Number of clusters
            
        Returns:
            Clustering results
        """
        try:
            # Extract embeddings
            embeddings = []
            valid_chunks = []
            
            for chunk in chunks_with_embeddings:
                embedding = chunk.get("embedding")
                if embedding is not None:
                    embeddings.append(embedding)
                    valid_chunks.append(chunk)
            
            if not embeddings:
                return {"error": "No embeddings found"}
            
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Apply clustering
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(embeddings_array)
            
            # Get cluster centers
            cluster_centers = kmeans.cluster_centers_
            
            # Find representative chunks for each cluster
            from sklearn.metrics import pairwise_distances_argmin_min
            representative_indices, _ = pairwise_distances_argmin_min(
                cluster_centers, embeddings_array
            )
            
            # Organize chunks by cluster
            clusters = {}
            for i in range(n_clusters):
                # Get chunks in this cluster
                cluster_chunk_indices = np.where(cluster_labels == i)[0]
                cluster_chunks = [valid_chunks[idx] for idx in cluster_chunk_indices]
                
                # Get representative chunk
                rep_idx = representative_indices[i]
                representative_chunk = valid_chunks[rep_idx]
                
                # Calculate cluster statistics
                cluster_embeddings = embeddings_array[cluster_chunk_indices]
                cluster_center = cluster_centers[i]
                
                # Calculate average distance to center
                distances = np.linalg.norm(cluster_embeddings - cluster_center, axis=1)
                avg_distance = float(np.mean(distances))
                
                clusters[i] = {
                    "cluster_id": i,
                    "chunk_count": len(cluster_chunks),
                    "representative_chunk": {
                        "chunk_id": representative_chunk.get("chunk_id"),
                        "page_number": representative_chunk.get("page_number"),
                        "text_preview": representative_chunk.get("text", "")[:200]
                    },
                    "chunk_ids": [chunk.get("chunk_id") for chunk in cluster_chunks],
                    "page_numbers": list(set(chunk.get("page_number") for chunk in cluster_chunks)),
                    "average_distance_to_center": avg_distance,
                    "cohesion_score": 1.0 / (1.0 + avg_distance)  # Higher is better
                }
            
            # Overall clustering statistics
            silhouette_score = self._calculate_silhouette_score(embeddings_array, cluster_labels)
            
            results = {
                "clusters": clusters,
                "statistics": {
                    "total_clusters": n_clusters,
                    "total_chunks": len(valid_chunks),
                    "chunks_without_embeddings": len(chunks_with_embeddings) - len(valid_chunks),
                    "average_cluster_size": len(valid_chunks) / n_clusters,
                    "silhouette_score": silhouette_score,
                    "clustering_quality": self._assess_clustering_quality(silhouette_score)
                },
                "clustering_method": "kmeans",
                "created_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Clustered {len(valid_chunks)} chunks into {n_clusters} clusters")
            return results
            
        except Exception as e:
            logger.error(f"Error clustering chunks: {e}")
            return {"error": str(e)}
    
    def _calculate_silhouette_score(
        self, 
        embeddings: np.ndarray, 
        labels: np.ndarray
    ) -> float:
        """Calculate silhouette score for clustering"""
        try:
            from sklearn.metrics import silhouette_score
            # Use sample if dataset is large
            if len(embeddings) > 1000:
                from sklearn.utils import resample
                sample_size = min(1000, len(embeddings))
                sample_indices = np.random.choice(len(embeddings), sample_size, replace=False)
                sample_score = silhouette_score(
                    embeddings[sample_indices], 
                    labels[sample_indices]
                )
                return float(sample_score)
            else:
                return float(silhouette_score(embeddings, labels))
        except:
            return 0.0
    
    def _assess_clustering_quality(self, silhouette_score: float) -> str:
        """Assess clustering quality based on silhouette score"""
        if silhouette_score > 0.7:
            return "Excellent"
        elif silhouette_score > 0.5:
            return "Good"
        elif silhouette_score > 0.3:
            return "Fair"
        else:
            return "Poor"
    
    def create_question_embeddings_index(
        self, 
        questions: List[Dict[str, Any]], 
        index_name: str
    ) -> str:
        """
        Create embeddings index for questions
        
        Args:
            questions: List of question dictionaries
            index_name: Name for the index
            
        Returns:
            Path to saved index
        """
        try:
            # Extract question texts
            question_texts = []
            metadata = []
            
            for question in questions:
                q_text = question.get("question_text", "")
                if q_text:
                    question_texts.append(q_text)
                    
                    q_meta = {
                        "question_id": question.get("question_id"),
                        "question_text": q_text,
                        "question_type": question.get("question_type"),
                        "difficulty": question.get("difficulty"),
                        "topic": question.get("normalized_topic"),
                        "subtopic": question.get("subtopic"),
                        "page_number": question.get("page_number")
                    }
                    metadata.append(q_meta)
            
            if not question_texts:
                raise ValueError("No valid question texts")
            
            # Generate embeddings
            embeddings = embedding_model.embed_batch(question_texts)
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Create index directory
            index_dir = os.path.join(self.vector_index_dir, "questions", index_name)
            os.makedirs(index_dir, exist_ok=True)
            
            # Save index
            index_data = {
                "embeddings": embeddings_array,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat(),
                "total_questions": len(question_texts)
            }
            
            index_path = os.path.join(index_dir, "question_index.pkl")
            with open(index_path, 'wb') as f:
                pickle.dump(index_data, f)
            
            logger.info(f"Created question embeddings index at {index_path}")
            return index_path
            
        except Exception as e:
            logger.error(f"Error creating question embeddings index: {e}")
            raise
    
    def get_embedding_statistics(
        self, 
        embeddings: List[List[float]]
    ) -> Dict[str, Any]:
        """
        Get statistics about embeddings
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            Embedding statistics
        """
        if not embeddings:
            return {"error": "No embeddings provided"}
        
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        stats = {
            "total_embeddings": len(embeddings),
            "embedding_dimension": embeddings_array.shape[1] if len(embeddings_array.shape) > 1 else 0,
            "mean_norm": float(np.mean(np.linalg.norm(embeddings_array, axis=1))),
            "std_norm": float(np.std(np.linalg.norm(embeddings_array, axis=1))),
            "min_norm": float(np.min(np.linalg.norm(embeddings_array, axis=1))),
            "max_norm": float(np.max(np.linalg.norm(embeddings_array, axis=1))),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        return stats