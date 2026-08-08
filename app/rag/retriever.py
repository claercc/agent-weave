from typing import Any

from app.rag.embedding import EmbeddingService
from app.rag.vectordb import VectorDBService


class Retriever:
    """将自然语言查询转换为向量并检索文档。"""

    def __init__(
        self,
        vectordb_service: VectorDBService,
        embedding_service: EmbeddingService,
    ) -> None:
        self._vectordb_service = vectordb_service
        self._embedding_service = embedding_service

    def retrieve(
        self,
        query: str,
        collection_name: str,
        top_k: int = 4,
    ) -> list[dict[str, Any]]:
        """生成查询向量并检索相关文档。"""

        query_embedding = (
            self._embedding_service.embed_query(query)
        )

        return self._vectordb_service.search(
            query_embedding=query_embedding,
            embedding_model=(
                self._embedding_service.model_name
            ),
            n_results=top_k,
            collection_name=collection_name,
        )

    def get_relevant_context(
        self,
        query: str,
        collection_name: str,
        top_k: int = 4,
    ) -> str:
        """获取格式化后的知识库上下文。"""

        results = self.retrieve(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
        )

        context_parts = []

        for index, result in enumerate(
            results,
            start=1,
        ):
            context_parts.append(
                f"【文档{index}】\n"
                f"{result['document']}\n"
            )

        return "\n".join(context_parts)