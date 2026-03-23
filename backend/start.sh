#!/bin/bash
# AI 中台系统 - 开发启动脚本

set -e

echo "======================================="
echo "  AI 中台系统 - 启动脚本"
echo "======================================="

# 进入后端目录
cd "$(dirname "$0")"

# 创建必要的目录
mkdir -p logs data/storage

# 检查 Python 版本
echo "[1/4] 检查 Python 版本..."
python --version

# 安装依赖
echo "[2/4] 安装依赖..."
pip install -e ".[dev]"

# 初始化数据库
echo "[3/4] 初始化数据库..."
# 首次启动时会自动创建表

# 启动服务
echo "[4/4] 启动服务..."
echo "======================================="
echo "  服务启动成功！"
echo "  API 文档：http://localhost:8000/docs"
echo "  健康检查：http://localhost:8000/health"
echo "======================================="

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
