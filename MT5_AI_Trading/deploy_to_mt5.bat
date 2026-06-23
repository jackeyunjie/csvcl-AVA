@echo off
chcp 65001 >nul
echo ==========================================
echo    部署 MT5 AI Trading EA
echo ==========================================
echo.

REM MT5数据目录
set MT5_DATA_DIR=C:\Users\MECHREVO\AppData\Roaming\MetaQuotes\Terminal\E2DED4AEB0CED878C91643E3916B9F07

REM 检查目录是否存在
if not exist "%MT5_DATA_DIR%" (
    echo [错误] 未找到MT5数据目录: %MT5_DATA_DIR%
    echo [提示] 请修改脚本中的 MT5_DATA_DIR 路径
    pause
    exit /b 1
)

echo [信息] MT5数据目录: %MT5_DATA_DIR%
echo.

REM 创建MQL5目录结构（如果不存在）
if not exist "%MT5_DATA_DIR%\MQL5\Experts" mkdir "%MT5_DATA_DIR%\MQL5\Experts"
if not exist "%MT5_DATA_DIR%\MQL5\Include\Zmq" mkdir "%MT5_DATA_DIR%\MQL5\Include\Zmq"

REM 复制EA文件
echo [信息] 复制EA文件...
copy /Y "mql5\Experts\AI_Trading_Bridge.mq5" "%MT5_DATA_DIR%\MQL5\Experts\" >nul
if errorlevel 1 (
    echo [错误] 复制EA文件失败
    pause
    exit /b 1
)
echo [OK] EA文件已复制

REM 检查ZMQ库是否存在
if not exist "%MT5_DATA_DIR%\MQL5\Include\Zmq\Zmq.mqh" (
    echo.
    echo [警告] 未找到ZMQ库文件！
    echo [提示] 请从 https://github.com/dingmaotu/mql-zmq 下载并复制到:
    echo        %MT5_DATA_DIR%\MQL5\Include\Zmq\
    echo.
)

REM 检查JSON库是否存在
if not exist "%MT5_DATA_DIR%\MQL5\Include\JAson.mqh" (
    echo [警告] 未找到JAson库文件！
    echo [提示] 请从 https://github.com/dingmaotu/mql-json 下载并复制到:
    echo        %MT5_DATA_DIR%\MQL5\Include\
    echo.
)

echo.
echo ==========================================
echo    部署完成！
echo ==========================================
echo.
echo 下一步操作：
echo 1. 打开MT5终端
echo 2. 在导航器中找到 AI_Trading_Bridge
echo 3. 双击或拖拽到图表上
echo 4. 在属性窗口中确认参数
echo 5. 勾选"允许实时交易"（如需要）
echo 6. 点击"确定"
echo.
echo 注意：首次运行建议使用模拟账户！
echo.
pause
