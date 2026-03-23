"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    """
    应用配置
    """
    # ========== 基础配置 ==========
    APP_NAME: str = "AI 中台系统"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"  # development, staging, production

    # ========== 服务配置 ==========
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # ========== 数据库配置 ==========
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_middle_platform"
    DATABASE_POOL_SIZE: int = 20  # 连接池大小
    DATABASE_MAX_OVERFLOW: int = 40  # 最大溢出连接数
    DATABASE_POOL_TIMEOUT: int = 30  # 获取连接超时时间（秒）
    DATABASE_POOL_RECYCLE: int = 3600  # 连接回收时间（秒）

    # ========== Redis 配置 ==========
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

    # ========== JWT 配置 ==========
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ========== 模型配置 ==========
    # 默认模型
    DEFAULT_LLM_MODEL: str = "qwen-72b"
    DEFAULT_EMBEDDING_MODEL: str = "bge-large-zh-v1.5"
    DEFAULT_MAX_TOKENS: int = 4096

    # 模型 API 配置（支持多模型）
    LLM_APIS: dict = {
        "qwen-72b": {
            "base_url": "http://localhost:8000/v1",
            "api_key": "sk-xxx",
            "max_tokens": 4096,
        },
        "chatglm3-6b": {
            "base_url": "http://localhost:8001/v1",
            "api_key": "sk-xxx",
            "max_tokens": 4096,
        },
        "deepseek-67b": {
            "base_url": "http://localhost:8002/v1",
            "api_key": "sk-xxx",
            "max_tokens": 4096,
        },
    }

    # ========== 向量库配置 ==========
    VECTOR_DB_TYPE: str = "milvus"  # milvus, qdrant
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "knowledge_base"

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "knowledge_base"

    # 向量维度（根据 embedding 模型）
    EMBEDDING_DIM: int = 1024

    # ========== 文件存储配置 ==========
    STORAGE_TYPE: str = "local"  # local, minio, s3
    LOCAL_STORAGE_PATH: str = "./data/storage"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "ai-middle-platform"

    # ========== 日志配置 ==========
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # ========== CORS 配置 ==========
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
    ]

    # ========== 限流配置 ==========
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100  # 每分钟请求数
    RATE_LIMIT_WINDOW: int = 60  # 秒

    # ========== 监控配置 ==========
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090

    # ========== 安全配置 ==========
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md"]
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    MAX_UPLOAD_FILES: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()
