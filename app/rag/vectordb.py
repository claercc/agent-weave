from typing import Any, cast
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings


class VectorDBService:
    """向量数据库服务。"""

    def __init__(
        self,
        persist_directory: str = "./.chroma_db",
    ) -> None:
        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
            ),
        )

    def get_or_create_collection(
        self,
        collection_name: str,
    ) -> chromadb.Collection:
        """获取或创建集合。"""
        return self._client.get_or_create_collection(name=collection_name)

    def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """添加文档到集合。"""
        collection = self.get_or_create_collection(collection_name)
        document_ids = ids or [str(uuid4()) for _ in documents]

        collection.upsert(
            documents=documents,
            metadatas=cast(Any, metadatas),
            ids=document_ids,
        )

    def search(
        self,
        collection_name: str,
        query: str,
        n_results: int = 4,
    ) -> list[dict[str, Any]]:
        """搜索集合。"""
        collection = self.get_or_create_collection(collection_name)
        results = collection.query(
            query_texts=[query],
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
        """删除集合。"""
        self._client.delete_collection(name=collection_name)

    def list_collections(self) -> list[str]:
        """列出所有集合。"""
        return [collection.name for collection in self._client.list_collections()]
