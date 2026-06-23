@echo off
chcp 65001 >nul
echo ==========================================
echo    MT5 AI 量化交易系统 - 双通道模式
echo ==========================================
echo.
echo  [MT5#1] KVB      - 生产环境 (端口: 5555/5556)
echo  [MT5#2] AVATRADE - 研发环境 (端口: 5565/5566)
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
echo ==========================================
echo  启动前检查清单：
echo ==========================================
echo.
echo  [ ] MT5#1 (KVB) 已启动，EA加载在图表上
echo  [ ] MT5#1 EA属性：允许算法交易 + 允许DLL导入
echo  [ ] MT5#2 (AVATRADE) 已启动，EA加载在图表上
echo  [ ] MT5#2 EA属性：允许算法交易 + 允许DLL导入
echo.
echo  确认以上检查完成后按任意键启动...
pause >nul

echo.
echo [信息] 启动双通道交易系统...
echo [信息] 按Ctrl+C停止
echo.

REM 启动双通道主程序
python python\core\mt5_bridge_dual.py

echo.
echo [信息] 系统已停止
pause
