"""
LLM 服务 - 大语言模型调用服务
"""
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass

from ..core.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    tokens_used: int
    finish_reason: str


class LLMService:
    """
    LLM 服务

    支持多种模型后端：
    - OpenAI 兼容 API
    - vLLM
    - 本地模型
    """

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.DEFAULT_LLM_MODEL
        self._client = None

    def _get_client(self):
        """获取 API 客户端"""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = None,
        stream: bool = False,
    ) -> LLMResponse:
        """
        聊天补全

        Args:
            messages: 消息历史
            temperature: 温度参数
            max_tokens: 最大输出 token 数
            stream: 是否流式输出

        Returns:
            LLMResponse: 响应
        """
        # 获取模型配置
        model_config = settings.LLM_APIS.get(self.model_name, {})
        base_url = model_config.get("base_url", "http://localhost:8000/v1")
        api_key = model_config.get("api_key", "")

        try:
            client = self._get_client()

            response = await client.post(
                f"{base_url}/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens or settings.DEFAULT_MAX_TOKENS,
                    "stream": stream,
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

            data = response.json()
            choice = data["choices"][0]

            return LLMResponse(
                content=choice["message"]["content"],
                model=data.get("model", self.model_name),
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                finish_reason=choice.get("finish_reason", "stop"),
            )

        except Exception as e:
            logger.error(f"LLM 调用失败：{e}")
            # 降级返回模拟响应
            return LLMResponse(
                content="抱歉，服务暂时不可用，请稍后重试。",
                model=self.model_name,
                tokens_used=0,
                finish_reason="error",
            )

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = None,
    ) -> AsyncIterator[str]:
        """
        流式聊天

        Args:
            messages: 消息历史
            temperature: 温度参数
            max_tokens: 最大输出 token 数

        Yields:
            响应文本片段
        """
        model_config = settings.LLM_APIS.get(self.model_name, {})
        base_url = model_config.get("base_url", "http://localhost:8000/v1")
        api_key = model_config.get("api_key", "")

        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/chat/completions",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens or settings.DEFAULT_MAX_TOKENS,
                        "stream": True,
                    },
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            import json
                            try:
                                chunk = json.loads(data)
                                content = chunk["choices"][0]["delta"].get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"流式 LLM 调用失败：{e}")
            yield "抱歉，流式服务暂时不可用。"

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = None,
    ) -> LLMResponse:
        """
        文本生成

        Args:
            prompt: 输入提示
            temperature: 温度参数
            max_tokens: 最大输出 token 数

        Returns:
            LLMResponse: 响应
        """
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, temperature, max_tokens)

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None


# 全局服务实例
_llm_service: Optional[LLMService] = None


def get_llm_service(model_name: str = None) -> LLMService:
    """获取 LLM 服务实例"""
    global _llm_service
    if _llm_service is None or (model_name and model_name != _llm_service.model_name):
        _llm_service = LLMService(model_name)
    return _llm_service
