"""
HTTP 连接器
"""
from typing import Any, Dict, List, Optional
import aiohttp

from .base import MCPConnector, ConnectorConfig, ConnectorStatus, ActionDefinition

from ...core.logger import get_logger

logger = get_logger(__name__)


class HTTPConnector(MCPConnector):
    """
    HTTP 连接器

    支持的操作:
    - request: 发送 HTTP 请求
    - get: 发送 GET 请求
    - post: 发送 POST 请求
    - put: 发送 PUT 请求
    - delete: 发送 DELETE 请求
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._actions = self._register_actions()

    def _register_actions(self) -> List[ActionDefinition]:
        """注册支持的操作"""
        return [
            ActionDefinition(
                name="request",
                description="发送 HTTP 请求",
                params_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "请求 URL"},
                        "method": {"type": "string", "description": "请求方法"},
                        "headers": {"type": "object", "description": "请求头"},
                        "body": {"type": "object", "description": "请求体"},
                        "timeout": {"type": "number", "description": "超时时间"},
                    },
                    "required": ["url"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "status_code": {"type": "integer"},
                        "headers": {"type": "object"},
                        "body": {"type": ["object", "string"]},
                    },
                },
            ),
            ActionDefinition(
                name="get",
                description="发送 GET 请求",
                params_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "请求 URL"},
                        "params": {"type": "object", "description": "查询参数"},
                        "headers": {"type": "object", "description": "请求头"},
                    },
                    "required": ["url"],
                },
                response_schema={
                    "type": ["object", "array", "string"],
                    "description": "响应内容",
                },
            ),
            ActionDefinition(
                name="post",
                description="发送 POST 请求",
                params_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "请求 URL"},
                        "body": {"type": "object", "description": "请求体"},
                        "headers": {"type": "object", "description": "请求头"},
                    },
                    "required": ["url", "body"],
                },
                response_schema={
                    "type": ["object", "array", "string"],
                    "description": "响应内容",
                },
            ),
        ]

    async def connect(self) -> bool:
        """建立 HTTP 连接"""
        try:
            self.status = ConnectorStatus.CONNECTING

            # 创建 HTTP Session
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)

            self.status = ConnectorStatus.ACTIVE
            logger.info("HTTP connector connected")
            return True

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            logger.error(f"HTTP connect failed: {e}")
            return False

    async def disconnect(self) -> bool:
        """断开 HTTP 连接"""
        try:
            self.status = ConnectorStatus.DISCONNECTING

            if self._session:
                await self._session.close()
                self._session = None

            self.status = ConnectorStatus.INACTIVE
            logger.info("HTTP connector disconnected")
            return True

        except Exception as e:
            logger.error(f"HTTP disconnect error: {e}")
            return False

    async def execute(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Any:
        """执行操作"""
        self._update_last_used()

        if action == "request":
            return await self._request(
                params.get("url"),
                params.get("method", "GET"),
                params.get("headers"),
                params.get("body"),
                params.get("timeout"),
            )
        elif action == "get":
            return await self._get(
                params.get("url"),
                params.get("params"),
                params.get("headers"),
            )
        elif action == "post":
            return await self._post(
                params.get("url"),
                params.get("body"),
                params.get("headers"),
            )
        else:
            raise ValueError(f"Unknown action: {action}")

    async def _request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        body: Optional[Dict] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        if not self._session:
            raise RuntimeError("Connector not connected")

        request_kwargs = {
            "method": method.upper(),
            "url": url,
            "headers": headers,
        }

        if body:
            request_kwargs["json"] = body

        if timeout:
            request_kwargs["timeout"] = aiohttp.ClientTimeout(total=timeout)

        async with self._session.request(**request_kwargs) as response:
            content = await response.text()
            try:
                import json
                body_data = json.loads(content)
            except json.JSONDecodeError:
                body_data = content

            return {
                "status_code": response.status,
                "headers": dict(response.headers),
                "body": body_data,
            }

    async def _get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> Any:
        """发送 GET 请求"""
        if params:
            from urllib.parse import urlencode
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(params)}"

        result = await self._request(url, "GET", headers)
        return result.get("body")

    async def _post(
        self,
        url: str,
        body: Dict[str, Any],
        headers: Optional[Dict] = None,
    ) -> Any:
        """发送 POST 请求"""
        result = await self._request(url, "POST", headers, body)
        return result.get("body")

    async def health_check(self) -> bool:
        """健康检查（通过访问配置的 host）"""
        try:
            if not self._session:
                return False

            if self.config.host:
                url = f"http://{self.config.host}:{self.config.port}/"
                result = await self._get(url)
                return result is not None

            return True

        except Exception as e:
            logger.error(f"HTTP health check failed: {e}")
            return False

    def get_actions(self) -> List[Dict]:
        """获取支持的操作列表"""
        return [action.to_dict() for action in self._actions]
