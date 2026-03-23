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
from ..services.llm import get_llm
from ..services.embedding import get_embedding

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

    if not messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")

    # 调用 LLM 服务
    llm = get_llm()
    response = await llm.chat(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

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
                    "content": response.get("content", ""),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": response.get("usage", {}),
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

    # 调用 Embedding 服务
    embedding_model = get_embedding()

    if isinstance(input, str):
        input = [input]

    embeddings = []
    for text in input:
        vector = await embedding_model.embed_query(text)
        embeddings.append(vector)

    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "index": i,
                "embedding": emb,
            }
            for i, emb in enumerate(embeddings)
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

    if not prompt:
        raise HTTPException(status_code=400, detail="prompt 不能为空")

    # 调用 LLM 服务
    llm = get_llm()
    response = await llm.generate(
        model=model,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return {
        "id": f"gen-{uuid.uuid4().hex[:8]}",
        "model": model,
        "text": response.get("text", ""),
        "usage": response.get("usage", {}),
    }
