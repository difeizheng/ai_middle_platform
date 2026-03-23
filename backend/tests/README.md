# 测试指南

本目录包含 AI 中台系统的完整测试套件。

## 目录结构

```
tests/
├── conftest.py              # pytest 配置和夹具
├── pytest.ini               # pytest 配置文件
├── __init__.py
├ ├── api/                   # API 层测试
│   ├── __init__.py
│   ├── test_auth.py         # 认证 API 测试
│   ├── test_middleware.py   # 中间件测试
│   └── test_scenarios.py    # 试点场景 API 测试
├ ├── services/              # 服务层测试
│   ├── __init__.py
│   ├── test_parser.py       # 文档解析器测试
│   └── test_chunker.py      # 文本分片器测试
└── test_integration.py      # 集成测试
```

## 运行测试

### 快速运行

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块
pytest tests/services/ -v
pytest tests/api/ -v

# 运行特定测试文件
pytest tests/test_integration.py -v

# 运行特定测试用例
pytest tests/services/test_parser.py::TestDocumentParser::test_parse_txt -v
```

### 覆盖率测试

```bash
# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# 查看覆盖率摘要
pytest tests/ --cov=app --cov-report=term-missing

# 生成 XML 报告（用于 CI/CD）
pytest tests/ --cov=app --cov-report=xml
```

### 使用测试脚本

```bash
# Linux/Mac
./run_tests.sh

# Windows
run_tests.bat
```

## 测试依赖

运行测试需要安装以下依赖：

```bash
pip install pytest pytest-asyncio pytest-cov httpx aiosqlite
```

或使用测试脚本自动安装。

## 测试用例

### 服务层测试 (~24 个用例)

#### 文档解析器 (test_parser.py)
- `test_supported_formats` - 测试支持的格式
- `test_parse_txt` - 测试 TXT 文件解析
- `test_parse_md` - 测试 Markdown 文件解析
- `test_parse_unsupported_format` - 测试不支持的格式
- `test_parse_nonexistent_file` - 测试不存在的文件
- `test_parse_pdf_placeholder` - PDF 解析占位测试
- `test_parse_docx_placeholder` - Word 解析占位测试
- `test_get_file_info` - 测试获取文件信息

#### 文本分片器 (test_chunker.py)
- `test_fixed_size_chunking` - 测试固定大小分片
- `test_paragraph_chunking` - 测试段落下分片
- `test_sentence_chunking` - 测试句子分片
- `test_empty_input` - 测试空输入
- `test_none_input` - 测试 None 输入
- `test_chunk_metadata` - 测试分片元数据
- `test_overlap_handling` - 测试重叠处理
- `test_custom_chunk_size` - 测试自定义分片大小
- `test_custom_overlap` - 测试自定义重叠大小

#### 限流器 (test_middleware.py)
- `test_consume_within_limit` - 测试在限制内的请求
- `test_consume_exceeds_limit` - 测试超出限制的请求
- `test_different_keys` - 测试不同的键独立计数
- `test_window_reset` - 测试时间窗口重置
- `test_consume_with_tokens` - 测试多 token 消耗
- `test_invalid_key` - 测试无效的键
- `test_rate_limiter_state` - 测试限流器状态

### API 层测试 (~13 个用例)

#### 认证 API (test_auth.py)
- `test_login_success` - 测试登录成功
- `test_login_invalid_credentials` - 测试无效凭证
- `test_get_current_user` - 测试获取当前用户
- `test_token_creation` - 测试 token 创建
- `test_login_missing_username` - 测试缺少用户名
- `test_login_missing_password` - 测试缺少密码

#### 试点场景 API (test_scenarios.py)
- `test_document_qa_query` - 测试文档问答查询
- `test_document_qa_chat` - 测试文档问答聊天
- `test_contract_compare` - 测试合同比对
- `test_customer_service_chat` - 测试智能客服聊天
- `test_create_session` - 测试创建会话
- `test_generate_report` - 测试生成报告
- `test_generate_meeting_summary` - 测试生成会议纪要
- `test_list_scenarios` - 测试获取场景列表

### 集成测试 (~12 个用例)

#### 健康检查 (TestHealthCheck)
- `test_health_endpoint` - 测试健康检查端点
- `test_root_endpoint` - 测试根路径

#### API 文档 (TestAPI_docs)
- `test_openapi_json` - 测试 OpenAPI 文档
- `test_docs_endpoint` - 测试 Swagger 文档
- `test_redoc_endpoint` - 测试 ReDoc 文档

#### 中间件 (TestMiddleware)
- `test_request_logging` - 测试请求日志中间件
- `test_request_id_propagation` - 测试请求 ID 传递

#### CORS (TestCORS)
- `test_cors_headers` - 测试 CORS 头

#### 错误处理 (TestErrorHandling)
- `test_404_handler` - 测试 404 处理
- `test_method_not_allowed` - 测试方法不允许

#### 认证集成 (TestAuthIntegration)
- `test_protected_endpoint_without_auth` - 测试受保护端点无需认证
- `test_protected_endpoint_with_invalid_token` - 测试无效 token

## 测试夹具

### conftest.py 提供的夹具

- `event_loop` - 事件循环（session 级别）
- `test_engine` - 测试数据库引擎（function 级别）
- `test_db` - 测试数据库会话（function 级别）
- `client` - 测试客户端（function 级别）
- `test_user_data` - 测试用户数据
- `test_model_data` - 测试模型数据

## 持续集成

测试套件可以在 CI/CD 流水线中运行：

```yaml
# GitHub Actions 示例
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: |
          pytest tests/ -v --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 测试最佳实践

1. **测试隔离**: 每个测试用例应该独立运行，不依赖其他测试的状态
2. **使用夹具**: 重用测试设置逻辑，保持测试代码 DRY
3. **异步测试**: 使用 `@pytest.mark.asyncio` 标记异步测试
4. **测试命名**: 测试函数名应该清晰描述测试意图
5. **断言明确**: 每个测试应该有明确的断言
6. **覆盖率目标**: 目标是核心业务逻辑达到 80%+覆盖率

## 故障排除

### 常见问题

1. **测试运行缓慢**: 使用 `-x` 在第一次失败时停止，使用 `-k` 运行特定测试
2. **数据库连接失败**: 确保测试使用 SQLite 内存数据库，不需要外部数据库
3. **异步测试失败**: 确保使用 `@pytest.mark.asyncio` 装饰器
4. **导入错误**: 确保在 backend 目录下运行测试

### 调试测试

```bash
# 使用详细输出
pytest tests/ -vvv

# 打印输出
pytest tests/ -s

# 在失败时进入调试器
pytest tests/ --pdb
```
