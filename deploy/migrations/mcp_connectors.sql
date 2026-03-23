-- AI 中台系统 - MCP 连接器数据库迁移脚本
-- Phase 2.2: MCP 连接器
-- 日期：2026 年 3 月 24 日

-- ========== MCP 连接器配置表 ==========
CREATE TABLE IF NOT EXISTS mcp_connectors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    connector_type VARCHAR(50) NOT NULL,  -- mysql, postgresql, http, redis, file, kafka, mongodb
    description TEXT,

    -- 连接配置
    host VARCHAR(500),
    port INTEGER,
    username VARCHAR(200),
    password VARCHAR(500),  -- 加密存储
    database VARCHAR(200),
    ssl BOOLEAN DEFAULT FALSE,

    -- 高级配置
    timeout INTEGER DEFAULT 30,  -- 超时时间（秒）
    max_connections INTEGER DEFAULT 10,  -- 最大连接数
    config_json JSONB DEFAULT '{}',  -- 额外配置

    -- 状态
    status VARCHAR(50) DEFAULT 'inactive',  -- active, inactive, error, connecting, disconnecting
    health_check_interval INTEGER DEFAULT 60,  -- 健康检查间隔（秒）
    last_health_check TIMESTAMP WITH TIME ZONE,
    last_health_status BOOLEAN,

    -- 元数据
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_mcp_connectors_name ON mcp_connectors(name);
CREATE INDEX idx_mcp_connectors_type ON mcp_connectors(connector_type);
CREATE INDEX idx_mcp_connectors_status ON mcp_connectors(status);
CREATE INDEX idx_mcp_connectors_is_active ON mcp_connectors(is_active);

-- 添加注释
COMMENT ON TABLE mcp_connectors IS 'MCP 连接器配置表';
COMMENT ON COLUMN mcp_connectors.config_json IS '额外配置（JSON 格式）';
COMMENT ON COLUMN mcp_connectors.health_check_interval IS '健康检查间隔（秒）';


-- ========== MCP 连接器操作日志表 ==========
CREATE TABLE IF NOT EXISTS mcp_connector_logs (
    id SERIAL PRIMARY KEY,
    connector_id INTEGER REFERENCES mcp_connectors(id),
    action VARCHAR(100),  -- 操作名称
    params JSONB,  -- 操作参数
    result JSONB,  -- 操作结果
    error_message TEXT,
    duration_ms INTEGER,  -- 执行时长（毫秒）
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mcp_logs_connector_id ON mcp_connector_logs(connector_id);
CREATE INDEX idx_mcp_logs_action ON mcp_connector_logs(action);
CREATE INDEX idx_mcp_logs_created_at ON mcp_connector_logs(created_at DESC);

-- 添加注释
COMMENT ON TABLE mcp_connector_logs IS 'MCP 连接器操作日志表';


-- ========== 初始化数据 ==========

-- 示例连接器配置（需要根据实际情况修改密码）
INSERT INTO mcp_connectors (name, connector_type, host, port, username, password, database, description) VALUES
('本地 MySQL', 'mysql', 'localhost', 3306, 'root', 'password', 'test_db', '本地 MySQL 数据库'),
('本地 PostgreSQL', 'postgresql', 'localhost', 5432, 'postgres', 'password', 'test_db', '本地 PostgreSQL 数据库'),
('本地 Redis', 'redis', 'localhost', 6379, NULL, NULL, '0', '本地 Redis 缓存'),
('本地 MongoDB', 'mongodb', 'localhost', 27017, NULL, NULL, 'test', '本地 MongoDB 数据库'),
('本地 Kafka', 'kafka', 'localhost', 9092, NULL, NULL, NULL, '本地 Kafka 消息队列'),
('HTTP 示例', 'http', 'api.example.com', 443, NULL, NULL, NULL, '外部 HTTP API')
ON CONFLICT (name) DO NOTHING;

-- 完成提示
SELECT 'MCP 连接器数据库迁移完成！' AS status;
