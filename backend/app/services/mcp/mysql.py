"""
MySQL 连接器
"""
from typing import Any, Dict, List, Optional
import asyncio

from .base import MCPConnector, ConnectorConfig, ConnectorStatus, ActionDefinition

from ...core.logger import get_logger

logger = get_logger(__name__)


class MySQLConnector(MCPConnector):
    """
    MySQL 连接器

    支持的操作:
    - query: 执行查询
    - execute: 执行 SQL（INSERT/UPDATE/DELETE）
    - transaction: 事务执行
    - get_tables: 获取表列表
    - describe_table: 获取表结构
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._pool = None
        self._actions = self._register_actions()

    def _register_actions(self) -> List[ActionDefinition]:
        """注册支持的操作"""
        return [
            ActionDefinition(
                name="query",
                description="执行 SQL 查询",
                params_schema={
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL 语句"},
                        "params": {"type": "array", "description": "参数列表"},
                    },
                    "required": ["sql"],
                },
                response_schema={
                    "type": "array",
                    "description": "查询结果列表",
                },
            ),
            ActionDefinition(
                name="execute",
                description="执行 SQL（INSERT/UPDATE/DELETE）",
                params_schema={
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL 语句"},
                        "params": {"type": "array", "description": "参数列表"},
                    },
                    "required": ["sql"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "rows_affected": {"type": "integer"},
                    },
                },
            ),
            ActionDefinition(
                name="get_tables",
                description="获取数据库表列表",
                params_schema={
                    "type": "object",
                    "properties": {
                        "schema": {"type": "string", "description": "数据库名"},
                    },
                },
                response_schema={
                    "type": "array",
                    "items": {"type": "string"},
                },
            ),
            ActionDefinition(
                name="describe_table",
                description="获取表结构",
                params_schema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "表名"},
                    },
                    "required": ["table"],
                },
                response_schema={
                    "type": "array",
                    "description": "列信息列表",
                },
            ),
        ]

    async def connect(self) -> bool:
        """建立 MySQL 连接"""
        try:
            self.status = ConnectorStatus.CONNECTING

            # 导入 aiomysql
            import aiomysql

            # 创建连接池
            self._pool = await aiomysql.create_pool(
                host=self.config.host or "localhost",
                port=self.config.port or 3306,
                user=self.config.username or "root",
                password=self.config.password or "",
                db=self.config.database,
                minsize=1,
                maxsize=self.config.max_connections,
                connect_timeout=self.config.timeout,
                charset="utf8mb4",
                autocommit=True,
            )

            self.status = ConnectorStatus.ACTIVE
            logger.info(f"MySQL connector connected: {self.config.host}:{self.config.port}")
            return True

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            logger.error(f"MySQL connect failed: {e}")
            return False

    async def disconnect(self) -> bool:
        """断开 MySQL 连接"""
        try:
            self.status = ConnectorStatus.DISCONNECTING

            if self._pool:
                self._pool.close()
                await self._pool.wait_closed()
                self._pool = None

            self.status = ConnectorStatus.INACTIVE
            logger.info("MySQL connector disconnected")
            return True

        except Exception as e:
            logger.error(f"MySQL disconnect error: {e}")
            return False

    async def execute(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Any:
        """执行操作"""
        self._update_last_used()

        if action == "query":
            return await self._query(params.get("sql"), params.get("params"))
        elif action == "execute":
            return await self._execute_sql(params.get("sql"), params.get("params"))
        elif action == "get_tables":
            return await self._get_tables()
        elif action == "describe_table":
            return await self._describe_table(params.get("table"))
        else:
            raise ValueError(f"Unknown action: {action}")

    async def _query(self, sql: str, sql_params: Optional[List] = None) -> List[Dict]:
        """执行查询"""
        if not self._pool:
            raise RuntimeError("Connector not connected")

        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql, sql_params)
                result = await cursor.fetchall()
                return [dict(row) for row in result]

    async def _execute_sql(
        self,
        sql: str,
        sql_params: Optional[List] = None,
    ) -> Dict[str, int]:
        """执行 SQL（INSERT/UPDATE/DELETE）"""
        if not self._pool:
            raise RuntimeError("Connector not connected")

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                row_count = await cursor.execute(sql, sql_params)
                await conn.commit()
                return {"rows_affected": row_count}

    async def _get_tables(self) -> List[str]:
        """获取表列表"""
        sql = "SHOW TABLES"
        result = await self._query(sql)
        return [list(row.values())[0] for row in result]

    async def _describe_table(self, table: str) -> List[Dict]:
        """获取表结构"""
        sql = f"DESCRIBE `{table}`"
        return await self._query(sql)

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._pool:
                return False

            result = await self._query("SELECT 1")
            return result is not None

        except Exception as e:
            logger.error(f"MySQL health check failed: {e}")
            return False

    def get_actions(self) -> List[Dict]:
        """获取支持的操作列表"""
        return [action.to_dict() for action in self._actions]
