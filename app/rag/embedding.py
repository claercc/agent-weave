from typing import List
from openai import OpenAI
from app.core.config import Settings


class EmbeddingService:
    def __init__(self, client: OpenAI, settings: Settings):
        self._client = client
        self._settings = settings
        self._embedding_model = "text-embedding-3-small"

    def embed_text(self, text: str) -> List[float]:
        response = self._client.embeddings.create(
            model=self._embedding_model, input=text
        )
        return response.data[0].embedding

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._client.embeddings.create(
            model=self._embedding_model, input=texts
        )
        return [embedding.embedding for embedding in embeddings.data]
