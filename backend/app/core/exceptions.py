"""
统一异常处理模块

提供统一的错误响应格式和异常处理器
"""
from typing import Any, Optional, Dict
from fastapi import HTTPException, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field


# ============= 错误响应模型 =============

class ErrorResponse(BaseModel):
    """统一错误响应模型"""
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(None, description="详细错误信息")
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数验证失败",
                "detail": "field 'name' is required",
                "data": None
            }
        }


# ============= 预定义错误代码 =============

class ErrorCode:
    """错误代码常量"""
    # 通用错误 (1000-1999)
    SUCCESS = "SUCCESS"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # 认证相关 (2000-2999)
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    API_KEY_INVALID = "API_KEY_INVALID"
    API_KEY_INACTIVE = "API_KEY_INACTIVE"

    # 资源相关 (3000-3999)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"

    # 业务相关 (4000-4999)
    INVALID_OPERATION = "INVALID_OPERATION"
    INVALID_STATE = "INVALID_STATE"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"

    # MCP 连接器 (5000-5999)
    MCP_CONNECTOR_ERROR = "MCP_CONNECTOR_ERROR"
    MCP_CONNECTION_FAILED = "MCP_CONNECTION_FAILED"
    MCP_EXECUTION_FAILED = "MCP_EXECUTION_FAILED"

    # Skills 市场 (6000-6999)
    SKILL_ERROR = "SKILL_ERROR"
    SKILL_NOT_FOUND = "SKILL_NOT_FOUND"
    SKILL_EXECUTION_FAILED = "SKILL_EXECUTION_FAILED"

    # 智能体工厂 (7000-7999)
    AGENT_ERROR = "AGENT_ERROR"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_EXECUTION_FAILED = "AGENT_EXECUTION_FAILED"

    # 知识工厂 (8000-8999)
    KNOWLEDGE_ERROR = "KNOWLEDGE_ERROR"
    KNOWLEDGE_NOT_FOUND = "KNOWLEDGE_NOT_FOUND"
    VECTOR_SEARCH_ERROR = "VECTOR_SEARCH_ERROR"

    # 模型工厂 (9000-9999)
    MODEL_ERROR = "MODEL_ERROR"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    INFERENCE_ERROR = "INFERENCE_ERROR"


# ============= 自定义异常类 =============

class AppException(HTTPException):
    """应用基础异常类"""

    def __init__(
        self,
        code: str = ErrorCode.INTERNAL_ERROR,
        message: str = "服务器内部错误",
        detail: Optional[str] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status_code,
            detail=detail,
        )
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
            "data": self.data,
        }


class ValidationError(AppException):
    """验证错误"""

    def __init__(self, detail: Optional[str] = None, data: Optional[Dict] = None):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message="请求参数验证失败",
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            data=data,
        )


class NotFoundError(AppException):
    """资源未找到错误"""

    def __init__(
        self,
        resource: str = "资源",
        detail: Optional[str] = None,
    ):
        super().__init__(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message=f"{resource}不存在",
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class UnauthorizedError(AppException):
    """未授权错误"""

    def __init__(
        self,
        message: str = "未授权，请先登录",
        detail: Optional[str] = None,
    ):
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenError(AppException):
    """禁止访问错误"""

    def __init__(
        self,
        message: str = "无权访问该资源",
        detail: Optional[str] = None,
    ):
        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message,
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ConflictError(AppException):
    """资源冲突错误"""

    def __init__(
        self,
        message: str = "资源已存在",
        detail: Optional[str] = None,
    ):
        super().__init__(
            code=ErrorCode.CONFLICT,
            message=message,
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
        )


class BusinessException(AppException):
    """业务异常"""

    def __init__(
        self,
        message: str = "业务处理失败",
        detail: Optional[str] = None,
        code: str = ErrorCode.INVALID_OPERATION,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        super().__init__(
            code=code,
            message=message,
            detail=detail,
            status_code=status_code,
        )


class PaymentError(BusinessException):
    """支付异常"""

    def __init__(
        self,
        message: str = "支付处理失败",
        detail: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            detail=detail,
            code=ErrorCode.INVALID_OPERATION,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class TooManyRequestsError(AppException):
    """请求过多错误"""

    def __init__(
        self,
        detail: Optional[str] = None,
    ):
        super().__init__(
            code=ErrorCode.TOO_MANY_REQUESTS,
            message="请求过于频繁，请稍后重试",
            detail=detail,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class ServiceUnavailableError(AppException):
    """服务不可用错误"""

    def __init__(
        self,
        message: str = "服务暂时不可用",
        detail: Optional[str] = None,
    ):
        super().__init__(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=message,
            detail=detail,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# ============= 异常处理器 =============

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """AppException 异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers={"X-Error-Code": exc.code},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTPException 异常处理器"""
    # 将标准 HTTPException 转换为统一格式
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": getattr(exc, "code", ErrorCode.INTERNAL_ERROR),
            "message": _get_message_from_status(exc.status_code, exc.detail),
            "detail": exc.detail,
            "data": None,
        },
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """请求验证异常处理器"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error.get("loc", [])),
            "message": error.get("msg", ""),
            "type": error.get("type", ""),
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": ErrorCode.VALIDATION_ERROR,
            "message": "请求参数格式错误",
            "detail": "参数验证失败，请检查请求数据",
            "data": {"errors": errors},
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器（兜底）"""
    # 这里可以添加日志记录
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": ErrorCode.INTERNAL_ERROR,
            "message": "服务器内部错误，请稍后重试",
            "detail": str(exc) if hasattr(exc, "__str__") else "未知错误",
            "data": None,
        },
    )


# ============= 辅助函数 =============

def _get_message_from_status(status_code: int, detail: Optional[str] = None) -> str:
    """根据状态码获取默认消息"""
    messages = {
        status.HTTP_400_BAD_REQUEST: "请求参数错误",
        status.HTTP_401_UNAUTHORIZED: "未授权，请先登录",
        status.HTTP_403_FORBIDDEN: "无权访问该资源",
        status.HTTP_404_NOT_FOUND: "资源不存在",
        status.HTTP_409_CONFLICT: "资源冲突",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "请求参数格式错误",
        status.HTTP_429_TOO_MANY_REQUESTS: "请求过于频繁",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "服务器内部错误",
        status.HTTP_502_BAD_GATEWAY: "网关错误",
        status.HTTP_503_SERVICE_UNAVAILABLE: "服务暂时不可用",
        status.HTTP_504_GATEWAY_TIMEOUT: "网关超时",
    }
    return messages.get(status_code, detail or "发生错误")


def create_error_response(
    code: str,
    message: str,
    status_code: int,
    detail: Optional[str] = None,
    data: Optional[Dict] = None,
) -> Dict[str, Any]:
    """创建错误响应字典"""
    return {
        "code": code,
        "message": message,
        "detail": detail,
        "data": data,
    }
