# MiniMax AI量化平台 — 分阶段实施路线图

> 版本: v1.0 (minmax标识)  
> 日期: 2026-06-06  
> 状态: 正式版

---

## 1. 实施原则

### 1.1 优先级决策

```
一票否决项（必须优先完成）:
├── 1. merge_asof无未来函数验证
├── 2. MT5实际点差接入
├── 3. v5单元测试覆盖
└── 4. 4周模拟盘观察

核心价值项（直接影响用户体验）:
├── 1. 自然语言策略生成
├── 2. 30秒回测响应
└── 3. 多Agent协作系统

增强项（提升平台竞争力）:
├── 1. Web UI界面
├── 2. 实时行情推送
└── 3. 策略市场
```

### 1.2 资源约束

| 资源 | 可用量 | 备注 |
|------|--------|------|
| 开发时间 | 8小时/天 | 兼职开发 |
| 服务器成本 | < $100/月 | 初期 |
| 技术栈 | Python+现有基础设施 | 最大化复用 |

---

## 2. 阶段规划总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MiniMax 实施路线图                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1      Phase 2      Phase 3      Phase 4      Phase 5      Phase 6  │
│  内核强化      AI生成       观察站       部署通道     多Agent      社区化   │
│  (4-6周)      (6-8周)      (4-6周)      (4-6周)      (4-6周)      (未来)   │
│                                                                             │
│  ┌─────┐      ┌─────┐      ┌─────┐      ┌─────┐      ┌─────┐              │
│  │验证 │      │策略 │      │实时 │      │模拟 │      │协作 │              │
│  │merge│      │生成 │      │分析 │      │盘   │      │系统 │              │
│  │asof │      │引擎 │      │面板 │      │部署 │      │优化 │              │
│  └─────┘      └─────┘      └─────┘      └─────┘      └─────┘              │
│                                                                             │
│  ════════════════════════════════════════════════════════════════════     │
│  验证质量     验证效果     验证效率     验证闭环     验证规模              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Phase 1: 内核强化 (4-6周)

### 3.1 目标

夯实回测平台基础，消除技术债，为后续功能提供稳定底座。

### 3.2 任务分解

| 任务 | 工作量 | 优先级 | 验收标准 |
|------|--------|--------|----------|
| **T1.1 验证merge_asof无未来函数** | 1周 | P0 | 回测结果与MT5一致 |
| T1.2 MT5实际点差接入 | 1周 | P0 | 点差数据正确获取 |
| T1.3 v5单元测试覆盖>80% | 2周 | P0 | 测试通过率>80% |
| T1.4 4周模拟盘观察 | 2周 | P1 | 记录偏差<20% |

### 3.3 详细任务

#### T1.1 merge_asof未来函数验证

**问题描述**:
多周期数据对齐使用`merge_asof`时，可能存在使用未来信息的问题。

**验证方法**:
```python
# 伪代码 - 验证逻辑
def verify_no_lookahead():
    """
    验证方法:
    1. 取T时刻的H1数据
    2. 检查D1数据是否只用T及之前的数据
    3. 逐K线验证
    """
    for h1_bar in h1_data:
        d1_bar = get_d1_for_time(h1_bar.timestamp)
        # 验证: d1_bar.timestamp <= h1_bar.timestamp
        assert d1_bar.timestamp <= h1_bar.timestamp
    
    return True
```

**验收标准**:
- 任意H1 K线时刻，使用的D1/H4数据不包含未来信息
- 与MT5 Strategy Tester结果对比偏差<0.1%

#### T1.2 MT5实际点差接入

**任务**:
将回测中的固定交易成本改为MT5实时点差。

**实现方案**:
```python
class MT5SpreadModel:
    """MT5点差模型"""
    
    def __init__(self, bridge: MT5Bridge):
        self.bridge = bridge
        self.spread_cache = {}
    
    async def get_spread(self, symbol: str, timestamp: datetime) -> float:
        """
        获取历史点差
        优先级: 缓存 > DuckDB历史 > 默认值
        """
        # 1. 检查缓存
        if symbol in self.spread_cache:
            return self.spread_cache[symbol]
        
        # 2. 从DuckDB获取历史点差
        spread = await self._get_historical_spread(symbol, timestamp)
        if spread:
            return spread
        
        # 3. 返回默认值
        return self._get_default_spread(symbol)
    
    def calculate_cost(self, order: Order) -> float:
        """计算交易成本 = 点差 + 手续费"""
        spread = self.get_spread(order.symbol, order.timestamp)
        commission = self._get_commission(order.symbol)
        return spread + commission
```

