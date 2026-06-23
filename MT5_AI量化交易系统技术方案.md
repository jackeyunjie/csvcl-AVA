# MT5 + AI 智能量化交易系统——技术方案与实施路径

## 面向未来全球最大私募与量化回测平台上市公司的架构蓝图

**版本**：V1.0
**日期**：2026年5月2日
**愿景**：打造全球领先的人工智能驱动量化交易平台

---

## 一、执行摘要

本方案基于深度技术调研（覆盖GitHub 15+开源项目、ACM/IEEE 权威论文、StrategyQuant X 官方文档、QuantConnect Lean 引擎架构、以及多个 MT5 ZeroMQ 生产级实践），提出了一套面向机构投资者级、具备"全球最大私募"和"量化平台上市公司"愿景的技术架构。

### 关键技术决策

| 决策项 | 推荐方案 | 核心理由 |
|--------|---------|---------|
| MT5 对接方式 | **ZeroMQ 分布式架构** | PUB/SUB+REQ/REP 双通道，微秒级延迟，支持 Linux+Windows 分离部署 |
| AI 技术栈 | **混合方案** | 核心交易自研（PyTorch/Stable-Baselines3）+ AI 分析接入 OpenAI/Claude API |
| 回测引擎 | **自研 + Lean 参考** | 事件驱动架构，回测→实盘无缝切换，分布式并行回测 |
| SQX 迁移 | **MQL5 导出 + Python 桥接** | SQX 生成策略导出为 MQL5 EA，通过 ZeroMQ 与 Python AI 系统通信 |
| 部署架构 | **Docker + Kubernetes** | 微服务化，支持高可用和横向扩展 |

---

## 二、技术选型详细论证

### 2.1 MT5 对接方式：ZeroMQ 分布式架构（强烈推荐）

经过对三种方案的深入比较，**ZeroMQ 方案**是唯一能满足机构级需求的架构：

#### 三种方案对比

| 维度 | ZeroMQ 分布式 | MQL5 原生 EA | mt5-python 库 |
|------|-------------|-------------|--------------|
| 延迟 | **微秒级** | 毫秒级 | 数十毫秒 |
| AI 能力 | **完整 Python 生态** | 极有限 | 有限 |
| 回测能力 | **独立高性能回测** | MT5 内置 | 简单回测 |
| 扩展性 | **横向扩展** | 单机 | 单机 |
| 故障恢复 | **心跳+自动重连** | 需手动 | 无 |
| 安全性 | **IP 白名单+防火墙** | 依赖 MT5 | 依赖 MT5 |
| 适用场景 | **机构级量化** | 简单 EA | 个人轻度使用 |

#### ZeroMQ 架构核心设计

参考 darwinex/dwx-zeromq-connector 和 Nova Quant Lab 的最佳实践 [^763^][^773^]：

**双通道架构**：

1. **PUB/SUB 通道（市场数据流）**：MT5 EA 作为 Publisher，每次 `OnTick()` 触发时广播 Bid/Ask 价格；Python AI 引擎作为 Subscriber，实时接收行情数据
2. **REQ/REP 通道（交易指令流）**：Python AI 引擎作为 Requester，发送 JSON 格式交易指令；MT5 EA 作为 Replier，执行 `OrderSend()` 并返回成交确认

**关键代码骨架（Python 端）**：

```python
import zmq
import json

class MT5_AI_Bridge:
    def __init__(self, mt5_ip, pub_port=5555, req_port=5556):
        self.context = zmq.Context()
        # 行情数据订阅
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{mt5_ip}:{pub_port}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        # 交易指令请求
        self.req_socket = self.context.socket(zmq.REQ)
        self.req_socket.connect(f"tcp://{mt5_ip}:{req_port}")

    def get_tick(self):
        try:
            msg = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
            return json.loads(msg)
        except zmq.Again:
            return None

    def send_order(self, symbol, action, volume, sl, tp):
        payload = {
            "action": action, "symbol": symbol,
            "volume": volume, "sl": sl, "tp": tp,
            "max_slippage_points": 10
        }
        self.req_socket.send_string(json.dumps(payload))
        return json.loads(self.req_socket.recv_string())
```

