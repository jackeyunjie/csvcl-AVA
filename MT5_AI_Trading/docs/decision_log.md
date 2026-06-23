# MT5 AI 量化交易系统 - 决策日志

## 2026-05-18: Phase 2 开发方向确定

### 决策
**Phase 2 核心方向：多品种策略管理与信号评分系统**

### 背景
Phase 1 基础设施已完成（ZeroMQ桥接、Python API桥接、主控制器、基础策略引擎、监控系统、安全机制）。
Phase 2 原计划为"核心引擎（策略+回测）"，但审查代码后发现：
- 策略引擎仅支持单品种（EURUSD）、单周期（H1）
- 信号生成采用简单指标投票制，缺乏质量评估
- 回测环境就绪但无策略绩效归因能力
- 多品种扩展是 Phase 3 AI 强化学习的前置条件

### 选择此方向的理由
1. **技术债务最小**：在单品种逻辑上继续堆叠AI，会导致后续重构成本激增
2. **复利效应**：多品种管理器一旦建成，所有后续策略可自动获得多品种能力
3. **风险分散**：实盘需要多品种分散风险，这是量化系统的基本能力
4. **数据基础**：AI训练需要多品种、多周期的特征数据

### 具体交付物
1. `MultiSymbolStrategyManager` - 多品种策略管理器
2. `SignalScorer` - 信号评分系统（历史胜率、盈亏比、夏普比率加权）
3. `PerformanceAttribution` - 绩效归因分析
4. 配置文件扩展：支持多品种、多周期、品种权重
5. 测试覆盖：多品种并发、信号评分准确性

### 排除的其他方向
- **直接启动 Phase 3 AI 强化学习**：数据管道和策略评估基础设施不足
- **先跑模拟盘验证**：系统能力边界已知，验证意义有限
- **Web 监控面板**：属于 Phase 5，当前优先级低于策略核心能力

## 2026-05-18: Phase 2 实现完成 + MT5实盘验证

### 完成内容
1. `multi_symbol_manager.py` - 添加`load_symbol_configs_from_dict`工厂方法、`signal_scorer`集成参数
2. `signal_scorer.py` - 添加`register_signal_from_trading_signal`、`batch_update_outcomes_from_positions`
3. `main_controller.py` - 支持多品种/单品种模式自动切换、`_process_multi_symbol_signals`流程
4. `trading_strategy.py` - 修复`_analyze_state`缺少`alignment_reason`参数的bug
5. `test_multi_symbol.py` - 23个单元测试（新增配置加载、Scorer集成、批量更新测试）
6. `test_multi_symbol_live.py` - 实盘数据流测试脚本

### 实盘验证结果
- **账户**: Ava-Real 1-MT5 #89467841 | 权益: $105.52
- **测试品种**: EURUSD, GBPUSD, USDJPY
- **数据流**: 3品种各58 ticks/30秒，接收率100%
- **信号生成**: USDJPY产生1个BUY信号（三元组8,8,5 | 评分0.725 | 信心度100%）
- **单元测试**: 23/23通过

### 发现的Bug与修复
- `trading_strategy.py:476` - `_analyze_state`函数签名缺少`alignment_reason`参数，导致实盘信号生成时NameError崩溃。已修复并验证。

### 下一步
- Phase 2正式交付，可进入Phase 3（AI强化学习）或继续模拟盘长期验证
