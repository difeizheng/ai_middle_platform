"""
文件连接器
"""
from typing import Any, Dict, List, Optional
import os
import aiofiles
import aiofiles.os
from pathlib import Path

from .base import MCPConnector, ConnectorConfig, ConnectorStatus, ActionDefinition

from ...core.logger import get_logger

logger = get_logger(__name__)


class FileConnector(MCPConnector):
    """
    文件连接器

    支持的操作:
    - read: 读取文件
    - write: 写入文件
    - append: 追加文件
    - delete: 删除文件
    - exists: 检查文件是否存在
    - list_dir: 列出目录内容
    - create_dir: 创建目录
    - get_file_info: 获取文件信息
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.base_path = Path(config.extra.get("base_path", "/"))
        self._actions = self._register_actions()

    def _register_actions(self) -> List[ActionDefinition]:
        """注册支持的操作"""
        return [
            ActionDefinition(
                name="read",
                description="读取文件内容",
                params_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                    },
                    "required": ["path"],
                },
                response_schema={"type": "string"},
            ),
            ActionDefinition(
                name="write",
                description="写入文件",
                params_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "content": {"type": "string", "description": "文件内容"},
                        "mode": {"type": "string", "description": "写入模式", "enum": ["w", "wb"]},
                    },
                    "required": ["path", "content"],
                },
                response_schema={"type": "boolean"},
            ),
            ActionDefinition(
                name="delete",
                description="删除文件",
                params_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                    },
                    "required": ["path"],
                },
                response_schema={"type": "boolean"},
            ),
            ActionDefinition(
                name="list_dir",
                description="列出目录内容",
                params_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "目录路径"},
                    },
                    "required": ["path"],
                },
                response_schema={
                    "type": "array",
                    "items": {"type": "string"},
                },
            ),
            ActionDefinition(
                name="create_dir",
                description="创建目录",
                params_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "目录路径"},
                        "parents": {"type": "boolean", "description": "是否创建父目录"},
                    },
                    "required": ["path"],
                },
                response_schema={"type": "boolean"},
            ),
            ActionDefinition(
                name="get_file_info",
                description="获取文件信息",
                params_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                    },
                    "required": ["path"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "size": {"type": "number"},
                        "modified": {"type": "string"},
                        "created": {"type": "string"},
                        "is_file": {"type": "boolean"},
                        "is_dir": {"type": "boolean"},
                    },
                },
            ),
        ]

    async def connect(self) -> bool:
        """建立文件连接器（检查基础路径）"""
        try:
            self.status = ConnectorStatus.CONNECTING

            # 检查基础路径是否存在
            if not self.base_path.exists():
                # 尝试创建
                os.makedirs(self.base_path, exist_ok=True)

            self.status = ConnectorStatus.ACTIVE
            logger.info(f"File connector connected: base_path={self.base_path}")
            return True

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            logger.error(f"File connect failed: {e}")
            return False

    async def disconnect(self) -> bool:
        """断开文件连接（无实际操作）"""
        self.status = ConnectorStatus.INACTIVE
        logger.info("File connector disconnected")
        return True

    async def execute(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Any:
        """执行操作"""
        self._update_last_used()

        if action == "read":
            return await self._read(params.get("path"))
        elif action == "write":
            return await self._write(
                params.get("path"),
                params.get("content"),
                params.get("mode", "w"),
            )
        elif action == "append":
            return await self._append(params.get("path"), params.get("content"))
        elif action == "delete":
            return await self._delete(params.get("path"))
        elif action == "exists":
            return await self._exists(params.get("path"))
        elif action == "list_dir":
            return await self._list_dir(params.get("path"))
        elif action == "create_dir":
            return await self._create_dir(params.get("path"), params.get("parents", True))
        elif action == "get_file_info":
            return await self._get_file_info(params.get("path"))
        else:
            raise ValueError(f"Unknown action: {action}")

    def _resolve_path(self, path: str) -> Path:
        """解析路径（防止目录遍历攻击）"""
        # 如果是绝对路径，检查是否在 base_path 内
        file_path = Path(path)
        if file_path.is_absolute():
            file_path = file_path.relative_to(file_path.anchor)

        # 组合基础路径
        full_path = self.base_path / file_path

        # 解析路径（处理..等）
        full_path = full_path.resolve()

        # 安全检查：确保路径在 base_path 内
        try:
            full_path.relative_to(self.base_path.resolve())
        except ValueError:
            raise ValueError(f"Path not allowed: {path}")

        return full_path

    async def _read(self, path: str) -> str:
        """读取文件"""
        file_path = self._resolve_path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            return await f.read()

    async def _write(self, path: str, content: str, mode: str = "w") -> bool:
        """写入文件"""
        file_path = self._resolve_path(path)

        # 确保父目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, mode, encoding="utf-8" if "b" not in mode else None) as f:
            await f.write(content)

        return True

    async def _append(self, path: str, content: str) -> bool:
        """追加文件"""
        file_path = self._resolve_path(path)

        async with aiofiles.open(file_path, "a", encoding="utf-8") as f:
            await f.write(content)

        return True

    async def _delete(self, path: str) -> bool:
        """删除文件"""
        file_path = self._resolve_path(path)

        if file_path.is_dir():
            os.rmdir(file_path)
        else:
            os.remove(file_path)

        return True

    async def _exists(self, path: str) -> bool:
        """检查文件是否存在"""
        file_path = self._resolve_path(path)
        return file_path.exists()

    async def _list_dir(self, path: str) -> List[str]:
        """列出目录内容"""
        dir_path = self._resolve_path(path)

        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        items = []
        async for item in os.scandir(dir_path):
            items.append(item.name)

        return items

    async def _create_dir(self, path: str, parents: bool = True) -> bool:
        """创建目录"""
        dir_path = self._resolve_path(path)

        if parents:
            os.makedirs(dir_path, exist_ok=True)
        else:
            os.mkdir(dir_path)

        return True

    async def _get_file_info(self, path: str) -> Dict[str, Any]:
        """获取文件信息"""
        file_path = self._resolve_path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        stat = os.stat(file_path)

        return {
            "path": str(path),
            "size": stat.st_size,
            "modified": str(stat.st_mtime),
            "created": str(stat.st_ctime),
            "is_file": file_path.is_file(),
            "is_dir": file_path.is_dir(),
        }

    async def health_check(self) -> bool:
        """健康检查（检查基础路径是否可访问）"""
        try:
            return self.base_path.exists() and os.access(self.base_path, os.R_OK | os.W_OK)

        except Exception as e:
            logger.error(f"File health check failed: {e}")
            return False

    def get_actions(self) -> List[Dict]:
        """获取支持的操作列表"""
        return [action.to_dict() for action in self._actions]
