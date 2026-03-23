"""
知识管理路由 - 知识工厂核心 API
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import os
import uuid

from ..core.database import get_db
from ..core.config import settings
from ..models.user import User
from ..models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeChunk
from ..auth.dependencies import get_current_user

router = APIRouter()


# ========== 知识库管理 ==========

@router.get("/bases")
async def list_knowledge_bases(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取知识库列表
    """
    result = await db.execute(select(KnowledgeBase).offset(skip).limit(limit))
    bases = result.scalars().all()

    return {
        "total": len(bases),
        "knowledge_bases": [
            {
                "id": b.id,
                "name": b.name,
                "description": b.description,
                "document_count": b.document_count,
                "chunk_count": b.chunk_count,
                "created_at": str(b.created_at),
            }
            for b in bases
        ],
    }


@router.post("/bases")
async def create_knowledge_base(
    name: str = Form(...),
    description: str = Form(None),
    embedding_model: str = Form("bge-large-zh-v1.5"),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建知识库
    """
    # 生成唯一的集合名称
    collection_name = f"kb_{uuid.uuid4().hex[:8]}"

    kb = KnowledgeBase(
        name=name,
        description=description,
        owner_id=current_user.id,
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        collection_name=collection_name,
    )

    db.add(kb)
    await db.commit()
    await db.refresh(kb)

    return {
        "id": kb.id,
        "name": kb.name,
        "collection_name": kb.collection_name,
        "message": "知识库创建成功",
    }


@router.get("/bases/{kb_id}")
async def get_knowledge_base(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取知识库详情
    """
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库不存在",
        )

    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "embedding_model": kb.embedding_model,
        "chunk_size": kb.chunk_size,
        "chunk_overlap": kb.chunk_overlap,
        "document_count": kb.document_count,
        "chunk_count": kb.chunk_count,
        "access_level": kb.access_level,
    }


# ========== 文档管理 ==========

@router.get("/bases/{kb_id}/documents")
async def list_documents(
    kb_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取知识库文档列表
    """
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.knowledge_base_id == kb_id)
        .offset(skip)
        .limit(limit)
    )
    documents = result.scalars().all()

    return {
        "total": len(documents),
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "file_name": d.file_name,
                "file_type": d.file_type,
                "file_size": d.file_size,
                "status": d.status,
                "chunk_count": d.chunk_count,
                "created_at": str(d.created_at),
            }
            for d in documents
        ],
    }


@router.post("/bases/{kb_id}/documents/upload")
async def upload_document(
    kb_id: int,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传文档到知识库
    """
    # 检查知识库是否存在
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库不存在",
        )

    uploaded = []
    for file in files:
        # 检查文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_FILE_TYPES:
            continue

        # 生成存储路径
        storage_path = os.path.join(
            settings.LOCAL_STORAGE_PATH,
            "knowledge",
            str(kb_id),
            f"{uuid.uuid4().hex}{file_ext}",
        )

        # 确保目录存在
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)

        # 保存文件
        with open(storage_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 创建文档记录
        doc = KnowledgeDocument(
            knowledge_base_id=kb_id,
            title=file.filename,
            file_name=file.filename,
            file_path=storage_path,
            file_type=file_ext[1:],
            file_size=len(content),
            status="pending",
        )

        db.add(doc)
        uploaded.append(doc)

    await db.commit()

    # TODO: 触发异步任务处理文档

    return {
        "message": f"上传成功，共 {len(uploaded)} 个文件",
        "documents": [
            {"id": d.id, "file_name": d.file_name, "status": d.status}
            for d in uploaded
        ],
    }


# ========== 知识检索 ==========

@router.post("/search")
async def search_knowledge(
    kb_id: int,
    query: str,
    top_k: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    检索知识库
    """
    # TODO: 实现向量检索
    # 目前返回空结果
    return {
        "query": query,
        "results": [],
        "message": "向量检索功能开发中",
    }
