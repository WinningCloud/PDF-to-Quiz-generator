import fitz  # PyMuPDF
import pdfplumber
from typing import Dict, List, Any, Tuple
import logging
import os
import json
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class PDFMetadata:
    """Metadata for PDF document"""
    filename: str
    filepath: str
    total_pages: int
    author: str = ""
    title: str = ""
    subject: str = ""
    created_date: str = ""
    modified_date: str = ""

class PDFIngestion:
    def __init__(self, upload_dir: str, processed_dir: str):
        self.upload_dir = upload_dir
        self.processed_dir = processed_dir
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
    
    def extract_metadata(self, pdf_path: str) -> PDFMetadata:
        """
        Extract metadata from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            PDFMetadata object
        """
        try:
            with fitz.open(pdf_path) as doc:
                metadata = doc.metadata
                
                pdf_metadata = PDFMetadata(
                    filename=os.path.basename(pdf_path),
                    filepath=pdf_path,
                    total_pages=len(doc),
                    author=metadata.get("author", ""),
                    title=metadata.get("title", ""),
                    subject=metadata.get("subject", ""),
                    created_date=metadata.get("creationDate", ""),
                    modified_date=metadata.get("modDate", "")
                )
                
                logger.info(f"Extracted metadata from {pdf_path}: {len(doc)} pages")
                return pdf_metadata
                
        except Exception as e:
            logger.error(f"Error extracting metadata from {pdf_path}: {e}")
            return PDFMetadata(
                filename=os.path.basename(pdf_path),
                filepath=pdf_path,
                total_pages=0
            )
    
    def extract_text_by_page(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from each page of PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of page dictionaries with text and metadata
        """
        pages = []
        
        try:
            # Use pdfplumber for better text extraction
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Extract text
                        text = page.extract_text()
                        
                        # Extract tables if any
                        tables = page.extract_tables()
                        
                        # Get page dimensions
                        width = page.width
                        height = page.height
                        
                        # Clean text
                        if text:
                            text = self._clean_text(text)
                        
                        page_data = {
                            "page_number": page_num,
                            "text": text or "",
                            "has_text": bool(text and text.strip()),
                            "word_count": len(text.split()) if text else 0,
                            "tables": tables or [],
                            "dimensions": {"width": width, "height": height},
                            "extraction_method": "pdfplumber",
                            "extraction_time": datetime.utcnow().isoformat()
                        }
                        
                        pages.append(page_data)
                        
                        logger.debug(f"Extracted page {page_num}: {len(text)} chars")
                        
                    except Exception as e:
                        logger.error(f"Error extracting page {page_num}: {e}")
                        # Add empty page data
                        pages.append({
                            "page_number": page_num,
                            "text": "",
                            "has_text": False,
                            "word_count": 0,
                            "tables": [],
                            "error": str(e),
                            "extraction_time": datetime.utcnow().isoformat()
                        })
            
            logger.info(f"Extracted {len(pages)} pages from {pdf_path}")
            return pages
            
        except Exception as e:
            logger.error(f"Error opening PDF {pdf_path}: {e}")
            
            # Fallback to PyMuPDF
            try:
                return self._extract_with_pymupdf(pdf_path)
            except Exception as fallback_error:
                logger.error(f"Fallback extraction also failed: {fallback_error}")
                return []
    
    def _extract_with_pymupdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Fallback extraction using PyMuPDF"""
        pages = []
        
        with fitz.open(pdf_path) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text
                text = page.get_text()
                
                # Clean text
                if text:
                    text = self._clean_text(text)
                
                page_data = {
                    "page_number": page_num + 1,
                    "text": text or "",
                    "has_text": bool(text and text.strip()),
                    "word_count": len(text.split()) if text else 0,
                    "tables": [],
                    "dimensions": {"width": page.rect.width, "height": page.rect.height},
                    "extraction_method": "pymupdf_fallback",
                    "extraction_time": datetime.utcnow().isoformat()
                }
                
                pages.append(page_data)
        
        logger.info(f"Fallback extracted {len(pages)} pages with PyMuPDF")
        return pages
    
    def extract_with_images(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text and images from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of page dictionaries with text and image info
        """
        pages = []
        
        try:
            with fitz.open(pdf_path) as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    
                    # Extract text
                    text = page.get_text()
                    if text:
                        text = self._clean_text(text)
                    
                    # Extract images
                    images = []
                    image_list = page.get_images()
                    
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        # Save image
                        image_filename = f"page_{page_num + 1}_img_{img_index}.{image_ext}"
                        image_path = os.path.join(self.processed_dir, "images", image_filename)
                        os.makedirs(os.path.dirname(image_path), exist_ok=True)
                        
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)
                        
                        images.append({
                            "image_index": img_index,
                            "filename": image_filename,
                            "path": image_path,
                            "extension": image_ext,
                            "size_bytes": len(image_bytes)
                        })
                    
                    page_data = {
                        "page_number": page_num + 1,
                        "text": text or "",
                        "has_text": bool(text and text.strip()),
                        "word_count": len(text.split()) if text else 0,
                        "images": images,
                        "image_count": len(images),
                        "extraction_method": "pymupdf_with_images",
                        "extraction_time": datetime.utcnow().isoformat()
                    }
                    
                    pages.append(page_data)
            
            logger.info(f"Extracted {len(pages)} pages with images")
            return pages
            
        except Exception as e:
            logger.error(f"Error extracting with images: {e}")
            return self.extract_text_by_page(pdf_path)
    
    def validate_pdf(self, pdf_path: str) -> Tuple[bool, List[str]]:
        """
        Validate PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []
        
        # Check file exists
        if not os.path.exists(pdf_path):
            issues.append("File does not exist")
            return False, issues
        
        # Check file size
        file_size = os.path.getsize(pdf_path)
        if file_size == 0:
            issues.append("File is empty")
            return False, issues
        
        if file_size > 100 * 1024 * 1024:  # 100MB limit
            issues.append("File too large (max 100MB)")
            return False, issues
        
        # Try to open PDF
        try:
            with fitz.open(pdf_path) as doc:
                page_count = len(doc)
                
                if page_count == 0:
                    issues.append("PDF has no pages")
                    return False, issues
                
                # Check for text content
                has_text = False
                for page_num in range(min(3, page_count)):  # Check first 3 pages
                    page = doc[page_num]
                    text = page.get_text()
                    if text and text.strip():
                        has_text = True
                        break
                
                if not has_text:
                    issues.append("PDF appears to have no extractable text (may be scanned)")
                
                logger.info(f"PDF validated: {page_count} pages, has_text={has_text}")
                return True, issues
                
        except Exception as e:
            issues.append(f"Invalid PDF file: {str(e)}")
            return False, issues
    
    def save_extraction_results(
        self, 
        pdf_id: int, 
        metadata: PDFMetadata, 
        pages: List[Dict]
    ) -> str:
        """
        Save extraction results to file
        
        Args:
            pdf_id: PDF document ID
            metadata: PDF metadata
            pages: Extracted pages
            
        Returns:
            Path to saved results
        """
        # Create results directory
        results_dir = os.path.join(self.processed_dir, str(pdf_id))
        os.makedirs(results_dir, exist_ok=True)
        
        # Prepare results
        results = {
            "pdf_id": pdf_id,
            "metadata": {
                "filename": metadata.filename,
                "total_pages": metadata.total_pages,
                "author": metadata.author,
                "title": metadata.title,
                "subject": metadata.subject,
                "extracted_at": datetime.utcnow().isoformat()
            },
            "pages": pages,
            "summary": {
                "total_pages_extracted": len(pages),
                "pages_with_text": sum(1 for p in pages if p.get("has_text")),
                "total_words": sum(p.get("word_count", 0) for p in pages),
                "total_tables": sum(len(p.get("tables", [])) for p in pages),
                "total_images": sum(p.get("image_count", 0) for p in pages)
            }
        }
        
        # Save to JSON
        results_path = os.path.join(results_dir, "extraction_results.json")
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save raw text for each page
        for page in pages:
            if page.get("has_text"):
                page_num = page["page_number"]
                text = page["text"]
                text_path = os.path.join(results_dir, f"page_{page_num:03d}.txt")
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(text)
        
        logger.info(f"Saved extraction results to {results_path}")
        return results_path
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        lines = text.splitlines()
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        # Join with single newline
        cleaned_text = "\n".join(cleaned_lines)
        
        # Fix common OCR/PDF issues
        replacements = {
            "\u00a0": " ",  # Non-breaking space
            "\u2028": "\n", # Line separator
            "\u2029": "\n", # Paragraph separator
            "  ": " ",      # Double spaces
            "\t": " ",      # Tabs
        }
        
        for old, new in replacements.items():
            cleaned_text = cleaned_text.replace(old, new)
        
        # Normalize line endings
        cleaned_text = "\n".join(line.strip() for line in cleaned_text.splitlines() if line.strip())
        
        return cleaned_text
    
    def get_pdf_stats(self, pdf_path: str) -> Dict[str, Any]:
        """
        Get statistics about PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            PDF statistics
        """
        try:
            with fitz.open(pdf_path) as doc:
                page_count = len(doc)
                
                # Sample pages for analysis
                sample_pages = min(10, page_count)
                text_samples = []
                word_counts = []
                
                for i in range(sample_pages):
                    page = doc[i]
                    text = page.get_text()
                    if text:
                        text_samples.append(text)
                        word_counts.append(len(text.split()))
                
                avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
                
                # Check if PDF is searchable
                is_searchable = len(text_samples) > 0
                
                # Estimate total words
                estimated_total_words = avg_words * page_count if avg_words > 0 else 0
                
                stats = {
                    "page_count": page_count,
                    "is_searchable": is_searchable,
                    "sample_pages_analyzed": sample_pages,
                    "average_words_per_page": round(avg_words, 1),
                    "estimated_total_words": int(estimated_total_words),
                    "file_size_bytes": os.path.getsize(pdf_path),
                    "file_size_mb": round(os.path.getsize(pdf_path) / (1024 * 1024), 2),
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting PDF stats: {e}")
            return {
                "error": str(e),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }