import re
from typing import Dict, List, Any, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class Chunk:
    """Chunk data structure"""
    chunk_id: str
    text: str
    page_number: int
    start_char: int
    end_char: int
    word_count: int
    metadata: Dict[str, Any]
    previous_page_ref: str = ""
    next_page_ref: str = ""

class PageChunker:
    def __init__(self, overlap_ratio: float = 0.3, max_chunk_size: int = 1000):
        """
        Initialize chunker
        
        Args:
            overlap_ratio: Ratio of overlap between chunks (0.3 = 30%)
            max_chunk_size: Maximum words per chunk
        """
        self.overlap_ratio = overlap_ratio
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = 200
    
    def chunk_pages_with_overlap(
        self, 
        pages: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        Chunk pages with overlap from previous and next pages
        
        Args:
            pages: List of page dictionaries with text
            
        Returns:
            List of chunks with overlap
        """
        chunks = []
        
        for i, page in enumerate(pages):
            page_number = page.get("page_number", i + 1)
            page_text = page.get("text", "")
            
            if not page_text or len(page_text.split()) < self.min_chunk_size:
                # If page is too small, combine with neighboring pages
                combined_chunks = self._handle_small_page(pages, i)
                chunks.extend(combined_chunks)
                continue
            
            # Get text from previous page for overlap
            prev_overlap = ""
            if i > 0:
                prev_page_text = pages[i-1].get("text", "")
                if prev_page_text:
                    prev_overlap = self._get_overlap_text(prev_page_text, "end")
            
            # Get text from next page for overlap
            next_overlap = ""
            if i < len(pages) - 1:
                next_page_text = pages[i+1].get("text", "")
                if next_page_text:
                    next_overlap = self._get_overlap_text(next_page_text, "start")
            
            # Create chunk with overlaps
            chunk_text = prev_overlap + "\n" + page_text + "\n" + next_overlap
            chunk_text = self._clean_chunk_text(chunk_text)
            
            # Create chunk
            chunk = Chunk(
                chunk_id=self._generate_chunk_id(page_number, 0),
                text=chunk_text,
                page_number=page_number,
                start_char=0,
                end_char=len(chunk_text),
                word_count=len(chunk_text.split()),
                metadata={
                    "original_page": page_number,
                    "has_prev_overlap": bool(prev_overlap),
                    "has_next_overlap": bool(next_overlap),
                    "prev_page": i if i > 0 else None,
                    "next_page": i + 2 if i < len(pages) - 1 else None,
                    "overlap_ratio": self.overlap_ratio,
                    "chunk_type": "page_with_overlap"
                },
                previous_page_ref=f"page_{i}" if i > 0 else "",
                next_page_ref=f"page_{i+2}" if i < len(pages) - 1 else ""
            )
            
            chunks.append(chunk)
            
            logger.debug(f"Created chunk for page {page_number}: {chunk.word_count} words")
        
        logger.info(f"Created {len(chunks)} chunks from {len(pages)} pages")
        return chunks
    
    def chunk_by_semantic_boundaries(
        self, 
        pages: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        Chunk text by semantic boundaries (paragraphs, headings)
        
        Args:
            pages: List of page dictionaries
            
        Returns:
            List of semantic chunks
        """
        chunks = []
        chunk_counter = 0
        
        for i, page in enumerate(pages):
            page_number = page.get("page_number", i + 1)
            page_text = page.get("text", "")
            
            if not page_text:
                continue
            
            # Split by paragraphs
            paragraphs = self._split_into_paragraphs(page_text)
            
            for para_idx, paragraph in enumerate(paragraphs):
                if not paragraph.strip():
                    continue
                
                # Check if paragraph is too large
                para_words = len(paragraph.split())
                if para_words > self.max_chunk_size:
                    # Split large paragraph
                    sub_chunks = self._split_large_paragraph(paragraph)
                    for sub_idx, sub_chunk in enumerate(sub_chunks):
                        chunk = self._create_semantic_chunk(
                            sub_chunk,
                            page_number,
                            chunk_counter,
                            para_idx,
                            sub_idx,
                            i,
                            pages
                        )
                        chunks.append(chunk)
                        chunk_counter += 1
                else:
                    # Use entire paragraph
                    chunk = self._create_semantic_chunk(
                        paragraph,
                        page_number,
                        chunk_counter,
                        para_idx,
                        0,
                        i,
                        pages
                    )
                    chunks.append(chunk)
                    chunk_counter += 1
        
        logger.info(f"Created {len(chunks)} semantic chunks")
        return chunks
    
    def chunk_with_sliding_window(
        self, 
        text: str, 
        page_number: int = 1
    ) -> List[Chunk]:
        """
        Chunk text using sliding window approach
        
        Args:
            text: Text to chunk
            page_number: Page number
            
        Returns:
            List of chunks
        """
        chunks = []
        words = text.split()
        
        if len(words) < self.min_chunk_size:
            # Text is too small, create single chunk
            chunk = Chunk(
                chunk_id=self._generate_chunk_id(page_number, 0),
                text=text,
                page_number=page_number,
                start_char=0,
                end_char=len(text),
                word_count=len(words),
                metadata={
                    "chunk_type": "sliding_window",
                    "window_size": len(words),
                    "overlap_words": 0
                }
            )
            return [chunk]
        
        # Calculate window size and overlap
        window_size = min(self.max_chunk_size, len(words))
        overlap_words = int(window_size * self.overlap_ratio)
        step_size = window_size - overlap_words
        
        # Create sliding windows
        for i in range(0, len(words) - overlap_words, step_size):
            end_idx = min(i + window_size, len(words))
            chunk_words = words[i:end_idx]
            chunk_text = " ".join(chunk_words)
            
            # Get context from previous window if available
            context_start = max(0, i - overlap_words)
            context_words = words[context_start:i]
            context_text = " ".join(context_words) if context_words else ""
            
            chunk = Chunk(
                chunk_id=self._generate_chunk_id(page_number, i),
                text=chunk_text,
                page_number=page_number,
                start_char=i,  # Approximate character position
                end_char=end_idx,
                word_count=len(chunk_words),
                metadata={
                    "chunk_type": "sliding_window",
                    "window_start": i,
                    "window_end": end_idx,
                    "window_size": window_size,
                    "overlap_words": overlap_words,
                    "context_preview": context_text[:100] + "..." if context_text else ""
                },
                previous_page_ref=f"window_{i-step_size}" if i > 0 else ""
            )
            
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} sliding window chunks")
        return chunks
    
    def _handle_small_page(
        self, 
        pages: List[Dict], 
        page_index: int
    ) -> List[Chunk]:
        """
        Handle small pages by combining with neighbors
        
        Args:
            pages: All pages
            page_index: Index of small page
            
        Returns:
            List of combined chunks
        """
        current_page = pages[page_index]
        page_number = current_page.get("page_number", page_index + 1)
        current_text = current_page.get("text", "")
        
        # Try to combine with next page
        if page_index < len(pages) - 1:
            next_page = pages[page_index + 1]
            next_text = next_page.get("text", "")
            combined_text = current_text + "\n" + next_text
            
            if len(combined_text.split()) >= self.min_chunk_size:
                chunk = Chunk(
                    chunk_id=self._generate_chunk_id(page_number, 0),
                    text=combined_text,
                    page_number=page_number,
                    start_char=0,
                    end_char=len(combined_text),
                    word_count=len(combined_text.split()),
                    metadata={
                        "original_pages": [page_number, page_number + 1],
                        "chunk_type": "combined_pages",
                        "combined_reason": "small_page"
                    },
                    next_page_ref=f"page_{page_number + 2}" if page_index + 1 < len(pages) - 1 else ""
                )
                return [chunk]
        
        # Try to combine with previous page
        if page_index > 0:
            prev_page = pages[page_index - 1]
            prev_text = prev_page.get("text", "")
            combined_text = prev_text + "\n" + current_text
            
            if len(combined_text.split()) >= self.min_chunk_size:
                chunk = Chunk(
                    chunk_id=self._generate_chunk_id(page_number - 1, 0),
                    text=combined_text,
                    page_number=page_number - 1,
                    start_char=0,
                    end_char=len(combined_text),
                    word_count=len(combined_text.split()),
                    metadata={
                        "original_pages": [page_number - 1, page_number],
                        "chunk_type": "combined_pages",
                        "combined_reason": "small_page"
                    },
                    previous_page_ref=f"page_{page_number - 2}" if page_index > 1 else ""
                )
                return [chunk]
        
        # Create small chunk anyway
        chunk = Chunk(
            chunk_id=self._generate_chunk_id(page_number, 0),
            text=current_text,
            page_number=page_number,
            start_char=0,
            end_char=len(current_text),
            word_count=len(current_text.split()),
            metadata={
                "chunk_type": "small_page",
                "warning": "page_below_minimum_size"
            }
        )
        return [chunk]
    
    def _get_overlap_text(self, text: str, position: str) -> str:
        """
        Get overlap text from a page
        
        Args:
            text: Page text
            position: 'start' or 'end'
            
        Returns:
            Overlap text
        """
        words = text.split()
        overlap_word_count = int(len(words) * self.overlap_ratio)
        
        if position == "start":
            overlap_words = words[:overlap_word_count]
        elif position == "end":
            overlap_words = words[-overlap_word_count:]
        else:
            return ""
        
        return " ".join(overlap_words)
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Split by double newlines
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean paragraphs
        cleaned_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para:
                cleaned_paragraphs.append(para)
        
        return cleaned_paragraphs
    
    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """Split large paragraph into smaller chunks"""
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for sentence in sentences:
            sentence_words = sentence.split()
            sentence_word_count = len(sentence_words)
            
            if current_word_count + sentence_word_count > self.max_chunk_size:
                # Finish current chunk
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [sentence]
                    current_word_count = sentence_word_count
                else:
                    # Sentence itself is too large
                    chunks.append(sentence)
                    current_word_count = 0
            else:
                current_chunk.append(sentence)
                current_word_count += sentence_word_count
        
        # Add last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _create_semantic_chunk(
        self, 
        text: str, 
        page_number: int, 
        chunk_id_suffix: int,
        para_idx: int,
        sub_idx: int,
        page_index: int,
        pages: List[Dict]
    ) -> Chunk:
        """Create a semantic chunk"""
        # Get context from previous paragraph if available
        prev_ref = ""
        if para_idx > 0 or sub_idx > 0:
            prev_ref = f"para_{para_idx}_{sub_idx-1}" if sub_idx > 0 else f"para_{para_idx-1}"
        
        # Get context from previous page
        prev_page_ref = ""
        if page_index > 0:
            prev_page_ref = f"page_{pages[page_index-1].get('page_number', page_index)}"
        
        # Get context from next page
        next_page_ref = ""
        if page_index < len(pages) - 1:
            next_page_ref = f"page_{pages[page_index+1].get('page_number', page_index + 2)}"
        
        return Chunk(
            chunk_id=f"{page_number}_{chunk_id_suffix:03d}",
            text=text,
            page_number=page_number,
            start_char=0,
            end_char=len(text),
            word_count=len(text.split()),
            metadata={
                "chunk_type": "semantic",
                "paragraph_index": para_idx,
                "sub_chunk_index": sub_idx,
                "is_paragraph": sub_idx == 0,
                "has_headings": self._contains_headings(text),
                "sentence_count": text.count('.') + text.count('!') + text.count('?')
            },
            previous_page_ref=prev_page_ref,
            next_page_ref=next_page_ref
        )
    
    def _contains_headings(self, text: str) -> bool:
        """Check if text contains potential headings"""
        # Simple heading detection
        lines = text.split('\n')
        for line in lines[:3]:  # Check first few lines
            line = line.strip()
            if line and len(line.split()) <= 10 and line.endswith(':'):
                return True
            if line and line.isupper() and len(line) < 100:
                return True
        return False
    
    def _clean_chunk_text(self, text: str) -> str:
        """Clean chunk text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Ensure proper spacing after punctuation
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        
        return text
    
    def _generate_chunk_id(self, page_number: int, position: int) -> str:
        """Generate unique chunk ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_str = f"{page_number}_{position}_{timestamp}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:8]
    
    def save_chunks_to_file(
        self, 
        chunks: List[Chunk], 
        output_path: str
    ) -> str:
        """
        Save chunks to JSON file
        
        Args:
            chunks: List of chunks
            output_path: Output file path
            
        Returns:
            Path to saved file
        """
        # Convert chunks to dictionaries
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "page_number": chunk.page_number,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "word_count": chunk.word_count,
                "metadata": chunk.metadata,
                "previous_page_ref": chunk.previous_page_ref,
                "next_page_ref": chunk.next_page_ref
            }
            chunk_dicts.append(chunk_dict)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_dicts, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(chunk_dicts)} chunks to {output_path}")
        return output_path
    
    def analyze_chunks(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """
        Analyze chunk statistics
        
        Args:
            chunks: List of chunks
            
        Returns:
            Analysis results
        """
        if not chunks:
            return {"error": "No chunks provided"}
        
        word_counts = [chunk.word_count for chunk in chunks]
        page_numbers = [chunk.page_number for chunk in chunks]
        
        # Calculate statistics
        stats = {
            "total_chunks": len(chunks),
            "total_words": sum(word_counts),
            "average_words_per_chunk": sum(word_counts) / len(chunks),
            "min_words": min(word_counts),
            "max_words": max(word_counts),
            "pages_covered": len(set(page_numbers)),
            "chunk_types": {},
            "size_distribution": {
                "small": len([w for w in word_counts if w < 300]),
                "medium": len([w for w in word_counts if 300 <= w < 700]),
                "large": len([w for w in word_counts if w >= 700])
            }
        }
        
        # Count chunk types
        for chunk in chunks:
            chunk_type = chunk.metadata.get("chunk_type", "unknown")
            stats["chunk_types"][chunk_type] = stats["chunk_types"].get(chunk_type, 0) + 1
        
        logger.info(f"Chunk analysis: {stats}")
        return stats