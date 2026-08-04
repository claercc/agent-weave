from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])

class HealthResponse(BaseModel):
    status: Literal["ok"]

@router.get("/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    """进程是否存活，是否可以正常响应"""
    return HealthResponse(status="ok")

@router.get("/ready", response_model=HealthResponse)
def readiness() -> HealthResponse:
    """应用是否准备就绪，是否可以接收请求"""
    return HealthResponse(status="ok")
