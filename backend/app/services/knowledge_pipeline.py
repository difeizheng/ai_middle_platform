"""
知识工厂 - 知识处理 Pipeline 任务
"""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..models.knowledge import KnowledgeDocument, KnowledgeChunk
from ..services.parser import DocumentParser
from ..services.chunker import TextChunker, Chunk
from ..services.embedding import EmbeddingService
from ..services.vector_store import VectorStoreService

from ..core.logger import get_logger

logger = get_logger(__name__)


class KnowledgePipelineService:
    """
    知识处理 Pipeline 服务

    处理流程:
    1. 文档解析 -> 2. 文本分片 -> 3. 向量化 -> 4. 存储
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.parser = DocumentParser()
        self.chunker = None  # 延迟初始化
        self.embedding_service = None
        self.vector_store = None

    def _init_services(self, knowledge_base: KnowledgeDocument):
        """初始化处理服务"""
        if self.chunker is None:
            self.chunker = TextChunker(
                chunk_size=knowledge_base.chunk_size,
                chunk_overlap=knowledge_base.chunk_overlap,
                strategy="semantic",
            )

        if self.embedding_service is None:
            self.embedding_service = EmbeddingService(
                model_name=knowledge_base.embedding_model
            )

        if self.vector_store is None:
            self.vector_store = VectorStoreService(
                collection_name=knowledge_base.collection_name
            )

    async def process_document(
        self,
        document_id: int,
    ) -> Dict[str, Any]:
        """
        处理文档

        Args:
            document_id: 文档 ID

        Returns:
            处理结果
        """
        logger.info(f"开始处理文档：{document_id}")

        # 获取文档信息
        result = await self.db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"文档不存在：{document_id}")

        # 更新状态为处理中
        await self._update_document_status(document_id, "processing")

        try:
            # 获取知识库配置
            result = await self.db.execute(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.knowledge_base_id == document.knowledge_base_id
                )
            )
            kb = result.scalar_one_or_none()

            if not kb:
                raise ValueError(f"知识库不存在：{document.knowledge_base_id}")

            # 初始化服务
            if self.chunker is None:
                self.chunker = TextChunker(
                    chunk_size=kb.chunk_size,
                    chunk_overlap=kb.chunk_overlap,
                    strategy="semantic",
                )

            if self.embedding_service is None:
                self.embedding_service = EmbeddingService(
                    model_name=kb.embedding_model
                )

            if self.vector_store is None:
                self.vector_store = VectorStoreService(
                    collection_name=kb.collection_name
                )

            # 连接向量库
            await self.vector_store.connect()

            # Step 1: 文档解析
            parse_result = await asyncio.to_thread(
                self.parser.parse, document.file_path
            )
            logger.info(f"文档解析完成：{len(parse_result['content'])} 字符")

            # Step 2: 文本分片
            chunks = self.chunker.chunk(parse_result["content"], parse_result["metadata"])
            logger.info(f"文本分片完成：{len(chunks)} 个分片")

            # Step 3: 向量化
            texts = [chunk.content for chunk in chunks]
            embeddings = await self.embedding_service.embed_batch(texts)
            vectors = [emb.embedding for emb in embeddings]
            logger.info(f"向量化完成：{len(vectors)} 个向量")

            # Step 4: 存储到向量数据库
            chunk_ids = [f"{document_id}_{i}" for i in range(len(chunks))]
            contents = [chunk.content for chunk in chunks]
            metadatas = [
                {
                    "document_id": document_id,
                    "chunk_index": chunk.chunk_index,
                    "start_pos": chunk.start_pos,
                    "end_pos": chunk.end_pos,
                    **chunk.metadata,
                }
                for chunk in chunks
            ]

            success = await self.vector_store.upsert(
                vectors=vectors,
                ids=chunk_ids,
                contents=contents,
                metadatas=metadatas,
            )

            if not success:
                raise Exception("向量存储失败")

            # Step 5: 保存到数据库
            await self._save_chunks(document_id, chunks, chunk_ids)

            # 更新文档状态
            await self._update_document_status(
                document_id,
                "completed",
                chunk_count=len(chunks),
            )

            # 更新知识库统计
            await self._update_knowledge_base_stats(document.knowledge_base_id)

            logger.info(f"文档处理完成：{document_id}")

            return {
                "success": True,
                "document_id": document_id,
                "chunk_count": len(chunks),
                "content_length": len(parse_result["content"]),
            }

        except Exception as e:
            logger.error(f"文档处理失败：{e}")
            await self._update_document_status(
                document_id,
                "failed",
                error_message=str(e),
            )
            raise

    async def _save_chunks(
        self,
        document_id: int,
        chunks: list,
        chunk_ids: list,
    ):
        """保存分片到数据库"""
        for i, chunk in enumerate(chunks):
            db_chunk = KnowledgeChunk(
                document_id=document_id,
                knowledge_base_id=(
                    await self.db.execute(
                        select(KnowledgeDocument.knowledge_base_id).where(
                            KnowledgeDocument.id == document_id
                        )
                    )
                ).scalar(),
                content=chunk.content,
                vector_id=chunk_ids[i],
                chunk_index=chunk.chunk_index,
                start_pos=chunk.start_pos,
                end_pos=chunk.end_pos,
                metadata=chunk.metadata,
            )
            self.db.add(db_chunk)

        await self.db.commit()

    async def _update_document_status(
        self,
        document_id: int,
        status: str,
        chunk_count: int = None,
        error_message: str = None,
    ):
        """更新文档状态"""
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }

        if chunk_count is not None:
            update_data["chunk_count"] = chunk_count

        if error_message is not None:
            update_data["error_message"] = error_message

        if status == "completed":
            update_data["processed_at"] = datetime.utcnow()

        await self.db.execute(
            update(KnowledgeDocument)
            .where(KnowledgeDocument.id == document_id)
            .values(**update_data)
        )
        await self.db.commit()

    async def _update_knowledge_base_stats(self, kb_id: int):
        """更新知识库统计信息"""
        # 统计文档数
        doc_result = await self.db.execute(
            select(KnowledgeDocument.id).where(
                KnowledgeDocument.knowledge_base_id == kb_id,
                KnowledgeDocument.status == "completed",
            )
        )
        doc_count = len(doc_result.scalars().all())

        # 统计分片数
        chunk_result = await self.db.execute(
            select(KnowledgeChunk.id).where(
                KnowledgeChunk.knowledge_base_id == kb_id
            )
        )
        chunk_count = len(chunk_result.scalars().all())

        # 更新知识库
        from ..models.knowledge import KnowledgeBase

        await self.db.execute(
            update(KnowledgeBase)
            .where(KnowledgeBase.id == kb_id)
            .values(
                document_count=doc_count,
                chunk_count=chunk_count,
                updated_at=datetime.utcnow(),
            )
        )
        await self.db.commit()


async def process_document_task(document_id: int, db: AsyncSession):
    """
    异步处理文档任务（用于 Celery 或后台任务）
    """
    pipeline = KnowledgePipelineService(db)
    try:
        result = await pipeline.process_document(document_id)
        logger.info(f"文档处理任务完成：{result}")
        return result
    except Exception as e:
        logger.error(f"文档处理任务失败：{e}")
        raise
