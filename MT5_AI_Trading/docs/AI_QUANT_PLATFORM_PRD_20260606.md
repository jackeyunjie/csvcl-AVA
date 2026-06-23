# AI量化策略平台需求文档 v0.1

> 日期: 2026-06-06
> 状态: 草案
> 目标: 建设一个面向研究、验证、观察和实施闭环的AI量化平台，而不是单纯的回测脚本集合。

## 1. 背景

当前项目已经积累了三类资产：

1. State Hex / H1 regime 研究资产。
2. 多周期共振收缩突破 v5 研究资产。
3. MT5/MT4 数据处理、邮件、观察数据库和模拟盘扫描脚本。

但当前工作流存在明显问题：

- Agent 能快速产出脚本和报告，但缺少统一的假设、数据、口径、审计和观察管理。
- 不同研究线统计口径不一致，例如 State 挖掘的 `H1=-F/short/5bars` 胜率 92.8% 需要重新核验成本、去重和事件口径。
- 回测到模拟观察之间缺少强制准入门槛。
- git 工作区混杂，MT5研究线和MT4邮件工具线没有清晰工程边界。

因此平台的第一目标不是“让AI自动下单”，而是让用户能够用AI完成：

```text
提出策略假设 -> 自动生成可复现研究计划 -> 拉取和审计数据 -> 生成策略代码 ->
执行无未来函数回测 -> 输出证据报告 -> 进入模拟观察 -> 对比回测和实时表现 ->
人工审批后实施
```

## 2. 产品定位

平台定位为 **AI辅助量化策略工厂**。

核心价值：

- 让非纯技术用户能用自然语言表达策略假设。
- 让AI把假设转成可测试的策略、因子、过滤条件和观察计划。
- 让所有策略结论带有数据版本、代码版本、成本模型、事件去重口径和审计记录。
- 让研究结果进入模拟观察，而不是直接跳到实盘。

明确不做：

- 不承诺自动赚钱。
- MVP阶段不做无人值守实盘自动交易。
- 不做没有审计痕迹的Agent自由改代码、自由下单。
- 不把未验证的ACD枢轴或单次高胜率报告作为交易依据。

## 3. 目标用户

### 3.1 策略研究员

需要快速验证想法、比较策略版本、管理研究假设和报告。

### 3.2 交易执行者

需要看到当前信号、历史证据、风控边界、观察记录和人工执行建议。

### 3.3 风控/复核者

需要检查是否有未来函数、成本是否真实、样本是否去重、回测和模拟盘是否一致。

### 3.4 平台开发者

需要可插拔接入数据源、回测引擎、券商/MT5接口、AI Agent和报告系统。

## 4. 产品原则

1. **先审计，再回测**  
   `merge_asof`、PIT数据、时间戳边界和高周期对齐是一票否决项。

2. **先真实成本，再谈胜率**  
   固定成本只能用于早期粗筛，平台正式结论必须使用MT5实际点差或可追溯成本快照。

3. **先统一口径，再比较路线**  
   State路线、v5收缩突破路线、M15路线必须用同一套事件去重、成本、Walk-forward、OOS/Test指标。

4. **先模拟观察，再实施**  
   回测通过只是准入条件，至少需要模拟盘观察和回测偏差解释。

5. **AI生成不等于AI批准**  
   Agent可以生成策略、代码和报告，但不能绕过审计门槛和人工审批。

## 5. MVP范围

### 5.1 策略假设中心

支持创建和管理策略假设：

- 假设名称、描述、市场、周期、方向、适用品种。
- 输入特征，例如 State Hex、squeeze_score、ADX、anchor_range_pct。
- 明确禁止项，例如未来函数、未去重事件、未扣成本胜率。
- 生命周期状态：`draft -> data_audit -> backtest -> review -> observation -> approved -> retired`。

### 5.2 数据与时间点审计

MVP必须实现：

- H1/H4/D1/M15 多周期数据统一存储。
- `merge_asof` 实时无未来函数验证。
- 高周期bar未收盘时不可被低周期bar使用。
- 每次回测保存数据版本、时间窗口、时区和缺失值处理记录。
- MT5实际点差快照导入和成本模型版本管理。

### 5.3 策略生成与策略模板

平台提供两种策略来源：

- 用户自然语言描述，由AI生成策略草稿。
- 现有策略模板参数化，例如 v5 squeeze、State regime gate、M15 Phase 1。

MVP策略必须包含：

- `strategy_manifest.yaml`
- 输入字段列表
- 时间点约束
- 事件生成规则
- 去重规则
- 出场规则
- 成本模型引用
- 风控参数

### 5.4 回测与验证

MVP支持：

