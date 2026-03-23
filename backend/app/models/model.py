"""
模型注册和管理相关模型
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base


class Model(Base):
    """
    模型实例表 - 记录已接入的模型
    """
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # 模型名称，如 qwen-72b
    display_name = Column(String(200))  # 显示名称

    # 模型类型
    model_type = Column(String(20), nullable=False)  # llm, embedding, rerank, vision

    # 接入方式
    provider = Column(String(50))  # openai, vllm, local, deepseek, zhipu
    base_url = Column(String(500))  # API 基础 URL
    api_key = Column(String(500))  # API 密钥（加密存储）

    # 模型能力
    max_context_length = Column(Integer, default=4096)  # 最大上下文长度
    max_tokens = Column(Integer, default=2048)  # 最大输出 token 数
    supports_function_call = Column(Boolean, default=False)  # 是否支持函数调用
    supports_vision = Column(Boolean, default=False)  # 是否支持视觉

    # 状态
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # 是否为默认模型

    # 性能指标
    avg_latency_ms = Column(Float, default=0.0)  # 平均延迟
    qps = Column(Integer, default=0)  # 当前 QPS

    # 配置
    config = Column(JSON, default=dict)  # 额外配置

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Model {self.name}>"


class ModelRegistry(Base):
    """
    模型注册表 - 记录模型版本和元数据
    """
    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id"))

    # 版本信息
    version = Column(String(50))  # 模型版本
    path = Column(String(500))  # 模型文件路径（本地模型）

    # 元数据
    description = Column(Text)  # 模型描述
    tags = Column(JSON, default=list)  # 标签
    metrics = Column(JSON, default=dict)  # 评估指标

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ModelRegistry {self.version}>"
