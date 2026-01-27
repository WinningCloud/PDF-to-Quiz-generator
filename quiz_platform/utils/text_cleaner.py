import re
import string
from typing import List, Optional
import logging
import os
logger = logging.getLogger(__name__)

class TextCleaner:
    def __init__(self):
        # Common patterns to remove
        self.patterns_to_remove = [
            r'\s+',  # Multiple whitespace
            r'\n+',  # Multiple newlines
            r'\t+',  # Multiple tabs
            r'\u00a0',  # Non-breaking space
            r'\u200b',  # Zero-width space
            r'\u200e',  # Left-to-right mark
            r'\u200f',  # Right-to-left mark
        ]
        
        # Replacement patterns
        self.replacement_patterns = {
            r'\.{2,}': '. ',  # Multiple dots to single dot
            r',{2,}': ', ',   # Multiple commas to single comma
            r';{2,}': '; ',   # Multiple semicolons to single semicolon
            r'!{2,}': '! ',   # Multiple exclamations to single
            r'\?{2,}': '? ',  # Multiple questions to single
        }
    
    def clean_text(self, text: str, remove_patterns: bool = True) -> str:
        """
        Clean text by removing unwanted patterns and normalizing
        
        Args:
            text: Input text to clean
            remove_patterns: Whether to remove patterns
            
        Returns:
            Cleaned text
        """
        if not text or not isinstance(text, str):
            return ""
        
        cleaned = text
        
        # Remove patterns if requested
        if remove_patterns:
            for pattern in self.patterns_to_remove:
                cleaned = re.sub(pattern, ' ', cleaned)
        
        # Apply replacement patterns
        for pattern, replacement in self.replacement_patterns.items():
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # Fix spacing around punctuation
        cleaned = self._fix_punctuation_spacing(cleaned)
        
        # Normalize whitespace
        cleaned = ' '.join(cleaned.split())
        
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned
    
    def clean_text_batch(self, texts: List[str]) -> List[str]:
        """
        Clean multiple texts
        
        Args:
            texts: List of texts to clean
            
        Returns:
            List of cleaned texts
        """
        return [self.clean_text(text) for text in texts]
    
    def _fix_punctuation_spacing(self, text: str) -> str:
        """Fix spacing around punctuation"""
        # Add space after punctuation if missing
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        
        # Remove space before punctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        
        # Fix spacing for parentheses and brackets
        text = re.sub(r'\(\s+', '(', text)
        text = re.sub(r'\s+\)', ')', text)
        text = re.sub(r'\[\s+', '[', text)
        text = re.sub(r'\s+\]', ']', text)
        
        # Fix spacing for quotes
        text = re.sub(r'\s+"', '"', text)
        text = re.sub(r'"\s+', '"', text)
        text = re.sub(r"\s+'", "'", text)
        text = re.sub(r"'\s+", "'", text)
        
        return text
    
    def remove_special_characters(self, text: str, keep_punctuation: bool = True) -> str:
        """
        Remove special characters from text
        
        Args:
            text: Input text
            keep_punctuation: Whether to keep punctuation
            
        Returns:
            Text with special characters removed
        """
        if not text:
            return ""
        
        if keep_punctuation:
            # Keep basic punctuation and alphanumeric
            allowed = string.ascii_letters + string.digits + string.punctuation + ' '
            cleaned = ''.join(char for char in text if char in allowed)
        else:
            # Keep only alphanumeric and spaces
            allowed = string.ascii_letters + string.digits + ' '
            cleaned = ''.join(char for char in text if char in allowed)
        
        return cleaned
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text"""
        if not text:
            return ""
        
        # Replace all whitespace characters with single space
        cleaned = re.sub(r'\s+', ' ', text)
        return cleaned.strip()
    
    def extract_sentences(self, text: str) -> List[str]:
        """
        Extract sentences from text
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        if not text:
            return []
        
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Clean each sentence
        cleaned_sentences = []
        for sentence in sentences:
            cleaned = self.clean_text(sentence)
            if cleaned and len(cleaned) > 10:  # Filter very short sentences
                cleaned_sentences.append(cleaned)
        
        return cleaned_sentences
    
    def extract_paragraphs(self, text: str) -> List[str]:
        """
        Extract paragraphs from text
        
        Args:
            text: Input text
            
        Returns:
            List of paragraphs
        """
        if not text:
            return []
        
        # Split by double newlines
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean each paragraph
        cleaned_paragraphs = []
        for para in paragraphs:
            cleaned = self.clean_text(para)
            if cleaned and len(cleaned.split()) > 5:  # Filter very short paragraphs
                cleaned_paragraphs.append(cleaned)
        
        return cleaned_paragraphs
    
    def calculate_readability_score(self, text: str) -> float:
        """
        Calculate simple readability score
        
        Args:
            text: Input text
            
        Returns:
            Readability score (0-100, higher is easier to read)
        """
        if not text:
            return 0.0
        
        sentences = self.extract_sentences(text)
        words = text.split()
        
        if not sentences or not words:
            return 0.0
        
        # Average words per sentence
        avg_words_per_sentence = len(words) / len(sentences)
        
        # Average syllables per word (simplified)
        syllable_count = sum(self._count_syllables(word) for word in words)
        avg_syllables_per_word = syllable_count / len(words)
        
        # Flesch Reading Ease Score (simplified)
        # Higher score = easier to read
        score = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
        
        # Normalize to 0-100
        score = max(0, min(100, score))
        
        return score
    
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simplified)"""
        word = word.lower()
        count = 0
        
        # Count vowel groups
        vowels = 'aeiouy'
        in_vowel_group = False
        
        for char in word:
            if char in vowels:
                if not in_vowel_group:
                    count += 1
                    in_vowel_group = True
            else:
                in_vowel_group = False
        
        # Adjust for special cases
        if word.endswith('e'):
            count -= 1
        if word.endswith('le') and len(word) > 2 and word[-3] not in vowels:
            count += 1
        if count == 0:
            count = 1
        
        return count
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract keywords from text
        
        Args:
            text: Input text
            top_n: Number of keywords to extract
            
        Returns:
            List of keywords
        """
        if not text:
            return []
        
        # Remove stopwords and get word frequencies
        stopwords = self._get_stopwords()
        words = text.lower().split()
        
        # Filter stopwords and short words
        filtered_words = [
            word for word in words 
            if word not in stopwords and len(word) > 2
        ]
        
        # Count frequencies
        from collections import Counter
        word_counts = Counter(filtered_words)
        
        # Get most common words
        keywords = [word for word, count in word_counts.most_common(top_n)]
        
        return keywords
    
    def _get_stopwords(self) -> set:
        """Get common stopwords"""
        return set([
            'the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with',
            'for', 'on', 'as', 'by', 'at', 'an', 'be', 'this', 'or', 'from',
            'but', 'not', 'are', 'which', 'have', 'has', 'had', 'was', 'were',
            'will', 'would', 'can', 'could', 'should', 'shall', 'may', 'might',
            'must', 'i', 'you', 'he', 'she', 'we', 'they', 'my', 'your', 'his',
            'her', 'our', 'their', 'me', 'him', 'us', 'them', 'mine', 'yours',
            'hers', 'ours', 'theirs', 'myself', 'yourself', 'himself', 'herself',
            'ourselves', 'yourselves', 'themselves'
        ])
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of text (simplified)
        
        Args:
            text: Input text
            
        Returns:
            Detected language code
        """
        if not text:
            return "unknown"
        
        # Simple character-based detection
        # Count percentage of common English letters
        english_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
        total_chars = len([c for c in text if c.isalpha()])
        
        if total_chars == 0:
            return "unknown"
        
        english_count = len([c for c in text if c in english_chars])
        english_percentage = english_count / total_chars
        
        if english_percentage > 0.9:
            return "en"
        else:
            # Could add other language detection here
            return "unknown"