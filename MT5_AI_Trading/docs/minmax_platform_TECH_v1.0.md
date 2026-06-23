# MiniMax AI量化平台 — 技术架构设计方案

> 版本: v1.0 (minmax标识)  
> 日期: 2026-06-06  
> 状态: 正式版

---

## 1. 技术选型

### 1.1 语言与框架

| 层级 | 技术选型 | 理由 |
|------|----------|------|
| **核心引擎** | Python 3.12 | 量化生态成熟、MT5 API原生支持 |
| **AI/LLM** | OpenAI GPT-4 + Claude | 策略生成需强推理能力 |
| **Web后端** | FastAPI | 高性能异步API、自动文档 |
| **Web前端** | React 18 + TypeScript | 现代仪表盘、组件化 |
| **实时通信** | WebSocket + ZeroMQ | 行情推送、MT5桥接 |
| **任务调度** | APScheduler | 轻量定时任务 |
| **数据存储** | DuckDB + SQLite | 嵌入式分析、策略缓存 |

### 1.2 与现有系统整合

**复用的现有组件**:

| 组件 | 位置 | 整合方式 |
|------|------|----------|
| MT5Bridge (ZeroMQ) | `python/core/mt5_bridge.py` | 直接集成 |
| StateHexEngine | `python/ai_engine/state_hex_engine.py` | 核心引擎 |
| KVB回测平台 | `python/backtest_platform/` | 继承架构 |
| process_real_mt4_data | `process_real_mt4_data.py` | 数据处理流程 |
| csv_color_marker | `csv_color_marker.py` | 可视化组件 |
| EmailSender | `email_sender.py` | 通知系统 |
| observation_db | `observation_db.py` | 复现检测 |

---

## 2. 系统架构

### 2.1 总体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MiniMax AI量化平台架构                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     用户交互层 (User Interface)                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │  │   Web UI    │  │  CLI Tool   │  │ Telegram Bot│  │  Email Alert │   │  │
│  │  │  (React)    │  │  (Click)    │  │             │  │             │   │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │  │
│  └─────────┼────────────────┼────────────────┼────────────────┼──────────┘  │
│            │                │                │                │              │
│  ┌─────────▼────────────────▼────────────────▼────────────────▼──────────┐  │
│  │                     API网关层 (API Gateway)                            │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                     FastAPI Server                              │  │  │
│  │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │  │  │
│  │  │  │ Strategy  │ │ Backtest  │ │  Market   │ │ Deployment│       │  │  │
│  │  │  │ Generator │ │  Engine   │ │  Observer │ │  Manager  │       │  │  │
│  │  │  │   API     │ │   API     │ │   API     │ │   API     │       │  │  │
│  │  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│  ┌─────────────────────────────────▼───────────────────────────────────────┐│
│  │                     多Agent协作层 (Multi-Agent)                          ││
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  ││
│  │  │  Research   │◄──►│ Orchestrator│◄──►│   Risk      │                  ││
│  │  │  Agent      │    │             │    │   Agent     │                  ││
│  │  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                  ││
│  │         │                 │                 │                          ││
│  │  ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐                 ││
│  │  │ H1_Squeeze  │    │ M15_Squeeze │    │  Execution  │                 ││
│  │  │ D1_State    │    │ State_Mining│    │   Agent     │                 ││
│  │  │ Reification │    │ Pattern_Find│    │             │                 ││
│  │  └─────────────┘    └─────────────┘    └─────────────┘                 ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│  ┌─────────────────────────────────▼───────────────────────────────────────┐│
│  │                      核心引擎层 (Core Engine)                            ││
│  │  ┌─────────────────────────────────────────────────────────────────┐   ││
│  │  │                   MiniMax Backtest Platform                     │   ││
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │   ││
│  │  │  │  Data   │ │ Compute │ │Strategy │ │Execution│ │Presentation│  │   ││
│  │  │  │  Layer  │ │  Layer  │ │  Layer  │ │  Layer  │ │   Layer   │  │   ││
│  │  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │   ││
│  │  │       └───────────┴───────────┴───────────┴───────────┘        │   ││
│  │  │                         StateHex Engine                        │   ││
│  │  └─────────────────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│  ┌─────────────────────────────────▼───────────────────────────────────────┐│
│  │                     基础设施层 (Infrastructure)                         ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     ││
│  │  │  MT5Bridge │  │  DuckDB     │  │   Redis     │  │   Docker    │     ││
│  │  │  (ZeroMQ)  │  │  Storage    │  │   Cache     │  │   Deploy    │     ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据流架构                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   MT5 Terminal                                                              │
│        │                                                                    │
│        │ OHLCV Tick                                                         │
│        ▼                                                                    │
│   ┌─────────────┐      ZeroMQ PUB/SUB      ┌─────────────┐                  │
│   │ MT5 Bridge  │ ──────────────────────→ │ Data Layer  │                  │
│   │ (ZeroMQ)    │                          │ MT5DataBridge│                  │
│   └─────────────┘                          └──────┬──────┘                  │
│                                                  │                          │
│                                                  ▼                          │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        Data Pipeline                                │   │
│   │                                                                      │   │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐        │   │
│   │  │  Parse   │───→│  Validate│───→│  Align   │───→│  Cache   │        │   │
│   │  │  Tick    │    │  Quality │    │  Multi-TF│    │  DuckDB  │        │   │
│   │  └──────────┘    └──────────┘    └──────────┘    └──────────┘        │   │
│   │                                                            │          │   │
│   └────────────────────────────────────────────────────────────┘          │   │
│                                       │                                    │
│                                       ▼                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     Compute Pipeline                                │   │
│   │                                                                      │   │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐        │   │
│   │  │ StateHex │───→│ Squeeze  │───→│ Momentum │───→│ Resonance│        │   │
│   │  │  Encode  │    │  Detect  │    │   Calc   │    │  Analyze │        │   │
│   │  └──────────┘    └──────────┘    └──────────┘    └──────────┘        │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                       │                                    │
│                                       ▼                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     Agent Pipeline                                  │   │
│   │                                                                      │   │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐        │   │
│   │  │ Research │───→│ Debate   │───→│  Risk    │───→│ Execution │        │   │
│   │  │  Signal  │    │  Filter  │    │  Check   │    │   Order  │        │   │
│   │  └──────────┘    └──────────┘    └──────────┘    └──────────┘        │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                       │                                    │
│                                       ▼                                    │
│   ┌─────────────┐      ZeroMQ REQ/REP      ┌─────────────┐                  │
│   │ MT5 Bridge  │ ←─────────────────────── │   Result    │                  │
│   │ (Execute)   │                         │   Store     │                  │
│   └─────────────┘                         └─────────────┘                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心模块详细设计

