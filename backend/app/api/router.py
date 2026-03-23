"""
API 路由
"""
from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router
from .models import router as models_router
from .knowledge import router as knowledge_router
from .inference import router as inference_router
from .applications import router as applications_router
from .logs import router as logs_router
from .scenarios import router as scenarios_router
from .agents import router as agents_router  # Phase 2 新增
from .mcp import router as mcp_router  # Phase 2 MCP 连接器
from .skills import router as skills_router  # Phase 2.3 Skills 市场
from .monitor import router as monitor_router  # Phase 2.4 运营监控

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
api_router.include_router(scenarios_router, prefix="/scenarios", tags=["试点场景"])
api_router.include_router(agents_router, prefix="/agents", tags=["智能体工厂"])  # Phase 2 新增
api_router.include_router(mcp_router, prefix="/mcp", tags=["MCP 连接器"])  # Phase 2 MCP 连接器
api_router.include_router(skills_router, prefix="/skills", tags=["Skills 市场"])  # Phase 2.3 Skills 市场
api_router.include_router(monitor_router, prefix="/monitor", tags=["运营监控"])  # Phase 2.4 运营监控