- 快速向量化粗筛，用于参数扫描。
- 严格事件驱动复核，用于正式结论。
- Train/Validation/Test 时间切分。
- Walk-forward。
- event_id 去重。
- long/short 分方向统计。
- 毛收益、净收益、成本、胜率、盈亏比、回撤、样本数。
- 回测运行卡片 Run Card。

### 5.5 AI研究助手

Agent不直接替代回测引擎，只负责生成、解释和复核：

- Research Planner: 拆解研究任务。
- Data Auditor: 检查数据和时间点。
- Strategy Coder: 生成策略模板和代码。
- Backtest Runner: 调用受控工具执行回测。
- Risk Reviewer: 检查样本、成本、去重、过拟合。
- Report Writer: 输出结构化报告。

### 5.6 模拟盘观察

MVP接入当前 `observation_db.py` 思路，提供：

- 实时信号记录。
- 回测预期和实时表现对比。
- 每日/每周观察总结。
- 异常样本标记。
- 策略降级或暂停机制。

### 5.7 报告与知识沉淀

每次研究输出：

- 结论摘要。
- 数据窗口和样本规模。
- 关键指标。
- 审计结果。
- 失败原因。
- 下一步建议。
- 可引用的本地报告路径。

## 6. P0需求

1. 验证实时 `merge_asof` 无未来函数。
2. 把固定交易成本改成MT5实际点差或成本快照。
3. 统一 State 和 v5 的事件去重与收益统计口径。
4. 补齐 v5 核心单元测试。
5. 将 `H1=-F/short/5bars` 按新口径重跑，确认92.8%胜率是否成立。
6. 启动4周模拟盘观察，但只能在前五项完成后开始正式计时。
7. 将 MT5研究线和MT4邮件工具线拆成独立提交或独立仓库边界。

## 7. P1需求

1. Web Dashboard：假设、回测、观察、报告统一入口。
2. 策略版本对比：同一假设下比较不同参数、不同出场规则、不同成本模型。
3. Agent工具审计：记录每次AI调用的数据、代码、命令和结果。
4. 多市场扩展：外汇、黄金、股指、A股、美股、加密货币按市场拆适配器。
5. 用户权限：研究员、复核者、执行者、管理员。

## 8. 关键成功指标

- 策略从自然语言假设到可复现回测的时间小于30分钟。
- 所有正式回测100%包含 Run Card。
- 所有正式策略100%通过无未来函数测试。
- 回测和模拟盘信号偏差可解释率大于90%。
- 每条策略都能追溯到数据版本、代码版本、成本模型和报告版本。

## 9. 风险

- AI过度生成策略，导致研究噪音变多。
- 高胜率结果可能来自未来函数、重复事件或成本遗漏。
- 开源项目许可证可能限制商业化嵌入。
- 多Agent并行过多，会造成结果堆积但无法消化。
- 直接接实盘会放大尚未审计的工程风险。

## 10. 开源项目调研结论

调研项目包括 Qlib、QuantConnect Lean、vn.py、NautilusTrader、vectorbt、backtesting.py、Freqtrade、Hummingbot、Jesse、FinRL/FinRL-X、Vibe-Trading。

结论：

- 不建议直接fork一个项目做全部平台。
- 建议建设自己的编排层和审计层，把外部项目作为可插拔能力。
- MVP优先复用理念和接口，不急于深度嵌入重型引擎。

初步站位：

- AI研究/因子思想参考 Qlib + RD-Agent。
- 国内交易接口和AI多因子投研参考 vn.py。
- 专业多资产回测/实盘参考 Lean 和 NautilusTrader。
- 快速参数扫描参考 vectorbt，但注意 Commons Clause 商业限制。
- 简单教学/轻量回测可参考 backtesting.py，但AGPL不适合作为闭源SaaS核心。
- 加密交易参考 Freqtrade/Hummingbot/Jesse，不作为当前MT5主线核心。
- AI交易工作台体验参考 Vibe-Trading，但平台必须加入更严格审计和实施门槛。

## 11. 参考项目

- Qlib: https://github.com/microsoft/qlib
- QuantConnect Lean: https://github.com/QuantConnect/Lean
- vn.py: https://github.com/vnpy/vnpy
- NautilusTrader: https://github.com/nautechsystems/nautilus_trader
- vectorbt: https://github.com/polakowo/vectorbt
- backtesting.py: https://github.com/kernc/backtesting.py
- Freqtrade: https://github.com/freqtrade/freqtrade
- Hummingbot: https://github.com/hummingbot/hummingbot
- Jesse: https://github.com/jesse-ai/jesse
- FinRL: https://github.com/AI4Finance-Foundation/FinRL
- Vibe-Trading: https://github.com/HKUDS/Vibe-Trading