**验收标准**:
- 历史K线使用历史平均点差
- 实时订单使用实时点差
- 成本计算与MT5报告一致

#### T1.3 v5单元测试

**测试覆盖目标**:
| 模块 | 当前覆盖 | 目标覆盖 | 测试数 |
|------|----------|----------|--------|
| data_layer | 30% | 80% | 50 |
| compute_layer | 25% | 80% | 80 |
| strategy_layer | 40% | 80% | 60 |
| execution_layer | 35% | 80% | 70 |
| StateHexEngine | 50% | 90% | 100 |

**测试用例示例**:
```python
# tests/test_compute_layer.py

class TestStateHexEncoding:
    """State Hex编码测试"""
    
    def test_squeeze_detection(self):
        """收缩检测"""
        data = generate_test_data(contraction_pattern=True)
        result = state_engine.detect_squeeze(data)
        assert result.is_squeeze == True
        assert result.contraction_pct > 0.8
    
    def test_resistance_levels(self):
        """支撑阻力位"""
        data = generate_test_data(range_boundaries=True)
        sr = state_engine.calculate_sr_levels(data)
        assert sr.resistance is not None
        assert sr.resistance > sr.support
    
    def test_multi_timeframe_alignment(self):
        """多周期对齐"""
        # 验证H1时刻D1数据不包含未来信息
        pass
```

#### T1.4 4周模拟盘观察

**观察指标**:
| 指标 | 回测预期 | 模拟盘目标 |
|------|----------|------------|
| 总收益率 | +15% | >+10% |
| 最大回撤 | <10% | <12% |
| 胜率 | 60% | >55% |
| 回测偏差 | - | <20% |

### 3.4 里程碑

```
Week 1:    [T1.1完成] ──────────────── merge_asof验证通过
Week 2:    [T1.2完成] ──────────────── MT5点差接入完成
Week 3-4:  [T1.3进行中] ───────────── 单元测试编写
Week 5-6:  [T1.3+T1.4] ───────────── 测试通过 + 模拟盘启动
```

---

## 4. Phase 2: AI策略生成 (6-8周)

### 4.1 目标

实现自然语言策略生成，降低量化交易门槛。

### 4.2 任务分解

| 任务 | 工作量 | 优先级 | 验收标准 |
|------|--------|--------|----------|
| **T2.1 LLM策略解析** | 2周 | P0 | 要素提取准确率>90% |
| T2.2 策略模板库 | 2周 | P0 | 至少5个模板 |
| T2.3 代码生成 | 1周 | P0 | 生成代码可执行 |
| T2.4 回测验证 | 1周 | P1 | 自动回测反馈 |

### 4.3 详细设计

#### T2.1 LLM策略解析

**Prompt工程**:
```python
STRATEGY_PARSER_PROMPT = """
你是一个专业的量化交易策略分析师。

用户输入: {user_input}

请提取以下信息并以JSON格式输出:
{{
    "symbol": "交易品种，如XAUUSD",
    "timeframe": "周期，如H1",
    "direction": "long/short/both",
    "entry_conditions": ["入场条件列表"],
    "exit_conditions": ["出场条件列表"],
    "hold_bars": 持仓周期,
    "stop_loss": "止损方式",
    "take_profit": "止盈方式",
    "filters": ["过滤条件"],
    "confidence": 置信度0-1
}}

规则:
- 品种必须是MT5支持的品种
- 周期必须是标准周期(M1/M5/M15/H1/H4/D1/W1/MN1)
- 如果信息不完整，给出最合理的推测
"""

class StrategyParser:
    async def parse(self, text: str) -> StrategyElements:
        response = await self.llm.generate(
            prompt=STRATEGY_PARSER_PROMPT.format(user_input=text),
            schema=StrategyElements
        )
        return StrategyElements.parse_raw(response)
```

#### T2.2 策略模板库

**模板列表**:

