from openai import OpenAI
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict
from quiz_platform.config.settings import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        logger.info(f"Initializing LLM with model: {settings.OPENAI_MODEL}")
        logger.info(f"Using base URL: {settings.LLM_BASE_URL}")

        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in environment variables")

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )

        self.model = settings.OPENAI_MODEL
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)

        
    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            raise
    
    def generate_json(self, prompt: str, system_prompt: str = None) -> Dict:
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response)

class EmbeddingModel:
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL  # e.g. "all-MiniLM-L6-v2"
        self.model = SentenceTransformer(self.model_name)
    
    def embed(self, text: str) -> List[float]:
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()


# Global instances
llm_client = LLMClient()
embedding_model = EmbeddingModel()
