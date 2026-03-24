-- AI 中台系统 - 初始化 SQL 脚本
-- 版本：0.7.0
-- 日期：2026-03-24
-- Phase 4: 生态建设

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

-- ========== Phase 4 生态建设表 ==========

-- 合作伙伴表
CREATE TABLE IF NOT EXISTS partners (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    level VARCHAR(50) DEFAULT 'certified',
    status VARCHAR(50) DEFAULT 'pending',
    company_name VARCHAR(200),
    company_website VARCHAR(500),
    contact_person VARCHAR(100),
    contact_email VARCHAR(200),
    contact_phone VARCHAR(50),
    logo_url VARCHAR(500),
    industry VARCHAR(100),
    location VARCHAR(200),
    certification_date TIMESTAMP WITH TIME ZONE,
    expiration_date TIMESTAMP WITH TIME ZONE,
    benefits JSON DEFAULT '{}',
    capabilities JSON DEFAULT '{}',
    success_cases JSON DEFAULT '{}',
    rating FLOAT DEFAULT 0.0,
    rating_count INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_partners_name ON partners(name);
CREATE INDEX idx_partners_level ON partners(level);
CREATE INDEX idx_partners_industry ON partners(industry);
CREATE INDEX idx_partners_status ON partners(status);

-- 合作伙伴申请表
CREATE TABLE IF NOT EXISTS partner_applications (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id),
    company_name VARCHAR(200) NOT NULL,
    company_website VARCHAR(500),
    company_size VARCHAR(50),
    industry VARCHAR(100),
    contact_person VARCHAR(100) NOT NULL,
    contact_email VARCHAR(200) NOT NULL,
    contact_phone VARCHAR(50),
    business_license VARCHAR(500),
    application_reason TEXT,
    capabilities JSON DEFAULT '{}',
    expected_level VARCHAR(50) DEFAULT 'certified',
    status VARCHAR(50) DEFAULT 'pending',
    review_comment TEXT,
    reviewer_id VARCHAR(36) REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_partner_applications_user ON partner_applications(user_id);
CREATE INDEX idx_partner_applications_status ON partner_applications(status);

-- 合作伙伴权益表
CREATE TABLE IF NOT EXISTS partner_benefits (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    level VARCHAR(50) NOT NULL,
    benefit_type VARCHAR(50),
    quota INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 合作伙伴活动表
CREATE TABLE IF NOT EXISTS partner_activities (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    activity_type VARCHAR(50),
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    location VARCHAR(200),
    online_url VARCHAR(500),
    max_participants INTEGER,
    organizer_id VARCHAR(36) REFERENCES partners(id),
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 解决方案分类表
CREATE TABLE IF NOT EXISTS solution_categories (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,
    icon VARCHAR(500),
    parent_id VARCHAR(36) REFERENCES solution_categories(id),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 解决方案表
CREATE TABLE IF NOT EXISTS solutions (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    display_name VARCHAR(200),
    description TEXT,
    industry VARCHAR(100),
    scenario VARCHAR(200),
    level VARCHAR(50) DEFAULT 'standard',
    status VARCHAR(50) DEFAULT 'draft',
    architecture JSON DEFAULT '{}',
    components JSON DEFAULT '{}',
    features JSON DEFAULT '{}',
    deployment_guide TEXT,
    config_template JSON DEFAULT '{}',
    view_count INTEGER DEFAULT 0,
    install_count INTEGER DEFAULT 0,
    rating FLOAT DEFAULT 0.0,
    rating_count INTEGER DEFAULT 0,
    author_id VARCHAR(36) REFERENCES users(id),
    author_name VARCHAR(100),
    tags JSON DEFAULT '[]',
    category_id VARCHAR(36) REFERENCES solution_categories(id),
    is_public BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_solutions_name ON solutions(name);
CREATE INDEX idx_solutions_industry ON solutions(industry);
CREATE INDEX idx_solutions_status ON solutions(status);

-- 解决方案案例表
CREATE TABLE IF NOT EXISTS solution_cases (
    id VARCHAR(36) PRIMARY KEY,
    solution_id VARCHAR(36) REFERENCES solutions(id),
    title VARCHAR(200) NOT NULL,
    customer_name VARCHAR(200),
    customer_logo VARCHAR(500),
    industry VARCHAR(100),
    challenge TEXT,
    solution_overview TEXT,
    implementation JSON DEFAULT '{}',
    results JSON DEFAULT '{}',
    testimonial TEXT,
    is_featured BOOLEAN DEFAULT FALSE,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_solution_cases_solution ON solution_cases(solution_id);

-- 解决方案模板表
CREATE TABLE IF NOT EXISTS solution_templates (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    template_type VARCHAR(50),
    content JSON NOT NULL,
    variables JSON DEFAULT '{}',
    version VARCHAR(20) DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 触发器
CREATE TRIGGER update_partners_updated_at BEFORE UPDATE ON partners
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_partner_applications_updated_at BEFORE UPDATE ON partner_applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_partner_activities_updated_at BEFORE UPDATE ON partner_activities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_solutions_updated_at BEFORE UPDATE ON solutions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_solution_cases_updated_at BEFORE UPDATE ON solution_cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========== Phase 5 计费系统表 ==========

-- 计费策略表
CREATE TABLE IF NOT EXISTS billing_plans (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    billing_type VARCHAR(20) NOT NULL,  -- token/call/subscription
    description TEXT,
    price_per_1k_tokens DECIMAL(10, 4) DEFAULT 0,
    price_per_call DECIMAL(10, 4) DEFAULT 0,
    monthly_fee DECIMAL(10, 2) DEFAULT 0,
    quota_limit INTEGER DEFAULT 0,
    overage_rate DECIMAL(10, 4) DEFAULT 1,
    model_pricing JSON DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_billing_plans_name ON billing_plans(name);
CREATE INDEX idx_billing_plans_type ON billing_plans(billing_type);
CREATE INDEX idx_billing_plans_active ON billing_plans(is_active);

-- 账户表
CREATE TABLE IF NOT EXISTS accounts (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id),
    balance DECIMAL(10, 2) DEFAULT 0,
    total_recharge DECIMAL(10, 2) DEFAULT 0,
    total_consumption DECIMAL(10, 2) DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'CNY',
    status VARCHAR(20) DEFAULT 'active',
    billing_plan_id VARCHAR(36) REFERENCES billing_plans(id),
    low_balance_warning DECIMAL(10, 2) DEFAULT 100,
    is_warning_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_accounts_user ON accounts(user_id);
CREATE INDEX idx_accounts_status ON accounts(status);

-- 计费记录表
CREATE TABLE IF NOT EXISTS billing_records (
    id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) REFERENCES accounts(id),
    record_type VARCHAR(20) NOT NULL,  -- charge/consume/refund/adjust
    amount DECIMAL(10, 4) NOT NULL,
    balance_before DECIMAL(10, 2) NOT NULL,
    balance_after DECIMAL(10, 2) NOT NULL,
    resource_type VARCHAR(20),
    resource_id VARCHAR(36),
    tokens_used INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    call_count INTEGER DEFAULT 0,
    order_id VARCHAR(36),
    api_log_id VARCHAR(36),
    description TEXT,
    metadata JSON DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_billing_records_account ON billing_records(account_id);
CREATE INDEX idx_billing_records_type ON billing_records(record_type);
CREATE INDEX idx_billing_records_created ON billing_records(created_at);

-- 充值订单表
CREATE TABLE IF NOT EXISTS recharge_orders (
    id VARCHAR(36) PRIMARY KEY,
    order_no VARCHAR(64) UNIQUE NOT NULL,
    account_id VARCHAR(36) REFERENCES accounts(id),
    user_id VARCHAR(36) REFERENCES users(id),
    amount DECIMAL(10, 2) NOT NULL,
    actual_amount DECIMAL(10, 2),
    payment_method VARCHAR(20),
    payment_status VARCHAR(20) DEFAULT 'pending',
    transaction_id VARCHAR(100),
    discount_rate DECIMAL(5, 4) DEFAULT 1,
    bonus_amount DECIMAL(10, 2) DEFAULT 0,
    description TEXT,
    client_ip VARCHAR(50),
    paid_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_recharge_orders_order_no ON recharge_orders(order_no);
CREATE INDEX idx_recharge_orders_account ON recharge_orders(account_id);
CREATE INDEX idx_recharge_orders_user ON recharge_orders(user_id);
CREATE INDEX idx_recharge_orders_status ON recharge_orders(payment_status);

-- 计费统计表
CREATE TABLE IF NOT EXISTS billing_stats (
    id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) REFERENCES accounts(id),
    stat_date TIMESTAMP WITH TIME ZONE NOT NULL,
    total_consumption DECIMAL(10, 2) DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_calls INTEGER DEFAULT 0,
    model_call_consumption DECIMAL(10, 2) DEFAULT 0,
    knowledge_base_consumption DECIMAL(10, 2) DEFAULT 0,
    agent_consumption DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_billing_stats_account ON billing_stats(account_id);
CREATE INDEX idx_billing_stats_date ON billing_stats(stat_date);

-- 触发器
CREATE TRIGGER update_billing_plans_updated_at BEFORE UPDATE ON billing_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recharge_orders_updated_at BEFORE UPDATE ON recharge_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 注释
COMMENT ON TABLE billing_plans IS '计费策略表';
COMMENT ON TABLE accounts IS '账户表';
COMMENT ON TABLE billing_records IS '计费记录表';
COMMENT ON TABLE recharge_orders IS '充值订单表';
COMMENT ON TABLE billing_stats IS '计费统计表';

-- ========== 配额管理表 ==========

-- 配额定义表
CREATE TABLE IF NOT EXISTS quotas (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    quota_type VARCHAR(50) NOT NULL,  -- qps/daily_calls/token_usage/concurrent
    resource_type VARCHAR(50) NOT NULL,  -- model_call/knowledge_base/agent/skill/all
    limit_value INTEGER NOT NULL,
    unit VARCHAR(20),  -- calls/tokens/second
    period_type VARCHAR(20) DEFAULT 'daily',  -- hourly/daily/weekly/monthly/none
    reset_time VARCHAR(20),  -- 重置时间，如 "00:00"
    scope_type VARCHAR(20) NOT NULL,  -- user/app/api_key
    scope_id VARCHAR(36),  -- 对应的 user_id/app_id/api_key_id
    parent_quota_id VARCHAR(36) REFERENCES quotas(id),
    is_inherited BOOLEAN DEFAULT FALSE,
    over_limit_action VARCHAR(20) DEFAULT 'reject',  -- reject/allow/log
    over_limit_rate DECIMAL(10, 4) DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    extra_config TEXT DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quotas_name ON quotas(name);
CREATE INDEX idx_quotas_type ON quotas(quota_type);
CREATE INDEX idx_quotas_scope ON quotas(scope_type, scope_id);
CREATE INDEX idx_quotas_resource ON quotas(resource_type);
CREATE INDEX idx_quotas_active ON quotas(is_active);

-- 配额使用量表
CREATE TABLE IF NOT EXISTS quota_usage (
    id VARCHAR(36) PRIMARY KEY,
    quota_id VARCHAR(36) REFERENCES quotas(id),
    scope_type VARCHAR(20) NOT NULL,
    scope_id VARCHAR(36) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    used_value INTEGER DEFAULT 0,
    limit_value INTEGER NOT NULL,
    remaining_value INTEGER DEFAULT 0,
    exceeded_value INTEGER DEFAULT 0,
    extra_data TEXT DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quota_usage_quota ON quota_usage(quota_id);
CREATE INDEX idx_quota_usage_scope ON quota_usage(scope_type, scope_id);
CREATE INDEX idx_quota_usage_period ON quota_usage(period_start, period_end);
CREATE UNIQUE INDEX idx_quota_usage_unique ON quota_usage(quota_id, scope_type, scope_id, period_start);

-- 配额检查日志表
CREATE TABLE IF NOT EXISTS quota_check_logs (
    id VARCHAR(36) PRIMARY KEY,
    quota_id VARCHAR(36) REFERENCES quotas(id),
    scope_type VARCHAR(20) NOT NULL,
    scope_id VARCHAR(36) NOT NULL,
    check_type VARCHAR(20) NOT NULL,  -- pre_check/post_update
    resource_type VARCHAR(50),
    requested_amount INTEGER DEFAULT 1,
    is_allowed BOOLEAN NOT NULL,
    reject_reason VARCHAR(100),
    context TEXT DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quota_check_logs_quota ON quota_check_logs(quota_id);
CREATE INDEX idx_quota_check_logs_scope ON quota_check_logs(scope_type, scope_id);
CREATE INDEX idx_quota_check_logs_created ON quota_check_logs(created_at);

-- 触发器
CREATE TRIGGER update_quotas_updated_at BEFORE UPDATE ON quotas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_quota_usage_updated_at BEFORE UPDATE ON quota_usage
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 注释
COMMENT ON TABLE quotas IS '配额定义表';
COMMENT ON TABLE quota_usage IS '配额使用量表';
COMMENT ON TABLE quota_check_logs IS '配额检查日志表';

COMMENT ON COLUMN quotas.quota_type IS '配额类型：qps/daily_calls/token_usage/concurrent';
COMMENT ON COLUMN quotas.resource_type IS '资源类型：model_call/knowledge_base/agent/skill/all';
COMMENT ON COLUMN quotas.period_type IS '周期类型：hourly/daily/weekly/monthly/none';
COMMENT ON COLUMN quotas.scope_type IS '配额层级：user/app/api_key';
COMMENT ON COLUMN quotas.over_limit_action IS '超额处理：reject/allow/log';

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

-- ========== 支付渠道系统（Phase 5.4） ==========

-- 支付渠道配置表
CREATE TABLE IF NOT EXISTS payment_channels (
    id VARCHAR(36) PRIMARY KEY,
    channel_name VARCHAR(50) UNIQUE NOT NULL,  -- alipay/wechat/unionpay
    channel_type VARCHAR(20) NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    icon_url VARCHAR(255),

    -- 认证配置
    app_id VARCHAR(100),
    merchant_id VARCHAR(100),
    api_key VARCHAR(255),
    api_secret VARCHAR(500),
    public_key TEXT,
    private_key TEXT,

    -- 配置项
    config TEXT DEFAULT '{}',

    -- 渠道状态
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    support_refund BOOLEAN DEFAULT TRUE,

    -- 限额配置
    min_amount DECIMAL(10, 2) DEFAULT 0,
    max_amount DECIMAL(10, 2) DEFAULT 999999,
    daily_limit DECIMAL(12, 2) DEFAULT 999999,

    -- 费率配置
    fee_rate DECIMAL(5, 4) DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payment_channels_name ON payment_channels(channel_name);
CREATE INDEX idx_payment_channels_active ON payment_channels(is_active);

-- 支付订单表
CREATE TABLE IF NOT EXISTS payment_orders (
    id VARCHAR(36) PRIMARY KEY,
    order_no VARCHAR(64) UNIQUE NOT NULL,
    transaction_id VARCHAR(100),

    -- 关联信息
    account_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    channel_id VARCHAR(36) NOT NULL REFERENCES payment_channels(id),

    -- 订单金额
    amount DECIMAL(10, 2) NOT NULL,
    actual_amount DECIMAL(10, 2),
    fee_amount DECIMAL(10, 4) DEFAULT 0,

    -- 支付信息
    payment_method VARCHAR(20),  -- web/app/h5/mini_program
    payment_status VARCHAR(20) DEFAULT 'pending',
    payment_time TIMESTAMP WITH TIME ZONE,

    -- 渠道回调数据
    callback_data TEXT DEFAULT '{}',
    callback_time TIMESTAMP WITH TIME ZONE,

    -- 订单描述
    subject VARCHAR(255),
    body TEXT,
    attach VARCHAR(255),

    -- 客户端信息
    client_ip VARCHAR(50),
    user_agent VARCHAR(500),

    -- 支付凭证
    pay_url VARCHAR(500),
    qr_code VARCHAR(500),
    app_param TEXT,

    -- 超时配置
    expires_at TIMESTAMP WITH TIME ZONE,
    timeout_expression VARCHAR(10),

    -- 退款信息
    refund_amount DECIMAL(10, 2) DEFAULT 0,
    refund_time TIMESTAMP WITH TIME ZONE,
    refund_reason VARCHAR(255),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payment_orders_order_no ON payment_orders(order_no);
CREATE INDEX idx_payment_orders_transaction ON payment_orders(transaction_id);
CREATE INDEX idx_payment_orders_account ON payment_orders(account_id);
CREATE INDEX idx_payment_orders_user ON payment_orders(user_id);
CREATE INDEX idx_payment_orders_status ON payment_orders(payment_status);
CREATE INDEX idx_payment_orders_created ON payment_orders(created_at);

-- 支付退款表
CREATE TABLE IF NOT EXISTS payment_refunds (
    id VARCHAR(36) PRIMARY KEY,
    refund_no VARCHAR(64) UNIQUE NOT NULL,
    refund_transaction_id VARCHAR(100),

    -- 关联订单
    order_id VARCHAR(36) NOT NULL REFERENCES payment_orders(id),
    account_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    channel_id VARCHAR(36) NOT NULL REFERENCES payment_channels(id),

    -- 退款金额
    refund_amount DECIMAL(10, 2) NOT NULL,
    refund_fee DECIMAL(10, 4) DEFAULT 0,

    -- 退款状态
    refund_status VARCHAR(20) DEFAULT 'pending',
    refund_time TIMESTAMP WITH TIME ZONE,

    -- 退款原因
    reason VARCHAR(255) NOT NULL,
    description TEXT,

    -- 渠道回调数据
    callback_data TEXT DEFAULT '{}',

    -- 操作信息
    operator_id VARCHAR(36),
    operator_comment VARCHAR(255),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payment_refunds_refund_no ON payment_refunds(refund_no);
CREATE INDEX idx_payment_refunds_order ON payment_refunds(order_id);
CREATE INDEX idx_payment_refunds_account ON payment_refunds(account_id);
CREATE INDEX idx_payment_refunds_status ON payment_refunds(refund_status);
CREATE INDEX idx_payment_refunds_created ON payment_refunds(created_at);

-- 支付回调日志表
CREATE TABLE IF NOT EXISTS payment_callback_logs (
    id VARCHAR(36) PRIMARY KEY,
    order_no VARCHAR(64) NOT NULL,
    channel_id VARCHAR(36) NOT NULL REFERENCES payment_channels(id),

    -- 回调数据
    raw_data TEXT NOT NULL,
    parsed_data TEXT DEFAULT '{}',

    -- 验证结果
    signature_valid BOOLEAN,
    verification_result TEXT,

    -- 处理结果
    is_processed BOOLEAN DEFAULT FALSE,
    process_result VARCHAR(20),
    error_message TEXT,

    -- 通知信息
    notify_id VARCHAR(100),
    notify_time TIMESTAMP WITH TIME ZONE,
    notify_type VARCHAR(20),

    client_ip VARCHAR(50),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payment_callback_logs_order ON payment_callback_logs(order_no);
CREATE INDEX idx_payment_callback_logs_channel ON payment_callback_logs(channel_id);
CREATE INDEX idx_payment_callback_logs_created ON payment_callback_logs(created_at);

-- 触发器
CREATE TRIGGER update_payment_channels_updated_at BEFORE UPDATE ON payment_channels
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_orders_updated_at BEFORE UPDATE ON payment_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_refunds_updated_at BEFORE UPDATE ON payment_refunds
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 注释
COMMENT ON TABLE payment_channels IS '支付渠道配置表';
COMMENT ON TABLE payment_orders IS '支付订单表';
COMMENT ON TABLE payment_refunds IS '支付退款表';
COMMENT ON TABLE payment_callback_logs IS '支付回调日志表';

COMMENT ON COLUMN payment_channels.channel_name IS '渠道名称：alipay/wechat/unionpay';
COMMENT ON COLUMN payment_channels.channel_type IS '渠道类型';
COMMENT ON COLUMN payment_channels.fee_rate IS '渠道费率（0.006 = 0.6%）';
COMMENT ON COLUMN payment_orders.payment_status IS '支付状态：pending/processing/success/failed/refunded/closed';
COMMENT ON COLUMN payment_refunds.refund_status IS '退款状态：pending/processing/success/failed';

-- ========== 账单和发票系统（Phase 5.5） ==========

-- 月度账单表
CREATE TABLE IF NOT EXISTS monthly_bills (
    id VARCHAR(36) PRIMARY KEY,
    bill_no VARCHAR(64) UNIQUE NOT NULL,

    -- 关联信息
    account_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,

    -- 账单周期
    billing_month VARCHAR(7) NOT NULL,  -- 格式：2026-03
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,

    -- 金额信息
    total_amount DECIMAL(10, 2) NOT NULL,
    paid_amount DECIMAL(10, 2) DEFAULT 0,
    unpaid_amount DECIMAL(10, 2) DEFAULT 0,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    refund_amount DECIMAL(10, 2) DEFAULT 0,

    -- 消费明细汇总
    model_call_amount DECIMAL(10, 2) DEFAULT 0,
    knowledge_base_amount DECIMAL(10, 2) DEFAULT 0,
    agent_amount DECIMAL(10, 2) DEFAULT 0,
    skill_amount DECIMAL(10, 2) DEFAULT 0,

    -- 使用量统计
    total_tokens INTEGER DEFAULT 0,
    total_calls INTEGER DEFAULT 0,
    total_storage_gb DECIMAL(10, 2) DEFAULT 0,

    -- 账单状态
    status VARCHAR(20) DEFAULT 'unpaid',  -- unpaid/paid/overdue/cancelled

    -- 支付信息
    payment_deadline TIMESTAMP WITH TIME ZONE,
    paid_at TIMESTAMP WITH TIME ZONE,
    payment_method VARCHAR(20),

    -- 账单文件
    bill_file_url VARCHAR(500),
    bill_data TEXT DEFAULT '{}',

    -- 通知信息
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP WITH TIME ZONE,

    -- 备注
    remark VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_monthly_bills_bill_no ON monthly_bills(bill_no);
CREATE INDEX idx_monthly_bills_account ON monthly_bills(account_id);
CREATE INDEX idx_monthly_bills_user ON monthly_bills(user_id);
CREATE INDEX idx_monthly_bills_month ON monthly_bills(billing_month);
CREATE INDEX idx_monthly_bills_status ON monthly_bills(status);

-- 发票表
CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR(36) PRIMARY KEY,
    invoice_no VARCHAR(64) UNIQUE,
    invoice_code VARCHAR(64),

    -- 关联信息
    account_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    bill_id VARCHAR(36) REFERENCES monthly_bills(id),

    -- 发票类型
    invoice_type VARCHAR(20) DEFAULT 'electronic',  -- electronic/paper
    status VARCHAR(20) DEFAULT 'pending',  -- pending/processing/issued/delivered/rejected

    -- 发票抬头信息
    title VARCHAR(200) NOT NULL,
    tax_id VARCHAR(50),
    company_address VARCHAR(200),
    company_phone VARCHAR(50),
    bank_name VARCHAR(100),
    bank_account VARCHAR(50),

    -- 发票金额
    amount DECIMAL(10, 2) NOT NULL,
    tax_rate DECIMAL(5, 4) DEFAULT 0.03,
    tax_amount DECIMAL(10, 2) DEFAULT 0,

    -- 收票信息
    receiver_name VARCHAR(100),
    receiver_email VARCHAR(100),
    receiver_phone VARCHAR(20),
    receiver_address VARCHAR(200),
    receiver_zip VARCHAR(10),

    -- 发票文件
    invoice_file_url VARCHAR(500),
    invoice_download_code VARCHAR(32),

    -- 物流信息（纸质发票）
    express_company VARCHAR(50),
    express_number VARCHAR(100),
    express_status VARCHAR(20),

    -- 申请信息
    application_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    issued_time TIMESTAMP WITH TIME ZONE,
    delivered_time TIMESTAMP WITH TIME ZONE,

    -- 拒绝信息
    reject_reason VARCHAR(500),

    -- 备注
    remark VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_invoices_invoice_no ON invoices(invoice_no);
CREATE INDEX idx_invoices_account ON invoices(account_id);
CREATE INDEX idx_invoices_user ON invoices(user_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_type ON invoices(invoice_type);

-- 发票申请表
CREATE TABLE IF NOT EXISTS invoice_applications (
    id VARCHAR(36) PRIMARY KEY,
    application_no VARCHAR(64) UNIQUE NOT NULL,

    -- 关联信息
    account_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,

    -- 申请信息
    invoice_type VARCHAR(20) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,

    -- 抬头信息
    title VARCHAR(200) NOT NULL,
    tax_id VARCHAR(50),
    company_address VARCHAR(200),
    company_phone VARCHAR(50),
    bank_name VARCHAR(100),
    bank_account VARCHAR(50),

    -- 收票信息
    receiver_name VARCHAR(100),
    receiver_email VARCHAR(100),
    receiver_phone VARCHAR(20),
    receiver_address VARCHAR(200),
    receiver_zip VARCHAR(10),

    -- 关联账单（可多张）
    bill_ids TEXT DEFAULT '[]',

    -- 审核状态
    audit_status VARCHAR(20) DEFAULT 'pending',  -- pending/approved/rejected
    auditor_id VARCHAR(36),
    audit_time TIMESTAMP WITH TIME ZONE,
    audit_remark VARCHAR(500),

    -- 申请状态
    status VARCHAR(20) DEFAULT 'pending',  -- pending/processing/completed/cancelled

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_invoice_applications_app_no ON invoice_applications(application_no);
CREATE INDEX idx_invoice_applications_account ON invoice_applications(account_id);
CREATE INDEX idx_invoice_applications_audit ON invoice_applications(audit_status);

-- 账单邮件日志表
CREATE TABLE IF NOT EXISTS bill_email_logs (
    id VARCHAR(36) PRIMARY KEY,
    bill_id VARCHAR(36) NOT NULL REFERENCES monthly_bills(id),
    user_id VARCHAR(36) NOT NULL,

    -- 邮件信息
    recipient_email VARCHAR(100) NOT NULL,
    email_subject VARCHAR(200),
    email_content TEXT,

    -- 发送状态
    send_status VARCHAR(20) DEFAULT 'pending',  -- pending/success/failed
    send_time TIMESTAMP WITH TIME ZONE,
    error_message TEXT,

    -- 打开追踪
    is_opened BOOLEAN DEFAULT FALSE,
    opened_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bill_email_logs_bill ON bill_email_logs(bill_id);
CREATE INDEX idx_bill_email_logs_user ON bill_email_logs(user_id);
CREATE INDEX idx_bill_email_logs_status ON bill_email_logs(send_status);

-- 触发器
CREATE TRIGGER update_monthly_bills_updated_at BEFORE UPDATE ON monthly_bills
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_invoice_applications_updated_at BEFORE UPDATE ON invoice_applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 注释
COMMENT ON TABLE monthly_bills IS '月度账单表';
COMMENT ON TABLE invoices IS '发票表';
COMMENT ON TABLE invoice_applications IS '发票申请表';
COMMENT ON TABLE bill_email_logs IS '账单邮件日志表';

COMMENT ON COLUMN monthly_bills.billing_month IS '账单月份：YYYY-MM';
COMMENT ON COLUMN monthly_bills.status IS '账单状态：unpaid/paid/overdue/cancelled';
COMMENT ON COLUMN invoices.invoice_type IS '发票类型：electronic/paper';
COMMENT ON COLUMN invoices.status IS '发票状态：pending/processing/issued/delivered/rejected';

-- ========== 完成 ==========

-- ========== 告警中心系统（Phase 5.6） ==========

-- 告警通知渠道配置表
CREATE TABLE IF NOT EXISTS alert_channels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    channel_type VARCHAR(50) NOT NULL,  -- email/sms/webhook/slack
    display_name VARCHAR(200),
    config TEXT DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id)
);

CREATE INDEX idx_alert_channels_name ON alert_channels(name);
CREATE INDEX idx_alert_channels_type ON alert_channels(channel_type);

-- 告警订阅表
CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    alert_type VARCHAR(50) NOT NULL,  -- balance/quota/cost
    resource_type VARCHAR(50),  -- account/app/api_key
    resource_id VARCHAR(100),
    channel_ids TEXT DEFAULT '[]',
    is_enabled BOOLEAN DEFAULT TRUE,
    custom_threshold FLOAT,
    custom_severity VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alert_subscriptions_user ON alert_subscriptions(user_id);
CREATE INDEX idx_alert_subscriptions_type ON alert_subscriptions(alert_type);
CREATE UNIQUE INDEX idx_subscription_unique ON alert_subscriptions(user_id, alert_type, resource_type, resource_id);

-- 预警记录表
CREATE TABLE IF NOT EXISTS warning_alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,  -- balance/quota/cost
    alert_subtype VARCHAR(50),  -- low_balance/high_usage/over_budget
    resource_type VARCHAR(50),  -- account/app/api_key
    resource_id VARCHAR(100),
    user_id INTEGER REFERENCES users(id),
    current_value FLOAT NOT NULL,
    threshold_value FLOAT NOT NULL,
    unit VARCHAR(50),  -- CNY/tokens/calls/percent
    severity VARCHAR(20) DEFAULT 'warning',  -- info/warning/error/critical
    status VARCHAR(20) DEFAULT 'pending',  -- pending/sent/acknowledged/resolved
    message TEXT,
    notified_channels TEXT DEFAULT '[]',
    notified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_warning_alerts_type ON warning_alerts(alert_type);
CREATE INDEX idx_warning_alerts_status ON warning_alerts(status);
CREATE INDEX idx_warning_alerts_resource ON warning_alerts(resource_type, resource_id);
CREATE INDEX idx_warning_alerts_user ON warning_alerts(user_id);
CREATE INDEX idx_warning_alerts_created ON warning_alerts(created_at);

-- 告警模板表
CREATE TABLE IF NOT EXISTS alert_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    template_type VARCHAR(50) NOT NULL,  -- email/sms/webhook
    subject_template TEXT,
    content_template TEXT NOT NULL,
    alert_types TEXT DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id)
);

CREATE INDEX idx_alert_templates_type ON alert_templates(template_type);

-- 触发器
CREATE TRIGGER update_alert_channels_updated_at BEFORE UPDATE ON alert_channels
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alert_subscriptions_updated_at BEFORE UPDATE ON alert_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_warning_alerts_updated_at BEFORE UPDATE ON warning_alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alert_templates_updated_at BEFORE UPDATE ON alert_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 注释
COMMENT ON TABLE alert_channels IS '告警通知渠道配置表';
COMMENT ON TABLE alert_subscriptions IS '告警订阅表';
COMMENT ON TABLE warning_alerts IS '预警记录表';
COMMENT ON TABLE alert_templates IS '告警模板表';

COMMENT ON COLUMN warning_alerts.alert_type IS '预警类型：balance/quota/cost';
COMMENT ON COLUMN warning_alerts.alert_subtype IS '预警子类型：low_balance/high_usage/over_budget';
COMMENT ON COLUMN warning_alerts.status IS '预警状态：pending/sent/acknowledged/resolved';
