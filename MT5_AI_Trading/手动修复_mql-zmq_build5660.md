# mql-zmq MT5 Build 5660 手动修复指南

## 问题原因

MT5 build 5100+ 的 MQL5 编译器更严格，`char` 和 `uchar` 类型不再自动兼容。

## 需要修改的文件

### 文件1：SocketOptions.mqh

**路径**：
```
C:\Users\MECHREVO\AppData\Roaming\MetaQuotes\Terminal\E2DED4AEB0CED878C91643E3916B9F07\MQL5\Include\Zmq\SocketOptions.mqh
```

**修改1** - 第 335 行（getStringOption 函数）：
```cpp
// 修改前：
   char buf[];

// 修改后：
   uchar buf[];
```

**修改2** - 第 351 行（setStringOption 函数）：
```cpp
// 修改前：
   char buf[];

// 修改后：
   uchar buf[];
```

---

### 文件2：Socket.mqh

**路径**：
```
C:\Users\MECHREVO\AppData\Roaming\MetaQuotes\Terminal\E2DED4AEB0CED878C91643E3916B9F07\MQL5\Include\Zmq\Socket.mqh
```

**修改1** - 在 `#include "ZmqMsg.mqh"` 之后添加兼容性函数：

找到第 27 行：
```cpp
#include "ZmqMsg.mqh"
```

在其后添加以下内容：

```cpp

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

```

**修改2** - 第 187-189 行（bind 函数）：
```cpp
// 修改前：
   char arr[];
   StringToUtf8(addr,arr);
   bool res=(0==zmq_bind(m_ref,arr));

// 修改后：
   uchar arr[];
   StringToUtf8(addr,arr);
   bool res=(0==zmq_bind_compat(m_ref,arr));
```

**修改3** - 第 198-200 行（unbind 函数）：
```cpp
// 修改前：
   char arr[];
   StringToUtf8(addr,arr);
   bool res=(0==zmq_unbind(m_ref,arr));

// 修改后：
   uchar arr[];
   StringToUtf8(addr,arr);
   bool res=(0==zmq_unbind_compat(m_ref,arr));
```

**修改4** - 第 209-211 行（connect 函数）：
```cpp
// 修改前：
   char arr[];
   StringToUtf8(addr,arr);
   bool res=(0==zmq_connect(m_ref,arr));

// 修改后：
   uchar arr[];
   StringToUtf8(addr,arr);
   bool res=(0==zmq_connect_compat(m_ref,arr));
```

**修改5** - 第 220-222 行（disconnect 函数）：
```cpp
// 修改前：
   char arr[];
   StringToUtf8(addr,arr);
   bool res=(0==zmq_disconnect(m_ref,arr));

// 修改后：
   uchar arr[];
   StringToUtf8(addr,arr);
   bool res=(0==zmq_disconnect_compat(m_ref,arr));
```

**修改6** - 第 231-233 行（monitor 函数）：
```cpp
// 修改前：
   uchar str[];
   StringToUtf8(addr,str);
   bool res=(0==zmq_socket_monitor(m_ref,str,events));

// 修改后：
   uchar str[];
   StringToUtf8(addr,str);
   bool res=(0==zmq_socket_monitor_compat(m_ref,str,events));
```

---

## 修改步骤

### 步骤1：备份文件

1. 打开文件夹：
   ```
   C:\Users\MECHREVO\AppData\Roaming\MetaQuotes\Terminal\E2DED4AEB0CED878C91643E3916B9F07\MQL5\Include\Zmq\
   ```

2. 复制 `SocketOptions.mqh` → `SocketOptions.mqh.bak`
3. 复制 `Socket.mqh` → `Socket.mqh.bak`

### 步骤2：修改 SocketOptions.mqh

1. 右键点击 `SocketOptions.mqh` → **编辑**（或打开方式 → 记事本）
2. 按 `Ctrl+F` 搜索 `char buf[]`
3. 将两处 `char buf[]` 改为 `uchar buf[]`
4. 保存文件（`Ctrl+S`）

### 步骤3：修改 Socket.mqh

1. 右键点击 `Socket.mqh` → **编辑**
2. 找到 `#include "ZmqMsg.mqh"`
3. 在其后添加兼容性函数代码（见上文）
4. 搜索并替换 5 个函数中的代码（bind/unbind/connect/disconnect/monitor）
5. 保存文件（`Ctrl+S`）

### 步骤4：重新编译

1. 打开 MT5 MetaEditor（按 F4）
2. 找到 `Experts → AI_Trading_Bridge`
3. 按 **F7** 编译
4. 确认显示 **"0 个错误，0 个警告"**

---

## 验证修改

修改完成后，文件应该包含：
- `SocketOptions.mqh`：2 处 `uchar buf[]`
- `Socket.mqh`：5 个兼容性函数 + 5 处调用修改

---

## 如果修改后仍有错误

1. 检查是否所有 `char arr[]` 都已改为 `uchar arr[]`
2. 检查兼容性函数是否添加在正确位置
3. 检查函数名拼写是否正确（`_compat` 后缀）
4. 如果无法解决，可以恢复备份文件重新修改

---

## 替代方案

如果手动修改太复杂，可以考虑：

**方案A**：下载已修复的 fork 版本
```
https://github.com/Furious-Production-LTD/mql-zmq
```

**方案B**：使用其他通信方案（如命名管道、文件交换等）

**方案C**：降级 MT5 到 build 5099 以下（不推荐）