### 3.1 自然语言策略生成引擎

```python
# mini_max/strategy/generator.py

class NaturalLanguageStrategyGenerator:
    """
    自然语言 → 可执行策略代码
    
    核心流程:
    1. LLM解析 → 提取策略要素
    2. 模板匹配 → 选择最接近模板
    3. 参数填充 → 生成策略代码
    4. 语法验证 → 确保可执行
    5. 回测配置 → 生成配置
    """
    
    def __init__(
        self,
        llm_provider: str = "openai",
        api_key: str = None,
        template_registry: TemplateRegistry = None
    ):
        self.llm = LLMClient(provider=llm_provider, api_key=api_key)
        self.templates = template_registry or TemplateRegistry()
        
    async def generate(
        self,
        natural_language: str,
        context: Dict = None
    ) -> StrategyBundle:
        """
        生成策略
        
        Args:
            natural_language: "MA5上穿MA20买入，跌破MA10卖出"
            context: 额外上下文 {symbols, timeframes}
        
        Returns:
            StrategyBundle: {code, config, doc, confidence}
        """
        # 1. LLM解析策略要素
        elements = await self._extract_elements(natural_language)
        
        # 2. 模板匹配
        template = self.templates.match(elements)
        
        # 3. 生成代码
        code = template.render(elements)
        
        # 4. 语法验证
        self._validate_syntax(code)
        
        # 5. 生成回测配置
        config = self._generate_backtest_config(elements, context)
        
        return StrategyBundle(
            code=code,
            config=config,
            template_id=template.id,
            confidence=elements.confidence
        )
    
    async def _extract_elements(self, text: str) -> StrategyElements:
        """LLM解析策略要素"""
        prompt = STRATEGY_EXTRACTION_PROMPT.format(user_input=text)
        response = await self.llm.generate(prompt, schema=StrategyElements)
        return StrategyElements.parse_raw(response)
```