**生产级安全要求** [^763^]：
- Windows 防火墙严格限制 ZMQ 端口，仅允许 Python AI 节点 IP
- 每 5 秒心跳检测（PING/PONG），超时 500ms 即判定断线
- 断线时 Python 端立即停止信号生成并触发紧急告警
- JSON 指令中包含 `max_slippage_points` 防止滑点侵蚀 Alpha

### 2.2 AI 技术栈：混合方案

#### 三层 AI 架构

| 层级 | 技术方案 | 功能 | 时间线 |
|------|---------|------|--------|
| **L1：快速智能层** | OpenAI/Claude API | 市场情绪分析、新闻摘要、财报解读 | 立即部署 |
| **L2：核心决策层** | PyTorch + Stable-Baselines3 | 强化学习交易决策（PPO/SAC/DQN） | 3-6 个月 |
| **L3：因子挖掘层** | LLM + AutoML | 自动化因子发现、特征工程 | 6-12 个月 |

#### 强化学习算法选择

根据 ACM Computing Surveys 2025 年综述论文 [^785^]，量化交易中的 RL 算法对比：

| 算法 | 类型 | 优势 | 适用场景 |
|------|------|------|---------|
| **PPO** | On-policy | 样本效率高、稳定、易实现 | 中等频率交易（1H-4H） |
| **SAC** | Off-policy Actor-Critic | 连续动作空间、最大熵框架 | 仓位管理、止损优化 |
| **DQN** | Value-based | 离散动作、表现稳定 | 入场/离场信号判断 |

推荐 GitHub 项目：Mrugendra7911/Deep_Reinforcement_Learning_Agent [^784^]
- 已实现 PPO/DQN/SAC 三种算法
- 包含市场状态分类（趋势/震荡/区间/低迷）
- Bootstrap 经验回放解决稀疏奖励问题
- 支持 Walk-Forward 优化验证

### 2.3 回测系统架构

参考 QuantConnect Lean 引擎架构 [^786^][^768^]，设计自研回测引擎：

**五大核心模块**：

```
IDataFeed（数据接入层）→ IAlgorithm（策略执行层）
                           ↓
ITransactionHandler（订单管理）→ IResultHandler（结果分析）
                           ↓
                IRealtimeHandler（事件管理）
```

| 模块 | 职责 | 技术实现 |
|------|------|---------|
| DataFeed | 多源数据接入、Tick→K 线聚合 | Apache Kafka + TimescaleDB |
| Algorithm | 策略执行、指标计算、信号生成 | Python 策略引擎 |
| TransactionHandler | 订单路由、成交模拟、滑点模型 | 事件驱动订单簿 |
| ResultHandler | 收益分析、风险指标、报告生成 | Pandas + Matplotlib |
| RealtimeHandler | 时间推进、事件调度 | 异步事件循环 |

**关键特性**：
- **回测→实盘无缝切换**：同一套策略代码，仅切换 DataFeed 和 TransactionHandler
- **分布式并行回测**：多节点同时回测不同参数组合，效率提升 10x+
- **Tick 级精度**：支持真实 Tick 数据回测，而非 OHLC 近似

---

## 三、系统总体架构

