"""
向量化服务
支持多种 Embedding 模型
"""
import asyncio
from typing import List, Union, Optional, Dict, Any
from dataclasses import dataclass

from ..core.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


@dataclass
class EmbeddingResult:
    """向量化结果"""
    text: str
    embedding: List[float]
    model: str
    usage: Dict[str, int]


class EmbeddingService:
    """
    向量化服务
    """

    def __init__(self, model_name: str = None):
        """
        Args:
            model_name: 模型名称
        """
        self.model_name = model_name or settings.DEFAULT_EMBEDDING_MODEL
        self._local_model = None

    async def embed(
        self,
        text: str,
        model: str = None,
    ) -> EmbeddingResult:
        """
        向量化单个文本

        Args:
            text: 待向量化的文本
            model: 模型名称

        Returns:
            EmbeddingResult
        """
        model = model or self.model_name

        # 根据模型类型选择向量化方式
        if model in ["bge-large-zh-v1.5", "text2vec", "m3e"]:
            return await self._embed_local(text, model)
        else:
            return await self._embed_api(text, model)

    async def embed_batch(
        self,
        texts: List[str],
        model: str = None,
        batch_size: int = 32,
    ) -> List[EmbeddingResult]:
        """
        批量向量化

        Args:
            texts: 待向量化的文本列表
            model: 模型名称
            batch_size: 批次大小

        Returns:
            向量化结果列表
        """
        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_tasks = [self.embed(text, model) for text in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)

        logger.info(f"批量向量化完成：{len(texts)} 条文本")

        return results

    async def _embed_local(
        self,
        text: str,
        model: str,
    ) -> EmbeddingResult:
        """使用本地模型向量化"""
        try:
            from sentence_transformers import SentenceTransformer

            if self._local_model is None:
                logger.info(f"加载本地 Embedding 模型：{model}")
                self._local_model = SentenceTransformer(model)

            embedding = self._local_model.encode(text, convert_to_numpy=True)

            return EmbeddingResult(
                text=text,
                embedding=embedding.tolist(),
                model=model,
                usage={"prompt_tokens": len(text)},
            )
        except ImportError:
            logger.warning("sentence-transformers 未安装，使用模拟向量")
            # 返回模拟向量用于开发测试
            return EmbeddingResult(
                text=text,
                embedding=[0.0] * settings.EMBEDDING_DIM,
                model=model,
                usage={"prompt_tokens": len(text)},
            )
        except Exception as e:
            logger.error(f"本地向量化失败：{e}")
            # 降级为模拟向量
            return EmbeddingResult(
                text=text,
                embedding=[0.0] * settings.EMBEDDING_DIM,
                model=model,
                usage={"prompt_tokens": len(text)},
            )

    async def _embed_api(
        self,
        text: str,
        model: str,
    ) -> EmbeddingResult:
        """使用 API 向量化"""
        try:
            import httpx

            # 获取模型配置
            model_config = settings.LLM_APIS.get(model, {})
            base_url = model_config.get("base_url", "http://localhost:8000/v1")
            api_key = model_config.get("api_key", "")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/embeddings",
                    json={
                        "model": model,
                        "input": text,
                    },
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

                embedding = data["data"][0]["embedding"]
                usage = data.get("usage", {})

                return EmbeddingResult(
                    text=text,
                    embedding=embedding,
                    model=model,
                    usage=usage,
                )
        except Exception as e:
            logger.error(f"API 向量化失败：{e}")
            # 降级为模拟向量
            return EmbeddingResult(
                text=text,
                embedding=[0.0] * settings.EMBEDDING_DIM,
                model=model,
                usage={"prompt_tokens": len(text)},
            )

    def embed_sync(self, text: str, model: str = None) -> EmbeddingResult:
        """同步向量化（用于非异步场景）"""
        return asyncio.run(self.embed(text, model))


# 全局服务实例
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(model_name: str = None) -> EmbeddingService:
    """获取向量化服务实例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(model_name)
    return _embedding_service
