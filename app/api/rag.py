from fastapi import APIRouter,Depends,HTTPException
from openai import OpenAI
from app.core.config import Settings, get_settings
from app.core.openai_client import get_openai_client
from app.services.rag_service import RAGService
from app.schemas.request import RAGQueryRequest, RAGIngestRequest
from app.schemas.response import RAGResponse
import logging

router = APIRouter(prefix="/rag",tags=["RAG"])

def get_rag_service(settings: Settings = Depends(get_settings),
    client: OpenAI = Depends(get_openai_client)) -> RAGService:
    return RAGService(settings=settings,client=client)

@router.post("/query",response_model=RAGResponse)
def query_rag(request: RAGQueryRequest,rag_service: RAGService = Depends(get_rag_service)):
    """
    RAG 查询接口
    根据用户查询从知识库中检索相关信息并生成回答
    """
    try:
        response = rag_service.query(request.query,top_k=request.top_k)
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    return response

@router.post("/ingest")
def rag_ingest(request: RAGIngestRequest,rag_service: RAGService = Depends(get_rag_service)):
    """
    RAG 文档导入接口
    将文档导入到向量数据库中
    """
    try:
        logging.info(f"开始导入文档到集合 {request.collection_name}")
        rag_service.ingest_documents(request.texts,request.collection_name,
                                                metadatas=request.metadatas)
        logging.info(f"文档导入完成，集合 {request.collection_name}")
    except Exception as e:
        logging.error(f"文档导入失败，集合 {request.collection_name}，错误信息：{str(e)}")
        raise HTTPException(status_code=500,detail=str(e))
    return  {"message": "Documents ingested successfully"} 

@router.get("/collections")
def get_collections(rag_service: RAGService = Depends(get_rag_service)):
    """
    列出所有向量数据库集合
    """
    return {"collections": rag_service._vector_db_service.list_collections()}

@router.delete("/collections/{collection_name}")
def delete_collection(collection_name: str,rag_service: RAGService = Depends(get_rag_service)):
    """
    删除向量数据库集合
    """
    try:
        rag_service._vector_db_service.delete_collection(collection_name)
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    return {"message": f"集合 {collection_name} 已删除"}