### 3.1 微服务架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    客户端层（Web/Mobile）                          │
│              React/Vue 前端 + React Native App                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │ REST API / WebSocket
┌──────────────────────▼──────────────────────────────────────────┐
│                    API 网关层（Kong/Nginx）                        │
│         认证、限流、负载均衡、请求路由                               │
└──────────┬───────────────────────────┬──────────────────────────┘
           │                           │
  ┌────────▼────────┐      ┌──────────▼──────────┐
  │   AI 决策引擎      │      │   回测引擎服务       │
  │  (Python/PyTorch) │      │   (分布式计算集群)    │
  └────────┬────────┘      └──────────┬──────────┘
           │                           │
  ┌────────▼───────────────────────────▼──────────┐
  │              消息队列层（Apache Kafka）         │
  │     行情流 │ 交易信号 │ 风控事件 │ 系统日志       │
  └────────┬───────────────────────────┬──────────┘
           │                           │
  ┌────────▼────────┐      ┌──────────▼──────────┐
  │   ZeroMQ 桥接器   │      │   数据存储层         │
  │  (MT5 Connector) │      │  TimescaleDB + Redis │
  └────────┬────────┘      └─────────────────────┘
           │
  ┌────────▼────────┐
  │   MT5 终端集群    │
  │  (Windows VPS)   │
  │  图表 × N        │
  └─────────────────┘
```

### 3.2 数据流架构

**实时数据流**：
```
MT5 OnTick() → ZeroMQ PUB → Python Subscriber → Kafka → AI Engine → Trading Signal
                                                          ↓
                                               Risk Check → ZeroMQ REQ → MT5 OrderSend()
```

**回测数据流**：
```
Historical Data (Parquet) → DataFeed → Strategy Engine → ResultHandler → Report
                                          ↑
                                    Parameter Grid (Optuna/Ray Tune)
