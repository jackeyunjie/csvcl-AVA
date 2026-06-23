# MT5 + AI 智能量化交易系统

## 系统概述

基于 ZeroMQ 分布式架构的 AI 驱动量化交易系统，支持：
- **实时行情接收** - 微秒级延迟
- **AI 智能决策** - 技术指标 + LLM 分析
- **自动交易执行** - 完整的订单管理
- **风险控制系统** - 多层级风控
- **实时监控告警** - 智能风险提醒

## State 架构口径

项目内 State 架构以 `docs/STATE_VIEWPOINT_AGENT_CONTRACT.md` 为准：

- 周期和周期视角是不同维度。
- 每个周期视角都是独立 Agent。
- 每个 Agent 包含本周期及以上大周期的时间戳对齐状态。
- `base/trend/volatility` 来自结构周期自身，`position` 统一使用该 Agent 的视角 close。

例如 H1 Agent 不是只看 H1 周期，而是输出 `MN1/W1/D1/H4/H1 @ H1_view`。M15 Agent 是另一套独立视角系统，不是简单多加一列 M15。

## 项目结构

```
MT5_AI_Trading/
├── mql5/
│   ├── Experts/
│   │   └── AI_Trading_Bridge.mq5    # MT5 ZeroMQ EA
│   └── Include/                      # MQL5 头文件
├── python/
│   ├── core/
│   │   ├── mt5_bridge.py            # Python-MT5桥接
│   │   └── main_controller.py       # 主控制器
│   ├── ai_engine/
│   │   ├── trading_strategy.py      # 交易策略引擎
│   │   └── llm_analyzer.py          # LLM AI分析
│   ├── backtest/
│   │   └── trading_env.py           # 强化学习环境
│   ├── monitoring/
│   │   └── monitor.py               # 实时监控
│   └── utils/                        # 工具函数
├── config/
│   └── trading_config.yaml          # 系统配置
├── data/
│   ├── historical/                   # 历史数据
│   └── models/                       # AI模型
├── logs/                             # 日志文件
├── requirements.txt                  # Python依赖
├── start_trading.bat                # Windows启动脚本
└── README.md                         # 项目文档
```

## 快速开始

### 1. 环境准备

**安装 MT5 ZeroMQ 库：**
1. 下载 [ZeroMQ library for MQL5](https://github.com/dingmaotu/mql-zmq)
2. 将 `Zmq` 文件夹复制到 MT5 的 `MQL5/Include/` 目录
3. 下载 [JAson library](https://github.com/dingmaotu/mql-json) 同样放入 `Include`

**安装 Python 依赖：**
```bash
pip install -r requirements.txt
```

### 2. 部署 MT5 EA

1. 将 `mql5/Experts/AI_Trading_Bridge.mq5` 复制到 MT5 的 `MQL5/Experts/` 目录
2. 在 MT5 中编译 EA（按 F7）
3. 将 EA 附加到图表上
4. 确认日志显示 "AI Trading Bridge 启动成功"

### 3. 启动交易系统

**Windows：**
```bash
start_trading.bat
```

**手动启动：**
```bash
python python/core/main_controller.py --config config/trading_config.yaml
```

### 4. 验证连接

系统启动后应显示：
```
[INFO] MT5连接成功，通信正常
[INFO] 账户余额: XXXX.XX
[INFO] 系统运行中，按Ctrl+C停止...
```

## 配置说明

编辑 `config/trading_config.yaml`：

```yaml
# MT5连接
mt5:
  host: localhost       # MT5所在IP
  pub_port: 5555        # 行情端口
  req_port: 5556        # 交易端口

# 交易设置
trading:
  symbol: EURUSD        # 交易品种
  min_confidence: 0.6   # 最小信号信心度
  enable_llm: false     # 是否启用AI分析

# 风险控制
risk:
  max_risk_per_trade: 0.02   # 单笔风险2%
  max_drawdown: 0.10         # 最大回撤10%
  max_positions: 5           # 最大持仓5个
```

## 核心功能

### 1. 自动化交易
- EMA/RSI/MACD/布林带等多指标综合信号
- ATR动态止损止盈
- Kelly仓位管理
- 自动滑点控制

### 2. AI 分析（可选）
- OpenAI GPT-4 / Claude 市场情绪分析
- 交易设置风险评估
- 智能风险提醒

### 3. 回测系统
- OpenAI Gym兼容环境
- Tick级精度回测
- 28+技术指标特征
- 自定义奖励函数

### 4. 实时监控
- 实时P&L追踪
- VaR/CVaR风险指标
- 最大回撤监控
- 智能告警系统

## 安全注意事项

⚠️ **风险提示：**
1. 首次使用请在 **模拟账户** 上测试
2. 建议先运行 **1-2周模拟盘** 验证策略
3. 实盘交易前确认风险参数设置合理
4. 始终保持对系统的监控

## 故障排除

**无法连接MT5：**
- 确认 EA 已正确附加到图表
- 检查防火墙是否放行端口 5555/5556
- 验证 `trading_config.yaml` 中的 host 设置

**信号不生成：**
- 检查 `min_confidence` 设置是否过高
- 确认历史数据足够（至少50根K线）
- 查看日志中的策略输出

**订单执行失败：**
- 确认MT5账户有交易权限
- 检查账户余额是否充足
- 验证交易品种是否可交易

## 开发计划

- [x] Phase 1: 基础设施（ZeroMQ桥接）
- [x] Phase 2: 核心引擎（策略+回测）
- [ ] Phase 3: AI强化学习（PPO/SAC）
- [ ] Phase 4: 多策略管理
- [ ] Phase 5: Web监控面板

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎反馈。
