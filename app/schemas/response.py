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


class CitationResponse(BaseModel):
    """引用响应"""

    index: int = Field(description="引用索引")
    source: str = Field(description="引用来源")
    excerpt: str = Field(description="引用摘录")
    score: float | None = Field(description="引用分数", default=None)


class AgentChatResponse(BaseModel):
    """智能体聊天响应"""

    session_id: str = Field(description="会话ID", min_length=1)
    answer: str = Field(description="Agent 最终回答")
    used_tools: list[str] = Field(description="使用的工具", default_factory=list)
    citations: list[CitationResponse] = Field(
        description="引用列表", default_factory=list
    )


class PDFInfoResponse(BaseModel):
    """PDF 信息响应"""

    message: str = Field(description="导入结果")
    filename: str = Field(description="PDF文件名")
    collection_name: str = Field(description="目标知识库名称")
    chunk_count: int = Field(description="文档分块数量", ge=0)
