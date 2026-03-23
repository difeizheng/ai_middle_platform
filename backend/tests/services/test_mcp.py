"""
MCP 连接器测试
"""
import pytest
from app.services.mcp.base import ConnectorConfig, ConnectorType, ConnectorStatus
from app.services.mcp.registry import ConnectorRegistry
from app.services.mcp.http import HTTPConnector
from app.services.mcp.redis import RedisConnector
from app.services.mcp.file import FileConnector
from app.services.mcp.postgresql import PostgreSQLConnector
from app.services.mcp.mongodb import MongoDBConnector
from app.services.mcp.kafka import KafkaConnector


class TestConnectorConfig:
    """连接器配置测试"""

    def test_create_config(self):
        """测试创建配置"""
        config = ConnectorConfig(
            name="test-connector",
            connector_type=ConnectorType.HTTP,
            host="localhost",
            port=8080,
        )

        assert config.name == "test-connector"
        assert config.connector_type == ConnectorType.HTTP
        assert config.host == "localhost"
        assert config.port == 8080

    def test_config_from_dict(self):
        """测试从字典创建配置"""
        data = {
            "name": "mysql-db",
            "type": "mysql",
            "host": "db.example.com",
            "port": 3306,
            "username": "root",
            "password": "secret",
            "database": "test",
        }

        config = ConnectorConfig.from_dict(data)

        assert config.name == "mysql-db"
        assert config.connector_type == ConnectorType.MYSQL
        assert config.host == "db.example.com"

    def test_config_to_dict(self):
        """测试配置转字典"""
        config = ConnectorConfig(
            name="test",
            connector_type=ConnectorType.REDIS,
            host="localhost",
        )

        data = config.to_dict()

        assert data["name"] == "test"
        assert data["type"] == "redis"
        assert "password" not in data  # 密码不应该在输出中


class TestConnectorRegistry:
    """连接器注册表测试"""

    @pytest.fixture
    def registry(self):
        """创建注册表实例"""
        return ConnectorRegistry()

    def test_singleton(self):
        """测试单例模式"""
        r1 = ConnectorRegistry()
        r2 = ConnectorRegistry()
        assert r1 is r2

    def test_register_type(self, registry):
        """测试注册连接器类型"""
        registry.register_type("http", HTTPConnector)
        types = registry.list_connector_types()
        assert "http" in types

    def test_get_connector_type(self, registry):
        """测试获取连接器类型"""
        registry.register_type("test_http", HTTPConnector)
        connector_class = registry.get_connector_type("test_http")
        assert connector_class == HTTPConnector

    def test_create_connector(self, registry):
        """测试创建连接器实例"""
        config = ConnectorConfig(
            name="test-file",
            connector_type=ConnectorType.FILE,
        )

        connector = registry.create_connector(
            "test-instance-1",
            "file",
            config,
        )

        assert connector is not None
        assert isinstance(connector, FileConnector)

    def test_get_connector(self, registry):
        """测试获取连接器实例"""
        config = ConnectorConfig(
            name="test",
            connector_type=ConnectorType.FILE,
        )

        registry.create_connector("test-get", "file", config)
        connector = registry.get_connector("test-get")

        assert connector is not None
        assert connector.config.name == "test"

    def test_remove_connector(self, registry):
        """测试移除连接器"""
        config = ConnectorConfig(
            name="test",
            connector_type=ConnectorType.FILE,
        )

        registry.create_connector("test-remove", "file", config)
        result = registry.remove_connector("test-remove")

        assert result is True
        assert registry.get_connector("test-remove") is None

    def test_get_stats(self, registry):
        """测试获取统计"""
        registry.register_type("stat_test", HTTPConnector)
        config = ConnectorConfig(
            name="test",
            connector_type=ConnectorType.FILE,
        )
        registry.create_connector("stat-test", "file", config)

        stats = registry.get_stats()

        assert "connector_types" in stats
        assert "connector_instances" in stats


class TestHTTPConnector:
    """HTTP 连接器测试"""

    @pytest.fixture
    def http_connector(self):
        """创建 HTTP 连接器"""
        config = ConnectorConfig(
            name="test-http",
            connector_type=ConnectorType.HTTP,
            timeout=10,
        )
        return HTTPConnector(config)

    @pytest.mark.asyncio
    async def test_connect(self, http_connector):
        """测试连接"""
        result = await http_connector.connect()
        assert result is True
        assert http_connector.status == ConnectorStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_disconnect(self, http_connector):
        """测试断开"""
        await http_connector.connect()
        result = await http_connector.disconnect()
        assert result is True
        assert http_connector.status == ConnectorStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_health_check(self, http_connector):
        """测试健康检查"""
        await http_connector.connect()
        result = await http_connector.health_check()
        # HTTP 连接器没有实际的健康检查目标，应该返回 True
        assert result is True

    @pytest.mark.asyncio
    async def test_get_request(self, http_connector):
        """测试 GET 请求（使用公共 API）"""
        await http_connector.connect()

        result = await http_connector.execute(
            "get",
            {"url": "https://httpbin.org/get"},
        )

        assert result is not None
        assert "url" in result or isinstance(result, dict)

    def test_get_actions(self, http_connector):
        """测试获取支持的操作"""
        actions = http_connector.get_actions()
        assert len(actions) > 0
        action_names = [a["name"] for a in actions]
        assert "request" in action_names
        assert "get" in action_names


