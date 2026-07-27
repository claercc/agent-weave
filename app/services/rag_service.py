from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.core.config import Settings
from app.rag.retriever import Retriever
from app.rag.chunk import ChunkService
from app.rag.vectordb import VectorDBService
from app.rag.embedding import EmbeddingService
from app.schemas.response import RAGResponse

class RAGService:
    def __init__(self,client: OpenAI,settings: Settings):
        self._client = client
        self._settings = settings
        self._chunk_service = ChunkService()
        self._embedding_service = EmbeddingService(client,settings)
        self._vector_db_service = VectorDBService()
        self._retriever = Retriever(self._vector_db_service)
    
    def ingest_documents(self,texts: List[str],collection_name: str = "default",
                         metadatas: Optional[Dict[str, Any]] = None) -> None:
        """将文本列表分块并存储到向量数据库中
        params:
        texts: 文本列表
        collection_name: 向量数据库中的集合名称
        metadatas: 文档元数据
        """
        # 1. 切分文档
        chunks = self._chunk_service.split_texts(texts)
        # 2. 生成唯一 ID
        ids = [f"doc_{i}_{hash(chunk) % 1000000}" for i, chunk in enumerate(chunks)]
        metadatas_list = [metadatas for _ in range(len(ids))]
        print(metadatas_list)
        self._vector_db_service.add_documents(
            documents=chunks,
            ids=ids,
            collection_name=collection_name,
            metadatas=metadatas_list
        )
    
    def retrieve_context(self,query: str,top_k: int = 4) -> str:
        """检索上下文
        params:
        query: 查询文本
        collection_name: 向量数据库中的集合名称
        top_k: 返回的文档数量
        return:
        格式化的上下文文本
        """
        results = self._retriever.get_relevant_context(
            query=query,
            top_k=top_k,
        )
        return results
    
    def generate_with_context(self,query: str,context: str,system_prompt: Optional[str] = None) -> str:
        """使用上下文生成响应
        params:
        query: 查询文本
        context: 上下文文本
        system_prompt: 系统提示
        return:
        生成的响应
        """
        if system_prompt is None:
            system_prompt = """
            你是一个知识库问答助手。请根据提供的上下文信息回答用户的问题。
            
            规则：
            1. 只能使用提供的上下文信息进行回答
            2. 如果上下文没有相关信息，请明确说明"根据提供的信息，我无法回答这个问题"
            3. 回答要简洁明了，不要添加无关内容
            """
        user_prompt = f"""
        上下文信息：{context}
        问题：{query}
        """
        response = self._client.chat.completions.create(
            model=self._settings.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content or ""
        
    def query(self,query: str,top_k: int = 4) -> RAGResponse:
        """
        完整的 RAG 查询流程
        
        :param query: 用户查询
        :param top_k: 返回文档数量
        :return: 包含回答和来源的字典
        """
        context = self.retrieve_context(query,top_k)
        answer = self.generate_with_context(query,context)
        return RAGResponse(
            answer=answer,
            context=context,
            query=query
        )




