"""
模型推理路由 - 统一推理接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import time
import uuid
import logging

from ..core.database import get_db
from ..core.config import settings
from ..models.user import User
from ..auth.dependencies import get_current_user
from ..services.llm import LLMService
from ..services.embedding import EmbeddingService
from ..services.billing_integration import charge_api_call

logger = logging.getLogger(__name__)

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
    llm_service = LLMService(model_name=model)
    response = await llm_service.chat(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # 获取 token 使用量
    total_tokens = response.tokens_used
    prompt_tokens = getattr(response, 'input_tokens', 0)
    completion_tokens = getattr(response, 'output_tokens', total_tokens)

    # 计费（异步，不阻断响应）
    try:
        billing_result = await charge_api_call(
            db=db,
            user_id=current_user.id,
            model_name=model,
            tokens_used=total_tokens,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
        )
        # 记录计费信息到日志
        if billing_result.get("charged"):
            logger.info(
                f"Billing: user={current_user.id}, model={model}, "
                f"tokens={total_tokens}, amount={billing_result.get('amount')}"
            )
            # 如果有余额预警，在响应中返回警告
            if billing_result.get("warning"):
                logger.warning(billing_result["warning"])
    except Exception as e:
        # 计费失败不阻断请求，只记录日志
        logger.error(f"Billing failed for user {current_user.id}: {e}")

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
                    "content": response.content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        "billing": billing_result if settings.DEBUG else None,  # 仅在调试模式返回计费信息
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
    embedding_service = EmbeddingService(model_name=model)

    if isinstance(input, str):
        input = [input]

    embeddings = []
    total_tokens = 0
    for text in input:
        result = await embedding_service.embed(text)
        embeddings.append(result.embedding)
        # 估算 token 数（按字符数 / 4 估算）
        total_tokens += len(text) // 4

    # 计费
    try:
        billing_result = await charge_api_call(
            db=db,
            user_id=current_user.id,
            model_name=model,
            tokens_used=total_tokens,
            resource_type="embedding",
        )
        if billing_result.get("charged"):
            logger.info(
                f"Billing: user={current_user.id}, model={model}, "
                f"type=embedding, tokens={total_tokens}, amount={billing_result.get('amount')}"
            )
    except Exception as e:
        logger.error(f"Billing failed for user {current_user.id}: {e}")

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
            "prompt_tokens": total_tokens,
            "total_tokens": total_tokens,
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
    llm_service = LLMService(model_name=model)
    response = await llm_service.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # 获取 token 使用量
    total_tokens = response.tokens_used
    prompt_tokens = getattr(response, 'input_tokens', len(prompt) // 4)
    completion_tokens = getattr(response, 'output_tokens', total_tokens - prompt_tokens)

    # 计费
    try:
        billing_result = await charge_api_call(
            db=db,
            user_id=current_user.id,
            model_name=model,
            tokens_used=total_tokens,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
        )
        if billing_result.get("charged"):
            logger.info(
                f"Billing: user={current_user.id}, model={model}, "
                f"type=generate, tokens={total_tokens}, amount={billing_result.get('amount')}"
            )
    except Exception as e:
        logger.error(f"Billing failed for user {current_user.id}: {e}")

    return {
        "id": f"gen-{uuid.uuid4().hex[:8]}",
        "model": model,
        "text": response.get("text", ""),
        "usage": response.get("usage", {}),
    }
