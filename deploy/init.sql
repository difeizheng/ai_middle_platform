-- AI 中台系统 - 初始化 SQL 脚本
-- 版本：0.1.0
-- 日期：2026-03-23

-- ========== 扩展 ==========
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 模糊查询支持

-- ========== 用户表 ==========
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    department VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    permissions JSON DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- ========== 模型表 ==========
CREATE TABLE IF NOT EXISTS models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    model_type VARCHAR(20) NOT NULL,
    provider VARCHAR(50),
    base_url VARCHAR(500),
    api_key VARCHAR(500),
    max_context_length INTEGER DEFAULT 4096,
    max_tokens INTEGER DEFAULT 2048,
    supports_function_call BOOLEAN DEFAULT FALSE,
    supports_vision BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    avg_latency_ms FLOAT DEFAULT 0.0,
    qps INTEGER DEFAULT 0,
    config JSON DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_models_name ON models(name);
CREATE INDEX idx_models_type ON models(model_type);
CREATE INDEX idx_models_active ON models(is_active);

-- ========== 模型注册表 ==========
CREATE TABLE IF NOT EXISTS model_registry (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id),
    version VARCHAR(50),
    path VARCHAR(500),
    description TEXT,
    tags JSON DEFAULT '[]',
    metrics JSON DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ========== 知识库表 ==========
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    owner_id INTEGER REFERENCES users(id),
    embedding_model VARCHAR(100) DEFAULT 'bge-large-zh-v1.5',
    chunk_size INTEGER DEFAULT 500,
    chunk_overlap INTEGER DEFAULT 50,
    collection_name VARCHAR(100) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    document_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    access_level VARCHAR(20) DEFAULT 'private',
    authorized_users JSON DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_knowledge_bases_name ON knowledge_bases(name);
CREATE INDEX idx_knowledge_bases_owner ON knowledge_bases(owner_id);

-- ========== 知识文档表 ==========
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id SERIAL PRIMARY KEY,
    knowledge_base_id INTEGER REFERENCES knowledge_bases(id),
    title VARCHAR(500),
    file_name VARCHAR(500),
    file_path VARCHAR(1000),
    file_hash VARCHAR(64),
    file_size BIGINT,
    file_type VARCHAR(20),
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    chunk_count INTEGER DEFAULT 0,
    metadata JSON DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_documents_kb ON knowledge_documents(knowledge_base_id);
CREATE INDEX idx_documents_status ON knowledge_documents(status);
CREATE INDEX idx_documents_created ON knowledge_documents(created_at);

-- ========== 知识分片表 ==========
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES knowledge_documents(id),
    knowledge_base_id INTEGER REFERENCES knowledge_bases(id),
    content TEXT NOT NULL,
    vector_id VARCHAR(100),
    embedding JSON,
    chunk_index INTEGER,
    start_pos INTEGER,
    end_pos INTEGER,
    metadata JSON DEFAULT '{}',
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chunks_document ON knowledge_chunks(document_id);
CREATE INDEX idx_chunks_kb ON knowledge_chunks(knowledge_base_id);
CREATE INDEX idx_chunks_vector ON knowledge_chunks(vector_id);

-- ========== 应用表 ==========
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    owner_id INTEGER REFERENCES users(id),
    app_type VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    quota_config JSON DEFAULT '{}',
    rate_limit JSON DEFAULT '{}',
    callback_url VARCHAR(500),
    total_calls INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_applications_name ON applications(name);
CREATE INDEX idx_applications_owner ON applications(owner_id);

-- ========== API Key 表 ==========
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    app_id INTEGER REFERENCES applications(id),
    key VARCHAR(100) UNIQUE NOT NULL,
    key_prefix VARCHAR(10),
    secret VARCHAR(255),
    permissions JSON DEFAULT '[]',
    allowed_models JSON DEFAULT '[]',
    allowed_ips JSON DEFAULT '[]',
    rate_limit_qps INTEGER DEFAULT 100,
    rate_limit_daily INTEGER DEFAULT 100000,
    is_active BOOLEAN DEFAULT TRUE,
    is_revoked BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    total_calls INTEGER DEFAULT 0,
    today_calls INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_keys_key ON api_keys(key);
CREATE INDEX idx_api_keys_app ON api_keys(app_id);

