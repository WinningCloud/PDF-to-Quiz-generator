import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import pickle
import json
import os
import logging
from datetime import datetime
import faiss
from sqlalchemy.orm import Session

from quiz_platform.config.settings import settings
from quiz_platform.db.models import VectorIndex, Chunk
from quiz_platform.core.embeddings import EmbeddingManager
from quiz_platform.utils.logger import get_logger

logger = get_logger(__name__)

class VectorStore:
    """Vector store for managing embeddings and similarity search"""
    
    def __init__(self, db: Session):
        self.db = db
        self.embedding_manager = EmbeddingManager(settings.VECTOR_INDEX_DIR)
        self.ensure_directory()
    
    def ensure_directory(self):
        """Ensure vector store directory exists"""
        os.makedirs(settings.VECTOR_INDEX_DIR, exist_ok=True)
    
    def create_index_for_pdf(
        self, 
        pdf_id: int, 
        chunks: List[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create vector index for PDF chunks
        
        Args:
            pdf_id: PDF document ID
            chunks: List of chunk dictionaries with embeddings
            
        Returns:
            Tuple of (index_path, index_stats)
        """
        try:
            # Extract embeddings and metadata
            embeddings = []
            metadata = []
            chunk_ids = []
            
            for chunk in chunks:
                embedding = chunk.get("embedding")
                if embedding is not None:
                    embeddings.append(embedding)
                    
                    # Prepare metadata
                    chunk_meta = {
                        "chunk_id": chunk.get("chunk_id"),
                        "pdf_id": pdf_id,
                        "page_number": chunk.get("page_number", 1),
                        "text_preview": chunk.get("text", "")[:200],
                        "word_count": chunk.get("word_count", 0),
                        "start_char": chunk.get("start_char", 0),
                        "end_char": chunk.get("end_char", 0),
                        "previous_page_ref": chunk.get("previous_page_ref", ""),
                        "next_page_ref": chunk.get("next_page_ref", ""),
                        "created_at": datetime.utcnow().isoformat()
                    }
                    metadata.append(chunk_meta)
                    chunk_ids.append(chunk.get("chunk_id"))
            
            if not embeddings:
                raise ValueError("No embeddings found in chunks")
            
            # Convert to numpy arrays
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Create FAISS index
            dimension = embeddings_array.shape[1]
            index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
            
            # Normalize vectors for cosine similarity
            faiss.normalize_L2(embeddings_array)
            index.add(embeddings_array)
            
            # Create index directory
            index_dir = os.path.join(settings.VECTOR_INDEX_DIR, f"pdf_{pdf_id}")
            os.makedirs(index_dir, exist_ok=True)
            
            # Save FAISS index
            index_path = os.path.join(index_dir, "faiss_index.bin")
            faiss.write_index(index, index_path)
            
            # Save metadata
            metadata_path = os.path.join(index_dir, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Save chunk IDs mapping
            chunk_mapping = {chunk_id: i for i, chunk_id in enumerate(chunk_ids)}
            mapping_path = os.path.join(index_dir, "chunk_mapping.json")
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(chunk_mapping, f, indent=2, ensure_ascii=False)
            
            # Create database record
            vector_index = VectorIndex(
                pdf_id=pdf_id,
                index_name=f"pdf_{pdf_id}_index",
                index_type="faiss",
                index_path=index_path,
                metadata_path=metadata_path,
                vector_count=len(embeddings),
                embedding_dim=dimension,
                metadata={
                    "chunk_count": len(chunks),
                    "created_at": datetime.utcnow().isoformat(),
                    "chunk_ids": chunk_ids
                }
            )
            
            self.db.add(vector_index)
            self.db.commit()
            
            # Calculate statistics
            index_stats = self._calculate_index_statistics(embeddings_array)
            
            logger.info(f"Created vector index for PDF {pdf_id} with {len(embeddings)} vectors")
            
            return index_path, index_stats
            
        except Exception as e:
            logger.error(f"Error creating vector index: {e}")
            self.db.rollback()
            raise
    
    def _calculate_index_statistics(self, embeddings: np.ndarray) -> Dict[str, Any]:
        """Calculate index statistics"""
        stats = {
            "vector_count": embeddings.shape[0],
            "embedding_dimension": embeddings.shape[1],
            "embedding_norms": {
                "mean": float(np.mean(np.linalg.norm(embeddings, axis=1))),
                "std": float(np.std(np.linalg.norm(embeddings, axis=1))),
                "min": float(np.min(np.linalg.norm(embeddings, axis=1))),
                "max": float(np.max(np.linalg.norm(embeddings, axis=1)))
            },
            "created_at": datetime.utcnow().isoformat()
        }
        
        return stats
    
    def load_index(self, pdf_id: int) -> Tuple[faiss.Index, List[Dict[str, Any]]]:
        """
        Load vector index for PDF
        
        Args:
            pdf_id: PDF document ID
            
        Returns:
            Tuple of (FAISS index, metadata)
        """
        try:
            # Get index record from database
            vector_index = self.db.query(VectorIndex).filter(
                VectorIndex.pdf_id == pdf_id
            ).first()
            
            if not vector_index:
                raise ValueError(f"No vector index found for PDF {pdf_id}")
            
            # Load FAISS index
            if not os.path.exists(vector_index.index_path):
                raise FileNotFoundError(f"Index file not found: {vector_index.index_path}")
            
            index = faiss.read_index(vector_index.index_path)
            
            # Load metadata
            if not os.path.exists(vector_index.metadata_path):
                raise FileNotFoundError(f"Metadata file not found: {vector_index.metadata_path}")
            
            with open(vector_index.metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.info(f"Loaded vector index for PDF {pdf_id}")
            
            return index, metadata
            
        except Exception as e:
            logger.error(f"Error loading vector index: {e}")
            raise
    
    def search_similar_chunks(
        self, 
        query: str, 
        pdf_id: int, 
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector index
        
        Args:
            query: Search query
            pdf_id: PDF document ID
            top_k: Number of results to return
            threshold: Similarity threshold
            
        Returns:
            List of similar chunks with scores
        """
        try:
            # Load index and metadata
            index, metadata = self.load_index(pdf_id)
            
            # Generate embedding for query
            query_embedding = self.embedding_manager.generate_embeddings(
                [{"text": query}]
            )[0].get("embedding")
            
            if query_embedding is None:
                raise ValueError("Failed to generate query embedding")
            
            # Convert to numpy array and normalize
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            # Search
            distances, indices = index.search(query_vector, min(top_k * 2, len(metadata)))
            
            # Prepare results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx >= len(metadata):
                    continue
                
                similarity = float(distance)  # Cosine similarity
                
                if similarity >= threshold:
                    chunk_meta = metadata[idx]
                    result = {
                        "chunk_id": chunk_meta.get("chunk_id"),
                        "pdf_id": pdf_id,
                        "page_number": chunk_meta.get("page_number", 1),
                        "similarity_score": similarity,
                        "text_preview": chunk_meta.get("text_preview", ""),
                        "word_count": chunk_meta.get("word_count", 0),
                        "position": {
                            "start_char": chunk_meta.get("start_char", 0),
                            "end_char": chunk_meta.get("end_char", 0)
                        }
                    }
                    results.append(result)
                
                if len(results) >= top_k:
                    break
            
            logger.info(f"Found {len(results)} similar chunks for query")
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            return []
    
    def find_relevant_chunks_for_question(
        self, 
        question: str, 
        pdf_id: int, 
        max_chunks: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find relevant chunks for a question
        
        Args:
            question: Question text
            pdf_id: PDF document ID
            max_chunks: Maximum chunks to return
            
        Returns:
            List of relevant chunks
        """
        # Search for similar chunks
        similar_chunks = self.search_similar_chunks(
            query=question,
            pdf_id=pdf_id,
            top_k=max_chunks * 2,
            threshold=0.6
        )
        
        # Sort by similarity and deduplicate by page
        relevant_chunks = []
        seen_pages = set()
        
        for chunk in sorted(similar_chunks, key=lambda x: x["similarity_score"], reverse=True):
            page_num = chunk.get("page_number")
            
            # Ensure we get chunks from different pages
            if page_num not in seen_pages or len(seen_pages) >= max_chunks:
                relevant_chunks.append(chunk)
                seen_pages.add(page_num)
            
            if len(relevant_chunks) >= max_chunks:
                break
        
        return relevant_chunks
    
    def get_chunk_by_id(self, chunk_id: str, pdf_id: int) -> Optional[Dict[str, Any]]:
        """
        Get chunk by ID
        
        Args:
            chunk_id: Chunk ID
            pdf_id: PDF document ID
            
        Returns:
            Chunk data or None
        """
        try:
            # Try to get from database first
            chunk = self.db.query(Chunk).filter(
                Chunk.chunk_id == chunk_id,
                Chunk.pdf_id == pdf_id
            ).first()
            
            if chunk:
                return {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "page_number": chunk.page_number,
                    "word_count": chunk.word_count,
                    "embedding": json.loads(chunk.embedding) if chunk.embedding else None
                }
            
            # Fallback to metadata file
            vector_index = self.db.query(VectorIndex).filter(
                VectorIndex.pdf_id == pdf_id
            ).first()
            
            if vector_index and os.path.exists(vector_index.metadata_path):
                with open(vector_index.metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                for chunk_meta in metadata:
                    if chunk_meta.get("chunk_id") == chunk_id:
                        return chunk_meta
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting chunk by ID: {e}")
            return None
    
    def update_index_with_new_chunks(
        self, 
        pdf_id: int, 
        new_chunks: List[Dict[str, Any]]
    ) -> bool:
        """
        Update existing index with new chunks
        
        Args:
            pdf_id: PDF document ID
            new_chunks: New chunks to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing index
            index, metadata = self.load_index(pdf_id)
            
            # Extract embeddings from new chunks
            new_embeddings = []
            new_metadata = []
            
            for chunk in new_chunks:
                embedding = chunk.get("embedding")
                if embedding is not None:
                    new_embeddings.append(embedding)
                    
                    chunk_meta = {
                        "chunk_id": chunk.get("chunk_id"),
                        "pdf_id": pdf_id,
                        "page_number": chunk.get("page_number", 1),
                        "text_preview": chunk.get("text", "")[:200],
                        "word_count": chunk.get("word_count", 0),
                        "created_at": datetime.utcnow().isoformat()
                    }
                    new_metadata.append(chunk_meta)
            
            if not new_embeddings:
                logger.warning("No embeddings in new chunks")
                return False
            
            # Convert to numpy and normalize
            new_embeddings_array = np.array(new_embeddings, dtype=np.float32)
            faiss.normalize_L2(new_embeddings_array)
            
            # Add to index
            index.add(new_embeddings_array)
            
            # Update metadata
            metadata.extend(new_metadata)
            
            # Save updated index and metadata
            vector_index = self.db.query(VectorIndex).filter(
                VectorIndex.pdf_id == pdf_id
            ).first()
            
            if vector_index:
                # Save FAISS index
                faiss.write_index(index, vector_index.index_path)
                
                # Save updated metadata
                with open(vector_index.metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                # Update database record
                vector_index.vector_count += len(new_embeddings)
                vector_index.updated_at = datetime.utcnow()
                vector_index.metadata = json.dumps({
                    "last_updated": datetime.utcnow().isoformat(),
                    "added_chunks": len(new_chunks)
                })
                
                self.db.commit()
                
                logger.info(f"Updated index for PDF {pdf_id} with {len(new_chunks)} new chunks")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating index: {e}")
            self.db.rollback()
            return False
    
    def delete_index(self, pdf_id: int) -> bool:
        """
        Delete vector index for PDF
        
        Args:
            pdf_id: PDF document ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get index record
            vector_index = self.db.query(VectorIndex).filter(
                VectorIndex.pdf_id == pdf_id
            ).first()
            
            if not vector_index:
                return False
            
            # Delete index files
            index_dir = os.path.dirname(vector_index.index_path)
            
            if os.path.exists(index_dir):
                import shutil
                shutil.rmtree(index_dir)
            
            # Delete database record
            self.db.delete(vector_index)
            self.db.commit()
            
            logger.info(f"Deleted vector index for PDF {pdf_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting index: {e}")
            self.db.rollback()
            return False
    
    def get_index_statistics(self, pdf_id: int) -> Dict[str, Any]:
        """
        Get statistics for vector index
        
        Args:
            pdf_id: PDF document ID
            
        Returns:
            Index statistics
        """
        try:
            vector_index = self.db.query(VectorIndex).filter(
                VectorIndex.pdf_id == pdf_id
            ).first()
            
            if not vector_index:
                return {"error": "Index not found"}
            
            stats = {
                "pdf_id": pdf_id,
                "index_name": vector_index.index_name,
                "index_type": vector_index.index_type,
                "vector_count": vector_index.vector_count,
                "embedding_dim": vector_index.embedding_dim,
                "created_at": vector_index.created_at.isoformat() if vector_index.created_at else None,
                "updated_at": vector_index.updated_at.isoformat() if vector_index.updated_at else None
            }
            
            # Add file information if available
            if os.path.exists(vector_index.index_path):
                stats["index_file_size"] = os.path.getsize(vector_index.index_path)
            
            if os.path.exists(vector_index.metadata_path):
                stats["metadata_file_size"] = os.path.getsize(vector_index.metadata_path)
            
            # Load metadata for additional stats
            if os.path.exists(vector_index.metadata_path):
                with open(vector_index.metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Calculate page distribution
                page_counts = {}
                for chunk_meta in metadata:
                    page_num = chunk_meta.get("page_number", 0)
                    page_counts[page_num] = page_counts.get(page_num, 0) + 1
                
                stats["page_distribution"] = page_counts
                stats["total_pages"] = len(page_counts)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting index statistics: {e}")
            return {"error": str(e)}
    
    def search_by_embedding(
        self, 
        embedding: List[float], 
        pdf_id: int, 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search using raw embedding
        
        Args:
            embedding: Query embedding
            pdf_id: PDF document ID
            top_k: Number of results
            
        Returns:
            Search results
        """
        try:
            index, metadata = self.load_index(pdf_id)
            
            # Convert to numpy and normalize
            query_vector = np.array([embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            # Search
            distances, indices = index.search(query_vector, top_k)
            
            # Prepare results
            results = []
            for distance, idx in zip(distances[0], indices[0]):
                if idx < len(metadata):
                    chunk_meta = metadata[idx]
                    results.append({
                        "chunk_id": chunk_meta.get("chunk_id"),
                        "similarity_score": float(distance),
                        "text_preview": chunk_meta.get("text_preview", ""),
                        "page_number": chunk_meta.get("page_number", 1)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching by embedding: {e}")
            return []
    
    def batch_search(
        self, 
        queries: List[str], 
        pdf_id: int, 
        top_k: int = 3
    ) -> List[List[Dict[str, Any]]]:
        """
        Batch search for multiple queries
        
        Args:
            queries: List of query texts
            pdf_id: PDF document ID
            top_k: Results per query
            
        Returns:
            List of results for each query
        """
        try:
            # Generate embeddings for all queries
            query_embeddings = []
            for query in queries:
                embedding_result = self.embedding_manager.generate_embeddings(
                    [{"text": query}]
                )[0]
                embedding = embedding_result.get("embedding")
                if embedding is not None:
                    query_embeddings.append(embedding)
            
            if not query_embeddings:
                return [[] for _ in queries]
            
            # Load index
            index, metadata = self.load_index(pdf_id)
            
            # Convert to numpy and normalize
            query_vectors = np.array(query_embeddings, dtype=np.float32)
            faiss.normalize_L2(query_vectors)
            
            # Batch search
            distances, indices = index.search(query_vectors, top_k)
            
            # Prepare results
            all_results = []
            for i in range(len(queries)):
                query_results = []
                for j in range(top_k):
                    idx = indices[i, j]
                    if idx < len(metadata):
                        chunk_meta = metadata[idx]
                        query_results.append({
                            "chunk_id": chunk_meta.get("chunk_id"),
                            "similarity_score": float(distances[i, j]),
                            "text_preview": chunk_meta.get("text_preview", ""),
                            "page_number": chunk_meta.get("page_number", 1)
                        })
                all_results.append(query_results)
            
            return all_results
            
        except Exception as e:
            logger.error(f"Error in batch search: {e}")
            return [[] for _ in queries]