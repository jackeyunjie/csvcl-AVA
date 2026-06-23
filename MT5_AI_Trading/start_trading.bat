@echo off
chcp 65001 >nul
echo ==========================================
echo    MT5 AI 量化交易系统
echo ==========================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请安装Python 3.8+
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist .venv\Scripts\activate.bat (
    echo [信息] 创建虚拟环境...
    python -m venv .venv
)

echo [信息] 激活虚拟环境...
call .venv\Scripts\activate.bat

REM 安装依赖
echo [信息] 检查依赖...
pip install -q -r requirements.txt

REM 创建必要目录
if not exist logs mkdir logs
if not exist data\historical mkdir data\historical
if not exist data\models mkdir data\models

echo.
echo [信息] 启动交易系统...
echo [信息] 按Ctrl+C停止
echo.

REM 启动主程序
python python\core\main_controller.py --config config\trading_config.yaml

echo.
echo [信息] 系统已停止
pause
