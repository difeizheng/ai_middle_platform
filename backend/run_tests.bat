@echo off
REM 测试运行脚本 (Windows)

echo ========================================
echo AI 中台系统 - 测试套件
echo ========================================

REM 切换到后端目录
cd /d "%~dp0"

REM 安装测试依赖（如果需要）
echo.
echo 1. 检查依赖...
pip install -q pytest pytest-asyncio pytest-cov httpx aiosqlite

REM 运行单元测试
echo.
echo 2. 运行单元测试...
pytest tests/services/ -v --tb=short

REM 运行 API 测试
echo.
echo 3. 运行 API 测试...
pytest tests/api/ -v --tb=short

REM 运行集成测试
echo.
echo 4. 运行集成测试...
pytest tests/test_integration.py -v --tb=short

REM 生成覆盖率报告
echo.
echo 5. 生成覆盖率报告...
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

echo.
echo ========================================
echo 测试完成！
echo 覆盖率报告：htmlcov/index.html
echo ========================================
