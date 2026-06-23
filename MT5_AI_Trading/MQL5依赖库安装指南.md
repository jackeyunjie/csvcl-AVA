# MQL5 依赖库安装指南（小白版）

## 概述

本指南将手把手教您安装 MT5 AI 交易系统所需的 MQL5 依赖库。

**需要安装的库：**
1. **mql-zmq** - ZeroMQ 通信库（让 MT5 和 Python 能对话）
2. **libzmq.dll** - ZeroMQ 的动态链接库（Windows 必需）
3. ~~mql-json~~ - **不需要！** MT5 build 1930+ 已内置 JSON 支持

---

## 第一步：确认 MT5 数据目录

### 1.1 打开 MT5 终端

双击桌面上的 **MetaTrader 5** 图标启动程序。

### 1.2 找到数据文件夹路径

在 MT5 顶部菜单栏点击：

```
文件 → 打开数据文件夹
```

会弹出一个文件夹窗口，路径类似：

```
C:\Users\MECHREVO\AppData\Roaming\MetaQuotes\Terminal\E2DED4AEB0CED878C91643E3916B9F07
```

**记住这个路径！** 后面会多次用到。

### 1.3 确认 MQL5 目录结构

在打开的数据文件夹中，确认有以下目录：

```
MQL5/
├── Experts/        ← EA 文件放这里
├── Include/        ← 头文件放这里
├── Libraries/      ← DLL 文件放这里
├── Indicators/     ← 指标文件
└── Scripts/        ← 脚本文件
```

如果缺少某个目录，手动创建它（右键 → 新建 → 文件夹）。

---

## 第二步：下载 mql-zmq 库

### 2.1 访问 GitHub 仓库

打开浏览器，访问：

```
https://github.com/dingmaotu/mql-zmq
```

### 2.2 下载代码

在页面右侧找到绿色的 **Code** 按钮，点击后选择 **Download ZIP**：

```
[Code ▼] → Download ZIP
```

等待下载完成，得到一个名为 `mql-zmq-master.zip` 的文件。

### 2.3 解压文件

1. 找到下载的 `mql-zmq-master.zip` 文件
2. 右键点击 → **全部解压缩...**（或"解压到当前文件夹"）
3. 解压后会得到一个 `mql-zmq-master` 文件夹

### 2.4 复制文件到 MT5 目录

打开解压后的 `mql-zmq-master` 文件夹，找到 `Include` 文件夹。

**需要复制的文件：**

```
mql-zmq-master/
└── Include/
    └── Zmq/                    ← 复制这个整个文件夹
        ├── Zmq.mqh             ← 主头文件
        ├── SocketOptions.mqh
        ├── Context.mqh
        ├── Socket.mqh
        └── ...（其他文件）
```

**复制操作：**

1. 右键点击 `Zmq` 文件夹 → **复制**
2. 打开 MT5 数据目录的 `MQL5/Include/` 文件夹
3. 右键空白处 → **粘贴**

完成后路径应该是：

```
MQL5/Include/Zmq/Zmq.mqh
```

### 2.5 复制 DLL 文件

在 `mql-zmq-master` 文件夹中，找到 DLL 文件：

```
mql-zmq-master/
└── Library/
    └── MT5/
        └── libzmq.dll          ← 复制这个文件
```

**复制操作：**

1. 右键点击 `libzmq.dll` → **复制**
2. 打开 MT5 数据目录的 `MQL5/Libraries/` 文件夹
3. 右键空白处 → **粘贴**

完成后路径应该是：

```
MQL5/Libraries/libzmq.dll
```

---

## 第三步：下载 mql-json 库

### 3.1 JSON 支持说明

**好消息！** MT5 build 1930 及以上版本已经内置了 JSON 支持，**不需要额外安装**。

EA 代码中使用了：
```cpp
#include <Json.mqh>  // MT5 内置 JSON 库
```

### 3.2 检查 MT5 版本

1. 打开 MT5 终端
2. 点击菜单：**帮助 → 关于**
3. 查看版本号，确认是 **build 1930 或更高**

如果版本过低，请更新 MT5：
- 点击菜单：**帮助 → 检查更新**
- 或从官网下载最新版本

### 3.3 如果版本确实过低（备选方案）

如果无法更新 MT5，可以使用第三方 JSON 库：

**方案 A：使用 MQL5 官方 JSON**
```
https://www.mql5.com/en/code/53107
```

**方案 B：使用 CJson**
```
https://github.com/franciscogomes2020/CJson
```

下载后复制到 `MQL5/Include/` 目录，并修改 EA 代码中的 `#include` 语句。

---

## 第四步：验证安装

### 4.1 检查文件是否齐全

打开 MT5 数据目录，确认以下文件都存在：

```
MQL5/
├── Include/
│   └── Zmq/
│       └── Zmq.mqh           ← mql-zmq 主文件
│   └── Json.mqh               ← MT5 内置（无需复制）
├── Libraries/
│   └── libzmq.dll             ← ZeroMQ DLL
└── Experts/
    └── AI_Trading_Bridge.mq5  ← 我们的 EA（如果已复制）
```

### 4.2 编译 EA

1. 打开 MT5 的 **MetaEditor**（在 MT5 中按 **F4** 或点击工具栏的编辑器图标）

2. 在 MetaEditor 左侧的导航器中，找到：
   ```
   Experts → AI_Trading_Bridge
   ```

3. 双击打开 `AI_Trading_Bridge.mq5`

4. 按 **F7** 或点击菜单：
   ```
   编译 → 编译
   ```