```

---

## 四、SQX 迁移路径

### 4.1 现有 SQX 策略迁移

基于 StrategyQuant X 官方文档和最佳实践 [^765^][^770^][^783^]：

**Phase 1：直接导出（立即可用）**
1. 在 SQX 中完成策略验证（Robustness Tests、Walk-Forward、Monte Carlo）
2. 设置 Symbol 配置与经纪商 MT5 完全一致（点差、Tick Size、杠杆）
3. 导出为 MQL5 EA（选择 MT5 Export）
4. 将 SQX 自定义指标复制到 `MQL5/Indicators` 目录
5. 在 MT5 中编译并运行

**Phase 2：Python 增强（3 个月内）**
1. 保留 SQX 生成的入场/离场逻辑（经过充分验证的规则引擎）
2. 将 SQX EA 的仓位管理、止损止盈交由 Python AI 系统动态优化
3. 通过 ZeroMQ 实现 SQX EA ↔ Python AI 的通信

**Phase 3：AI 替代（6-12 个月）**
1. 用 RL 代理替代 SQX 的固定规则
2. SQX 作为策略种子生成器（遗传算法产生初始策略候选）
3. Python RL 代理在 SQX 策略基础上持续学习和优化

### 4.2 自定义指标迁移

SQX 外部指标导入流程 [^770^]：
1. 使用 `SqIndicatorValuesExportEA` 从 MT5 导出指标值到 CSV
2. 在 SQX Data Manager → External Indicators 中导入 CSV
3. 指标即可作为 Building Block 在策略生成中使用
4. 生成策略时可自动导出为 MQL5 代码调用该指标

---

## 五、核心功能模块设计

### 5.1 自动化交易系统

| 功能 | 技术实现 | 说明 |
|------|---------|------|
| AI 入场识别 | RL Agent (PPO/SAC) | 基于 28+ 技术指标特征，学习最优入场时机 |
| 动态仓位管理 | Kelly Criterion + 风险预算 | 根据胜率、赔率、账户净值动态调整仓位 |
| 智能止损止盈 | ATR-based 动态止损 + 盈利跟踪 | 参考 ATR 波动率自适应调整，盈利后触发移动止盈 |
| 滑点控制 | ZeroMQ JSON 中的 max_slippage | 超出预设滑点自动拒绝成交 |
| 多账户管理 | 支持同时管理多个 MT5 账户 | 资金分配、风险隔离 |

### 5.2 回测系统

| 功能 | 技术实现 | 说明 |
|------|---------|------|
| 多时间框架回测 | Tick/1M/5M/1H/1D | 支持 Tick 级精度 |
| 参数优化 | Optuna / Ray Tune | 分布式并行，贝叶斯优化 |
| Walk-Forward 分析 | 滚动窗口内外样本验证 | 防止过拟合 |
| Monte Carlo 模拟 | 打乱交易顺序 1000 次 | 评估策略鲁棒性 |
| 交易Cost建模 | 滑点、手续费、隔夜利息 | 精确模拟真实成本 |
| 多品种组合回测 | 相关性矩阵、资金分配 | 组合级风险收益分析 |

### 5.3 智能 EA 系统

| 功能 | 技术实现 | 说明 |
|------|---------|------|
| 市场状态分类 | Random Forest | 自动识别趋势/震荡/区间/低迷状态 |
| 策略选择器 | 状态→策略映射 | 不同市场状态启用不同策略 |
| 自学习能力 | Online RL + 经验回放 | 实盘交易数据持续优化策略 |
| 异常检测 | Isolation Forest | 检测市场异常行为，暂停交易 |
| 情绪分析 | LLM (GPT-4/Claude) | 分析新闻/社交媒体情绪，辅助决策 |

### 5.4 实时监控系统

| 功能 | 技术实现 | 说明 |
|------|---------|------|
| 实时 P&L 监控 | WebSocket → 前端 | 毫秒级延迟更新 |
| 风险指标监控 | VaR、CVaR、最大回撤 | 超过阈值自动告警 |
| 策略性能监控 | 胜率、盈亏比、夏普比率 | 策略衰减预警 |
| AI 决策可视化 | SHAP / Attention 热力图 | 解释 AI 为什么做出某个决策 |
| 多终端监控大屏 | Grafana + Prometheus | 系统级监控 |
| 智能告警 | 微信/钉钉/邮件/短信 | 分级告警机制 |

---

## 六、实施路径规划

### Phase 1：基础设施搭建（第 1-2 个月）

**目标**：建立 MT5-Python 通信桥梁，SQX 策略正常运行在 MT5 上

| 任务 | 交付物 | 优先级 |
|------|--------|--------|
| 搭建开发环境 | Docker 开发环境 + CI/CD 流水线 | P0 |
| 部署 MT5 终端集群 | 2+ Windows VPS + MT5 | P0 |
| 开发 ZeroMQ EA (MQL5) | 支持 PUB/SUB + REQ/REP 的 EA | P0 |
| 开发 Python AI Bridge | ZMQ_Execution_Bridge 类 | P0 |
| SQX 策略迁移 | 5-10 个核心策略在 MT5 上运行 | P0 |
| 数据存储搭建 | TimescaleDB + Redis | P1 |
| 行情数据接入 | 历史数据下载 + 实时 Tick 流 | P1 |

### Phase 2：AI 核心引擎开发（第 3-4 个月）

**目标**：完成强化学习交易代理的训练和验证

| 任务 | 交付物 | 优先级 |
|------|--------|--------|
| 特征工程系统 | 28+ 技术指标特征提取器 | P0 |
| 市场状态分类器 | Random Forest 状态识别模型 | P0 |
| RL 环境构建 | OpenAI Gym 兼容的交易环境 | P0 |
| PPO Agent 训练 | 训练好的 PPO 模型 | P0 |
| DQN Agent 训练 | 训练好的 DQN 模型 | P1 |
| 回测引擎开发 | 支持 Tick 级精度的回测系统 | P0 |
| 参数优化系统 | Optuna 分布式参数优化 | P1 |

### Phase 3：回测与实盘对接（第 5-6 个月）

**目标**：回测→实盘无缝切换，首批 AI 策略上线

| 任务 | 交付物 | 优先级 |
|------|--------|--------|
| Walk-Forward 验证 | 3 个月 Walk-Forward 回测报告 | P0 |
| Monte Carlo 验证 | 1000 次 Monte Carlo 模拟报告 | P0 |
| 模拟盘交易 | 1 个月模拟盘验证 | P0 |
| 实盘小规模上线 | 10% 资金实盘运行 | P0 |
| 风控系统开发 | 四级回撤控制 + 紧急平仓 | P0 |
| 监控大屏开发 | Grafana 监控面板 | P1 |
| 告警系统 | 分级告警机制 | P1 |

### Phase 4：平台化与规模化（第 7-12 个月）

**目标**：支持多策略、多账户、多品种，平台化运营

| 任务 | 交付物 | 优先级 |
|------|--------|--------|
| 多策略管理 | 支持 50+ 策略同时运行 | P0 |
| 多账户管理 | 支持 10+ 账户统一管理 | P0 |
| AI 策略工厂 | 策略自动生成、评估、部署流水线 | P0 |
| LLM 因子挖掘 | 自动化因子发现系统 | P1 |
| 用户界面开发 | Web 管理后台 | P1 |
| API 开放 | 第三方开发者接入 | P2 |
| 数据服务 | 历史数据 API 服务 | P2 |

---

## 七、关键开源资源清单

### 7.1 GitHub 核心项目

| 项目 | 地址 | 用途 |
|------|------|------|
| darwinex/dwx-zeromq-connector | github.com/darwinex/dwx-zeromq-connector | MT5 ZeroMQ 连接器的行业标准参考 |
| Gunther-Schulz/MQL5-JSON-API-2 | github.com/Gunther-Schulz/MQL5-JSON-API-2 | MQL5 JSON API，支持指标调用 |
| aminch8/MT5-ZeroMQ | github.com/aminch8/MT5-ZeroMQ | ZeroMQ EA 实现参考 |
| QuantConnect/Lean | github.com/QuantConnect/Lean | 开源量化引擎，回测架构参考 |
| Mrugendra7911/Deep_RL_Agent | github.com/Mrugendra7911/Deep_Reinforcement_Learning_Agent | RL 交易代理（PPO/DQN/SAC）|
| AndrzejMiskow/TradeAI | github.com/AndrzejMiskow/TradeAI | Transformer 时间序列交易模型 |
| vnpy/vnpy | github.com/vnpy/vnpy | 国产量化交易框架，架构参考 |

### 7.2 Python 核心依赖

```
pyzmq>=25.0          # ZeroMQ Python 绑定
pandas>=2.0          # 数据处理
numpy>=1.24          # 数值计算
stable-baselines3    # RL 算法（PPO/SAC/DQN）
torch>=2.0           # PyTorch 深度学习
scikit-learn         # 机器学习（随机森林、孤立森林）
optuna               # 超参数优化
kafka-python         # 消息队列
timescaledb          # 时序数据库
redis                # 缓存
fastapi              # API 框架
prometheus-client    # 监控指标
grafana-api          # 监控面板
openai               # LLM API 调用
anthropic            # Claude API 调用
```

---

## 八、知识产权与专利布局

### 8.1 发明专利方向（面向上市公司IP布局）

参考 VNAPI 专利（CN）和 Lean Engine 架构 [^774^][^768^]：

| 专利方向 | 创新点 | 保护范围 |
|---------|--------|---------|
| **AI 驱动交易信号生成方法** | RL + 市场状态分类 + 自适应奖励函数 | 信号生成全流程 |
| **分布式量化回测方法** | 回测代码与实盘代码统一，无需修改切换 | 回测→实盘无缝切换 |
| **多策略动态调度系统** | 市场状态→策略映射 + 实时性能评估 | 策略选择与切换 |
| **AI 可解释交易系统** | SHAP/Attention + 交易决策可视化 | AI 交易决策解释 |
| **多账户风险聚合方法** | 账户间风险关联计算 + 统一风控 | 多账户风控 |
| **实时滑点预测与规避** | 基于 LSTM 的滑点预测 + 动态延迟发送 | 订单执行优化 |

### 8.2 软件著作权

| 软件名称 | 功能描述 |
|---------|---------|
| AI 量化交易引擎系统 V1.0 | 核心交易决策引擎 |
| 智能回测与分析平台 V1.0 | 回测引擎 + 绩效分析 |
| 多账户交易管理系统 V1.0 | 账户管理 + 风险控制 |
| AI 策略监控与预警系统 V1.0 | 实时监控 + 智能告警 |

---

## 九、上市路径规划

### 9.1 分阶段商业目标

| 阶段 | 时间 | 目标 | 关键指标 |
|------|------|------|---------|
| **种子期** | 0-6 个月 | 产品 MVP 上线，首个实盘账户盈利 | 夏普比率 > 1.5，实盘收益率 > 20% |
| **成长期** | 6-12 个月 | 管理资金突破 1000 万美元 | AUM > $10M，策略数量 20+ |
| **扩张期** | 1-2 年 | 平台化运营，开放 API | 注册用户 1000+，第三方策略 50+ |
| **Pre-IPO** | 2-3 年 | 管理资金突破 1 亿美元 | AUM > $100M，营收 > $10M |
| **IPO** | 3-5 年 | 科创板/港股上市 | AUM > $1B，合规完备 |

### 9.2 合规准备

| 合规事项 | 时间线 | 说明 |
|---------|--------|------|
| 私募基金备案 | 第 6 个月 | 在中国证券投资基金业协会备案 |
| 香港 9 号牌 | 第 12 个月 | 香港证监会资产管理牌照 |
| FCA 注册 | 第 18 个月 | 英国金融行为监管局注册 |
| SEC 注册 | 第 24 个月 | 美国证券交易委员会投资顾问注册 |
| ISO 27001 | 持续 | 信息安全管理体系认证 |

---

## 十、技术风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| **MT5 断线** | 交易中断 | 心跳检测 + 自动重连 + 紧急平仓脚本 |
| **AI 模型过拟合** | 实盘亏损 | Walk-Forward + Monte Carlo + 模拟盘验证 |
| **延迟过高** | 滑点增大 | VPS 就近部署 + 延迟监控 + 动态阈值 |
| **数据质量** | 信号错误 | 多数据源交叉验证 + 异常检测 |
| **策略衰减** | 收益下降 | 持续监控夏普比率，衰减时自动切换策略 |
| **网络安全** | 账户被盗 | IP 白名单 + 防火墙 + API 密钥轮换 + 2FA |

---

## 十一、团队配置建议

| 角色 | 人数 | 技能要求 |
|------|------|---------|
| 量化研究员 | 2-3 | 金融工程 + Python + 统计学 |
| AI 工程师 | 2 | PyTorch + RL + NLP |
| 后端工程师 | 2-3 | Python + 分布式系统 + 数据库 |
| MQL5 开发 | 1-2 | MQL5 + ZeroMQ + MT5 深度开发 |
| DevOps | 1 | Docker + K8s + CI/CD |
| 产品经理 | 1 | 量化交易产品经验 |
| 风控专员 | 1 | 金融风控 + 量化风险模型 |

---

## 附录 A：核心代码参考

### A.1 MQL5 ZeroMQ EA 完整骨架

```mql5
//+------------------------------------------------------------------+
//| ZeroMQ EA for MT5 - AI Trading Bridge                            |
//+------------------------------------------------------------------+
#include <Zmq/Zmq.mqh>

