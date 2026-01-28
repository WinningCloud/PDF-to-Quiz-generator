from openai import OpenAI
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict
import json
import torch
from config.settings import settings
import os

# 🔥 Prevent transformers from downloading all hardware variants
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

logger = logging.getLogger(__name__)

# Reduce torch CPU threads (saves memory on Render)
torch.set_num_threads(1)


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
        self.model_name = settings.EMBEDDING_MODEL
        self._model = None  # NOT LOADED YET

    def _get_model(self):
        """Lazy load the embedding model only when needed (lightweight mode)"""
        if self._model is None:
            logger.info(f"Loading embedding model (CPU only): {self.model_name}")

            self._model = SentenceTransformer(
                self.model_name,
                device="cpu",                 # 🔥 Force CPU (Render has no GPU)
                trust_remote_code=False       # Safer + avoids extra downloads
            )

        return self._model


    def embed(self, text: str) -> List[float]:
    model = self._get_model()
    embedding = model.encode(
        text,
        convert_to_numpy=True,
        normalize_embeddings=True,  # smaller vectors
        batch_size=1                # low memory
    )
    return embedding.tolist()


    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        model = self._get_model()
        embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=2   # keep tiny for Render
        )
        return embeddings.tolist()



# Global instances (SAFE now — model not loaded yet)
llm_client = LLMClient()
embedding_model = EmbeddingModel()