**策略提取Prompt模板**:
```python
STRATEGY_EXTRACTION_PROMPT = """
你是一位专业的量化交易策略工程师。请将用户的交易想法转化为结构化要素。

用户输入: {user_input}

请提取以下要素（如未提及则标记为null）：
1. 品种 (symbol): XAUUSD, EURUSD, GER40, US30等
2. 周期 (timeframe): M15, H1, H4, D1等
3. 方向 (direction): long / short / both
4. 入场条件 (entry): 列表形式
5. 出场条件 (exit): 列表形式
6. 持仓周期 (hold_bars): 数字或null
7. 止损类型 (stop_loss): 前低/ATR/固定点数
8. 止盈类型 (take_profit): 固定R/风险回报比/持仓周期
9. 过滤器 (filters): 额外过滤条件

输出格式（JSON）:
{
    "symbol": "...",
    "timeframe": "...",
    "direction": "...",
    "entry_conditions": [...],
    "exit_conditions": [...],
    "hold_bars": ...,
    "stop_loss": "...",
    "take_profit": "...",
    "filters": [...],
    "confidence": 0.0-1.0
}
"""
```

### 3.2 快速回测引擎

```python
# mini_max/backtest/engine.py

class FastBacktestEngine:
    """
    30秒回测引擎
    
    设计要点:
    - 向量化预筛选 + 事件驱动精确验证
    - 多周期数据对齐 (merge_asof)
    - MT5实际点差模拟
    - Walk-Forward滚动回测
    """
    
    def __init__(
        self,
        data_bridge: MT5DataBridge,
        state_engine: StateHexEngine,
        execution_layer: ExecutionLayer
    ):
        self.data = data_bridge
        self.state = state_engine
        self.executor = execution_layer
        
    async def run(
        self,
        strategy: Strategy,
        config: BacktestConfig
    ) -> BacktestReport:
        """
        执行回测
        
        目标: 30秒内返回结果
        """
        start_time = time.time()
        
        # 1. 数据加载 (并行)
        data = await self._load_data_parallel(
            config.symbols,
            config.timeframes,
            config.date_range
        )
        
        # 2. 向量化预筛选 (快速)
        if self._vectorized_filter(strategy, data):
            return BacktestReport(
                status="rejected",
                reason="策略逻辑不符合市场结构",
                elapsed_ms=time.time() - start_time
            )
        
        # 3. 计算State Hex特征
        features = self.state.calculate_features(data)
        
        # 4. Walk-Forward回测
        results = []
        for train, val, test in self._walk_forward_split(data, config):
            # 4.1 训练期参数优化
            params = self._optimize(strategy, train)
            
            # 4.2 验证期检查
            val_result = await self._run_single(strategy, params, val)
            if not self._validate_result(val_result):
                continue
            
            # 4.3 测试期最终结果
            test_result = await self._run_single(strategy, params, test)
            results.append(WalkForwardResult(train, val, test_result))
            
            # 超时检查
            if time.time() - start_time > 25:
                break
        
        # 5. 生成报告
        report = self._generate_report(results)
        report.elapsed_ms = time.time() - start_time
        
        return report
    
    async def _load_data_parallel(
        self,
        symbols: List[str],
        timeframes: List[str],
        date_range: Tuple[str, str]
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """并行加载多品种多周期数据"""
        tasks = [
            self.data.get_ohlcv(symbol, tf, date_range[0], date_range[1])
            for symbol in symbols
            for tf in timeframes
        ]
        results = await asyncio.gather(*tasks)
        
        # 整理为 {symbol: {timeframe: dataframe}}
        data = {}
        idx = 0
        for symbol in symbols:
            data[symbol] = {}
            for tf in timeframes:
                data[symbol][tf] = results[idx]
                idx += 1
        
        return data
    
    def _vectorized_filter(self, strategy: Strategy, data: Dict) -> bool:
        """
        向量化预筛选
        
        快速过滤明显不符合市场结构的策略
        返回True表示策略无效
        """
        # 检查策略是否与当前市场状态兼容
        for symbol, tf_data in data.items():
            for tf, df in tf_data.items():
                if not strategy.compatible_with_data(df):
                    return True
        return False
```

