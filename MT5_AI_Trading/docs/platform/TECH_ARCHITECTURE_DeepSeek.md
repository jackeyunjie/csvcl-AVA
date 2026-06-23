# AI量化多周期视角交易平台 — 技术架构设计方案 (DeepSeek版)

> 版本: v2.0 | 日期: 2026-06-06 | 模型: DeepSeek
>
> 本文档基于现有 `MT5_AI量化交易系统技术方案.md` 中的 ZeroMQ 分布式架构,
> 结合最新开源多Agent项目 (TradingAgents, CryptoTrader AI, RD-Agent, ContestTrade) 的架构思想,
> 设计完整的 AI 量化多周期视角交易平台技术架构。
>
> 配合阅读: 产品功能规格说明 DeepSeek 版、核心模块详细设计 DeepSeek 版

---

## 一、技术选型

### 1.1 核心决策

| 决策项 | 选型 | 理由 |
|--------|------|------|
| **编程语言** | Python 3.12 (核心引擎) + TypeScript (Web前端) | Python量化生态最完整, TypeScript前端现代化 |
| **MT5对接** | **ZeroMQ PUB/SUB + REQ/REP 双通道** | 已有技术方案, 微秒级延迟, 支持分布式 |
| **LLM提供商** | DeepSeek (主力) + OpenAI/Claude (备用) | 成本低, 中文能力强, API兼容OpenAI格式 |
| **AI框架** | LangGraph (Agent编排) + PyTorch (ML) | TradingAgents已验证LangGraph适合多Agent |
| **回测引擎** | **自研 Pipeform Engine** (继承v5) | 需要as-of对齐+多Agent辩论+State视角, 现有引擎不满足 |
| **数据库** | SQLite (本地缓存) + RDS MySQL 8.0 (远端) | 已有阿里云RDS, 零额外成本 |
| **消息队列** | Redis (轻量替代Kafka) | 单机部署不需要Kafka的复杂度 |
| **Web框架** | FastAPI (后端) + React (前端) | 性能好, 异步原生支持, 量化圈标准 |
| **部署** | 单机 Windows (Phase 1) → Docker + 阿里云ECS (Phase 2) | 渐进式, 不提前过度工程化 |

### 1.2 不选的技术及理由

| 不选 | 理由 |
|------|------|
| **Rust核心引擎** (OpenFinClaw路线) | 人才难找, MT5 Python API不兼容, 当前性能瓶颈在数据量不在语言 |
| **Kubernetes集群** | Phase 1单机完全够用, K8s运维成本远超收益 |
| **Apache Kafka** | 单机场景Redis Pub/Sub足够, Kafka需要额外运维 |
| **Qlib作为回测引擎** | Qlib面向A股, 不支持MT5数据源, 不支持我们的squeeze多周期逻辑 |
| **vnpy作为交易执行** | vnpy太重(28K stars但需学整个框架), 我们只需MT5一个券商 |
| **TradingAgents直接套用** | TradingAgents面向美股+Yahoo Finance, 我们需要MT5+多周期收缩逻辑 |

### 1.3 竞品技术架构对比

| 项目 | 架构亮点 | 我们借鉴 | 我们不照搬的原因 |
|------|---------|---------|----------------|
| **TradingAgents** (71K⭐) | LangGraph多Agent, 分析师→辩论→交易员四层 | Agent分层思想、辩论机制设计 | 面向美股基本面, 我们的核心是技术面多周期收缩 |
| **CryptoTrader AI** | 4Agent辩论+硬编码风控门 | 风控不依赖LLM用硬规则 | 只支持Crypto, 我们需外汇/股指/股票 |
| **sudo-trade** | 牛熊Agent辩论+裁判 | 辩论流程设计、EventBus解耦 | 只有股票, 用yfinance数据, 无回测 |
| **RD-Agent** (微软) | R&D Loop自动化因子挖掘 | 假设→实现→回测→反馈循环 | 面向A股, 依赖Qlib, Windows需WSL |
| **NexQuant** | RD-Agent + 1分钟EUR/USD | Forex量化+因子挖掘实际案例 | 基于RD-Agent, 同样依赖Qlib环境 |
| **ai-hedge-fund** (59K⭐) | 14个传奇投资者人格Agent | 多视角分析理念 | Demo性质, 无实盘, 用yfinance |
| **ContestTrade** | 内部竞赛+排名淘汰机制 | Agent淘汰机制 | 无多周期视角, 无MT5 |
| **OpenFinClaw** | 自然语言→策略60秒 | CLI+策略Marketplace理念 | Rust核心, 生态不兼容我们现有代码 |

