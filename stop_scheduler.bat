@echo off
REM 获取脚本所在目录并切换到该目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ====================================================
echo        MT4数据处理系统 - 停止定时调度器
echo ====================================================
echo 正在停止定时调度器...
echo.
taskkill /f /im python.exe /fi "WINDOWTITLE eq *MT4数据处理定时调度器*"
echo.
echo 定时调度器已停止
echo ====================================================
pause