Context context;
Socket pubSocket, repSocket;

int OnInit() {
    // PUB socket for market data
    pubSocket = context.socket(ZMQ_PUB);
    pubSocket.bind("tcp://*:5555");
    // REP socket for trading commands
    repSocket = context.socket(ZMQ_REP);
    repSocket.bind("tcp://*:5556");
    return INIT_SUCCEEDED;
}

void OnTick() {
    // Publish tick data
    MqlTick tick;
    if(SymbolInfoTick(_Symbol, tick)) {
        string json = StringFormat(
            "{\"symbol\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,\"time\":%I64d}",
            _Symbol, tick.bid, tick.ask, tick.time
        );
        ZmqMsg msg(json);
        pubSocket.send(msg);
    }
    // Check for trade commands (non-blocking)
    ZmqMsg req;
    if(repSocket.recv(req, ZMQ_NOBLOCK)) {
        string cmd = req.getData();
        string response = ExecuteTrade(cmd);
        ZmqMsg resp(response);
        repSocket.send(resp);
    }
}

string ExecuteTrade(string json) {
    // Parse JSON, execute OrderSend, return result
    // ... (包含完整的订单处理逻辑)
    return "{\"status\":\"ok\",\"ticket\":12345}";
}

void OnDeinit(const int reason) {
    pubSocket.close();
    repSocket.close();
}
```

### A.2 RL 交易环境（OpenAI Gym 兼容）

```python
import gym
from gym import spaces
import numpy as np
import pandas as pd