---

## 二、系统总体架构

### 2.1 四层架构

```
┌──────────────────────────────────────────────────────────────────┐
│              接入层 (Gateway Layer)                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │ CLI 命令  │  │ Web 仪表盘│  │ Telegram  │  │ 邮件通知      │   │
│  │ pipeform  │  │ React UI │  │ Bot 推送  │  │ (复用email_   │   │
│  │           │  │          │  │           │  │  sender.py)   │   │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬───────┘   │
│        └──────────────┴─────────────┴───────────────┘           │
│                              │ FastAPI REST + WebSocket           │
├──────────────────────────────┼───────────────────────────────────┤
│              业务编排层 (Orchestration Layer)                      │
│  ┌────────────────┐ ┌──────────────────┐ ┌──────────────────┐   │
│  │ Strategy        │ │ Debate           │ │ Observation      │   │
│  │ Orchestrator    │ │ Orchestrator     │ │ Scheduler        │   │
│  │ (策略生命周期)   │ │ (Agent辩论编排)   │ │ (定时扫描/日报)   │   │
│  └───────┬────────┘ └────────┬─────────┘ └────────┬─────────┘   │
│          └───────────────────┼────────────────────┘             │
│                              │                                    │
├──────────────────────────────┼───────────────────────────────────┤
│              核心引擎层 (Core Engine Layer)                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   Pipeform Engine (继承v5)                    │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │ │
│  │  │ Data     │ │ Signal   │ │ Backtest │ │ Report   │       │ │
│  │  │ Pipeline │ │ Detector │ │ Engine   │ │ Builder  │       │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  Agent Framework                              │ │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐  │ │
│  │  │R-H1    │ │R-M15   │ │R-D1    │ │E-View  │ │RK-View  │  │ │
│  │  │Squeeze │ │Squeeze │ │Stocks  │ │(执行)   │ │(风控)   │  │ │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └─────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  LLM Gateway                                  │ │
│  │  DeepSeek API / OpenAI API / Claude API / 本地 Ollama         │ │
│  └─────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│              基础设施层 (Infrastructure Layer)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ MT5      │ │ RDS      │ │ Redis    │ │ SQLite +         │   │
│  │ ZeroMQ   │ │ MySQL 8  │ │ 消息队列  │ │ Feather 缓存     │   │
│  │ 桥接器    │ │ (远程)   │ │          │ │ (本地)           │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 关键数据流

#### 2.2.1 实盘交易数据流 (远期)

```
MT5终端 (Windows)
  │ OnTick() 触发
  ▼
