"""
API 日志和审计日志模型
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON, BigInteger, Index, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base


class APILog(Base):
    """
    API 调用日志表
    """
    __tablename__ = "api_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 请求信息
    trace_id = Column(String(64), index=True)  # 全链路追踪 ID
    request_id = Column(String(64), unique=True)  # 请求 ID

    # 用户信息
    user_id = Column(Integer, ForeignKey("users.id"))
    app_id = Column(Integer, ForeignKey("applications.id"))
    api_key = Column(String(100), index=True)

    # 请求详情
    method = Column(String(10))  # GET, POST, etc.
    path = Column(String(500))  # 请求路径
    endpoint = Column(String(200))  # API 端点名称

    # 请求内容
    request_headers = Column(JSON)
    request_body = Column(JSON)
    query_params = Column(JSON)

    # 响应信息
    response_status = Column(Integer)  # HTTP 状态码
    response_headers = Column(JSON)
    response_body = Column(JSON)

    # 性能指标
    latency_ms = Column(Float)  # 延迟（毫秒）
    tokens_used = Column(Integer, default=0)  # 使用的 token 数
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)

    # 模型信息
    model_name = Column(String(100))  # 使用的模型

    # 状态
    is_success = Column(Boolean, default=True)
    error_message = Column(Text)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 索引
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_endpoint_created', 'endpoint', 'created_at'),
    )

    def __repr__(self):
        return f"<APILog {self.request_id}>"


class AuditLog(Base):
    """
    审计日志表 - 记录用户操作
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 操作信息
    trace_id = Column(String(64))
    action = Column(String(50), nullable=False, index=True)  # 操作类型：login, create, update, delete, query

    # 用户信息
    user_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String(50))

    # 资源信息
    resource_type = Column(String(50))  # user, model, knowledge, application
    resource_id = Column(Integer)
    resource_name = Column(String(200))

    # 操作详情
    operation = Column(String(20))  # create, update, delete, view
    old_value = Column(JSON)  # 修改前的值
    new_value = Column(JSON)  # 修改后的值

    # 环境信息
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    request_path = Column(String(500))

    # 结果
    result = Column(String(20))  # success, failure, denied
    error_message = Column(Text)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<AuditLog {self.id}>"
