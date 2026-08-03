from fastapi import (APIRouter,
                     Depends,
                     File,
                     Form,
                     HTTPException,
                     UploadFile,
                     )
from openai import OpenAI
from app.core.config import Settings, get_settings
from app.core.openai_client import get_openai_client
from app.services.rag_service import RAGService
from app.schemas.request import RAGQueryRequest, RAGIngestRequest
from app.schemas.response import RAGResponse, PDFInfoResponse
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
        logging.info(f"开始查询{request.query}")
        response = rag_service.query(request.query,request.collection_name,top_k=request.top_k)
    except Exception as e:
        logging.error(f"查询失败，错误信息：{str(e)}")
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

# UploadFile：接收上传文件
# File：告诉 FastAPI 这是文件字段
# Form：接收 multipart 表单里的普通字段
# PDFIngestResponse：约束成功响应结构
@router.post("/ingest/pdf",response_model=PDFInfoResponse)
async def rag_ingest_pdf(file: UploadFile = File(...),
                         collection_name: str = Form("default"),
                         rag_service: RAGService = Depends(get_rag_service)) -> PDFInfoResponse:
    """
    RAG PDF 导入接口
    将 PDF 文件导入到向量数据库中
    """
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400,detail="文件必须是 PDF 格式")

    collection_name = collection_name.strip()
    if not collection_name:
        raise HTTPException(status_code=400,detail="知识库名称不能为空")

    try:
        content = await file.read()
        chunk_count = rag_service.ingest_pdf(
            content = content,
            filename = filename,
            collection_name = collection_name
        )
    except ValueError  as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc
    except Exception as e:
        logging.error(f"PDF 导入失败，错误信息：{str(e)}")
        raise HTTPException(status_code=500,detail=str(e)) from e

    return PDFInfoResponse(
        message="PDF 导入成功",
        filename=filename,
        collection_name=collection_name,
        chunk_count=chunk_count
    )
    
