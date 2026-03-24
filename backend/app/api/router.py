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
from .developer import router as developer_router  # Phase 4 开发者门户
from .partners import router as partners_router  # Phase 4 合作伙伴计划
from .solutions import router as solutions_router  # Phase 4 行业解决方案
from .alliance import router as alliance_router  # Phase 4 生态联盟
from .billing import router as billing_router  # Phase 5 计费系统
from .quota import router as quota_router  # Phase 5.2 配额管理
from .usage_stats import router as usage_stats_router  # Phase 5.3 使用量统计
from .payment import router as payment_router  # Phase 5.4 支付渠道
from .billing_invoice import router as billing_invoice_router  # Phase 5.5 账单和发票
from .alert import router as alert_router  # Phase 5.6 告警中心

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
api_router.include_router(developer_router, prefix="/developer", tags=["开发者门户"])  # Phase 4 开发者门户
api_router.include_router(partners_router, prefix="/partners", tags=["合作伙伴计划"])  # Phase 4 合作伙伴计划
api_router.include_router(solutions_router, prefix="/solutions", tags=["行业解决方案"])  # Phase 4 行业解决方案
api_router.include_router(alliance_router, prefix="/alliance", tags=["生态联盟"])  # Phase 4 生态联盟
api_router.include_router(billing_router, prefix="/billing", tags=["计费系统"])  # Phase 5 计费系统
api_router.include_router(quota_router, prefix="/quota", tags=["配额管理"])  # Phase 5.2 配额管理
api_router.include_router(usage_stats_router, prefix="/stats", tags=["使用量统计"])  # Phase 5.3 使用量统计
api_router.include_router(payment_router, prefix="/payment", tags=["支付渠道"])  # Phase 5.4 支付渠道
api_router.include_router(billing_invoice_router, prefix="/bills", tags=["账单和发票"])  # Phase 5.5 账单和发票
api_router.include_router(alert_router, prefix="/alert", tags=["告警中心"])  # Phase 5.6 告警中心
