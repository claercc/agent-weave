from typing import Any, cast
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings


class VectorDBService:
    """只负责向量存储和相似度查询。"""

    def __init__(
        self,
        persist_directory: str = "./.chroma_db",
    ) -> None:
        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(
                # 禁用匿名遥测
                anonymized_telemetry=False,
            ),
        )

    def get_or_create_collection(
        self,
        collection_name: str,
        embedding_model: str,
    ) -> chromadb.Collection:
        """获取或创建使用 cosine 距离的集合。"""

        collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=None,
            configuration=cast(
                Any,
                {
                    "hnsw": {
                        "space": "cosine",
                    },
                },
            ),
            metadata={
                "embedding_model": embedding_model,
            },
        )

        stored_model = (collection.metadata or {}).get("embedding_model")

        if stored_model != embedding_model:
            raise ValueError(
                "知识库使用的 Embedding 模型不一致："
                f"当前配置为 {embedding_model}，"
                f"知识库记录为 {stored_model or 'unknown'}。"
                "请删除并重新导入该知识库。"
            )

        return collection

    def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        embeddings: list[list[float]],
        embedding_model: str,
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """保存文档以及已经生成的向量。"""

        if len(documents) != len(embeddings):
            raise ValueError("文档数量与 Embedding 向量数量不一致")

        if metadatas is not None and (len(metadatas) != len(documents)):
            raise ValueError("文档数量与元数据数量不一致")

        collection = self.get_or_create_collection(
            collection_name=collection_name,
            embedding_model=embedding_model,
        )

        document_ids = ids or [str(uuid4()) for _ in documents]

        collection.upsert(
            documents=documents,
            embeddings=cast(Any, embeddings),
            metadatas=cast(Any, metadatas),
            ids=document_ids,
        )

    def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        embedding_model: str,
        n_results: int = 4,
    ) -> list[dict[str, Any]]:
        """使用显式查询向量搜索文档。"""

        collection = self.get_or_create_collection(
            collection_name=collection_name,
            embedding_model=embedding_model,
        )

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
        )

        documents = results["documents"] or [[]]
        metadatas = results["metadatas"] or [[]]
        distances = results["distances"] or [[]]

        return [
            {
                "document": document,
                "metadatas": (
                    metadatas[0][index] if index < len(metadatas[0]) else None
                ),
                "distance": (
                    distances[0][index] if index < len(distances[0]) else None
                ),
            }
            for index, document in enumerate(documents[0])
        ]

    def delete_collection(
        self,
        collection_name: str,
    ) -> None:
        """删除知识库集合。"""

        self._client.delete_collection(name=collection_name)

    def list_collections(self) -> list[str]:
        """列出所有知识库集合。"""

        return [collection.name for collection in self._client.list_collections()]
