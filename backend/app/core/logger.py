"""
日志配置
"""
import structlog
from loguru import logger
import sys
from .config import settings


def setup_logging():
    """
    配置日志系统
    """
    # 配置 loguru
    logger.remove()
    logger.add(
        sys.stdout,
        format=settings.LOG_FORMAT,
        level=settings.LOG_LEVEL,
        colorize=True,
    )
    logger.add(
        "logs/app.log",
        rotation="500 MB",
        retention="10 days",
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
    )

    # 配置 structlog（用于结构化日志）
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(settings, "LOG_LEVEL", "INFO").upper()
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    return logger


def get_logger(name: str = __name__):
    """
    获取 logger 实例
    """
    return logger.bind(module=name)
