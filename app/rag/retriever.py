from typing import List, Dict, Any
from app.rag.vectordb import VectorDBService


class Retriever:
    def __init__(
        self, vectordb_service: VectorDBService, collection_name: str = "default"
    ):

        self._vectordb_service = vectordb_service
        self._collection_name = collection_name

    def retrieve(
        self, query: str, collection_name: str, top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """检索文档
        params:
        query: 查询文本
        top_k: 返回的文档数量
        """
        return self._vectordb_service.search(
            query=query, n_results=top_k, collection_name=collection_name
        )

    def get_relevant_context(
        self, query: str, collection_name: str, top_k: int = 4
    ) -> str:
        """获取格式化的上下文文本，用于注入提示词
        params:
        query: 查询文本
        top_k: 返回的文档数量
        return:
        格式化的上下文文本
        """
        results = self.retrieve(query, collection_name=collection_name, top_k=top_k)
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"【文档{i}】\n{result['document']}\n")
        return "\n".join(context_parts)
