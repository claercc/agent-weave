from typing import List,Dict,Any,Optional
import chromadb
from app.core.config import get_settings
from chromadb.config import Settings as ChromaSettings

class VectorDBService:
    """向量数据库服务"""
    def __init__(self,persist_directory: str = "./.chroma_db"):
        """
        params:
        persist_directory: 向量数据库的持久化目录
        """
        settings = get_settings()
        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False
            )
        )
    
    def get_or_create_collection(self,collection_name: str) -> chromadb.Collection:
        """获取或创建一个集合"""
        return self._client.get_or_create_collection(
            name=collection_name
        )
    
    def add_documents(self,collection_name: str,documents: List[str],
                      metadatas: Optional[List[Dict[str,Any]]] = None,ids: Optional[List[str]] = None):
        """添加文档到集合"""
        collection = self.get_or_create_collection(collection_name)
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    def search(self,collection_name: str,query: str,
                n_results: int = 4) -> List[Dict[str,Any]]:
                """搜索集合"""
                collection = self.get_or_create_collection(collection_name)
                results = collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
                return [
                    {
                        "document": results["documents"][0][i],
                        "metadatas": results["metadatas"][0][i] if results["metadatas"] else None,
                        "distance": results["distances"][0][i]
                    }
                    for i in range(len(results["documents"][0]))
                ]
    def delete_collection(self,collection_name: str):
        """删除集合"""
        self._client.delete_collection(
            collection_name=collection_name
        )

    def list_collections(self) -> List[str]:
        """列出所有集合"""
        return [collection.name for collection in self._client.list_collections()]
