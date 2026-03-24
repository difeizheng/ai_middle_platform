"""
Pydantic Schemas - 输入验证和响应模型

提供统一的请求验证和响应格式
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import re


# ============= 通用验证器 =============

def validate_string_length(value: str, min_len: int = 0, max_len: int = 200) -> str:
    """验证字符串长度"""
    if not value or len(value) < min_len:
        raise ValueError(f"字符串长度不能少于 {min_len} 个字符")
    if len(value) > max_len:
        raise ValueError(f"字符串长度不能超过 {max_len} 个字符")
    return value


def validate_name(value: str) -> str:
    """验证名称格式"""
    if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9_-]+$', value):
        raise ValueError("名称只能包含中文、英文、数字、下划线和连字符")
    return validate_string_length(value, min_len=1, max_len=100)


def validate_description(value: Optional[str]) -> Optional[str]:
    """验证描述格式"""
    if value is None:
        return value
    return validate_string_length(value, max_len=1000)


# ============= 通用响应模型 =============

class SuccessResponse(BaseModel):
    """成功响应基础模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    success: bool = True
    data: List[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0


# ============= 用户相关 Schemas =============

class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("用户名只能包含英文、数字和下划线")
        return v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("邮箱地址格式不正确")
        return v


class UserCreate(UserBase):
    """用户创建请求"""
    password: str = Field(..., min_length=8, max_length=100, description="密码")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("密码长度不能少于 8 个字符")
        if not re.search(r'[A-Z]', v):
            raise ValueError("密码必须包含至少一个大写字母")
        if not re.search(r'[a-z]', v):
            raise ValueError("密码必须包含至少一个小写字母")
        if not re.search(r'\d', v):
            raise ValueError("密码必须包含至少一个数字")
        return v


class UserUpdate(BaseModel):
    """用户更新请求"""
    email: Optional[str] = Field(None, description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    department: Optional[str] = Field(None, max_length=100, description="部门")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is None:
            return v
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("邮箱地址格式不正确")
        return v


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    department: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============= 应用相关 Schemas =============

class ApplicationBase(BaseModel):
    """应用基础模型"""
    name: str = Field(..., min_length=1, max_length=200, description="应用名称")
    description: Optional[str] = Field(None, max_length=1000, description="应用描述")
    app_type: str = Field(default="web", description="应用类型")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_name(v)

    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        return validate_description(v)

    @field_validator('app_type')
    @classmethod
    def validate_app_type(cls, v):
        allowed_types = ['web', 'mobile', 'api', 'internal', 'other']
        if v not in allowed_types:
            raise ValueError(f"应用类型必须是：{', '.join(allowed_types)}")
        return v


class ApplicationCreate(ApplicationBase):
    """应用创建请求"""
    pass


class ApplicationUpdate(BaseModel):
    """应用更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="应用名称")
    description: Optional[str] = Field(None, max_length=1000, description="应用描述")
    is_active: Optional[bool] = Field(None, description="是否激活")
    quota_config: Optional[Dict[str, Any]] = Field(None, description="配额配置")
    rate_limit: Optional[Dict[str, Any]] = Field(None, description="限流配置")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is None:
            return v
        return validate_name(v)


class ApplicationResponse(BaseModel):
    """应用响应"""
    id: int
    name: str
    description: Optional[str]
    app_type: str
    is_active: bool
    total_calls: int
    total_tokens: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============= API Key 相关 Schemas =============

class APIKeyCreate(BaseModel):
    """API Key 创建请求"""
    expires_days: Optional[int] = Field(None, ge=1, le=3650, description="过期天数")
    permissions: Optional[List[str]] = Field(default_factory=list, description="权限列表")
    allowed_models: Optional[List[str]] = Field(default_factory=list, description="允许的模型")
    allowed_ips: Optional[List[str]] = Field(default_factory=list, description="允许的 IP")


class APIKeyResponse(BaseModel):
    """API Key 响应（不包含明文）"""
    id: int
    key_prefix: str
    is_active: bool
    is_revoked: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    """API Key 创建响应（仅返回一次明文）"""
    id: int
    api_key: str
    api_secret: str
    key_prefix: str
    expires_at: Optional[datetime]
    message: str


# ============= 模型相关 Schemas =============

class ModelBase(BaseModel):
    """模型基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="模型名称")
    provider: str = Field(..., min_length=1, max_length=50, description="提供商")
    model_type: str = Field(..., description="模型类型")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_name(v)

    @field_validator('model_type')
    @classmethod
    def validate_model_type(cls, v):
        allowed_types = ['llm', 'embedding', 'rerank', 'tts', 'stt', 'image']
        if v not in allowed_types:
            raise ValueError(f"模型类型必须是：{', '.join(allowed_types)}")
        return v


class ModelCreate(ModelBase):
    """模型创建请求"""
    config: Dict[str, Any] = Field(default_factory=dict, description="模型配置")
    api_key: str = Field(..., description="API Key")


class ModelUpdate(BaseModel):
    """模型更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class ModelResponse(BaseModel):
    """模型响应"""
    id: int
    name: str
    provider: str
    model_type: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============= 知识库相关 Schemas =============

class KnowledgeBase(BaseModel):
    """知识库基础模型"""
    name: str = Field(..., min_length=1, max_length=200, description="知识库名称")
    description: Optional[str] = Field(None, max_length=1000, description="描述")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_name(v)


class KnowledgeCreate(KnowledgeBase):
    """知识库创建请求"""
    pass


class KnowledgeUpdate(BaseModel):
    """知识库更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class KnowledgeResponse(BaseModel):
    """知识库响应"""
    id: int
    name: str
    description: Optional[str]
    document_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentUpload(BaseModel):
    """文档上传请求"""
    name: str = Field(..., min_length=1, max_length=200, description="文档名称")
    knowledge_base_id: int = Field(..., description="知识库 ID")


# ============= 智能体相关 Schemas =============

class AgentBase(BaseModel):
    """智能体基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="智能体名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    role: str = Field(default="executor", description="角色")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_name(v)

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ['planner', 'executor', 'reviewer', 'summarizer', 'custom']
        if v not in allowed_roles:
            raise ValueError(f"角色必须是：{', '.join(allowed_roles)}")
        return v


class AgentCreate(AgentBase):
    """智能体创建请求"""
    model_id: Optional[int] = Field(None, description="绑定的模型 ID")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置")
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="工具列表")


class AgentUpdate(BaseModel):
    """智能体更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    role: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None


class AgentExecuteRequest(BaseModel):
    """智能体执行请求"""
    task: str = Field(..., min_length=1, max_length=5000, description="任务描述")
    session_id: Optional[str] = Field(None, description="会话 ID")
    stream: bool = Field(default=False, description="是否流式输出")
    max_steps: int = Field(default=10, ge=1, le=50, description="最大步骤数")


class AgentResponse(BaseModel):
    """智能体响应"""
    id: int
    name: str
    description: Optional[str]
    role: str
    model_id: Optional[int]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============= MCP 连接器相关 Schemas =============

class MCPConnectorBase(BaseModel):
    """MCP 连接器基础模型"""
    name: str = Field(..., min_length=1, max_length=200, description="连接器名称")
    connector_type: str = Field(..., description="连接器类型")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_name(v)


class MCPConnectorCreate(MCPConnectorBase):
    """MCP 连接器创建请求"""
    host: Optional[str] = Field(None, description="主机地址")
    port: Optional[int] = Field(None, ge=1, le=65535, description="端口")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置")

    @model_validator(mode='after')
    def validate_connection(self):
        # 如果指定了 host，port 也必须指定
        if self.host and not self.port:
            raise ValueError("指定主机地址时必须指定端口")
        return self


class MCPConnectorUpdate(BaseModel):
    """MCP 连接器更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class MCPExecuteRequest(BaseModel):
    """MCP 连接器执行请求"""
    action: str = Field(..., min_length=1, description="操作名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="操作参数")


# ============= Skills 相关 Schemas =============

class SkillExecuteRequest(BaseModel):
    """Skill 执行请求"""
    data: Any = Field(..., description="输入数据")
    operation: str = Field(..., min_length=1, description="操作类型")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置")


# ============= 推理相关 Schemas =============

class Message(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="角色")
    content: str = Field(..., min_length=1, max_length=50000, description="内容")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ['system', 'user', 'assistant']
        if v not in allowed_roles:
            raise ValueError(f"角色必须是：{', '.join(allowed_roles)}")
        return v


class ChatCompletionRequest(BaseModel):
    """聊天补全请求"""
    model: Optional[str] = Field(None, description="模型名称")
    messages: List[Message] = Field(..., min_length=1, description="消息列表")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    max_tokens: Optional[int] = Field(None, ge=1, le=10000, description="最大 token 数")
    stream: bool = Field(default=False, description="是否流式输出")


class InferenceRequest(BaseModel):
    """推理请求"""
    prompt: str = Field(..., min_length=1, max_length=50000, description="提示词")
    model: Optional[str] = Field(None, description="模型名称")
    max_tokens: Optional[int] = Field(None, ge=1, le=10000)


# ============= 监控相关 Schemas =============

class TimeRangeQuery(BaseModel):
    """时间范围查询"""
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    period: Optional[str] = Field(default="1h", description="时间粒度")

    @field_validator('period')
    @classmethod
    def validate_period(cls, v):
        allowed_periods = ['1m', '5m', '15m', '30m', '1h', '6h', '12h', '1d']
        if v not in allowed_periods:
            raise ValueError(f"时间粒度必须是：{', '.join(allowed_periods)}")
        return v


class AlertRuleCreate(BaseModel):
    """告警规则创建"""
    name: str = Field(..., min_length=1, max_length=100, description="规则名称")
    metric_name: str = Field(..., description="指标名称")
    threshold: float = Field(..., description="阈值")
    condition: str = Field(..., description="条件")
    notification_channels: List[str] = Field(default_factory=list, description="通知渠道")


# ============= 日志查询 Schemas =============

class LogQuery(BaseModel):
    """日志查询请求"""
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    level: Optional[str] = Field(None, description="日志级别")
    keyword: Optional[str] = Field(None, max_length=200, description="关键词")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