-- ========== API 日志表 ==========
CREATE TABLE IF NOT EXISTS api_logs (
    id SERIAL PRIMARY KEY,
    trace_id VARCHAR(64),
    request_id VARCHAR(64) UNIQUE,
    user_id INTEGER REFERENCES users(id),
    app_id INTEGER REFERENCES applications(id),
    api_key VARCHAR(100),
    method VARCHAR(10),
    path VARCHAR(500),
    endpoint VARCHAR(200),
    request_headers JSON,
    request_body JSON,
    query_params JSON,
    response_status INTEGER,
    response_headers JSON,
    response_body JSON,
    latency_ms FLOAT,
    tokens_used INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    model_name VARCHAR(100),
    is_success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_logs_trace ON api_logs(trace_id);
CREATE INDEX idx_api_logs_user ON api_logs(user_id);
CREATE INDEX idx_api_logs_endpoint ON api_logs(endpoint);
CREATE INDEX idx_api_logs_created ON api_logs(created_at);
CREATE INDEX idx_api_logs_user_created ON api_logs(user_id, created_at);
CREATE INDEX idx_api_logs_endpoint_created ON api_logs(endpoint, created_at);

-- ========== 审计日志表 ==========
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    trace_id VARCHAR(64),
    action VARCHAR(50) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    username VARCHAR(50),
    resource_type VARCHAR(50),
    resource_id INTEGER,
    resource_name VARCHAR(200),
    operation VARCHAR(20),
    old_value JSON,
    new_value JSON,
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    request_path VARCHAR(500),
    result VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- ========== 插入初始数据 ==========

-- 默认管理员用户 (密码：admin123)
-- 使用 bcrypt 加密
INSERT INTO users (username, email, hashed_password, full_name, role, is_superuser, is_active)
VALUES (
    'admin',
    'admin@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS3MebAJ.',  -- admin123
    '系统管理员',
    'admin',
    TRUE,
    TRUE
);

-- 默认模型配置
INSERT INTO models (name, display_name, model_type, provider, base_url, is_active, is_default)
VALUES
    ('qwen-72b', '通义千问 72B', 'llm', 'openai', 'http://localhost:8001/v1', TRUE, TRUE),
    ('chatglm3-6b', 'ChatGLM3 6B', 'llm', 'openai', 'http://localhost:8002/v1', TRUE, FALSE),
    ('deepseek-67b', 'DeepSeek 67B', 'llm', 'openai', 'http://localhost:8003/v1', TRUE, FALSE),
    ('bge-large-zh-v1.5', 'BGE 中文向量', 'embedding', 'local', NULL, TRUE, TRUE);

-- ========== 视图 ==========

-- 活跃应用视图
CREATE OR REPLACE VIEW v_active_applications AS
SELECT
    a.id,
    a.name,
    a.app_type,
    u.username as owner_name,
    a.total_calls,
    a.total_tokens,
    a.created_at
FROM applications a
LEFT JOIN users u ON a.owner_id = u.id
WHERE a.is_active = TRUE;

-- API 调用统计视图（按天）
CREATE OR REPLACE VIEW v_daily_api_stats AS
SELECT
    DATE(created_at) as stat_date,
    endpoint,
    COUNT(*) as total_calls,
    SUM(CASE WHEN is_success THEN 1 ELSE 0 END) as success_calls,
    AVG(latency_ms) as avg_latency,
    SUM(tokens_used) as total_tokens
FROM api_logs
GROUP BY DATE(created_at), endpoint
ORDER BY stat_date DESC, total_calls DESC;

-- ========== 函数 ==========

-- 更新 updated_at 时间戳
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_models_updated_at BEFORE UPDATE ON models
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_bases_updated_at BEFORE UPDATE ON knowledge_bases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========== 注释 ==========

COMMENT ON TABLE users IS '用户表';
COMMENT ON TABLE models IS '模型注册表';
COMMENT ON TABLE knowledge_bases IS '知识库表';
COMMENT ON TABLE knowledge_documents IS '知识文档表';
COMMENT ON TABLE knowledge_chunks IS '知识分片表';
COMMENT ON TABLE applications IS '应用表';
COMMENT ON TABLE api_keys IS 'API Key 表';
COMMENT ON TABLE api_logs IS 'API 调用日志表';
COMMENT ON TABLE audit_logs IS '审计日志表';

-- ========== 完成 ==========
