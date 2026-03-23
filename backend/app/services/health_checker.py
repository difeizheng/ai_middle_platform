"""
服务健康检查器

定期检查各服务的健康状态并上报
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import time

from app.core.logger import get_logger
from app.core.database import get_db_session
from app.models.monitor import SystemHealth
from app.services.metrics import get_metric_collector

logger = get_logger(__name__)


class ServiceHealthChecker:
    """
    服务健康检查器

    支持检查的服务类型:
    - database: 数据库连接
    - redis: Redis 连接
    - embedding: 向量化服务
    - llm: LLM 服务
    - mcp: MCP 连接器
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._check_interval = 30  # 默认 30 秒检查一次

    async def start(self, interval: int = 30):
        """启动健康检查"""
        self._check_interval = interval
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info(f"健康检查器已启动，检查间隔：{interval}秒")

    async def stop(self):
        """停止健康检查"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("健康检查器已停止")

    async def _check_loop(self):
        """健康检查循环"""
        while self._running:
            try:
                await self._check_all_services()
            except Exception as e:
                logger.error(f"健康检查出错：{e}")
            await asyncio.sleep(self._check_interval)

    async def _check_all_services(self):
        """检查所有服务"""
        services_to_check = [
            ("database", self._check_database),
            ("redis", self._check_redis),
            ("embedding", self._check_embedding),
            ("llm", self._check_llm),
        ]

        for service_name, check_func in services_to_check:
            try:
                status, latency, details = await check_func()
                await self._report_health(
                    service_name=service_name,
                    service_type=service_name,
                    status=status,
                    latency_ms=latency,
                    details=details,
                )
            except Exception as e:
                logger.error(f"检查服务 {service_name} 失败：{e}")
                await self._report_health(
                    service_name=service_name,
                    service_type=service_name,
                    status="unhealthy",
                    message=str(e),
                )

    async def _check_database(self) -> tuple:
        """检查数据库连接"""
        start_time = time.time()
        try:
            db = await get_db_session().__anext__()
            await db.execute("SELECT 1")
            latency = (time.time() - start_time) * 1000
            return "healthy", latency, {"connection": "ok"}
        except Exception as e:
            return "unhealthy", 0, {"error": str(e)}

    async def _check_redis(self) -> tuple:
        """检查 Redis 连接"""
        start_time = time.time()
        try:
            # 检查 Redis 是否配置
            from app.core.config import settings
            if not settings.REDIS_URL:
                return "degraded", 0, {"warning": "Redis 未配置"}

            from app.core.cache import get_redis

            redis = get_redis()
            await redis.ping()
            latency = (time.time() - start_time) * 1000
            return "healthy", latency, {"ping": "pong"}
        except ImportError:
            return "degraded", 0, {"warning": "Redis 模块未安装"}
        except Exception as e:
            return "unhealthy", 0, {"error": str(e)}

    async def _check_embedding(self) -> tuple:
        """检查向量化服务"""
        start_time = time.time()
        try:
            from app.services.embedding import EmbeddingService

            embedding_service = EmbeddingService()
            # 简单测试
            result = await embedding_service.embed("health check")
            latency = (time.time() - start_time) * 1000
            return "healthy", latency, {"model": result.model}
        except Exception as e:
            return "degraded", 0, {"error": str(e)}

    async def _check_llm(self) -> tuple:
        """检查 LLM 服务"""
        start_time = time.time()
        try:
            from app.services.llm import LLMService

            llm_service = LLMService()
            # 简单测试（不实际调用 API，只检查配置）
            if llm_service.model_name:
                latency = (time.time() - start_time) * 1000
                return "healthy", latency, {"model": llm_service.model_name}
            else:
                return "degraded", 0, {"warning": "未配置默认 LLM 模型"}
        except Exception as e:
            return "degraded", 0, {"error": str(e)}

    async def _report_health(
        self,
        service_name: str,
        service_type: str,
        status: str,
        latency_ms: float = 0,
        details: Optional[Dict] = None,
        message: Optional[str] = None,
    ):
        """上报健康状态到数据库"""
        try:
            db = await get_db_session().__anext__()
            health = SystemHealth(
                service_name=service_name,
                service_type=service_type,
                status=status,
                latency_ms=latency_ms,
                error_rate=0.0 if status == "healthy" else 1.0,
                success_rate=1.0 if status == "healthy" else 0.0,
                details=details or {},
                message=message,
            )
            db.add(health)
            await db.commit()
        except Exception as e:
            logger.error(f"上报健康状态失败：{e}")

    async def check_now(self, service_name: str = None) -> Dict[str, Any]:
        """立即执行一次健康检查"""
        if service_name:
            check_map = {
                "database": self._check_database,
                "redis": self._check_redis,
                "embedding": self._check_embedding,
                "llm": self._check_llm,
            }
            if service_name in check_map:
                status, latency, details = await check_map[service_name]()
                await self._report_health(
                    service_name=service_name,
                    service_type=service_name,
                    status=status,
                    latency_ms=latency,
                    details=details,
                )
                return {"service": service_name, "status": status, "latency_ms": latency}
            else:
                return {"error": f"未知服务：{service_name}"}
        else:
            await self._check_all_services()
            return {"status": "completed"}


# 全局健康检查器实例
_global_health_checker: Optional[ServiceHealthChecker] = None


def get_health_checker() -> ServiceHealthChecker:
    """获取全局健康检查器"""
    global _global_health_checker
    if _global_health_checker is None:
        _global_health_checker = ServiceHealthChecker()
    return _global_health_checker


async def start_health_checker(interval: int = 30):
    """启动健康检查器"""
    checker = get_health_checker()
    await checker.start(interval)


async def stop_health_checker():
    """停止健康检查器"""
    checker = get_health_checker()
    await checker.stop()