ZeroMQ PUB Socket (tcp://*:5555)
  │ JSON: {"symbol":"GER40","bid":24910.5,"ask":24912.0,"time":...}
  ▼
Python Subscriber (pipeform/bridge/mt5_subscriber.py)
  │ 解析JSON → 写入Redis Stream
  ▼
Redis Stream "market:ticks:GER40"
  │
  ├─→ Agent-H1-Squeeze: 每小时聚合为H1 bar → 检查squeeze setup
  ├─→ Agent-M15-Squeeze: 每15分钟聚合为M15 bar → 检查squeeze setup
  └─→ RK-View: 实时检查风险限额

发现setup后:
  Agent → Redis Stream "signals:pending"
  RK-View 检查通过 → Redis Stream "signals:approved"
  E-View 读取 → ZeroMQ REQ Socket → MT5 OrderSend()
```

#### 2.2.2 回测数据流

```
用户命令: pipeform backtest --strategy squeeze_v5 --symbols GER40
  │
  ▼
StrategyOrchestrator.backtest()
  │
  ▼
DataPipeline.fetch(symbol="GER40", timeframes=["M15","H1","H4"], days=365)
  │ 检查SQLite缓存 → 未命中则调用MT5 API
  ▼
pd.DataFrame (M15/H1/H4 OHLCV, timestamp对齐)
  │
  ▼
SignalDetector.process(df) → squeeze_setups
  │ compute_bb_width / compute_sr_range / compute_adx / compute_squeeze_score
  │ find_setups / detect_breakouts
  ▼
BacktestEngine.run(setups, events, exit_rules=["fixed_hold_5bar","structure_stop","1r_partial_trail"])
  │ Walk-Forward split → 各项指标计算
  ▼
ReportBuilder.build(metrics, trades) → Markdown报告 + JSON数据
```

#### 2.2.3 Agent辩论数据流

```
用户命令: pipeform debate --topic "GER40 M15 short"
  │
  ▼
DebateOrchestrator.debate(topic, asset_class="index_fx")
  │
  ├─→ Agent-H1-Squeeze.analyze() → AgentReport
  │     使用已有v5回测数据, 生成标准报告
  │
  ├─→ Agent-M15-Squeeze.analyze() → AgentReport  
  │     使用Phase 1诊断数据, 标注"未完整回测"
  │
  └─→ Agent-State-Short.analyze() → AgentReport
        使用State策略挖掘数据 (204组实验中short最佳)
  │
  ▼
DebateOrchestrator.synthesize(reports)
  │ 交叉验证: 对比各Agent的Walk-Forward Test段
  │ 识别共识: 所有Agent一致的结论
  │ 标记分歧: 需要人工判断的冲突
  ▼
DebateResult → Markdown报告 + JSON → 用户
```

---

## 三、与现有系统的集成设计

### 3.1 现有基础设施清单

| 基础设施 | 位置 | 状态 | 集成方式 |
|----------|------|------|---------|
| MT5 Python API | `python/backtest_platform/data_layer.py` | ✅ 可用 | 封装为 `DataPipeline.fetch()` |
| Squeeze Observer | `python/analytics/squeeze_observer.py` | ✅ 可用 | 拆分为 `SignalDetector` 模块 |
| Multi-TF Squeeze | `python/analytics/multi_timeframe_squeeze.py` | ✅ 可用 | 核心指标计算逻辑保留 |
| v5 研究引擎 | `squeeze_multi_timeframe_research_v5.py` | ✅ 可用 | 重构为 `BacktestEngine` + `ReportBuilder` |
| v4 继承链 | `squeeze_multi_timeframe_research_v4.py` / `v3.py` | ✅ 归档 | 保留在 `archive/`, 不删除 |
| 模拟盘扫描 | `run_v5_simulation.py` | ✅ 可用 | 重构为 `ObservationScheduler.scan_once()` |
| 日报生成 | `run_v5_daily_summary.py` | ✅ 可用 | 重构为 `DailyReporter` 类 |
| 观察数据库 | `observation_db.py` | ✅ 可用 | 封装为 `ObservationStore` |
| 状态具体化 | `reification_agent.py` | ✅ 可用 | 整合到 `E-View Agent` |
| M15 Phase1 | `squeeze_m15_phase1_diagnosis.py` | ✅ 可用 | 封装为 `Agent-M15-Squeeze` |
| MT4数据处理器 | `process_real_mt4_data.py` | ✅ 可用 | 作为MT4数据桥接, 增强多数据源支持 |
| CSV颜色标记 | `csv_color_marker.py` | ✅ 可用 | 用于Excel报告的颜色增强输出 |
| 邮件发送 | `email_sender.py` (mt4-data-processor) | ✅ 可用 | 复用为通知推送通道 |
| 阿里云RDS | `rm-2zeh695s5607s218p` MySQL 8.0 | ✅ 可用 | 策略版本、Agent报告、辩论记录持久化 |
| 阿里云ECS | `iZ6w2tu6dc6tfbZ` Windows Server 2022 | ✅ 可用 | Phase 2 部署目标 |

### 3.2 集成策略: 1+1>2

```
现有代码                      →    新平台集成           效果
─────────────────────────────────────────────────────────
v5 squeeze引擎 (已验证)       →    BacktestEngine核心    零风险, 直接复用
run_v5_simulation.py          →    ObservationScheduler   增强为持续监控
email_sender.py               →    通知推送通道           日报/告警自动发送
process_real_mt4_data.py      →    MT4数据桥接器          MT4+MT5双数据源
csv_color_marker.py           →    报告颜色增强           回测报告可视化
RDS MySQL                     →    策略元数据存储         已有实例, 零额外成本

新增能力:
TradingAgents的LangGraph       →    DebateOrchestrator    辩论编排
CryptoTrader AI的风控门        →    RK-View硬编码规则      风控不依赖LLM
RD-Agent的R&D Loop            →    StrategyOptimizer      因子自动挖掘
ContestTrade的竞赛排名          →    Agent排名淘汰机制      自动淘汰低效Agent
```

---

## 四、核心模块技术设计

### 4.1 ZeroMQ 桥接器 (继承现有方案)

```python
# pipeform/bridge/mt5_bridge.py
# 继承 MT5_AI量化交易系统技术方案.md 中的设计

class MT5Bridge:
    """MT5 ZeroMQ 桥接器 — 继承现有技术方案"""
    
    def __init__(self, mt5_host="localhost", pub_port=5555, req_port=5556):
        self.context = zmq.Context()
        # PUB/SUB: 行情数据订阅
        self.sub = self.context.socket(zmq.SUB)
        self.sub.connect(f"tcp://{mt5_host}:{pub_port}")
        self.sub.setsockopt_string(zmq.SUBSCRIBE, "")
        # REQ/REP: 交易指令
        self.req = self.context.socket(zmq.REQ)
        self.req.connect(f"tcp://{mt5_host}:{req_port}")
        # 心跳检测
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 5  # 5秒心跳
    
    def get_tick(self) -> Optional[dict]:
        """非阻塞获取Tick"""
        try:
            msg = self.sub.recv_string(flags=zmq.NOBLOCK)
            return json.loads(msg)
        except zmq.Again:
            return None
    
    def send_order(self, symbol, action, volume, sl=0, tp=0, max_slippage=10) -> dict:
        """发送交易指令"""
        payload = {
            "action": action, "symbol": symbol,
            "volume": volume, "sl": sl, "tp": tp,
            "max_slippage_points": max_slippage
        }
        self.req.send_string(json.dumps(payload))
        return json.loads(self.req.recv_string())
```

### 4.2 AI引擎设计

#### 4.2.1 LLM Gateway (统一抽象层)

```python
# pipeform/ai/llm_gateway.py

class LLMGateway:
    """统一LLM接入层 — 支持多Provider切换"""
    
    PROVIDERS = {
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-chat",
            "cost_per_1k_input": 0.00014,   # ¥0.001
            "cost_per_1k_output": 0.00028,  # ¥0.002
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o",
            "cost_per_1k_input": 0.0025,
            "cost_per_1k_output": 0.01,
        },
        "local_ollama": {
            "base_url": "http://localhost:11434/v1",
            "default_model": "qwen2.5:14b",
            "cost_per_1k_input": 0,
            "cost_per_1k_output": 0,
        }
    }
    
    def chat(self, messages, provider="deepseek", model=None, json_mode=False) -> str:
        """统一对话接口"""
        # 自动选择provider, 支持fallback
        pass
    
    def extract_strategy(self, user_input: str) -> StrategySpec:
        """从自然语言提取策略规格 (核心能力)"""
        prompt = f"""
        你是一个量化策略解析器。从用户输入中提取策略参数, 输出JSON。
        
        用户输入: {user_input}
        
        输出格式:
        {{
            "strategy_type": "squeeze_breakout | ma_cross | trend_follow | mean_reversion",
            "timeframe": "M15 | H1 | H4 | D1",
            "entry_conditions": [...],
            "filter_conditions": [...],
            "exit_rules": [...],
            "risk_params": {{"stop_loss_pips": 80, "take_profit_ratio": 3.0}},
            "symbols": ["GER40", ...],
            "ambiguities": ["哪些参数需要用户澄清"]
        }}
        """
        return self._parse_json_response(self.chat([{"role": "user", "content": prompt}]))
