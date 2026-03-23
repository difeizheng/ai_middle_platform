"""
SQL Server 连接器
"""
from typing import Any, Dict, List, Optional
import asyncio

from .base import MCPConnector, ConnectorConfig, ConnectorStatus, ActionDefinition

from ...core.logger import get_logger

logger = get_logger(__name__)


class SQLServerConnector(MCPConnector):
    """
    SQL Server 连接器

    支持的操作:
    - query: 执行 SQL 查询
    - execute: 执行 SQL（INSERT/UPDATE/DELETE）
    - transaction: 事务执行
    - get_tables: 获取表列表
    - describe_table: 获取表结构
    - get_databases: 获取数据库列表
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
                        "database": {"type": "string", "description": "数据库名"},
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
                        "database": {"type": "string", "description": "数据库名"},
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
                                    "database": {"type": "string"},
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
                        "database": {"type": "string", "description": "数据库名"},
                        "schema": {"type": "string", "description": "模式名"},
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
                        "schema": {"type": "string", "description": "模式名"},
                        "database": {"type": "string", "description": "数据库名"},
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
                            "max_length": {"type": "integer"},
                        },
                    },
                },
            ),
            ActionDefinition(
                name="get_databases",
                description="获取数据库列表",
                params_schema={
                    "type": "object",
                    "properties": {},
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
                        "database": {"type": "string", "description": "数据库名"},
                        "schema": {"type": "string", "description": "模式名"},
                    },
                },
                response_schema={
                    "type": "array",
                    "items": {"type": "string"},
                },
            ),
        ]

    async def _connect(self) -> bool:
        """连接到 SQL Server 数据库"""
        try:
            import asyncio_mssql as mssql

            # 构建连接字符串
            connection_string = self._build_connection_string()

            # 创建连接
            self._conn = await mssql.connect(connection_string)

            logger.info(f"SQL Server 连接器已连接：{self.config.name}")
            return True

        except ImportError:
            logger.error("asyncio_mssql 库未安装，请使用 pip install asyncio-mssql 安装")
            return False
        except Exception as e:
            logger.error(f"连接 SQL Server 失败：{e}")
            return False

    def _build_connection_string(self) -> str:
        """构建 SQL Server 连接字符串"""
        host = self.config.host
        port = self.config.port or 1433
        database = self.config.database or "master"
        username = self.config.credentials.get("username", "")
        password = self.config.credentials.get("password", "")

        # ODBC 连接字符串格式
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={host},{port};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password}"
        )

    async def _disconnect(self):
        """断开连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info(f"SQL Server 连接器已断开：{self.config.name}")

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
            "get_databases": self._get_databases,
            "get_procedures": self._get_procedures,
        }

        if action not in action_map:
            raise ValueError(f"不支持的操作：{action}")

        return await action_map[action](params)

    async def _query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行查询"""
        sql = params.get("sql")
        sql_params = params.get("params", [])
        database = params.get("database")

        if not sql:
            raise ValueError("SQL 不能为空")

        # 切换数据库
        if database:
            await self._conn.execute(f"USE [{database}]")

        cursor = await self._conn.cursor()
        await cursor.execute(sql, sql_params)

        columns = [col[0] for col in cursor.description]
        rows = await cursor.fetchall()

        # 转换为字典列表
        result = [dict(zip(columns, row)) for row in rows]
        return {"data": result, "row_count": len(result)}

    async def _execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行 SQL"""
        sql = params.get("sql")
        sql_params = params.get("params", [])
        database = params.get("database")

        if not sql:
            raise ValueError("SQL 不能为空")

        # 切换数据库
        if database:
            await self._conn.execute(f"USE [{database}]")

        cursor = await self._conn.cursor()
        await cursor.execute(sql, sql_params)
        rows_affected = cursor.rowcount
        await self._conn.commit()

        return {"rows_affected": rows_affected}

    async def _transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行事务"""
        statements = params.get("statements", [])
        database = params.get("database")

        if not statements:
            raise ValueError("SQL 语句列表不能为空")

        # 切换数据库
        if database:
            await self._conn.execute(f"USE [{database}]")

        cursor = await self._conn.cursor()
        results = []

        try:
            await self._conn.execute("BEGIN TRANSACTION")

            for stmt in statements:
                sql = stmt.get("sql")
                sql_params = stmt.get("params", [])
                await cursor.execute(sql, sql_params)
                results.append({"rows_affected": cursor.rowcount})

            await self._conn.execute("COMMIT TRANSACTION")
            return {"success": True, "results": results}

        except Exception as e:
            await self._conn.execute("ROLLBACK TRANSACTION")
            raise e

    async def _get_tables(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取表列表"""
        database = params.get("database", "")
        schema = params.get("schema", "dbo")
        table_type = params.get("table_type", "TABLE")

        # 切换数据库
        if database:
            await self._conn.execute(f"USE [{database}]")

        cursor = await self._conn.cursor()

        type_map = {"TABLE": "U", "VIEW": "V"}
        xtype = type_map.get(table_type, "U")

        query = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = ? AND TABLE_TYPE = ?
            ORDER BY TABLE_NAME
        """

        await cursor.execute(query, (schema, table_type))
        rows = await cursor.fetchall()

        return {"tables": [row[0] for row in rows]}

    async def _describe_table(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取表结构"""
        table_name = params.get("table_name")
        schema = params.get("schema", "dbo")
        database = params.get("database", "")

        if not table_name:
            raise ValueError("表名不能为空")

        # 切换数据库
        if database:
            await self._conn.execute(f"USE [{database}]")

        cursor = await self._conn.cursor()

        query = """
            SELECT
                c.COLUMN_NAME,
                c.DATA_TYPE,
                CASE WHEN c.IS_NULLABLE = 'YES' THEN 1 ELSE 0 END as nullable,
                c.CHARACTER_MAXIMUM_LENGTH as max_length,
                c.NUMERIC_PRECISION as precision,
                c.NUMERIC_SCALE as scale
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.TABLE_SCHEMA = ? AND c.TABLE_NAME = ?
            ORDER BY c.ORDINAL_POSITION
        """

        await cursor.execute(query, (schema, table_name))
        rows = await cursor.fetchall()

        columns = []
        for row in rows:
            columns.append(
                {
                    "column_name": row[0],
                    "data_type": row[1],
                    "nullable": bool(row[2]),
                    "max_length": row[3],
                    "precision": row[4],
                    "scale": row[5],
                }
            )

        return {"columns": columns}

    async def _get_databases(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取数据库列表"""
        cursor = await self._conn.cursor()

        await cursor.execute("SELECT name FROM sys.databases WHERE state = 0 ORDER BY name")
        rows = await cursor.fetchall()

        return {"databases": [row[0] for row in rows]}

    async def _get_procedures(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取存储过程列表"""
        database = params.get("database", "")
        schema = params.get("schema", "dbo")

        # 切换数据库
        if database:
            await self._conn.execute(f"USE [{database}]")

        cursor = await self._conn.cursor()

        query = """
            SELECT ROUTINE_NAME
            FROM INFORMATION_SCHEMA.ROUTINES
            WHERE ROUTINE_TYPE = 'PROCEDURE' AND ROUTINE_SCHEMA = ?
            ORDER BY ROUTINE_NAME
        """

        await cursor.execute(query, (schema,))
        rows = await cursor.fetchall()

        return {"procedures": [row[0] for row in rows]}

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            cursor = await self._conn.cursor()
            await cursor.execute("SELECT 1")
            return {"status": "healthy", "latency_ms": 0}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
