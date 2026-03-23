"""
模型推理路由 - 统一推理接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import time
import uuid

from ..core.database import get_db
from ..core.config import settings
from ..models.user import User
from ..auth.dependencies import get_current_user

router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(
    model: str = None,
    messages: list = None,
    temperature: float = 0.7,
    max_tokens: int = None,
    stream: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    聊天补全接口（OpenAI 兼容）
    """
    # 使用默认模型
    if model is None:
        model = settings.DEFAULT_LLM_MODEL

    # TODO: 调用模型服务
    # 目前返回模拟响应
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "这是 AI 中台系统的模拟响应。实际实现将调用配置的模型服务。",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 50,
            "total_tokens": 50,
        },
    }


@router.post("/embeddings")
async def create_embeddings(
    input: str | List[str],
    model: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    文本向量化接口
    """
    if model is None:
        model = settings.DEFAULT_EMBEDDING_MODEL

    # TODO: 调用 embedding 模型
    # 目前返回模拟响应
    if isinstance(input, str):
        input = [input]

    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "index": i,
                "embedding": [0.0] * settings.EMBEDDING_DIM,  # 模拟向量
            }
            for i in range(len(input))
        ],
        "model": model,
        "usage": {
            "prompt_tokens": 0,
            "total_tokens": 0,
        },
    }


@router.post("/generate")
async def generate(
    prompt: str,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    文本生成接口
    """
    if model is None:
        model = settings.DEFAULT_LLM_MODEL

    # TODO: 调用模型服务
    return {
        "id": f"gen-{uuid.uuid4().hex[:8]}",
        "model": model,
        "text": "这是 AI 中台系统的模拟响应。实际实现将调用配置的模型服务。",
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 50,
            "total_tokens": 50,
        },
    }