```

### 4.3 DataPipeline (数据流水线)

```python
# pipeform/engine/data_pipeline.py

class DataPipeline:
    """统一数据获取层 — 封装MT5 API + 缓存"""
    
    def __init__(self):
        self.cache = SQLiteCache("data/cache.db")  # 本地缓存
        self.mt5_fetcher = MT5DataFetcher()         # MT5直连
    
    def fetch(self, symbol, timeframes, lookback_days) -> Dict[str, pd.DataFrame]:
        """
        获取数据 — 缓存优先
        
        返回: {"M15": df_m15, "H1": df_h1, "H4": df_h4}
        所有df的timestamp已对齐, 已去除未来函数风险
        """
        result = {}
        for tf in timeframes:
            # 1. 查缓存
            df = self.cache.get(symbol, tf, lookback_days)
            if df is not None:
                result[tf] = df
                continue
            # 2. 从MT5获取
            df = self.mt5_fetcher.fetch(symbol, tf, lookback_days)
            # 3. 写入缓存
            self.cache.put(symbol, tf, df)
            result[tf] = df
        return result
```

---

## 五、技术风险与应对

| 风险 | 等级 | 应对 |
|------|------|------|
| MT5 ZeroMQ断连 | 🔴 高 | 5秒心跳+自动重连+断连时挂起交易 |
| LLM API不可用 | 🟡 中 | 多Provider Fallback (DeepSeek→OpenAI→本地Ollama) |
| 回测结果过拟合 | 🔴 高 | Walk-Forward+MC模拟+Agent交叉验证 |
| M15数据量爆炸 | 🟡 中 | expanding分位数而非rolling+只保留必要列 |
| 多Agent辩论冲突无法解决 | 🟢 低 | 明确标记"需人工判断"+降权规则 |
| 策略衰减 | 🟡 中 | 健康度三色灯+自动触发重优化告警 |
| 网络延迟导致滑点 | 🟡 中 | `max_slippage_points`拒绝机制+延迟监控 |

---

## 六、关键开源项目引用清单

| 项目 | GitHub | 借鉴重点 |
|------|--------|---------|
| **TradingAgents** | `TauricResearch/TradingAgents` | LangGraph多Agent四层架构, 牛熊辩论机制 |
| **CryptoTrader AI** | `ma-pony/cryptotrader-ai` | 4Agent辩论+硬编码风控门, 中文输出 |
| **ai-hedge-fund** | `virattt/ai-hedge-fund` | 多投资人格Agent, 风险管理Agent |
| **sudo-trade** | `shravanrevanna/sudo-trade` | 牛熊辩论+裁判, EventBus插件架构 |
| **RD-Agent (微软)** | `microsoft/RD-Agent` | R&D Loop自动化因子挖掘, CoSTEER代码生成 |
| **NexQuant** | `TPTBusiness/NexQuant` | RD-Agent在外汇1分钟数据上的实战 |
| **ContestTrade** | `FinStep-AI/ContestTrade` | 内部竞赛排名, Agent淘汰机制 |
| **FinRL-X** | `AI4Finance-Foundation/FinRL-Trading` | weight-centric模块化架构, 回测→实盘一致性 |
| **OpenFinClaw** | `mirror29/openfinclaw-cli` | CLI+自然语言→策略, 竞品对比 |
| **LLM-TradeBot** | `EthanAlgoX/LLM-TradeBot` | Multi-Agent crypto trading, OpenRouter支持 |
| **VnPy** | `vnpy/vnpy` | vnpy.alpha ML因子模块, MT5 Gateway |
| **Freqtrade** | `freqtrade/freqtrade` | FreqAI ML模块, Telegram通知 |
