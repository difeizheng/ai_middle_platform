"""
知识库相关模型
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON, ForeignKey, BigInteger
from sqlalchemy.sql import func
from ..core.database import Base


class KnowledgeBase(Base):
    """
    知识库表
    """
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # 知识库名称
    description = Column(Text)  # 描述

    # 所有者
    owner_id = Column(Integer, ForeignKey("users.id"))

    # 配置
    embedding_model = Column(String(100), default="bge-large-zh-v1.5")
    chunk_size = Column(Integer, default=500)  # 分片大小
    chunk_overlap = Column(Integer, default=50)  # 分片重叠

    # 向量集合名称
    collection_name = Column(String(100), unique=True)

    # 状态
    is_active = Column(Boolean, default=True)
    document_count = Column(Integer, default=0)  # 文档数量
    chunk_count = Column(Integer, default=0)  # 分片数量

    # 权限
    access_level = Column(String(20), default="private")  # private, department, public
    authorized_users = Column(JSON, default=list)  # 授权用户列表

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<KnowledgeBase {self.name}>"


class KnowledgeDocument(Base):
    """
    知识文档表
    """
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)

    # 文档信息
    title = Column(String(500))  # 文档标题
    file_name = Column(String(500))  # 原始文件名
    file_path = Column(String(1000))  # 文件存储路径
    file_hash = Column(String(64))  # 文件 hash（用于去重）
    file_size = Column(BigInteger)  # 文件大小（字节）
    file_type = Column(String(20))  # pdf, docx, xlsx, txt, md

    # 处理状态
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)  # 错误信息

    # 处理结果
    chunk_count = Column(Integer, default=0)  # 生成的分片数
    metadata = Column(JSON, default=dict)  # 元数据

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<KnowledgeDocument {self.file_name}>"


class KnowledgeChunk(Base):
    """
    知识分片表（存储文本内容和向量索引引用）
    """
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=False)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)

    # 分片内容
    content = Column(Text, nullable=False)  # 分片文本内容

    # 向量索引
    vector_id = Column(String(100))  # 向量数据库中的 ID
    embedding = Column(JSON)  # 向量（可选，用于缓存）

    # 位置信息
    chunk_index = Column(Integer)  # 分片索引
    start_pos = Column(Integer)  # 在原文档中的起始位置
    end_pos = Column(Integer)  # 在原文档中的结束位置

    # 元数据
    metadata = Column(JSON, default=dict)  # 页码、章节等

    # 使用统计
    hit_count = Column(Integer, default=0)  # 被检索命中次数

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<KnowledgeChunk {self.id}>"