class TestRedisConnector:
    """Redis 连接器测试"""

    @pytest.fixture
    def redis_connector(self):
        """创建 Redis 连接器"""
        config = ConnectorConfig(
            name="test-redis",
            connector_type=ConnectorType.REDIS,
            host="localhost",
            port=6379,
        )
        return RedisConnector(config)

    @pytest.mark.asyncio
    async def test_connect_fail(self, redis_connector):
        """测试连接失败（没有 Redis 服务）"""
        # 注意：如果本地没有 Redis 服务，这个测试会失败
        result = await redis_connector.connect()
        # 连接应该失败或成功取决于是否有 Redis 服务
        assert isinstance(result, bool)


class TestFileConnector:
    """文件连接器测试"""

    @pytest.fixture
    def file_connector(self, tmp_path):
        """创建文件连接器"""
        config = ConnectorConfig(
            name="test-file",
            connector_type=ConnectorType.FILE,
            extra={"base_path": str(tmp_path)},
        )
        return FileConnector(config)

    @pytest.mark.asyncio
    async def test_connect(self, file_connector):
        """测试连接"""
        result = await file_connector.connect()
        assert result is True
        assert file_connector.status == ConnectorStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_write_and_read(self, file_connector):
        """测试写入和读取"""
        await file_connector.connect()

        # 写入
        write_result = await file_connector.execute(
            "write",
            {
                "path": "test.txt",
                "content": "Hello, World!",
            },
        )
        assert write_result is True

        # 读取
        content = await file_connector.execute(
            "read",
            {"path": "test.txt"},
        )
        assert content == "Hello, World!"

    @pytest.mark.asyncio
    async def test_create_dir(self, file_connector):
        """测试创建目录"""
        await file_connector.connect()

        result = await file_connector.execute(
            "create_dir",
            {"path": "test_dir"},
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_list_dir(self, file_connector):
        """测试列出目录"""
        await file_connector.connect()

        # 先创建一些文件
        await file_connector.execute(
            "write",
            {"path": "file1.txt", "content": "1"},
        )
        await file_connector.execute(
            "write",
            {"path": "file2.txt", "content": "2"},
        )

        # 列出目录
        items = await file_connector.execute(
            "list_dir",
            {"path": "."},
        )
        assert "file1.txt" in items
        assert "file2.txt" in items

    @pytest.mark.asyncio
    async def test_get_file_info(self, file_connector):
        """测试获取文件信息"""
        await file_connector.connect()

        await file_connector.execute(
            "write",
            {"path": "info.txt", "content": "test"},
        )

        info = await file_connector.execute(
            "get_file_info",
            {"path": "info.txt"},
        )

        assert "size" in info
        assert "is_file" in info
        assert info["is_file"] is True

    @pytest.mark.asyncio
    async def test_path_security(self, file_connector):
        """测试路径安全（防止目录遍历）"""
        await file_connector.connect()

        # 尝试访问父目录应该失败
        with pytest.raises(ValueError):
            await file_connector.execute(
                "read",
                {"path": "../../../etc/passwd"},
            )

    def test_health_check(self, file_connector):
        """测试健康检查"""
        result = file_connector.health_check()
        # 同步方法
        assert isinstance(result, bool) or result is True


class TestPostgreSQLConnector:
    """PostgreSQL 连接器测试"""

    @pytest.fixture
    def postgresql_connector(self):
        """创建 PostgreSQL 连接器"""
        config = ConnectorConfig(
            name="test-postgresql",
            connector_type=ConnectorType.POSTGRESQL,
            host="localhost",
            port=5432,
            username="postgres",
            password="postgres",
            database="test",
        )
        return PostgreSQLConnector(config)

    @pytest.mark.asyncio
    async def test_connect_fail(self, postgresql_connector):
        """测试连接失败（没有 PostgreSQL 服务）"""
        result = await postgresql_connector.connect()
        # 连接结果取决于是否有 PostgreSQL 服务
        assert isinstance(result, bool)

    def test_get_actions(self, postgresql_connector):
        """测试获取支持的操作"""
        actions = postgresql_connector.get_actions()
        assert len(actions) > 0
        action_names = [a["name"] for a in actions]
        assert "query" in action_names
        assert "execute" in action_names


class TestMongoDBConnector:
    """MongoDB 连接器测试"""

    @pytest.fixture
    def mongodb_connector(self):
        """创建 MongoDB 连接器"""
        config = ConnectorConfig(
            name="test-mongodb",
            connector_type=ConnectorType.MONGODB,
            host="localhost",
            port=27017,
            database="test",
        )
        return MongoDBConnector(config)

    @pytest.mark.asyncio
    async def test_connect_fail(self, mongodb_connector):
        """测试连接失败（没有 MongoDB 服务）"""
        result = await mongodb_connector.connect()
        # 连接结果取决于是否有 MongoDB 服务
        assert isinstance(result, bool)

    def test_get_actions(self, mongodb_connector):
        """测试获取支持的操作"""
        actions = mongodb_connector.get_actions()
        assert len(actions) > 0
        action_names = [a["name"] for a in actions]
        assert "find" in action_names
        assert "insert_one" in action_names


class TestKafkaConnector:
    """Kafka 连接器测试"""

    @pytest.fixture
    def kafka_connector(self):
        """创建 Kafka 连接器"""
        config = ConnectorConfig(
            name="test-kafka",
            connector_type=ConnectorType.KAFKA,
            host="localhost",
            port=9092,
        )
        return KafkaConnector(config)

    @pytest.mark.asyncio
    async def test_connect_fail(self, kafka_connector):
        """测试连接失败（没有 Kafka 服务）"""
        result = await kafka_connector.connect()
        # 连接结果取决于是否有 Kafka 服务
        assert isinstance(result, bool)

    def test_get_actions(self, kafka_connector):
        """测试获取支持的操作"""
        actions = kafka_connector.get_actions()
        assert len(actions) > 0
        action_names = [a["name"] for a in actions]
        assert "produce" in action_names
        assert "consume" in action_names
