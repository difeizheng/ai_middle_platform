"""
FastAPI 应用主入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from .core.config import settings
from .core.database import init_db, close_db
from .core.logger import setup_logging, get_logger
from .api.router import api_router
from .services.mcp.registry import auto_register_types
from .services.skills import auto_register_builtin_skills

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时执行
    logger.info("AI 中台系统启动中...")
    setup_logging()
    await init_db()
    logger.info("数据库初始化完成")

    # 注册 MCP 连接器类型
    auto_register_types()
    logger.info("MCP 连接器类型注册完成")

    # 注册内置 Skills
    auto_register_builtin_skills()
    logger.info("Skills 市场初始化完成")

    yield

    # 关闭时执行
    logger.info("AI 中台系统关闭中...")
    await close_db()


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="企业级 AI 中台系统 - 模型工厂 | 知识工厂 | 智能体工厂 | Skills 市场",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    请求日志中间件
    """
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000  # 毫秒

    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.2f}ms"
    )

    return response


@app.middleware("http")
async def add_headers(request: Request, call_next):
    """
    添加通用响应头
    """
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "")
    response.headers["X-Process-Time"] = str(time.time())
    return response


# 注册路由
app.include_router(api_router, prefix="/api/v1")


# 健康检查
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": time.time(),
    }


# 根路径
@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "企业级 AI 中台系统",
        "docs": "/docs",
    }


# 异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "内部错误，请联系管理员",
        },
    )
