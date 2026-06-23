@echo off
chcp 65001 >nul
title Fundamental Data Pipeline

echo ==========================================
echo  美股基本面 + 宏观指标数据管道
echo ==========================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请确保已安装并加入 PATH
    pause
    exit /b 1
)

:: 检查虚拟环境
if exist ".venv\Scripts\python.exe" (
    echo [信息] 使用虚拟环境 .venv
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    echo [信息] 使用系统 Python
    set "PYTHON=python"
)

:: 检查依赖
echo [信息] 检查依赖...
%PYTHON% -c "import yfinance, duckdb, pandas" 2>nul
if errorlevel 1 (
    echo [警告] 依赖未安装，尝试自动安装...
    %PYTHON% -m pip install yfinance duckdb pandas fredapi beautifulsoup4 -q
)

:: 创建日志目录
if not exist "logs" mkdir logs

echo.
echo [1] 全量更新 (个股 + 宏观)
echo [2] 仅更新个股
echo [3] 仅更新宏观
echo [4] 显示数据库汇总
echo [5] 启动定时调度 (每周五21:00)
echo [6] 查询某只股票
echo.
set /p choice="请选择操作 [1-6]: "

if "%choice%"=="1" (
    echo [执行] 全量更新...
    %PYTHON% python\data\fundamental_pipeline.py --force
) else if "%choice%"=="2" (
    echo [执行] 仅更新个股...
    %PYTHON% python\data\fundamental_pipeline.py --equity-only --force
) else if "%choice%"=="3" (
    echo [执行] 仅更新宏观...
    %PYTHON% python\data\fundamental_pipeline.py --macro-only --force
) else if "%choice%"=="4" (
    echo [执行] 显示汇总...
    %PYTHON% python\data\fundamental_pipeline.py --summary
) else if "%choice%"=="5" (
    echo [执行] 启动定时调度...
    echo 按 Ctrl+C 停止
    %PYTHON% python\data\fundamental_pipeline.py --schedule
) else if "%choice%"=="6" (
    set /p sym="输入股票代码 (如 AAPL): "
    %PYTHON% python\data\fundamental_pipeline.py --query-eq %sym%
) else (
    echo [错误] 无效选择
)

echo.
pause