**Walk-Forward分割器**:
```python
def _walk_forward_split(
    self,
    data: Dict,
    config: BacktestConfig
) -> Generator[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame], None, None]:
    """
    Walk-Forward滚动分割
    
    配置: train_pct=0.6, val_pct=0.2, test_pct=0.2
    
    时间线:
    |----Train----|----Val----|--Test--|----Train----|----Val----|--Test--|
    ```
    """
    start, end = config.date_range
    total_days = (end - start).days
    train_days = int(total_days * config.train_pct)
    val_days = int(total_days * config.val_pct)
    test_days = total_days - train_days - val_days
    
    step = test_days  # 滚动步长
    
    current = start
    while current + timedelta(days=train_days + val_days + test_days) <= end:
        train_end = current + timedelta(days=train_days)
        val_end = train_end + timedelta(days=val_days)
        test_end = val_end + timedelta(days=test_days)
        
        yield (
            self._slice_data(data, current, train_end),
            self._slice_data(data, train_end, val_end),
            self._slice_data(data, val_end, test_end)
        )
        
        current += timedelta(days=step)
```

### 3.3 多Agent协作系统

```python
# mini_max/agents/orchestrator.py

class AgentOrchestrator:
    """
    多Agent编排器
    
    协调Research/Execution/Risk三个Agent群体
    实现智能决策流程
    """
    
    def __init__(self):
        self.research_agents = AgentPool(ResearchAgent)
        self.execution_agent = ExecutionAgent()
        self.risk_agent = RiskAgent()
        
        # 消息队列
        self.message_bus = MessageBus()
        
        # 协作规则
        self.collaboration_rules = CollaborationRules()
        
    async def process_signal(self, market_signal: MarketSignal) -> ProcessResult:
        """
        处理市场信号
        
        时序:
        1. Research Agent 分析 → 策略建议
        2. Risk Agent 审核 → 风险评估
        3. Execution Agent 执行 → 订单结果
        4. Research Agent 复盘 → 学习反馈
        """
        # 1. 研究分析
        research_task = self.research_agents.analyze(market_signal)
        research_result = await research_task
        
        if not research_result.has_actionable_signal:
            return ProcessResult(status="no_action", result=research_result)
        
        # 2. 风险审核
        risk_task = self.risk_agent.check(research_result)
        risk_result = await risk_task
        
        if not risk_result.approved:
            return ProcessResult(
                status="risk_rejected",
                result=research_result,
                risk_reason=risk_result.reason
            )
        
        # 3. 执行订单
        execution_task = self.execution_agent.execute(
            research_result.strategy,
            risk_result.limits
        )
        execution_result = await execution_task
        
        # 4. 学习反馈
        await self.research_agents.feedback(
            original_signal=market_signal,
            execution_result=execution_result
        )
        
        return ProcessResult(
            status="success",
            result=execution_result
        )


class ResearchAgentPool:
    """研究Agent池"""
    
    def __init__(self):
        self.agents = {
            "h1_squeeze": H1SqueezeAgent(),
            "m15_squeeze": M15SqueezeAgent(),
            "d1_state": D1StateAgent(),
            "state_mining": StateMiningAgent(),
            "reification": ReificationAgent(),
        }
    
    async def analyze(self, signal: MarketSignal) -> ResearchResult:
        """多Agent并行分析"""
        tasks = [
            agent.analyze(signal)
            for agent in self.agents.values()
        ]
        results = await asyncio.gather(*tasks)
        
        # 多Agent投票
        return self._aggregate_results(results)
    
    def _aggregate_results(self, results: List[ResearchResult]) -> ResearchResult:
        """
        多Agent结果聚合
        
        策略:
        - 胜率加权: 高置信度Agent权重更大
        - 共识优先: 多数Agent信号优先
        - 异议保留: 记录少数派观点
        """
        # 计算加权信号强度
        weighted_signal = sum(
            r.signal_strength * r.confidence
            for r in results
        ) / sum(r.confidence for r in results)
        
        # 共识检测
        consensus = self._check_consensus(results)
        
        return ResearchResult(
            signal_strength=weighted_signal,
            consensus=consensus,
            details=results,
            minority_opinion=self._get_dissent(results)
        )
```

### 3.4 实时市场分析模块

```python
# mini_max/market/observer.py

class MarketObserver:
    """
    实时市场观察站
    
    功能:
    - 多周期共振分析
    - 收缩突破追踪
    - 复现检测提醒
    """
    
    def __init__(
        self,
        data_bridge: MT5DataBridge,
        state_engine: StateHexEngine,
        notifier: Notifier
    ):
        self.data = data_bridge
        self.state = state_engine
        self.notifier = notifier
        
        # 观察配置
        self.watchlist = {}  # symbol -> WatchConfig
        
        # 扫描器
        self.scanners = [
            StateHexScanner(),      # State Hex组合分析
            SqueezeBreakoutScanner(), # 收缩突破检测
            ResonanceScanner(),       # 多周期共振检测
            ReificationScanner(),     # 复现检测
        ]
        
    async def scan_all(self) -> List[MarketAlert]:
        """全市场扫描"""
        alerts = []
        
        for symbol, config in self.watchlist.items():
            # 1. 获取最新数据
            data = await self._get_latest_data(symbol, config.timeframes)
            
            # 2. 计算State Hex
            states = self.state.encode(data)
            
            # 3. 多扫描器检测
            for scanner in self.scanners:
                scanner_alerts = await scanner.scan(states, config)
                alerts.extend(scanner_alerts)
            
            # 4. 共振分析
            resonance = self._analyze_resonance(states)
            if resonance.strength > 0.7:
                alerts.append(MarketAlert(
                    type="resonance",
                    symbol=symbol,
                    strength=resonance.strength,
                    details=resonance
                ))
        
        # 5. 去重 + 优先级排序
        alerts = self._deduplicate(alerts)
        alerts = self._prioritize(alerts)
        
        return alerts
    
    async def track_squeeze_process(self, symbol: str) -> SqueezeProcess:
        """
        追踪收缩突破过程
        
        返回收缩过程的完整时序记录
        """
        # 获取最近24小时的M15数据
        data = await self.data.get_ohlcv(symbol, "M15", hours=24)
        
        # 计算收缩指标
        squeeze_indicator = self._compute_squeeze_indicator(data)
        
        # 分割收缩阶段
        stages = self._segment_squeeze_stages(squeeze_indicator)
        
        return SqueezeProcess(
            symbol=symbol,
            current_stage=stages[-1],
            history=stages,
            breakout_probability=self._calc_breakout_prob(stages)
        )
```

**收缩过程追踪**:
```python
def _segment_squeeze_stages(
    self,
    squeeze_indicator: pd.Series
) -> List[SqueezeStage]:
    """
    分割收缩阶段
    
    阶段定义:
    - normal: BB宽度 > 80th percentile
    - building: BB宽度下降中
    - squeeze: BB宽度 < 20th percentile
    - breakout: 价格突破BB上下轨
    """
    stages = []
    
    # 计算阈值
    upper = squeeze_indicator.quantile(0.8)
    lower = squeeze_indicator.quantile(0.2)
    
    current_stage = "normal"
    streak_count = 0
    
    for i, value in enumerate(squeeze_indicator):
        if value > upper:
            new_stage = "normal"
        elif value < lower:
            new_stage = "squeeze"
        else:
            # 收缩进行中
            if current_stage == "squeeze":
                new_stage = "squeeze"
            elif value < squeeze_indicator.iloc[i-1]:
                new_stage = "building"
            else:
                new_stage = "normal"
        
        if new_stage == current_stage:
            streak_count += 1
        else:
            streak_count = 1
            current_stage = new_stage
        
        stages.append(SqueezeStage(
            timestamp=squeeze_indicator.index[i],
            stage=current_stage,
            indicator_value=value,
            streak_bars=streak_count
        ))
    
    return stages
```

---

## 4. ZeroMQ通信接口

### 4.1 MT5 Bridge接口

基于现有 `python/core/mt5_bridge.py` 扩展：

```python
# mini_max/bridge/mt5_extended.py

class MT5ExtendedBridge(MT5Bridge):
    """
    扩展MT5桥接器
    
    在现有MT5Bridge基础上增加:
    - 历史数据请求
    - 点差数据获取
    - 订单簿数据
    """
    
    # 新增端口
    HIST_PORT = 5567    # 历史数据请求
    SPREAD_PORT = 5568  # 实时点差
    
    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """获取历史K线数据"""
        request = {
            "type": "historical_data",
            "symbol": symbol,
            "timeframe": timeframe,
            "start": start.isoformat(),
            "end": end.isoformat()
        }
        
        response = await self._send_request(self.HIST_PORT, request)
        return self._parse_ohlcv_response(response)
    
    async def get_spread(self, symbol: str) -> SpreadData:
        """获取实时点差"""
        request = {"type": "spread", "symbol": symbol}
        response = await self._send_request(self.SPREAD_PORT, request)
        return SpreadData(**response)
```

### 4.2 消息协议

```python
# 消息类型定义
class MessageType(Enum):
    # 行情消息
    TICK = "tick"
    OHLCV = "ohlcv"
    SPREAD = "spread"
    
    # 交易消息
    ORDER_REQUEST = "order_request"
    ORDER_RESULT = "order_result"
    POSITION_UPDATE = "position_update"
    
    # 状态消息
    HEARTBEAT = "heartbeat"
    CONNECTION_STATUS = "connection_status"
    
    # Agent消息
    AGENT_SIGNAL = "agent_signal"
    AGENT_RESULT = "agent_result"
    RISK_APPROVAL = "risk_approval"


@dataclass
class Message:
    """统一消息格式"""
    type: MessageType
    timestamp: datetime
    source: str
    target: str
    payload: Dict
    correlation_id: str = None
    
    def to_bytes(self) -> bytes:
        return json.dumps({
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "target": self.target,
            "payload": self.payload,
            "correlation_id": self.correlation_id
        }).encode("utf-8")
```

---

## 5. 部署架构

### 5.1 本地部署 (推荐个人交易者)

```yaml
# docker-compose.yml
version: '3.8'

services:
  minmax-api:
    build: .
    ports:
      - "8000:8000"      # FastAPI
      - "8501:8501"      # Streamlit Web UI
    volumes:
      - ./data:/app/data
      - ./strategies:/app/strategies
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MT5_PATH=${MT5_PATH}
    depends_on:
      - duckdb

  duckdb:
    image: duckdb/duckdb:latest
    volumes:
      - ./data/duckdb:/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### 5.2 云端部署 (机构用户)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            AWS / 云端部署                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐               │
│  │   ALB       │────▶│   ECS       │────▶│   RDS       │               │
│  │ (负载均衡)  │     │ (API服务)   │     │ (PostgreSQL)│               │
│  └─────────────┘     └─────────────┘     └─────────────┘               │
│         │                   │                                          │
│         │                   ▼                                          │
│         │            ┌─────────────┐                                    │
│         │            │   EFS       │                                    │
│         │            │ (共享存储)  │                                    │
│         │            └─────────────┘                                    │
│         │                   │                                          │
│         ▼                   ▼                                          │
│  ┌─────────────┐     ┌─────────────┐                                    │
│  │ CloudFront  │     │  EC2        │                                    │
│  │ (CDN)       │     │ (MT5 Bridge)│                                    │
│  └─────────────┘     └─────────────┘                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. 性能优化

### 6.1 回测性能优化

| 优化策略 | 实现 | 预期提升 |
|----------|------|----------|
| 向量化预筛选 | NumPy批量计算 | 50% |
| 数据预加载 | DuckDB缓存 | 30% |
| 多进程并行 | ProcessPoolExecutor | 40% |
| JIT编译 | Numba热路径 | 60% |
| 增量计算 | 差分更新 | 70% |

### 6.2 实时性能优化

```python
# 数据缓存策略
class DataCache:
    """多级缓存"""
    
    def __init__(self):
        # L1: 内存缓存 (最近1小时)
        self.l1 = LRUCache(maxsize=1000)
        
        # L2: DuckDB (最近1个月)
        self.l2 = DuckDBCache()
        
        # L3: MT5原始数据 (全部)
        self.l3 = MT5Bridge()
    
    async def get(self, key: DataKey) -> pd.DataFrame:
        # 1. L1命中
        if data := self.l1.get(key):
            return data
        
        # 2. L2命中
        if data := await self.l2.get(key):
            self.l1.set(key, data)
            return data
        
        # 3. L3获取
        data = await self.l3.get(key)
        await self.l2.set(key, data)
        self.l1.set(key, data)
        return data
```

---

## 7. 关键技术决策

### 7.1 架构决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 回测引擎 | 自研+VectorBT借鉴 | 需要State Hex专属指标 |
| 多周期对齐 | merge_asof | 需验证无未来函数 |
| 成本模型 | MT5实时点差 | 非固定成本更准确 |
| Agent框架 | 自研 | 需要与回测平台深度整合 |
| 数据存储 | DuckDB | 嵌入式高性能，已有基础 |

### 7.2 未来扩展方向

| 阶段 | 扩展内容 | 优先级 |
|------|----------|--------|
| Phase 2 | 多券商支持 (IBKR, Interactive) | 中 |
| Phase 2 | GPU加速回测 | 中 |
| Phase 3 | 分布式回测集群 | 低 |
| Phase 3 | 机器学习预测 | 低 |
| Phase 4 | 社区策略市场 | 低 |

---

## 8. 参考与借鉴

### 8.1 开源项目

| 项目 | 借鉴内容 | 整合方式 |
|------|----------|----------|
| Microsoft Qlib | 数据处理管道 | 参考设计 |
| FinRL-X | 模块化策略管道 | 参考实现 |
| VectorBT | 向量化回测理念 | 技术借鉴 |
| NautilusTrader | 事件驱动架构 | 架构参考 |

### 8.2 现有代码复用清单

| 文件 | 复用模块 | 整合方式 |
|------|----------|----------|
| `python/core/mt5_bridge.py` | ZeroMQ通信 | 直接集成 |
| `python/backtest_platform/` | 五层架构 | 继承扩展 |
| `python/ai_engine/state_hex_engine.py` | 状态编码 | 核心引擎 |
| `observation_db.py` | 复现检测 | 直接使用 |
| `process_real_mt4_data.py` | 数据处理 | 流程复用 |
| `csv_color_marker.py` | 可视化 | 样式复用 |

---

## 9. 附录

### 9.1 文件结构

```
MiniMax/
├── docs/                          # 文档
│   ├── minmax_platform_PRD_v1.0.md
│   ├── minmax_platform_TECH_v1.0.md
│   ├── minmax_platform_API_v1.0.md
│   ├── minmax_platform_DB_v1.0.md
│   ├── minmax_platform_SECURITY_v1.0.md
│   └── minmax_platform_ROADMAP_v1.0.md
│
├── mini_max/                      # 主代码
│   ├── __init__.py
│   ├── main.py                    # FastAPI入口
│   │
│   ├── api/                       # API层
│   │   ├── routes/
│   │   │   ├── strategy.py
│   │   │   ├── backtest.py
│   │   │   ├── market.py
│   │   │   └── deployment.py
│   │   └── dependencies.py
│   │
│   ├── agents/                    # Agent层
│   │   ├── orchestrator.py
│   │   ├── research/
│   │   │   ├── base.py
│   │   │   ├── h1_squeeze.py
│   │   │   ├── m15_squeeze.py
│   │   │   ├── d1_state.py
│   │   │   └── reification.py
│   │   ├── execution/
│   │   │   └── agent.py
│   │   └── risk/
│   │       └── agent.py
│   │
│   ├── backtest/                 # 回测引擎 (继承现有)
│   │   ├── engine.py
│   │   ├── data_layer.py
│   │   ├── compute_layer.py
│   │   ├── strategy_layer.py
│   │   ├── execution_layer.py
│   │   └── presentation_layer.py
│   │
│   ├── strategy/                 # 策略生成
│   │   ├── generator.py
│   │   ├── templates/
│   │   │   ├── ma_crossover.py
│   │   │   ├── squeeze_breakout.py
│   │   │   └── state_hex.py
│   │   └── llm_client.py
│   │
│   ├── market/                  # 市场观察
│   │   ├── observer.py
│   │   ├── scanners/
│   │   │   ├── state_hex.py
│   │   │   ├── squeeze.py
│   │   │   └── resonance.py
│   │   └── notifiers/
│   │       ├── telegram.py
│   │       └── email.py
│   │
│   ├── bridge/                  # 桥接层
│   │   ├── mt5_extended.py
│   │   └── zeromq_protocol.py
│   │
│   └── storage/                  # 存储层
│       ├── duckdb_manager.py
│       └── observation_db.py
│
├── tests/                        # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── data/                         # 数据目录
│   ├── duckdb/
│   ├── cache/
│   └── strategies/
│
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

### 9.2 依赖清单

```txt
# Core
python>=3.12
numpy>=1.26
pandas>=2.1
duckdb>=0.9

# AI/LLM
openai>=1.0
anthropic>=0.7

# Web
fastapi>=0.109
uvicorn>=0.27
pydantic>=2.5
streamlit>=1.30

# MT5/Communication
MetaTrader5>=5.0
zeromq>=4.3

# 回测优化
numba>=0.59
ta-lib>=0.4

# 任务调度
apscheduler>=3.10

# 通知
telegram-send>=0.25

# 测试
pytest>=7.4
pytest-asyncio>=0.23
```