| 模板ID | 名称 | 参数 | 适用场景 |
|--------|------|------|----------|
| MA_CROSSOVER | 均线交叉 | fast, slow, exit | 趋势行情 |
| SQUEEZE_BREAKOUT | 收缩突破 | timeframe, direction | 震荡突破 |
| STATE_HEX_DIR | State方向 | state_pattern | 多周期共振 |
| PIVOT_REVERSAL | 枢轴反转 | pivot_type | 区间交易 |
| BOLLINGER_BOUNCE | 布林反弹 | period, std_dev | 均值回归 |
| ATR_TRAILING | ATR追踪 | atr_period, multiplier | 趋势跟踪 |

**模板结构**:
```python
class StrategyTemplate(ABC):
    @abstractmethod
    def get_params(self) -> List[TemplateParam]:
        """定义模板参数"""
        pass
    
    @abstractmethod
    def generate_code(self, params: Dict) -> str:
        """生成策略代码"""
        pass
    
    @abstractmethod
    def validate_params(self, params: Dict) -> bool:
        """验证参数"""
        pass
```

### 4.4 里程碑

```
Week 1-2:   [T2.1完成] ───────────── LLM解析上线
Week 3-4:   [T2.2完成] ───────────── 5个模板可用
Week 5:     [T2.3完成] ───────────── 代码生成可用
Week 6-8:   [T2.4+优化] ──────────── 自动回测反馈
```

---

## 5. Phase 3: 市场观察站 (4-6周)

### 5.1 目标

实现实时市场监控和复现检测提醒。

### 5.2 任务分解

| 任务 | 工作量 | 优先级 | 验收标准 |
|------|--------|--------|----------|
| T3.1 Web状态面板 | 2周 | P0 | 多周期状态展示 |
| T3.2 复现检测 | 1周 | P0 | 70%/80%阈值触发 |
| T3.3 通知推送 | 1周 | P1 | Telegram+邮件 |
| T3.4 历史对比 | 1周 | P2 | 相似形态识别 |

### 5.3 详细设计

#### T3.1 Web状态面板

**界面设计**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│  MiniMax 市场观察站                                    [设置] [刷新]    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  XAUUSD H1  ─────────────────────────────────────────────────────────  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ MN1 │ W1  │ D1  │ H4  │ H1  │ M15 │  ← 周期选择                  │   │
│  │  8  │  6  │  0  │  8  │  4  │  C  │    State: 4 (趋势向上)      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  收缩度: ████████████████████░░░░ 78%                                  │
│  D1/H4组合: 0_8 (收缩底座 + 非收缩)                                      │
│                                                                         │
│  [收缩突破过程]                                                         │
│  06-05 22:00 ████████░░░░░░░░░░░░░░░░░░░░ 收缩开始                     │
│  06-06 02:00 ████████████████████░░░░░░░░░ 收缩持续                    │
│  06-06 06:00 ████████████████████████████░ 高度收缩                   │
│  06-06 10:00 ?????????????????????????????? 等待确认                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**技术实现**:
```python
# mini_max/market/web_panel.py

class MarketWebPanel:
    """市场状态Web面板"""
    
    def __init__(self):
        self.stocks = {
            "/": streamlit,
            # ...
        }
    
    def render(self):
        st.title("MiniMax 市场观察站")
        
        # 品种选择
        symbol = st.selectbox("选择品种", SUPPORTED_SYMBOLS)
        
        # 多周期状态
        states = self.observer.get_multi_tf_state(symbol)
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        periods = ["MN1", "W1", "D1", "H4", "H1", "M15"]
        for col, period in zip([col1, col2, col3, col4, col5, col6], periods):
            with col:
                state = states[period]
                st.metric(period, state.state_hex, f"{state.contraction_pct:.0f}%")
        
        # 收缩过程图
        squeeze_history = self.observer.get_squeeze_history(symbol)
        st.line_chart(squeeze_history)
```

### 5.4 里程碑

```
Week 1-2:   [T3.1完成] ───────────── Web面板上线
Week 3:     [T3.2完成] ───────────── 复现检测可用
Week 4:     [T3.3完成] ───────────── 通知推送就绪
Week 5-6:   [T3.4+优化] ──────────── 历史对比功能
```

---

## 6. Phase 4: 部署通道 (4-6周)

### 6.1 目标

实现回测→模拟盘→实盘的完整部署流程。

