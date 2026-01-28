import pytest
import tempfile
import os
from unittest.mock import Mock, patch
import json

from core.page_chunker import PageChunker, Chunk
from core.pdf_ingestion import PDFIngestion

class TestPageChunker:
    def setup_method(self):
        """Setup test environment"""
        self.chunker = PageChunker(overlap_ratio=0.3, max_chunk_size=1000)
        
        # Create test pages
        self.test_pages = [
            {
                "page_number": 1,
                "text": "This is page 1 content. It contains important information about the topic. "
                        "The topic is very interesting and has many aspects to explore. "
                        "We will discuss various aspects in detail.",
                "has_text": True,
                "word_count": 25
            },
            {
                "page_number": 2,
                "text": "Page 2 continues the discussion. More details about the topic are provided here. "
                        "Additional information helps understand the concepts better. "
                        "Examples are given to illustrate the points.",
                "has_text": True,
                "word_count": 24
            },
            {
                "page_number": 3,
                "text": "Final page with conclusions. Summary of all important points. "
                        "Recommendations for further study. Final thoughts on the topic.",
                "has_text": True,
                "word_count": 15
            }
        ]
    
    def test_chunk_pages_with_overlap(self):
        """Test chunking pages with overlap"""
        chunks = self.chunker.chunk_pages_with_overlap(self.test_pages)
        
        assert len(chunks) == 3
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        
        # Check chunk properties
        for i, chunk in enumerate(chunks):
            assert chunk.page_number == i + 1
            assert chunk.word_count > 0
            assert chunk.text is not None
            assert chunk.chunk_id is not None
            
            # Check metadata
            assert "has_prev_overlap" in chunk.metadata
            assert "has_next_overlap" in chunk.metadata
    
    def test_chunk_by_semantic_boundaries(self):
        """Test chunking by semantic boundaries"""
        chunks = self.chunker.chunk_by_semantic_boundaries(self.test_pages)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        
        # Check chunk types
        chunk_types = set(chunk.metadata.get("chunk_type") for chunk in chunks)
        assert "semantic" in chunk_types
    
    def test_chunk_with_sliding_window(self):
        """Test chunking with sliding window"""
        # Create longer text
        long_text = " ".join(["Sentence {}.".format(i) for i in range(50)])
        
        chunks = self.chunker.chunk_with_sliding_window(long_text, page_number=1)
        
        assert len(chunks) > 1  # Should create multiple chunks
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        
        # Check sliding window metadata
        for chunk in chunks:
            assert chunk.metadata.get("chunk_type") == "sliding_window"
            assert "window_size" in chunk.metadata
            assert "overlap_words" in chunk.metadata
    
    def test_handle_small_page(self):
        """Test handling small pages"""
        small_pages = [
            {
                "page_number": 1,
                "text": "Very short text.",
                "has_text": True,
                "word_count": 3
            },
            {
                "page_number": 2,
                "text": "Another short page with minimal content.",
                "has_text": True,
                "word_count": 5
            }
        ]
        
        chunks = self.chunker.chunk_pages_with_overlap(small_pages)
        
        # Should combine or handle small pages appropriately
        assert len(chunks) <= 2
    
    def test_chunk_id_generation(self):
        """Test chunk ID generation"""
        chunk = Chunk(
            chunk_id="test_id",
            text="Test text",
            page_number=1,
            start_char=0,
            end_char=10,
            word_count=2,
            metadata={}
        )
        
        assert chunk.chunk_id == "test_id"
        assert isinstance(chunk.chunk_id, str)
    
    def test_save_and_load_chunks(self):
        """Test saving and loading chunks"""
        chunks = self.chunker.chunk_pages_with_overlap(self.test_pages)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
            
            # Save chunks
            self.chunker.save_chunks_to_file(chunks, temp_file)
            
            # Load chunks
            with open(temp_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            assert len(loaded_data) == len(chunks)
            
            # Clean up
            os.unlink(temp_file)
    
    def test_analyze_chunks(self):
        """Test chunk analysis"""
        chunks = self.chunker.chunk_pages_with_overlap(self.test_pages)
        
        analysis = self.chunker.analyze_chunks(chunks)
        
        assert "total_chunks" in analysis
        assert "total_words" in analysis
        assert "average_words_per_chunk" in analysis
        assert "pages_covered" in analysis
        
        assert analysis["total_chunks"] == len(chunks)
        assert analysis["pages_covered"] == 3
    
    def test_chunk_clean_text(self):
        """Test text cleaning in chunks"""
        dirty_text = "  This  is  dirty  text.  \n\nWith  extra  spaces.  "
        
        cleaned = self.chunker._clean_chunk_text(dirty_text)
        
        assert "  " not in cleaned  # No double spaces
        assert cleaned.startswith("This")  # No leading spaces
        assert cleaned.endswith("spaces.")  # No trailing spaces
    
    def test_split_into_paragraphs(self):
        """Test paragraph splitting"""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        
        paragraphs = self.chunker._split_into_paragraphs(text)
        
        assert len(paragraphs) == 3
        assert all(p.strip() for p in paragraphs)
    
    def test_split_large_paragraph(self):
        """Test splitting large paragraphs"""
        # Create a long paragraph
        long_paragraph = ". ".join(["Sentence {}".format(i) for i in range(20)])
        
        sub_chunks = self.chunker._split_large_paragraph(long_paragraph)
        
        assert len(sub_chunks) > 1
        assert all(len(chunk.split()) <= self.chunker.max_chunk_size for chunk in sub_chunks)
    
    @patch('core.page_chunker.PageChunker._split_into_paragraphs')
    def test_chunk_by_semantic_boundaries_empty(self, mock_split):
        """Test chunking with empty text"""
        mock_split.return_value = []
        
        empty_pages = [{"page_number": 1, "text": "", "has_text": False}]
        chunks = self.chunker.chunk_by_semantic_boundaries(empty_pages)
        
        assert len(chunks) == 0
    
    def test_chunk_metadata_structure(self):
        """Test chunk metadata structure"""
        chunks = self.chunker.chunk_pages_with_overlap(self.test_pages)
        
        for chunk in chunks:
            metadata = chunk.metadata
            
            # Required fields
            assert "chunk_type" in metadata
            assert "original_page" in metadata
            
            # For page_with_overlap type
            if metadata["chunk_type"] == "page_with_overlap":
                assert "has_prev_overlap" in metadata
                assert "has_next_overlap" in metadata
                assert "overlap_ratio" in metadata
    
    def test_chunk_word_count_accuracy(self):
        """Test chunk word count accuracy"""
        test_text = "This is a test sentence with seven words."
        expected_word_count = 7
        
        chunk = Chunk(
            chunk_id="test",
            text=test_text,
            page_number=1,
            start_char=0,
            end_char=len(test_text),
            word_count=len(test_text.split()),
            metadata={}
        )
        
        assert chunk.word_count == expected_word_count
    
    def test_chunk_position_tracking(self):
        """Test chunk position tracking"""
        text = "Sample text for position testing."
        
        chunk = Chunk(
            chunk_id="test",
            text=text,
            page_number=1,
            start_char=0,
            end_char=len(text),
            word_count=len(text.split()),
            metadata={}
        )
        
        assert chunk.start_char == 0
        assert chunk.end_char == len(text)
        assert chunk.end_char > chunk.start_char
    
    def test_chunk_references(self):
        """Test chunk page references"""
        chunks = self.chunker.chunk_pages_with_overlap(self.test_pages)
        
        # First chunk should have next page reference
        assert chunks[0].next_page_ref == "page_2"
        
        # Middle chunk should have both references
        assert chunks[1].previous_page_ref == "page_1"
        assert chunks[1].next_page_ref == "page_3"
        
        # Last chunk should have previous reference
        assert chunks[2].previous_page_ref == "page_2"