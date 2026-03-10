"""智能体相关路由"""
from fastapi import APIRouter
from pydantic import BaseModel
from ..models import ChatRequest, ChatResponse
from ..services import agent_service

router = APIRouter(prefix="/api/agent", tags=["agent"])


class ClearHistoryRequest(BaseModel):
    user_id: int


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """智能体对话"""
    result = agent_service.chat(request.message, request.user_id)
    return ChatResponse(**result)


@router.post("/clear-history")
def clear_history(request: ClearHistoryRequest):
    """清空指定用户的对话历史"""
    success = agent_service.clear_conversation_history(request.user_id)
    return {"success": success, "message": "对话历史已清空" if success else "用户对话历史不存在"}

