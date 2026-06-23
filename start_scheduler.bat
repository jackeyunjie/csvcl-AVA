@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title MT4数据处理定时调度器

REM 获取脚本所在目录并切换到该目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ====================================================
echo        MT4数据处理系统 - 定时调度器
echo ====================================================
echo 当前时间: %date% %time%
echo 调度器将在每天早上7:03自动执行auto_email_config.py
echo 日志将保存到 scheduler.log 文件中
echo 按Ctrl+C可以停止调度器
echo ====================================================
echo.
echo 选择运行模式:
echo 1. 定时模式 (默认) - 仅按计划执行
echo 2. 立即+定时模式 - 立即执行一次，然后按计划执行
echo.
choice /c 12 /m "请选择运行模式"
if errorlevel 2 (
    echo 正在以立即+定时模式启动调度器...
    python scheduler.py --immediate
) else (
    echo 正在以定时模式启动调度器...
    python scheduler.py
)
if %errorlevel% neq 0 (
    echo.
    echo 调度器启动失败，请检查错误信息
    pause
)