### 6.2 任务分解

| 任务 | 工作量 | 优先级 | 验收标准 |
|------|--------|--------|----------|
| T4.1 MT5模拟盘对接 | 2周 | P0 | 订单成功执行 |
| T4.2 风控审核层 | 1周 | P0 | 拦截违规订单 |
| T4.3 绩效追踪 | 1周 | P1 | 偏差检测 |
| T4.4 二次确认 | 1周 | P2 | 实盘安全 |

### 6.3 详细设计

#### T4.1 MT5模拟盘对接

**基于现有MT5Bridge扩展**:
```python
# mini_max/deployment/mt5_deployment.py

class MT5DeploymentManager:
    """MT5部署管理器"""
    
    def __init__(self, bridge: MT5Bridge):
        self.bridge = bridge
        self.risk_engine = RiskEngine()
    
    async def deploy_to_simulation(self, strategy: Strategy, config: DeploymentConfig):
        """部署到MT5模拟账户"""
        # 1. 风控审核
        risk_result = await self.risk_engine.check(strategy, config)
        if not risk_result.approved:
            raise RiskCheckFailed(risk_result.violations)
        
        # 2. 订阅行情
        await self.bridge.subscribe(config.symbol)
        
        # 3. 创建EA实例（通过ZeroMQ）
        ea_config = self._create_ea_config(strategy, config)
        await self.bridge.create_ea(ea_config)
        
        # 4. 返回部署信息
        return DeploymentInfo(
            deployment_id=uuid4(),
            mt5_ticket=ea_config.ticket,
            status="active"
        )
    
    async def sync_performance(self, deployment_id: str) -> PerformanceReport:
        """同步实盘绩效"""
        positions = await self.bridge.get_positions()
        trades = await self.bridge.get_closed_trades()
        
        # 计算当前绩效
        current_pnl = sum(p.unrealized_pnl for p in positions)
        realized_pnl = sum(t.pnl for t in trades)
        
        # 与回测对比
        backtest_result = await self._get_backtest_result(deployment_id)
        deviation = self._calculate_deviation(
            current_pnl + realized_pnl,
            backtest_result.total_return
        )
        
        # 偏差检测
        if deviation > 0.2:
            await self.notifier.send_deviation_alert(deployment_id, deviation)
        
        return PerformanceReport(
            deployment_id=deployment_id,
            current_pnl=current_pnl,
            realized_pnl=realized_pnl,
            backtest_deviation=deviation
        )
```

### 6.4 里程碑

```
Week 1-2:   [T4.1完成] ───────────── 模拟盘部署可用
Week 3:     [T4.2完成] ───────────── 风控审核上线
Week 4:     [T4.3完成] ───────────── 绩效追踪就绪
Week 5-6:   [T4.4+优化] ──────────── 二次确认机制
```

---

## 7. Phase 5: 多Agent协作 (4-6周)

### 7.1 目标

完善多Agent系统，实现智能协作决策。

### 7.2 任务分解

| 任务 | 工作量 | 优先级 | 验收标准 |
|------|--------|--------|----------|
| T5.1 Agent编排器 | 2周 | P0 | 任务调度正常 |
| T5.2 辩论机制 | 2周 | P1 | 共识/异议记录 |
| T5.3 学习反馈 | 1周 | P1 | 策略改进 |
| T5.4 监控面板 | 1周 | P2 | Agent状态 |

### 7.3 详细设计

#### T5.1 Agent编排器

```python
# mini_max/agents/orchestrator.py

class AgentOrchestrator:
    """Agent编排器"""
    
    def __init__(self):
        self.research_pool = ResearchAgentPool()
        self.execution_agent = ExecutionAgent()
        self.risk_agent = RiskAgent()
        self.message_bus = MessageBus()
    
    async def process_market_signal(self, signal: MarketSignal) -> ProcessResult:
        """处理市场信号"""
        # 1. 研究Agent分析
        research_results = await self.research_pool.analyze_parallel(signal)
        
        # 2. 汇总研究结论
        consensus = self._aggregate_research(research_results)
        
        if not consensus.actionable:
            return ProcessResult(status="no_action", reason=consensus.reason)
        
        # 3. 风控审核
        risk_result = await self.risk_agent.check(
            strategy=consensus.strategy,
            context=consensus.context
        )
        
        if not risk_result.approved:
            return ProcessResult(
                status="risk_rejected",
                reason=risk_result.reason,
                violations=risk_result.violations
            )
        
        # 4. 执行
        execution_result = await self.execution_agent.execute(
            strategy=consensus.strategy,
            limits=risk_result.limits
        )
        
        # 5. 学习反馈
        await self.research_pool.feedback(signal, execution_result)
        
        return ProcessResult(
            status="success",
            result=execution_result
        )
```

