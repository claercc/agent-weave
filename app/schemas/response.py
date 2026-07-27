from pydantic import BaseModel, Field

class SummaryResponse(BaseModel):
    """文章总结"""
    title: str = Field(description="文章标题")
    summary: str = Field(description="文章总结")
    keywords: list[str] = Field(description="文章关键词")

class RAGResponse(BaseModel):
    """RAG 响应"""
    answer: str = Field(description="回答")
    context: str = Field(description="上下文")
    query: str = Field(description="查询")
