"""
API 路由模块
"""
from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router
from .models import router as models_router
from .knowledge import router as knowledge_router
from .inference import router as inference_router
from .applications import router as applications_router
from .logs import router as logs_router

# 创建主路由
api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(users_router, prefix="/users", tags=["用户管理"])
api_router.include_router(models_router, prefix="/models", tags=["模型管理"])
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["知识管理"])
api_router.include_router(inference_router, prefix="/inference", tags=["模型推理"])
api_router.include_router(applications_router, prefix="/applications", tags=["应用管理"])
api_router.include_router(logs_router, prefix="/logs", tags=["日志管理"])
