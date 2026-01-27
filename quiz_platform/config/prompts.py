from typing import List, Dict

class SystemPrompts:
    """System prompts for different agents"""
    
    # Planner Agent
    PLANNER_SYSTEM = """You are a quiz generation planner. Your task is to analyze PDF content and plan how many and what type of questions to generate from each chunk.
    Consider:
    1. Content density of each chunk
    2. Important concepts present
    3. Appropriate question types (MCQ, short answer)
    4. Difficulty levels (Easy, Medium, Hard)
    5. Balance across topics
    
    Return a JSON with your plan."""
    
    # PDF/Text Analysis Agent
    PDF_ANALYZER_SYSTEM = """You are a PDF content analyzer. Extract key information from text chunks including:
    1. Main topics and subtopics
    2. Key concepts and entities
    3. Important facts and definitions
    4. Relationships between concepts
    
    Be thorough and accurate."""
    
    # Topic Extraction Agent
    TOPIC_EXTRACTOR_SYSTEM = """You are a topic extraction expert. Extract hierarchical topics and subtopics from text.
    Focus on:
    1. Main themes
    2. Sub-themes
    3. Specific concepts
    4. Technical terms
    
    Organize them in a structured way."""
    
    # Question Generation Agent
    # QUESTION_GENERATOR_SYSTEM = """You are an expert question generator for educational content.
    # Generate high-quality questions that:
    # 1. Are directly answerable from the provided text
    # 2. Test understanding, not just recall
    # 3. Have clear, unambiguous correct answers
    # 4. Include appropriate distractors for MCQs
    # 5. Are at appropriate difficulty level
    
    # Always verify answers are in the text."""
    QUESTION_GENERATOR_SYSTEM = """You are a structured JSON question generator.

    You do NOT write explanations, prose, or markdown.
    You ONLY return valid JSON.

    Your task is to generate quiz questions that strictly follow the required JSON schema.

    If you cannot follow the schema EXACTLY, return an empty JSON array [].

    You must ensure:
    - All answers come directly from the provided text
    - No guessing or outside knowledge
    - No partially filled fields
    """

    
    # Validation Agent
    VALIDATOR_SYSTEM = """You are a question validation expert. Validate if:
    1. The question is answerable from the source text
    2. The answer is correct and complete
    3. The question is clear and unambiguous
    4. Distractors (if any) are plausible but incorrect
    5. Difficulty level is appropriate
    
    Provide validation score and feedback."""
    
    # Deduplication Agent
    DEDUP_SYSTEM = """You are a duplicate detector. Identify if two questions are semantically similar or duplicates.
    Consider:
    1. Same core concept being tested
    2. Similar phrasing or rephrasing
    3. Same answer expected
    4. Overlap in content
    
    Be strict but reasonable."""

class UserPrompts:
    """User prompts template for different tasks"""
    
    @staticmethod
    def generate_quiz_plan(chunk_count: int, content_summary: str) -> str:
        return f"""Based on {chunk_count} chunks of content, create a quiz generation plan.
        
        Content Summary:
        {content_summary}
        
        Plan should include:
        - Questions per chunk
        - Question types distribution
        - Difficulty distribution
        - Estimated total questions
        
        Return JSON format."""
    
    @staticmethod
    def extract_topics(text: str, page_num: int) -> str:
        return f"""Extract topics and subtopics from the following text (Page {page_num}):
        
        Text:
        {text}
        
        Extract:
        1. Main topics (1-3)
        2. Subtopics for each main topic (3-5 each)
        3. Key entities/concepts mentioned
        
        Return as JSON."""
    
    # @staticmethod
    # def generate_questions(text: str, subtopic: str, count: int = 2) -> str:
    #     return f"""Generate {count} questions about '{subtopic}' from the following text:
        
    #     Text:
    #     {text}
        
    #     Requirements:
    #     1. Mix of MCQ and short answer questions
    #     2. Clear correct answers
    #     3. For MCQs: 4 options with plausible distractors
    #     4. Indicate difficulty (Easy/Medium/Hard)
        
    #     Return as JSON."""
    @staticmethod
    def generate_questions(text: str, subtopic: str, count: int = 2) -> str:
        return f"""
    Generate {count} quiz questions about '{subtopic}' using ONLY the information in the text below.

    TEXT:
    {text}

    ================= OUTPUT FORMAT RULES (STRICT) =================

    Return ONLY valid JSON.
    Do NOT include explanations or text outside JSON.

    Each question MUST follow this EXACT structure:

    {{
    "question": "string",
    "question_type": "mcq" OR "short_answer", //lowercase only
    "options": ["option1", "option2", "option3", "option4"],  // REQUIRED for MCQ
    "answer": "FULL TEXT of the correct answer",
    "difficulty": "easy" | "medium" | "hard",
    "explanation": "short explanation from the text"
    }}

    ---------------- MCQ RULES (MANDATORY) ----------------
    • You MUST provide exactly 4 options
    • Options must be distinct and plausible
    • The "answer" MUST exactly match ONE of the options
    • DO NOT return A/B/C/D
    • DO NOT return 1/2/3/4
    • DO NOT return index numbers
    • DO NOT leave answer empty

    ---------------- SHORT ANSWER RULES ----------------
    • Answer must be a short factual phrase from the text
    • DO NOT leave answer empty

    ---------------- GENERAL RULES ----------------
    • Questions must be directly answerable from the text
    • Do NOT invent facts
    • Do NOT repeat the same question
    • If the text does not support a good question, SKIP it

    Return a JSON ARRAY of questions.
    """

    
    @staticmethod
    def validate_question(question: Dict, source_text: str) -> str:
        return f"""Validate this question based on the source text:
        
        Question: {question.get('question_text')}
        Options: {question.get('options', [])}
        Answer: {question.get('answer')}
        Type: {question.get('question_type')}
        Difficulty: {question.get('difficulty')}
        
        Source Text:
        {source_text}
        
        Validate and provide:
        1. Is answerable from text? (True/False)
        2. Answer correctness score (0-1)
        3. Clarity score (0-1)
        4. Difficulty appropriateness (True/False)
        5. Overall validation score (0-1)
        6. Feedback/comments
        
        Return as JSON."""
    
    @staticmethod
    def normalize_topics(subtopics: List[str], target_count: int = 10) -> str:
        return f"""Normalize these subtopics into approximately {target_count} main topics:
        
        Subtopics:
        {subtopics}
        
        Requirements:
        1. Group semantically similar subtopics
        2. Create descriptive topic names
        3. Maintain hierarchy
        4. Ensure coverage of all concepts
        
        Return as JSON with topics and their subtopics."""