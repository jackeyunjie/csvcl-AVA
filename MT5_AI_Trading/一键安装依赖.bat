@echo off
chcp 65001 >nul
echo ==========================================
echo    MT5 AI 交易系统 - 依赖库安装助手
echo ==========================================
echo.
echo 本脚本将帮助您检查 MQL5 依赖库安装状态
echo.

REM 设置 MT5 数据目录（请根据实际情况修改）
set MT5_DATA_DIR=C:\Users\MECHREVO\AppData\Roaming\MetaQuotes\Terminal\E2DED4AEB0CED878C91643E3916B9F07

REM 检查 MT5 目录
if not exist "%MT5_DATA_DIR%\MQL5" (
    echo [错误] 未找到 MT5 数据目录！
    echo.
    echo 请修改本脚本中的 MT5_DATA_DIR 路径：
    echo   1. 右键点击本文件 → 编辑
    echo   2. 找到 set MT5_DATA_DIR= 这一行
    echo   3. 修改为您的 MT5 数据目录路径
    echo   4. 保存并重新运行
    echo.
    echo 如何找到 MT5 数据目录：
    echo   1. 打开 MT5 终端
    echo   2. 点击菜单：文件 → 打开数据文件夹
    echo   3. 复制地址栏中的路径
    echo.
    pause
    exit /b 1
)

echo [信息] MT5 数据目录: %MT5_DATA_DIR%
echo.

REM 创建必要的目录
if not exist "%MT5_DATA_DIR%\MQL5\Include\Zmq" mkdir "%MT5_DATA_DIR%\MQL5\Include\Zmq"
if not exist "%MT5_DATA_DIR%\MQL5\Libraries" mkdir "%MT5_DATA_DIR%\MQL5\Libraries"
if not exist "%MT5_DATA_DIR%\MQL5\Experts" mkdir "%MT5_DATA_DIR%\MQL5\Experts"

echo [信息] 目录结构已准备
echo.

REM 检查是否已安装
echo [检查] 检查现有安装...
set MISSING_ZMQ=0
set MISSING_DLL=0

if not exist "%MT5_DATA_DIR%\MQL5\Include\Zmq\Zmq.mqh" (
    set MISSING_ZMQ=1
    echo   [缺失] mql-zmq (Zmq.mqh)
) else (
    echo   [已安装] mql-zmq
)

if not exist "%MT5_DATA_DIR%\MQL5\Libraries\libzmq.dll" (
    set MISSING_DLL=1
    echo   [缺失] libzmq.dll
) else (
    echo   [已安装] libzmq.dll
)

echo   [信息] JSON 支持: MT5 内置 (build 1930+)
echo.

REM 如果都已安装，直接退出
if "%MISSING_ZMQ%"=="0" if "%MISSING_DLL%"=="0" (
    echo [信息] 所有依赖库已安装！
    echo.
    goto :COPY_EA
)

echo [信息] 需要手动下载以下库：
echo.

if "%MISSING_ZMQ%"=="1" (
    echo === mql-zmq ===
    echo 下载地址: https://github.com/dingmaotu/mql-zmq
    echo 操作步骤:
    echo   1. 点击页面右侧绿色的 [Code] 按钮
    echo   2. 选择 [Download ZIP]
    echo   3. 解压下载的文件
    echo   4. 复制解压后的 Include\Zmq 文件夹到:
    echo      %MT5_DATA_DIR%\MQL5\Include\
    echo   5. 复制解压后的 Library\MT5\libzmq.dll 到:
    echo      %MT5_DATA_DIR%\MQL5\Libraries\
    echo.
)

echo [提示] 下载完成后，请重新运行本脚本
echo.
pause
exit /b 0

:COPY_EA
echo [信息] 复制 EA 文件...
copy /Y "mql5\Experts\AI_Trading_Bridge.mq5" "%MT5_DATA_DIR%\MQL5\Experts\" >nul
if errorlevel 1 (
    echo [警告] EA 文件复制失败，请手动复制
    echo   源文件: mql5\Experts\AI_Trading_Bridge.mq5
    echo   目标: %MT5_DATA_DIR%\MQL5\Experts\
) else (
    echo [OK] EA 文件已复制
)

echo.
echo ==========================================
echo    安装检查完成！
echo ==========================================
echo.
echo 下一步操作：
echo 1. 打开 MT5 的 MetaEditor（按 F4）
echo 2. 找到 Experts → AI_Trading_Bridge
echo 3. 双击打开，按 F7 编译
echo 4. 确认显示 "0 个错误，0 个警告"
echo 5. 回到 MT5，将 EA 附加到图表
echo 6. 勾选"允许导入动态链接库(DLL)"
echo 7. 首次测试不要勾选"允许实时交易"
echo.
echo 详细步骤请参考：MQL5依赖库安装指南.md
echo.
pause
