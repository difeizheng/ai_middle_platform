"""
PostgreSQL 连接器
"""
from typing import Any, Dict, List, Optional
import asyncio

from .base import MCPConnector, ConnectorConfig, ConnectorStatus, ActionDefinition

try:
    import asyncpg
except ImportError:
    asyncpg = None

from ...core.logger import get_logger

logger = get_logger(__name__)


class PostgreSQLConnector(MCPConnector):
    """
    PostgreSQL 连接器

    支持的操作:
    - query: 执行查询语句
    - execute: 执行增删改语句
    - get_tables: 获取所有表
    - describe_table: 获取表结构
    - get_schemas: 获取所有 schema
    """

    def __init__(self, config: ConnectorConfig):
        if asyncpg is None:
            raise ImportError("asyncpg is not installed. Please install it: pip install asyncpg")

        super().__init__(config)
        self._pool: Optional[asyncpg.Pool] = None
        self._actions = self._register_actions()

    def _register_actions(self) -> List[ActionDefinition]:
        """注册支持的操作"""
        return [
            ActionDefinition(
                name="query",
                description="执行 SQL 查询语句",
                params_schema={
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL 查询语句"},
                        "params": {"type": "array", "items": {"type": "string"}, "description": "参数列表"},
                    },
                    "required": ["sql"],
                },
                response_schema={
                    "type": "array",
                    "items": {"type": "object"},
                },
            ),
            ActionDefinition(
                name="execute",
                description="执行 SQL 增删改语句",
                params_schema={
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL 语句"},
                        "params": {"type": "array", "items": {"type": "string"}, "description": "参数列表"},
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
                description="获取所有表",
                params_schema={
                    "type": "object",
                    "properties": {
                        "schema": {"type": "string", "description": "schema 名称，默认 public"},
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
                        "schema": {"type": "string", "description": "schema 名称，默认 public"},
                    },
                    "required": ["table"],
                },
                response_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "column": {"type": "string"},
                            "type": {"type": "string"},
                            "nullable": {"type": "boolean"},
                            "default": {"type": "string"},
                        },
                    },
                },
            ),
            ActionDefinition(
                name="get_schemas",
                description="获取所有 schema",
                params_schema={"type": "object"},
                response_schema={
                    "type": "array",
                    "items": {"type": "string"},
                },
            ),
        ]

    async def connect(self) -> bool:
        """建立 PostgreSQL 连接"""
        try:
            self.status = ConnectorStatus.CONNECTING

            # 构建连接字符串
            ssl_mode = "require" if self.config.ssl else "prefer"

            self._pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port or 5432,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database or "postgres",
                min_size=2,
                max_size=self.config.max_connections,
                command_timeout=self.config.timeout,
                ssl=ssl_mode if self.config.ssl else None,
            )

            self.status = ConnectorStatus.ACTIVE
            logger.info(f"PostgreSQL connector '{self.config.name}' connected successfully")
            return True

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            logger.error(f"PostgreSQL connector '{self.config.name}' connect failed: {e}")
            return False

    async def disconnect(self) -> bool:
        """断开 PostgreSQL 连接"""
        try:
            self.status = ConnectorStatus.DISCONNECTING

            if self._pool:
                await self._pool.close()
                self._pool = None

            self.status = ConnectorStatus.INACTIVE
            logger.info(f"PostgreSQL connector '{self.config.name}' disconnected")
            return True

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            logger.error(f"PostgreSQL connector '{self.config.name}' disconnect failed: {e}")
            return False

    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """执行操作"""
        if self.status != ConnectorStatus.ACTIVE:
            raise RuntimeError("Connector is not connected")

        self._update_last_used()

        try:
            if action == "query":
                return await self._query(params)
            elif action == "execute":
                return await self._execute(params)
            elif action == "get_tables":
                return await self._get_tables(params)
            elif action == "describe_table":
                return await self._describe_table(params)
            elif action == "get_schemas":
                return await self._get_schemas()
            else:
                raise ValueError(f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"PostgreSQL connector execute '{action}' failed: {e}")
            raise

    async def _query(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行查询"""
        sql = params.get("sql")
        sql_params = params.get("params", [])

        if not sql:
            raise ValueError("SQL is required")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *sql_params)
            return [dict(row) for row in rows]

    async def _execute(self, params: Dict[str, Any]) -> Dict[str, int]:
        """执行增删改"""
        sql = params.get("sql")
        sql_params = params.get("params", [])

        if not sql:
            raise ValueError("SQL is required")

        async with self._pool.acquire() as conn:
            result = await conn.execute(sql, *sql_params)
            # 解析结果，例如 "SELECT 5" 或 "UPDATE 10"
            parts = result.split()
            rows_affected = int(parts[-1]) if parts else 0
            return {"rows_affected": rows_affected}

    async def _get_tables(self, params: Dict[str, Any]) -> List[str]:
        """获取所有表"""
        schema = params.get("schema", "public")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = $1 AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """,
                schema
            )
            return [row["table_name"] for row in rows]

    async def _describe_table(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取表结构"""
        table = params.get("table")
        schema = params.get("schema", "public")

        if not table:
            raise ValueError("Table name is required")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = $1 AND table_name = $2
                ORDER BY ordinal_position
                """,
                schema, table
            )
            return [
                {
                    "column": row["column_name"],
                    "type": row["data_type"],
                    "nullable": row["is_nullable"] == "YES",
                    "default": row["column_default"],
                }
                for row in rows
            ]

    async def _get_schemas(self) -> List[str]:
        """获取所有 schema"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schema_name
                """
            )
            return [row["schema_name"] for row in rows]

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if self.status != ConnectorStatus.ACTIVE or not self._pool:
                return False

            # 执行简单的查询测试连接
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            return True
        except Exception as e:
            logger.error(f"PostgreSQL connector health check failed: {e}")
            self.status = ConnectorStatus.ERROR
            return False

    def get_actions(self) -> List[Dict[str, Any]]:
        """获取支持的操作列表"""
        return [action.to_dict() for action in self._actions]