### 7.4 里程碑

```
Week 1-2:   [T5.1完成] ───────────── 编排器上线
Week 3-4:   [T5.2完成] ───────────── 辩论机制可用
Week 5:     [T5.3完成] ───────────── 学习反馈就绪
Week 6:     [T5.4+优化] ──────────── 监控面板
```

---

## 8. Phase 6: 社区化 (未来)

### 8.1 功能规划

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 策略市场 | 用户发布/订阅策略 | P1 |
| 策略评分 | 社区评价体系 | P2 |
| 策略复制 | 一键跟单 | P2 |
| 竞赛系统 | 模拟交易竞赛 | P3 |

### 8.2 商业模式

| 模式 | 说明 | 定价 |
|------|------|------|
| 免费版 | 基础功能 | $0 |
| 专业版 | 高级功能 | $29/月 |
| 机构版 | 多用户+API | $99/月 |
| 策略分成 | 策略作者收益 | 20%分成 |

---

## 9. 风险与缓解

| 阶段 | 主要风险 | 影响 | 缓解措施 |
|------|----------|------|----------|
| Phase 1 | merge_asof有未来函数 | 高 | 一票否决，优先验证 |
| Phase 1 | 回测与实盘偏差大 | 高 | 4周模拟盘观察 |
| Phase 2 | LLM生成质量不稳定 | 中 | 模板约束+回测验证 |
| Phase 3 | 复现检测误报 | 中 | 多维度验证 |
| Phase 4 | MT5连接不稳定 | 中 | 自动重连机制 |
| Phase 5 | Agent协作死锁 | 低 | 超时+降级机制 |

---

## 10. 验收标准汇总

| 阶段 | 验收标准 | 验证方法 |
|------|----------|----------|
| Phase 1 | merge_asof无未来函数 | 逐K线验证 |
| Phase 1 | 单元测试>80% | 测试覆盖率报告 |
| Phase 1 | 模拟盘偏差<20% | 4周数据对比 |
| Phase 2 | 策略生成准确率>90% | 100个测试用例 |
| Phase 2 | 回测响应<30秒 | 计时测试 |
| Phase 3 | 告警准确率>80% | 历史告警统计 |
| Phase 4 | 订单执行成功率>99% | MT5日志统计 |
| Phase 5 | Agent协作成功率>99% | 任务完成率 |

---

## 11. 附录

### 11.1 依赖关系

```
Phase 1 (必须先完成)
    │
    ├─→ Phase 2 (需要稳定回测引擎)
    │       │
    │       └─→ Phase 3 (需要回测验证)
    │
    ├─→ Phase 4 (需要风控基础)
    │
    └─→ Phase 5 (需要所有基础)
```

### 11.2 资源估算

| 阶段 | 开发时间 | 服务器成本 | 外部服务 |
|------|----------|------------|----------|
| Phase 1 | 40小时 | $20/月 | - |
| Phase 2 | 60小时 | $30/月 | OpenAI API |
| Phase 3 | 30小时 | $30/月 | - |
| Phase 4 | 40小时 | $30/月 | MT5 |
| Phase 5 | 40小时 | $40/月 | - |
| **总计** | **210小时** | **$150/月** | - |

### 11.3 文档清单

| 文档 | 路径 |
|------|------|
| 产品需求文档 | `docs/minmax_platform_PRD_v1.0.md` |
| 技术架构文档 | `docs/minmax_platform_TECH_v1.0.md` |
| API接口规范 | `docs/minmax_platform_API_v1.0.md` |
| 数据库设计 | `docs/minmax_platform_DB_v1.0.md` |
| 安全风控机制 | `docs/minmax_platform_SECURITY_v1.0.md` |
| 实施路线图 | `docs/minmax_platform_ROADMAP_v1.0.md` |