class TradingEnv(gym.Env):
    def __init__(self, df, initial_balance=10000):
        super().__init__()
        self.df = df
        self.initial_balance = initial_balance
        # 28 个特征 + 3 个账户状态
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(31,), dtype=np.float32
        )
        # 动作：0=Hold, 1=Buy, 2=Sell, 3=Close
        self.action_space = spaces.Discrete(4)

    def reset(self):
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0  # 0=无持仓, 1=多, -1=空
        return self._get_observation()

    def step(self, action):
        reward = self._calculate_reward(action)
        self.current_step += 1
        done = self.current_step >= len(self.df) - 1
        obs = self._get_observation()
        return obs, reward, done, {}

    def _get_observation(self):
        features = self.df.iloc[self.current_step][[
            'EMA_10', 'EMA_50', 'RSI', 'ATR', 'MACD',
            'BB_upper', 'BB_lower', 'ADX', 'CCI', 'MOM',
            'Volume_MA', 'Volatility', 'Returns', 'Log_Returns',
            'High_Low', 'Open_Close', 'SMA_20', 'SMA_200',
            'Stoch_K', 'Stoch_D', 'Williams_R', 'OBV',
            'MFI', 'ROC', 'TSI', 'UO', 'Keltner',
            'Donchian'
        ]].values
        account_state = np.array([
            self.balance / self.initial_balance,
            self.position,
            self.current_step / len(self.df)
        ])
        return np.concatenate([features, account_state]).astype(np.float32)

    def _calculate_reward(self, action):
        # Convex P&L reward with drawdown penalty
        current_price = self.df.iloc[self.current_step]['close']
        next_price = self.df.iloc[self.current_step + 1]['close']
        pnl = 0
        if action == 1 and self.position == 0:  # Buy
            self.position = 1
            self.entry_price = current_price
        elif action == 2 and self.position == 0:  # Sell
            self.position = -1
            self.entry_price = current_price
        elif action == 3 and self.position != 0:  # Close
            pnl = (current_price - self.entry_price) * self.position
            self.balance += pnl
            self.position = 0
        # 持仓中按市价计算浮动盈亏
        if self.position != 0:
            unrealized = (next_price - self.entry_price) * self.position
        else:
            unrealized = 0
        drawdown_penalty = max(0, (self.initial_balance - self.balance) * 0.01)
        return pnl + unrealized * 0.1 - drawdown_penalty
```

---

## 附录 B：推荐技术书籍与论文

| 类型 | 资源 | 用途 |
|------|------|------|
| 论文 | Reinforcement Learning for Quantitative Trading (ACM 2025) | RL 量化交易综述 |
| 论文 | Artificial Neural Networks for Stock Market Prediction | LSTM/CNN/MLP 预测 |
| 书籍 | Advances in Financial Machine Learning (Marcos Lopez de Prado) | 金融机器学习经典 |
| 书籍 | Reinforcement Learning for Finance (Berkeley) | 金融 RL 应用 |
| 开源 | QuantConnect Lean Engine Documentation | 回测引擎架构参考 |
| 文档 | StrategyQuant X Programming Guide | SQX 策略编程 |

---

*本方案基于 2026 年 4-5 月最新技术调研，涵盖 GitHub 15+ 开源项目、ACM/IEEE 权威论文、以及多个生产级 MT5-Python 集成实践。方案设计面向"全球最大私募"和"量化平台上市公司"的长期愿景，采用模块化架构，支持渐进式演进。*
