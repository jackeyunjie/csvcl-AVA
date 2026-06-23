@echo off
chcp 65001 >nul
echo ==========================================
echo    mql-zmq MT5 Build 5660 兼容性修复工具
echo ==========================================
echo.

REM 设置 MT5 数据目录
set MT5_DATA_DIR=C:\Users\MECHREVO\AppData\Roaming\MetaQuotes\Terminal\E2DED4AEB0CED878C91643E3916B9F07

REM 检查目录
if not exist "%MT5_DATA_DIR%\MQL5\Include\Zmq" (
    echo [错误] 未找到 mql-zmq 安装目录！
    pause
    exit /b 1
)

echo [信息] 开始修复 SocketOptions.mqh...
echo.

REM 备份原文件
copy /Y "%MT5_DATA_DIR%\MQL5\Include\Zmq\SocketOptions.mqh" "%MT5_DATA_DIR%\MQL5\Include\Zmq\SocketOptions.mqh.bak" >nul
echo [OK] 已备份原文件到 SocketOptions.mqh.bak

REM 使用 PowerShell 修复文件
powershell -Command "
$file = '%MT5_DATA_DIR%\MQL5\Include\Zmq\SocketOptions.mqh'
$content = Get-Content $file -Raw

# 修复 getStringOption 函数
$content = $content -replace 'bool SocketOptions::getStringOption\(int option,string &value,size_t length\)\s*\{\s*char buf\[\];', 'bool SocketOptions::getStringOption(int option,string &value,size_t length)\n  {\n   uchar buf[];'

# 修复 setStringOption 函数  
$content = $content -replace 'bool SocketOptions::setStringOption\(int option,const string value,bool ending\)\s*\{\s*char buf\[\];', 'bool SocketOptions::setStringOption(int option,const string value,bool ending)\n  {\n   uchar buf[];'

Set-Content $file $content -NoNewline
"

echo [OK] SocketOptions.mqh 修复完成
echo.

echo [信息] 开始修复 Socket.mqh...
copy /Y "%MT5_DATA_DIR%\MQL5\Include\Zmq\Socket.mqh" "%MT5_DATA_DIR%\MQL5\Include\Zmq\Socket.mqh.bak" >nul
echo [OK] 已备份原文件到 Socket.mqh.bak

powershell -Command "
$file = '%MT5_DATA_DIR%\MQL5\Include\Zmq\Socket.mqh'
$content = Get-Content $file -Raw

# 在 #include 后添加兼容性函数
$compatCode = @'
//+------------------------------------------------------------------+
//| MT5 Build 5100+ 兼容性修复 (char -> uchar)                      |
//+------------------------------------------------------------------+
int zmq_bind_compat(intptr_t s,const uchar &addr[])
  {
   char addrChar[];
   ArrayResize(addrChar, ArraySize(addr));
   for(int i=0; i<ArraySize(addr); i++) addrChar[i] = (char)addr[i];
   return zmq_bind(s, addrChar);
  }

int zmq_unbind_compat(intptr_t s,const uchar &addr[])
  {
   char addrChar[];
   ArrayResize(addrChar, ArraySize(addr));
   for(int i=0; i<ArraySize(addr); i++) addrChar[i] = (char)addr[i];
   return zmq_unbind(s, addrChar);
  }

int zmq_connect_compat(intptr_t s,const uchar &addr[])
  {
   char addrChar[];
   ArrayResize(addrChar, ArraySize(addr));
   for(int i=0; i<ArraySize(addr); i++) addrChar[i] = (char)addr[i];
   return zmq_connect(s, addrChar);
  }

int zmq_disconnect_compat(intptr_t s,const uchar &addr[])
  {
   char addrChar[];
   ArrayResize(addrChar, ArraySize(addr));
   for(int i=0; i<ArraySize(addr); i++) addrChar[i] = (char)addr[i];
   return zmq_disconnect(s, addrChar);
  }

int zmq_socket_monitor_compat(intptr_t s,const uchar &addr[],int events)
  {
   char addrChar[];
   ArrayResize(addrChar, ArraySize(addr));
   for(int i=0; i<ArraySize(addr); i++) addrChar[i] = (char)addr[i];
   return zmq_socket_monitor(s, addrChar, events);
  }

'@

# 在 Socket 类定义之前插入兼容性函数
$content = $content -replace '(#include \"ZmqMsg.mqh\")', \"`$1`n`n$compatCode\"\n\n$content = $content -replace 'char arr\[\];\s*StringToUtf8\(addr,arr\);\s*bool res=\(0==zmq_bind\(m_ref,arr\)\);', 'uchar arr[];\n   StringToUtf8(addr,arr);\n   bool res=(0==zmq_bind_compat(m_ref,arr));'

$content = $content -replace 'char arr\[\];\s*StringToUtf8\(addr,arr\);\s*bool res=\(0==zmq_unbind\(m_ref,arr\)\);', 'uchar arr[];\n   StringToUtf8(addr,arr);\n   bool res=(0==zmq_unbind_compat(m_ref,arr));'

$content = $content -replace 'char arr\[\];\s*StringToUtf8\(addr,arr\);\s*bool res=\(0==zmq_connect\(m_ref,arr\)\);', 'uchar arr[];\n   StringToUtf8(addr,arr);\n   bool res=(0==zmq_connect_compat(m_ref,arr));'

$content = $content -replace 'char arr\[\];\s*StringToUtf8\(addr,arr\);\s*bool res=\(0==zmq_disconnect\(m_ref,arr\)\);', 'uchar arr[];\n   StringToUtf8(addr,arr);\n   bool res=(0==zmq_disconnect_compat(m_ref,arr));'

$content = $content -replace 'bool res=\(0==zmq_socket_monitor\(m_ref,str,events\)\);', 'bool res=(0==zmq_socket_monitor_compat(m_ref,str,events));'

Set-Content $file $content -NoNewline
"

echo [OK] Socket.mqh 修复完成
echo.
echo ==========================================
echo    修复完成！
echo ==========================================
echo.
echo 请重新在 MetaEditor 中按 F7 编译 EA
echo.
echo 如果仍有问题，请检查：
echo 1. 备份文件 .bak 是否生成
echo 2. 文件修改是否正确
echo 3. 是否需要重启 MetaEditor
echo.
pause
