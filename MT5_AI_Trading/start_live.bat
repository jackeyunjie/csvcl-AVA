@echo off
chcp 65001 >nul
echo ==========================================
echo   MT5 AI 实盘交易引擎
echo   版本: V3 (回测优化版)
echo ==========================================
echo.
echo 回测参数:
echo   - 最优持仓: 12小时
echo   - 目标品种: US_30, US_500, US_TECH100
echo   - 最小置信度: 0.70
echo   - 自动平仓: 12小时后
echo.
echo 模式选择:
echo   1. 模拟模式 (推荐先测试)
echo   2. 实盘模式
echo.
set /p mode="选择模式 (1/2): "

if "%mode%"=="1" (
    echo.
    echo [模拟模式] 只打印信号，不发送交易指令
    python run_live.py
) else if "%mode%"=="2" (
    echo.
    echo [实盘模式] 信号将发送到 MT5 EA 执行
    echo 请确认 MT5 EA 已加载并运行
    pause
    python run_live.py --live
) else (
    echo 无效选择
    pause
)
