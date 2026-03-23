"""
MCP 连接器 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.api.middleware import rate_limit
from app.services.mcp.base import ConnectorConfig, ConnectorType, ConnectorStatus
from app.services.mcp.registry import get_registry, ConnectorRegistry

router = APIRouter()


# ========== 连接器类型管理 ==========

@router.get("/types")
async def list_connector_types(
    current_user: User = Depends(get_current_user),
):
    """获取支持的连接器类型列表"""
    registry = get_registry()
    types = registry.list_connector_types()

    # 返回每种类型的描述
    type_info = {
        "mysql": {"name": "MySQL", "description": "MySQL 数据库连接"},
        "postgresql": {"name": "PostgreSQL", "description": "PostgreSQL 数据库连接"},
        "http": {"name": "HTTP", "description": "HTTP/REST API 连接"},
        "redis": {"name": "Redis", "description": "Redis 缓存服务连接"},
        "file": {"name": "File", "description": "本地/网络文件系统连接"},
        "kafka": {"name": "Kafka", "description": "Kafka 消息队列连接"},
        "mongodb": {"name": "MongoDB", "description": "MongoDB 数据库连接"},
    }

    return {
        "success": True,
        "data": [
            {
                "type": t,
                "info": type_info.get(t, {"name": t, "description": "未知类型"}),
            }
            for t in types
        ],
    }


# ========== 连接器实例管理 ==========

@router.get("/connectors")
async def list_connectors(
    current_user: User = Depends(get_current_user),
):
    """获取所有连接器实例"""
    registry = get_registry()
    connectors = registry.list_connectors()

    return {
        "success": True,
        "data": connectors,
    }


@router.post("/connectors")
async def create_connector(
    name: str = Body(..., description="连接器名称"),
    connector_type: str = Body(..., description="连接器类型"),
    host: str = Body(None, description="主机地址"),
    port: int = Body(None, description="端口"),
    username: str = Body(None, description="用户名"),
    password: str = Body(None, description="密码"),
    database: str = Body(None, description="数据库名"),
    extra: Dict[str, Any] = Body(default_factory=dict, description="额外配置"),
    current_user: User = Depends(get_current_user),
):
    """创建连接器实例"""
    registry = get_registry()

    # 检查类型是否支持
    if connector_type not in registry.list_connector_types():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的连接器类型：{connector_type}",
        )

    # 创建配置
    config = ConnectorConfig(
        name=name,
        connector_type=ConnectorType(connector_type),
        host=host,
        port=port,
        username=username,
        password=password,
        database=database,
        extra=extra,
    )

    # 生成实例 ID
    import uuid
    instance_id = str(uuid.uuid4())

    # 创建连接器
    connector = registry.create_connector(instance_id, connector_type, config)

    if not connector:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建连接器失败",
        )

    return {
        "success": True,
        "data": {
            "instance_id": instance_id,
            "name": name,
            "type": connector_type,
            "config": config.to_dict(),
        },
    }


@router.get("/connectors/{instance_id}")
async def get_connector(
    instance_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取连接器详情"""
    registry = get_registry()
    connector = registry.get_connector(instance_id)

    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="连接器不存在",
        )

    return {
        "success": True,
        "data": connector.get_status(),
    }


@router.delete("/connectors/{instance_id}")
async def delete_connector(
    instance_id: str,
    current_user: User = Depends(get_current_user),
):
    """删除连接器"""
    registry = get_registry()

    connector = registry.get_connector(instance_id)
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="连接器不存在",
        )

    # 先断开连接
    await connector.disconnect()

    # 移除连接器
    registry.remove_connector(instance_id)

    return {
        "success": True,
        "message": "连接器已删除",
    }


# ========== 连接器操作 ==========

@router.post("/connectors/{instance_id}/connect")
async def connect_connector(
    instance_id: str,
    current_user: User = Depends(get_current_user),
):
    """连接连接器"""
    registry = get_registry()
    connector = registry.get_connector(instance_id)

    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="连接器不存在",
        )

    success = await connector.connect()

    return {
        "success": True,
        "connected": success,
        "status": connector.status.value,
    }


@router.post("/connectors/{instance_id}/disconnect")
async def disconnect_connector(
    instance_id: str,
    current_user: User = Depends(get_current_user),
):
    """断开连接器"""
    registry = get_registry()
    connector = registry.get_connector(instance_id)

    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="连接器不存在",
        )

    success = await connector.disconnect()

    return {
        "success": True,
        "disconnected": success,
        "status": connector.status.value,
    }


@router.post("/connectors/{instance_id}/health")
async def health_check_connector(
    instance_id: str,
    current_user: User = Depends(get_current_user),
):
    """健康检查"""
    registry = get_registry()
    connector = registry.get_connector(instance_id)

    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="连接器不存在",
        )

    healthy = await connector.health_check()

    return {
        "success": True,
        "healthy": healthy,
        "status": connector.status.value,
    }


@router.post("/connectors/{instance_id}/execute")
@rate_limit(max_requests=100, window=60)
async def execute_action(
    instance_id: str,
    action: str = Body(..., description="操作名称"),
    params: Dict[str, Any] = Body(default_factory=dict, description="操作参数"),
    current_user: User = Depends(get_current_user),
):
    """执行操作"""
    registry = get_registry()
    connector = registry.get_connector(instance_id)

    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="连接器不存在",
        )

    if connector.status != ConnectorStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"连接器未激活：{connector.status.value}",
        )

    try:
        result = await connector.execute(action, params)

        return {
            "success": True,
            "data": result,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行失败：{str(e)}",
        )


@router.get("/connectors/{instance_id}/actions")
async def list_actions(
    instance_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取连接器支持的操作列表"""
    registry = get_registry()
    connector = registry.get_connector(instance_id)

    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="连接器不存在",
        )

    if hasattr(connector, "get_actions"):
        actions = connector.get_actions()
    else:
        actions = []

    return {
        "success": True,
        "data": actions,
    }


# ========== 批量操作 ==========

@router.post("/connectors/connect-all")
async def connect_all_connectors(
    current_user: User = Depends(get_current_user),
):
    """连接所有连接器"""
    registry = get_registry()
    results = await registry.connect_all()

    return {
        "success": True,
        "data": results,
    }


@router.post("/connectors/disconnect-all")
async def disconnect_all_connectors(
    current_user: User = Depends(get_current_user),
):
    """断开所有连接器"""
    registry = get_registry()
    results = await registry.disconnect_all()

    return {
        "success": True,
        "data": results,
    }


@router.get("/connectors/health-all")
async def health_check_all_connectors(
    current_user: User = Depends(get_current_user),
):
    """检查所有连接器健康状态"""
    registry = get_registry()
    results = await registry.health_check_all()

    return {
        "success": True,
        "data": results,
    }


@router.get("/stats")
async def get_registry_stats(
    current_user: User = Depends(get_current_user),
):
    """获取注册表统计信息"""
    registry = get_registry()
    stats = registry.get_stats()

    return {
        "success": True,
        "data": stats,
    }
