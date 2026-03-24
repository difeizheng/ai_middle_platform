"""
API Key 管理服务

提供 API Key 的生成、加密存储、验证等功能
"""
import secrets
from typing import Optional, List
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from .encryption import get_encryption_service
from ..models.app import APIKey, Application
from ..core.logger import get_logger

logger = get_logger(__name__)


# API Key 前缀
API_KEY_PREFIX = "sk_"


def generate_api_key() -> tuple[str, str]:
    """
    生成新的 API Key 和 Secret

    Returns:
        tuple: (api_key, api_secret)
        - api_key: 完整 API Key（格式：sk_xxx）
        - api_secret: API Secret（明文，仅返回一次）
    """
    # 生成 API Key（32 字节随机字符串）
    key_body = secrets.token_urlsafe(32)
    api_key = f"{API_KEY_PREFIX}{key_body}"

    # 生成 API Secret（48 字节随机字符串）
    api_secret = secrets.token_urlsafe(48)

    return api_key, api_secret


def hash_api_key(api_key: str) -> str:
    """
    对 API Key 进行哈希（用于存储和查询）

    Args:
        api_key: 原始 API Key

    Returns:
        str: 哈希后的 API Key
    """
    import hashlib
    return hashlib.sha256(api_key.encode()).hexdigest()


async def create_api_key(
    db: AsyncSession,
    app_id: int,
    name: Optional[str] = None,
    permissions: Optional[List[str]] = None,
    allowed_models: Optional[List[str]] = None,
    expires_days: Optional[int] = None,
) -> dict:
    """
    创建新的 API Key

    Args:
        db: 数据库会话
        app_id: 应用 ID
        name: API Key 名称（可选）
        permissions: 权限列表
        allowed_models: 允许使用的模型列表
        expires_days: 过期天数（可选）

    Returns:
        dict: 包含 API Key 信息的字典
        {
            "id": int,
            "api_key": str,  # 完整 API Key（仅返回一次）
            "api_secret": str,  # API Secret（仅返回一次）
            "key_prefix": str,
            "created_at": datetime,
            "expires_at": Optional[datetime],
        }
    """
    # 生成 API Key 和 Secret
    api_key, api_secret = generate_api_key()

    # 加密 API Secret
    encryption_service = get_encryption_service()
    encrypted_secret = encryption_service.encrypt(api_secret)

    # 哈希 API Key（用于存储）
    hashed_key = hash_api_key(api_key)

    # 计算过期时间
    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)

    # 创建数据库记录
    db_api_key = APIKey(
        app_id=app_id,
        key=hashed_key,
        key_prefix=api_key[:12],  # 保存前 12 个字符用于显示
        secret=encrypted_secret,
        permissions=permissions or [],
        allowed_models=allowed_models or [],
        expires_at=expires_at,
    )

    db.add(db_api_key)
    await db.commit()
    await db.refresh(db_api_key)

    logger.info(f"Created new API Key for application {app_id}")

    # 返回 API Key 信息（明文仅返回一次）
    return {
        "id": db_api_key.id,
        "api_key": api_key,
        "api_secret": api_secret,
        "key_prefix": db_api_key.key_prefix,
        "created_at": db_api_key.created_at,
        "expires_at": db_api_key.expires_at,
    }


async def verify_api_key(
    db: AsyncSession,
    api_key: str,
) -> Optional[APIKey]:
    """
    验证 API Key

    Args:
        db: 数据库会话
        api_key: 待验证的 API Key

    Returns:
        APIKey 对象或 None
    """
    # 哈希 API Key
    hashed_key = hash_api_key(api_key)

    # 查询数据库
    result = await db.execute(
        select(APIKey).where(
            APIKey.key == hashed_key,
            APIKey.is_active == True,
            APIKey.is_revoked == False,
        )
    )
    api_key_obj = result.scalar_one_or_none()

    if not api_key_obj:
        logger.warning(f"Invalid API Key: {api_key[:8]}...")
        return None

    # 检查过期时间
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
        logger.warning(f"API Key expired: {api_key_obj.key_prefix}")
        return None

    # 更新最后使用时间
    api_key_obj.last_used_at = datetime.utcnow()
    await db.commit()

    return api_key_obj


async def get_api_key_secret(
    db: AsyncSession,
    api_key_id: int,
) -> Optional[str]:
    """
    获取 API Secret（解密后）

    Args:
        db: 数据库会话
        api_key_id: API Key ID

    Returns:
        str: API Secret（明文）或 None
    """
    result = await db.execute(
        select(APIKey).where(APIKey.id == api_key_id)
    )
    api_key_obj = result.scalar_one_or_none()

    if not api_key_obj or not api_key_obj.secret:
        return None

    # 解密 Secret
    encryption_service = get_encryption_service()
    try:
        api_secret = encryption_service.decrypt(api_key_obj.secret)
        return api_secret
    except Exception as e:
        logger.error(f"Failed to decrypt API Secret: {e}")
        return None


async def revoke_api_key(
    db: AsyncSession,
    api_key_id: int,
) -> bool:
    """
    吊销 API Key

    Args:
        db: 数据库会话
        api_key_id: API Key ID

    Returns:
        bool: 是否成功吊销
    """
    await db.execute(
        update(APIKey)
        .where(APIKey.id == api_key_id)
        .values(is_revoked=True)
    )
    await db.commit()

    logger.info(f"Revoked API Key: {api_key_id}")
    return True


async def rotate_api_key(
    db: AsyncSession,
    api_key_id: int,
) -> Optional[dict]:
    """
    轮换 API Key

    Args:
        db: 数据库会话
        api_key_id: API Key ID

    Returns:
        dict: 新的 API Key 信息（如果成功）
    """
    # 获取现有 API Key
    result = await db.execute(
        select(APIKey).where(APIKey.id == api_key_id)
    )
    api_key_obj = result.scalar_one_or_none()

    if not api_key_obj:
        return None

    # 生成新的 API Key 和 Secret
    new_api_key, new_api_secret = generate_api_key()

    # 加密新的 Secret
    encryption_service = get_encryption_service()
    encrypted_secret = encryption_service.encrypt(new_api_secret)

    # 哈希新的 API Key
    new_hashed_key = hash_api_key(new_api_key)

    # 更新数据库
    api_key_obj.key = new_hashed_key
    api_key_obj.key_prefix = new_api_key[:12]
    api_key_obj.secret = encrypted_secret
    api_key_obj.updated_at = datetime.utcnow()

    await db.commit()

    logger.info(f"Rotated API Key: {api_key_id}")

    return {
        "id": api_key_obj.id,
        "api_key": new_api_key,
        "api_secret": new_api_secret,
        "key_prefix": api_key_obj.key_prefix,
    }


async def list_api_keys(
    db: AsyncSession,
    app_id: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> List[APIKey]:
    """
    列出 API Keys

    Args:
        db: 数据库会话
        app_id: 应用 ID（可选）
        is_active: 是否激活（可选）

    Returns:
        List[APIKey]: API Key 列表
    """
    query = select(APIKey)

    if app_id:
        query = query.where(APIKey.app_id == app_id)

    if is_active is not None:
        query = query.where(APIKey.is_active == is_active)

    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_api_key(
    db: AsyncSession,
    api_key_id: int,
) -> bool:
    """
    删除 API Key

    Args:
        db: 数据库会话
        api_key_id: API Key ID

    Returns:
        bool: 是否成功删除
    """
    await db.execute(
        delete(APIKey).where(APIKey.id == api_key_id)
    )
    await db.commit()

    logger.info(f"Deleted API Key: {api_key_id}")
    return True
