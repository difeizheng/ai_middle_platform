@echo off
REM Phase 2 开发启动脚本

echo ========================================
echo AI 中台系统 - Phase 2 开发启动
echo ========================================
echo.

echo Phase 2 重点：
echo   1. 智能体工厂 - 可视化编排的多智能体协作系统
echo   2. MCP 连接器 - 对接外部系统和服务的通用连接器
echo   3. Skills 市场 - 开发者生态和技能共享平台
echo.

echo 预计周期：2026 年 4 月 - 2026 年 6 月
echo.

echo ========================================
echo 检查 Phase 1 完成状态...
echo ========================================
echo.

REM 检查依赖
echo 安装/更新依赖...
pip install -r requirements.txt

echo.
echo ========================================
echo Phase 1 测试运行...
echo ========================================
echo.

REM 运行 Phase 1 测试
pytest tests/ -v --tb=short

echo.
echo ========================================
echo Phase 2 开发准备完成！
echo ========================================
echo.
echo 下一步:
echo   1. 阅读 Phase 2 规划文档：docs/PHASE2_PLANNING.md
echo   2. 开始智能体工厂开发
echo   3. 开发 MCP 连接器
echo   4. 构建 Skills 市场
echo.
