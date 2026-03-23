"""
Oracle 连接器
"""
from typing import Any, Dict, List, Optional
import asyncio

from .base import MCPConnector, ConnectorConfig, ConnectorStatus, ActionDefinition

from ...core.logger import get_logger

logger = get_logger(__name__)


class OracleConnector(MCPConnector):
    """
    Oracle 数据库连接器

    支持的操作:
    - query: 执行 SQL 查询
    - execute: 执行 SQL（INSERT/UPDATE/DELETE）
    - transaction: 事务执行
    - get_tables: 获取表列表
    - describe_table: 获取表结构
    - get_sequences: 获取序列列表
    - get_procedures: 获取存储过程列表
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
                name="transaction",
                description="执行事务（多条 SQL 一起执行）",
                params_schema={
                    "type": "object",
                    "properties": {
                        "statements": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "sql": {"type": "string"},
                                    "params": {"type": "array"},
                                },
                            },
                            "description": "SQL 语句列表",
                        },
                    },
                    "required": ["statements"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "results": {"type": "array"},
                    },
                },
            ),
            ActionDefinition(
                name="get_tables",
                description="获取表列表",
                params_schema={
                    "type": "object",
                    "properties": {
                        "schema": {"type": "string", "description": "用户名/模式名"},
                        "table_type": {
                            "type": "string",
                            "description": "表类型（TABLE/VIEW）",
                        },
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
                        "table_name": {"type": "string", "description": "表名"},
                        "schema": {"type": "string", "description": "用户名/模式名"},
                    },
                    "required": ["table_name"],
                },
                response_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "column_name": {"type": "string"},
                            "data_type": {"type": "string"},
                            "nullable": {"type": "boolean"},
                            "data_length": {"type": "integer"},
                        },
                    },
                },
            ),
            ActionDefinition(
                name="get_sequences",
                description="获取序列列表",
                params_schema={
                    "type": "object",
                    "properties": {
                        "schema": {"type": "string", "description": "用户名/模式名"},
                    },
                },
                response_schema={
                    "type": "array",
                    "items": {"type": "string"},
                },
            ),
            ActionDefinition(
                name="get_procedures",
                description="获取存储过程列表",
                params_schema={
                    "type": "object",
                    "properties": {
                        "schema": {"type": "string", "description": "用户名/模式名"},
                    },
                },
                response_schema={
                    "type": "array",
                    "items": {"type": "string"},
                },
            ),
        ]

    async def _connect(self) -> bool:
        """连接到 Oracle 数据库"""
        try:
            import oracledb

            # 构建连接字符串
            dsn = self._build_dsn()

            # 创建连接池
            self._pool = oracledb.create_pool(
                dsn=dsn,
                user=self.config.credentials.get("username", ""),
                password=self.config.credentials.get("password", ""),
                min=2,
                max=10,
                increment=1,
            )

            logger.info(f"Oracle 连接器已连接：{self.config.name}")
            return True

        except ImportError:
            logger.error("oracledb 库未安装，请使用 pip install oracledb 安装")
            return False
        except Exception as e:
            logger.error(f"连接 Oracle 失败：{e}")
            return False

    def _build_dsn(self) -> str:
        """构建 Oracle DSN"""
        host = self.config.host
        port = self.config.port or 1521
        service_name = self.config.database or ""
        sid = self.config.credentials.get("sid", "")

        if sid:
            return f"{host}:{port}/{sid}"
        else:
            return f"{host}:{port}/{service_name}"

    async def _disconnect(self):
        """断开连接"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            logger.info(f"Oracle 连接器已断开：{self.config.name}")

    async def _execute_action(
        self, action: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行操作"""
        action_map = {
            "query": self._query,
            "execute": self._execute,
            "transaction": self._transaction,
            "get_tables": self._get_tables,
            "describe_table": self._describe_table,
            "get_sequences": self._get_sequences,
            "get_procedures": self._get_procedures,
        }

        if action not in action_map:
            raise ValueError(f"不支持的操作：{action}")

        return await action_map[action](params)

    async def _query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行查询"""
        sql = params.get("sql")
        sql_params = params.get("params", [])

        if not sql:
            raise ValueError("SQL 不能为空")

        async with self._pool.acquire() as conn:
            cursor = conn.cursor()
            await cursor.execute(sql, sql_params)
            columns = [col[0].lower() for col in cursor.description]
            rows = await cursor.fetchall()
            await cursor.close()

            # 转换为字典列表
            result = [dict(zip(columns, row)) for row in rows]
            return {"data": result, "row_count": len(result)}

    async def _execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行 SQL"""
        sql = params.get("sql")
        sql_params = params.get("params", [])

        if not sql:
            raise ValueError("SQL 不能为空")

        async with self._pool.acquire() as conn:
            cursor = conn.cursor()
            await cursor.execute(sql, sql_params)
            rows_affected = cursor.rowcount
            await conn.commit()
            await cursor.close()

            return {"rows_affected": rows_affected}

    async def _transaction(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行事务"""
        statements = params.get("statements", [])

        if not statements:
            raise ValueError("SQL 语句列表不能为空")

        async with self._pool.acquire() as conn:
            cursor = conn.cursor()
            results = []

            try:
                for stmt in statements:
                    sql = stmt.get("sql")
                    sql_params = stmt.get("params", [])
                    await cursor.execute(sql, sql_params)
                    results.append({"rows_affected": cursor.rowcount})

                await conn.commit()
                return {"success": True, "results": results}

            except Exception as e:
                await conn.rollback()
                raise e

            finally:
                await cursor.close()

    async def _get_tables(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取表列表"""
        schema = params.get("schema", "")
        table_type = params.get("table_type", "TABLE")

        async with self._pool.acquire() as conn:
            cursor = conn.cursor()

            query = """
                SELECT table_name FROM all_tables
                WHERE owner = :schema
                UNION ALL
                SELECT view_name as table_name FROM all_views
                WHERE owner = :schema AND :table_type = 'VIEW'
            """

            await cursor.execute(query, {"schema": schema.upper(), "table_type": table_type})
            rows = await cursor.fetchall()
            await cursor.close()

            return {"tables": [row[0] for row in rows]}

    async def _describe_table(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取表结构"""
        table_name = params.get("table_name")
        schema = params.get("schema", "")

        if not table_name:
            raise ValueError("表名不能为空")

        async with self._pool.acquire() as conn:
            cursor = conn.cursor()

            query = """
                SELECT column_name, data_type, nullable, data_length, data_precision, data_scale
                FROM all_tab_columns
                WHERE table_name = :table_name
                AND owner = :schema
                ORDER BY column_id
            """

            await cursor.execute(
                query,
                {"table_name": table_name.upper(), "schema": schema.upper()},
            )
            rows = await cursor.fetchall()
            await cursor.close()

            columns = []
            for row in rows:
                columns.append(
                    {
                        "column_name": row[0],
                        "data_type": row[1],
                        "nullable": row[2] == "Y",
                        "data_length": row[3],
                        "data_precision": row[4],
                        "data_scale": row[5],
                    }
                )

            return {"columns": columns}

    async def _get_sequences(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取序列列表"""
        schema = params.get("schema", "")

        async with self._pool.acquire() as conn:
            cursor = conn.cursor()

            query = """
                SELECT sequence_name FROM all_sequences
                WHERE sequence_owner = :schema
                ORDER BY sequence_name
            """

            await cursor.execute(query, {"schema": schema.upper()})
            rows = await cursor.fetchall()
            await cursor.close()

            return {"sequences": [row[0] for row in rows]}

    async def _get_procedures(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取存储过程列表"""
        schema = params.get("schema", "")

        async with self._pool.acquire() as conn:
            cursor = conn.cursor()

            query = """
                SELECT object_name, object_type FROM all_procedures
                WHERE owner = :schema
                ORDER BY object_name
            """

            await cursor.execute(query, {"schema": schema.upper()})
            rows = await cursor.fetchall()
            await cursor.close()

            procedures = []
            for row in rows:
                procedures.append(
                    {"name": row[0], "type": row[1]}
                )

            return {"procedures": procedures}

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            async with self._pool.acquire() as conn:
                cursor = conn.cursor()
                await cursor.execute("SELECT 1 FROM DUAL")
                await cursor.close()
                return {"status": "healthy", "latency_ms": 0}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