### 4.3 检查编译结果

**如果成功：**
- 底部"工具箱"窗口显示：
  ```
  0 个错误，0 个警告
  ```
- 文件旁边出现绿色勾选标记

**如果失败（常见错误）：**

| 错误信息 | 原因 | 解决方法 |
|---------|------|---------|
| `无法打开 #include <Zmq/Zmq.mqh>` | mql-zmq 未安装 | 检查 `MQL5/Include/Zmq/` 是否存在 |
| `无法打开 #include <Json.mqh>` | MT5 版本过低 | 更新 MT5 到 build 1930+ |
| `无法加载 libzmq.dll` | DLL 未复制 | 检查 `MQL5/Libraries/libzmq.dll` 是否存在 |
| `需要允许 DLL 导入` | 编译设置问题 | 见下方"允许 DLL 导入"设置 |

### 4.4 允许 DLL 导入（编译设置）

如果编译提示 DLL 相关错误：

1. 在 MetaEditor 中，点击菜单：
   ```
   工具 → 选项
   ```

2. 在左侧选择 **编译器**

3. 勾选 **允许 DLL 导入**

4. 点击 **确定**

5. 重新按 **F7** 编译

---

## 第五步：附加 EA 到图表

### 5.1 回到 MT5 终端

点击 MT5 窗口或按 **Alt+F4** 关闭 MetaEditor 回到 MT5。

### 5.2 打开图表

1. 在左侧"市场报价"窗口找到 **EURUSD**
2. 右键点击 → **图表窗口**
3. 或双击 EURUSD 打开图表

### 5.3 附加 EA

**方法1 - 拖拽：**
1. 在左侧导航器中找到：
   ```
   Expert Advisors → AI_Trading_Bridge
   ```
2. 用鼠标拖拽到图表上

**方法2 - 双击：**
1. 在导航器中双击 `AI_Trading_Bridge`

### 5.4 设置 EA 属性

会弹出一个属性窗口，设置以下参数：

```
常用选项卡：
  [√] 允许实时交易          ← 如果要真实交易才勾选（建议先不勾）
  [√] 允许导入动态链接库(DLL) ← 必须勾选！

输入参数选项卡：
  InpZmqHost: *             ← 保持默认
  InpPubPort: 5555          ← 保持默认
  InpRepPort: 5556          ← 保持默认
  InpEnableLogging: true    ← 保持默认（方便调试）
```

**重要：** 首次测试建议 **不要勾选"允许实时交易"**！

### 5.5 确认 EA 运行

点击 **确定** 后：

1. 图表右上角出现 **AI_Trading_Bridge** 名称
2. 旁边有一个 **笑脸图标**（表示正常运行）
3. 如果显示 **哭脸**，说明有错误，查看"专家"标签页的日志

### 5.6 查看日志

在 MT5 底部找到 **工具箱** 窗口，切换到 **专家** 标签页：

应该能看到类似日志：

```
AI_Trading_Bridge EURUSD,H1: [INFO] AI Trading Bridge 启动成功
AI_Trading_Bridge EURUSD,H1: [INFO] PUB端口: 5555 | REP端口: 5556
AI_Trading_Bridge EURUSD,H1: [INFO] PUB socket绑定成功: tcp://*:5555
AI_Trading_Bridge EURUSD,H1: [INFO] REP socket绑定成功: tcp://*:5556
```

---

## 第六步：测试 Python 连接

### 6.1 启动 Python 系统

打开命令提示符（CMD）或 PowerShell：

```bash
cd "d:\qoder\csvcl - AVA\MT5_AI_Trading"
python python\core\main_controller.py
```

### 6.2 检查连接状态

Python 端应该显示：

```
[INFO] MT5连接成功，通信正常
[INFO] 账户余额: XXXX.XX
[INFO] 系统运行中，按Ctrl+C停止...
```

### 6.3 查看行情接收

过几秒后应该能看到：

```
[Client] 收到Tick: EURUSD | Bid: 1.08510 | Ask: 1.08530
```

---

## 常见问题排查

### Q1: 编译时提示 "Zmq.mqh 找不到"

**检查：**
1. `MQL5/Include/Zmq/` 文件夹是否存在
2. 文件夹内是否有 `Zmq.mqh` 文件
3. 文件名是否大小写正确（Windows 不区分大小写，但最好一致）

### Q2: EA 附加后显示哭脸

**检查：**
1. 是否勾选了"允许导入动态链接库(DLL)"
2. 查看"专家"日志中的错误信息
3. 端口 5555/5556 是否被其他程序占用

### Q3: Python 无法连接 MT5

**检查：**
1. MT5 中 EA 是否正常运行（笑脸图标）
2. 防火墙是否阻止了端口 5555/5556
3. `trading_config.yaml` 中的 host 是否为 `localhost`

### Q4: 端口被占用

**解决：**
1. 关闭占用端口的程序
2. 或修改 EA 和 Python 配置使用其他端口（如 5557/5558）

---

## 安全提醒

⚠️ **首次使用务必：**

1. **使用模拟账户**（Demo Account）
2. **不要勾选"允许实时交易"**
3. **确认 `live_trading: false` 和 `dry_run: true`**
4. **观察日志输出，确认一切正常后再考虑实盘**

---

## 下一步

安装完成后：

1. 运行 `tests/test_communication.py` 验证通信
2. 运行 `tests/test_dry_run.py` 验证安全机制
3. 观察 1-2 小时模拟运行日志
4. 确认无误后再考虑开启真实交易

如有问题，请查看日志并反馈具体错误信息。
