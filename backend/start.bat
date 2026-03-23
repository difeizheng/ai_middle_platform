@echo off
REM AI 中台系统 - Windows 开发启动脚本

echo =======================================
echo   AI 中台系统 - 启动脚本 (Windows)
echo =======================================

REM 进入后端目录
cd /d "%~dp0"

REM 创建必要的目录
if not exist "logs" mkdir logs
if not exist "data\storage" mkdir data\storage

REM 检查 Python 版本
echo [1/4] 检查 Python 版本...
python --version

REM 安装依赖
echo [2/4] 安装依赖...
pip install -e ".[dev]"

REM 启动服务
echo [3/4] 启动服务...
echo =======================================
echo   服务启动成功！
echo   API 文档：http://localhost:8000/docs
echo   健康检查：http://localhost:8000/health
echo =======================================

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
