-- AI 中台系统 - 智能体工厂数据库迁移脚本
-- Phase 2: 智能体工厂
-- 日期：2026-03-24

-- ========== 智能体表 ==========
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    role VARCHAR(100),  -- planner, executor, reviewer, summarizer
    model_id INTEGER REFERENCES models(id),
    config JSONB DEFAULT '{}',
    tools JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_agents_name ON agents(name);
CREATE INDEX idx_agents_role ON agents(role);
CREATE INDEX idx_agents_is_active ON agents(is_active);
CREATE INDEX idx_agents_created_by ON agents(created_by);

-- 添加注释
COMMENT ON TABLE agents IS '智能体表';
COMMENT ON COLUMN agents.role IS '角色：planner(规划者), executor(执行者), reviewer(审核者), summarizer(总结者)';
COMMENT ON COLUMN agents.config IS '智能体配置：temperature, max_tokens, system_prompt, memory_enabled, reflection_enabled';
COMMENT ON COLUMN agents.tools IS '绑定工具列表：[{id, name, config}]';


-- ========== 智能体流程表 ==========
CREATE TABLE IF NOT EXISTS agent_flows (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    version VARCHAR(50) DEFAULT '1.0.0',
    nodes JSONB DEFAULT '[]',
    edges JSONB DEFAULT '[]',
    variables JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    is_template BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_agent_flows_name ON agent_flows(name);
CREATE INDEX idx_agent_flows_is_active ON agent_flows(is_active);
CREATE INDEX idx_agent_flows_is_template ON agent_flows(is_template);

-- 添加注释
COMMENT ON TABLE agent_flows IS '智能体流程表（可视化编排的工作流）';
COMMENT ON COLUMN agent_flows.nodes IS '节点定义：[{id, type, position, data, inputs, outputs}]';
COMMENT ON COLUMN agent_flows.edges IS '连接关系：[{id, source, target, sourceHandle, targetHandle}]';
COMMENT ON COLUMN agent_flows.variables IS '流程变量定义：[{name, type, default, description}]';


-- ========== 智能体执行历史表 ==========
CREATE TABLE IF NOT EXISTS agent_executions (
    id SERIAL PRIMARY KEY,
    flow_id INTEGER REFERENCES agent_flows(id),
    agent_id INTEGER REFERENCES agents(id),
    status VARCHAR(50) DEFAULT 'running',  -- running, success, failed, cancelled
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    logs JSONB DEFAULT '[]',
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agent_executions_flow_id ON agent_executions(flow_id);
CREATE INDEX idx_agent_executions_agent_id ON agent_executions(agent_id);
CREATE INDEX idx_agent_executions_status ON agent_executions(status);
CREATE INDEX idx_agent_executions_created_at ON agent_executions(created_at DESC);

-- 添加注释
COMMENT ON TABLE agent_executions IS '智能体执行历史表';
COMMENT ON COLUMN agent_executions.logs IS '执行日志：[{timestamp, node_id, level, message, data}]';


-- ========== 智能体记忆表 ==========
CREATE TABLE IF NOT EXISTS agent_memories (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    session_id VARCHAR(100),
    memory_type VARCHAR(50),  -- short_term, long_term, episodic, semantic
    content TEXT,
    embedding JSONB,
    importance INTEGER DEFAULT 1,  -- 1-5
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_agent_memories_agent_id ON agent_memories(agent_id);
CREATE INDEX idx_agent_memories_session_id ON agent_memories(session_id);
CREATE INDEX idx_agent_memories_memory_type ON agent_memories(memory_type);
CREATE INDEX idx_agent_memories_importance ON agent_memories(importance);

-- 添加注释
COMMENT ON TABLE agent_memories IS '智能体记忆表（长期记忆）';
COMMENT ON COLUMN agent_memories.embedding IS '向量表示：[0.1, 0.2, ...]';


-- ========== 智能体工具注册表 ==========
CREATE TABLE IF NOT EXISTS agent_tools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(100),  -- search, compute, code, document, api, custom
    tool_type VARCHAR(50),  -- builtin, api, code, script
    config JSONB DEFAULT '{}',
    inputs JSONB DEFAULT '[]',
    outputs JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    is_builtin BOOLEAN DEFAULT FALSE,
    author VARCHAR(200),
    version VARCHAR(50) DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_agent_tools_name ON agent_tools(name);
CREATE INDEX idx_agent_tools_category ON agent_tools(category);
CREATE INDEX idx_agent_tools_is_active ON agent_tools(is_active);

-- 添加注释
COMMENT ON TABLE agent_tools IS '智能体工具注册表';
COMMENT ON COLUMN agent_tools.config IS '工具配置：{endpoint, method, code, script_path}';
COMMENT ON COLUMN agent_tools.inputs IS '输入定义（JSON Schema）';
COMMENT ON COLUMN agent_tools.outputs IS '输出定义（JSON Schema）';


-- ========== 初始化数据 ==========

-- 内置工具
INSERT INTO agent_tools (name, description, category, tool_type, is_builtin, is_active, inputs, outputs, config) VALUES
('web_search', '在互联网上搜索信息', 'search', 'builtin', TRUE, TRUE,
 '[{"name": "query", "type": "string", "required": true, "description": "搜索关键词"}, {"name": "num_results", "type": "number", "required": false, "description": "返回数量", "default": 10}]',
 '[{"name": "results", "type": "array", "description": "搜索结果列表"}]',
 '{"search_engine": "google"}'),

('code_executor', '执行代码（支持 Python）', 'code', 'builtin', TRUE, TRUE,
 '[{"name": "code", "type": "string", "required": true, "description": "代码内容"}, {"name": "language", "type": "string", "required": false, "description": "编程语言", "default": "python"}, {"name": "timeout", "type": "number", "required": false, "description": "超时时间", "default": 30}]',
 '[{"name": "result", "type": "object", "description": "执行结果"}]',
 '{"sandbox": "local"}'),

('calculator', '执行数学计算', 'compute', 'builtin', TRUE, TRUE,
 '[{"name": "expression", "type": "string", "required": true, "description": "数学表达式"}]',
 '[{"name": "result", "type": "number", "description": "计算结果"}]',
 '{}'),

('http_request', '发送 HTTP 请求', 'api', 'builtin', TRUE, TRUE,
 '[{"name": "url", "type": "string", "required": true, "description": "请求 URL"}, {"name": "method", "type": "string", "required": false, "description": "请求方法", "default": "GET"}, {"name": "headers", "type": "object", "required": false, "description": "请求头"}, {"name": "body", "type": "object", "required": false, "description": "请求体"}, {"name": "timeout", "type": "number", "required": false, "description": "超时时间", "default": 30}]',
 '[{"name": "response", "type": "object", "description": "HTTP 响应"}]',
 '{"default_timeout": 30}'),

('document_parser', '解析文档（PDF/Word/Excel/PPT/TXT/MD）', 'document', 'builtin', TRUE, TRUE,
 '[{"name": "file_path", "type": "string", "required": true, "description": "文件路径"}, {"name": "file_type", "type": "string", "required": false, "description": "文件类型"}]',
 '[{"name": "content", "type": "string", "description": "文档内容"}]',
 '{}');

-- 示例智能体
INSERT INTO agents (name, description, role, config, tools, is_active) VALUES
('规划助手', '擅长分解复杂任务并制定执行计划', 'planner',
 '{"temperature": 0.7, "max_tokens": 4096, "system_prompt": "你是一个任务规划专家。", "memory_enabled": true, "reflection_enabled": true}',
 '[{"id": "web_search", "name": "网页搜索"}]',
 TRUE),

('执行专家', '高效的执行者，擅长调用工具完成任务', 'executor',
 '{"temperature": 0.5, "max_tokens": 4096, "system_prompt": "你是一个高效的执行者。", "memory_enabled": true, "reflection_enabled": false}',
 '[{"id": "web_search", "name": "网页搜索"}, {"id": "code_executor", "name": "代码执行"}, {"id": "http_request", "name": "HTTP 请求"}]',
 TRUE),

('审核员', '严格的审核者，擅长检查和改进输出质量', 'reviewer',
 '{"temperature": 0.3, "max_tokens": 4096, "system_prompt": "你是一个严格的审核者，擅长发现错误和问题。", "memory_enabled": false, "reflection_enabled": true}',
 '[]',
 TRUE),

('总结者', '优秀的总结者，擅长从大量信息中提取关键点', 'summarizer',
 '{"temperature": 0.5, "max_tokens": 4096, "system_prompt": "你是一个优秀的总结者，擅长提取关键信息。", "memory_enabled": true, "reflection_enabled": false}',
 '[{"id": "document_parser", "name": "文档解析"}]',
 TRUE);

-- 示例流程模板：搜索 - 分析-总结
INSERT INTO agent_flows (name, description, version, nodes, edges, variables, is_template, is_active) VALUES
('搜索分析流程', '搜索信息并分析总结的工作流', '1.0.0',
 '[
    {"id": "input_1", "type": "input", "position": {"x": 100, "y": 200}, "data": {"label": "用户输入", "output_name": "query"}, "inputs": [], "outputs": [{"name": "query", "type": "string"}]},
    {"id": "agent_search", "type": "agent", "position": {"x": 300, "y": 200}, "data": {"label": "搜索", "agent_id": 2}, "inputs": [{"name": "input", "type": "string"}], "outputs": [{"name": "output", "type": "string"}]},
    {"id": "agent_analyze", "type": "agent", "position": {"x": 500, "y": 200}, "data": {"label": "分析", "agent_id": 2}, "inputs": [{"name": "input", "type": "string"}], "outputs": [{"name": "output", "type": "string"}]},
    {"id": "agent_summarize", "type": "agent", "position": {"x": 700, "y": 200}, "data": {"label": "总结", "agent_id": 4}, "inputs": [{"name": "input", "type": "string"}], "outputs": [{"name": "output", "type": "string"}]},
    {"id": "output_1", "type": "output", "position": {"x": 900, "y": 200}, "data": {"label": "输出"}, "inputs": [{"name": "final", "type": "string"}], "outputs": []}
  ]',
 '[
    {"id": "edge_1", "source": "input_1", "target": "agent_search", "sourceHandle": "query", "targetHandle": "input"},
    {"id": "edge_2", "source": "agent_search", "target": "agent_analyze", "sourceHandle": "output", "targetHandle": "input"},
    {"id": "edge_3", "source": "agent_analyze", "target": "agent_summarize", "sourceHandle": "output", "targetHandle": "input"},
    {"id": "edge_4", "source": "agent_summarize", "target": "output_1", "sourceHandle": "output", "targetHandle": "final"}
  ]',
 '[{"name": "query", "type": "string", "default": "", "description": "搜索关键词"}]',
 TRUE, TRUE);

-- 完成提示
SELECT '智能体工厂数据库迁移完成！' AS status;
