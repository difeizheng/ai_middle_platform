# AI 中台系统

> 企业级 AI 能力基础设施 - 构建可持续的 AI 能力体系

**版本：** 0.2.0
**日期：** 2026 年 3 月 24 日

---

## 快速开始

### 方式一：Docker Compose 部署（推荐）

```bash
# 启动所有服务
docker-compose -f deploy/docker-compose.yml up -d

# 查看日志
docker-compose logs -f backend
```

### 方式二：本地开发

```bash
# 启动后端
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload

# 启动前端
cd frontend
npm install
npm run dev
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 前端 | http://localhost:3000 |

### 默认账户

```
用户名：admin
密码：admin123
```

---

## 项目结构

```
.
├── backend/              # 后端服务
│   ├── app/
│   │   ├── api/         # API 路由
│   │   ├── auth/        # 认证授权
│   │   ├── core/        # 核心配置
│   │   ├── models/      # 数据模型
│   │   └── main.py      # 入口文件
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/             # 前端应用
│   ├── src/
│   │   ├── pages/       # 页面组件
│   │   ├── store/       # 状态管理
│   │   └── utils/       # 工具函数
│   └── package.json
├── deploy/               # 部署配置
│   ├── docker-compose.yml
│   ├── prometheus.yml
│   └── init.sql
└── docs/                 # 文档
    ├── architecture.md
    └── DEV_LOG.md
```

---

## 核心功能

- **模型工厂** - 统一接入和管理多模型
- **知识工厂** - 文档解析、向量化、检索
- **API 网关** - 认证鉴权、限流熔断
- **应用管理** - 应用接入和 API Key 管理
- **日志审计** - 全链路日志和统计

---

详细文档请查看 `docs/` 目录。
