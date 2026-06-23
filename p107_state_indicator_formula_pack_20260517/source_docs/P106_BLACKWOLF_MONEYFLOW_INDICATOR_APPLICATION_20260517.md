# P106 黑狼资金流指标应用框架

日期：2026-05-17

## 1. 总结论

黑狼资金流数据引入后，Hermass A 股系统可以从单纯的价格状态观察，升级为：

```text
price-first 主裁决
state-first 状态主线
moneyflow energy-increment 能量增量证据
turnover / amount liquidity confirmation 流动性确认
chip distribution cost-map 筹码成本分布观察
```

但资金流不能替代价格状态，也不能替代 P17 状态组合窗口验证。

正确定位：

```text
价格状态决定是否进入观察环境
策略条件决定是否进入策略适配候选
资金流、换手率、筹码峰只做二级确认和解释增强
```

## 2. 资金流指标分类

### 2.1 按订单规模

常见分类：

```text
超大单
大单
中单
小单
```

不同数据源的划分标准可能不同。公开数据体系中，BigQuant 示例按挂单额划分：

```text
小单：挂单额 < 4 万元
中单：4 万元 <= 挂单额 < 20 万元
大单：20 万元 <= 挂单额 < 100 万元
超大单：挂单额 >= 100 万元
```

黑狼数据的具体口径必须以黑狼字段说明为准，不能默认套用其他供应商标准。

### 2.2 按主动/被动

常见分类：

```text
active_buy 主动买入
active_sell 主动卖出
passive_buy 被动买入
passive_sell 被动卖出
```

中文解释：

- 主动买入：主动去吃卖盘。
- 主动卖出：主动去砸买盘。
- 被动买入：挂买单等待别人卖给你。
- 被动卖出：挂卖单等待别人买走。

这比单纯看“净流入”更有价值，因为它能区分：

```text
主动推动
被动承接
主动抛压
被动派发
```

### 2.3 按主力/散户

常见定义：

```text
主力 = 大单 + 超大单
散户 = 小单，部分口径会把中单单独列出
```

主力净流入不是“机构一定在买”，它只是大额订单方向的统计近似。

### 2.4 按筹码峰

筹码峰不是资金流本身，而是成本分布观察。

它回答的问题是：

```text
历史成交主要集中在哪些价格区域？
当前价格在筹码密集区之上、之中，还是之下？
突破时是否穿越主要筹码压力区？
回落时是否接近主要成本支撑区？
```

筹码峰适合作为：

```text
price structure reference 价格结构参考
cost-map observation 成本地图观察
resistance/support explanation 压力支撑解释
```

不适合作为单独主裁决。

## 3. 推荐接入字段

### 3.1 L0 raw 原始字段

黑狼原始字段必须先完整保留：

```text
symbol
name
trade_date
amount
turnover_rate
main_net_inflow
main_net_inflow_ratio
super_large_buy_amount
super_large_sell_amount
super_large_net_inflow
large_buy_amount
large_sell_amount
large_net_inflow
medium_buy_amount
medium_sell_amount
medium_net_inflow
small_buy_amount
small_sell_amount
small_net_inflow
active_buy_amount
active_sell_amount
passive_buy_amount
passive_sell_amount
chip_peak_price
chip_peak_concentration
chip_cost_90
chip_cost_70
profit_chips_ratio
source_name
```

实际字段以黑狼导出文件为准。

### 3.2 标准化字段

建议 Hermass 标准字段：

```text
moneyflow_main_net_amount
moneyflow_main_net_ratio
moneyflow_large_net_amount
moneyflow_super_large_net_amount
moneyflow_small_net_amount
moneyflow_active_buy_amount
moneyflow_active_sell_amount
moneyflow_active_net_amount
moneyflow_large_small_divergence
moneyflow_main_persistence_3d
moneyflow_main_persistence_5d
turnover_rate
amount_yi
chip_peak_main_price
chip_peak_distance_pct
chip_concentration_score
energy_increment_available
research_only_flag
```

## 4. 指标如何应用

### 4.1 资金关注增强

用于回答：

```text
这个观察对象是否有资金关注？
```

可观察：

- 主力净流入是否为正。
- 超大单/大单净流入是否连续。
- 主动买入是否增强。
- 成交额是否高于自身过去均值。

产品表达：

```text
资金关注增强
资金关注一般
资金关注不足
资金流与价格状态分化
```

不要表达为：

```text
主力买入，应该跟进
```

### 4.2 假突破过滤

用于回答：

```text
价格突破是否有成交和资金配合？
```

可观察：

- 突破当天 amount 是否放大。
- turnover_rate 是否提升。
- 主力净流入是否同步增强。
- 小单净流入是否过热。

解释逻辑：

```text
价格突破 + 成交额放大 + 主力净流入改善 = 更值得复核
价格突破 + 成交额不足 + 主力净流出 = 需要谨慎观察
```

### 4.3 吸筹 / 洗盘 / 派发观察

这里只能做“观察”，不能做确定性解释。

可定义三类研究标签：

```text
large_order_absorption_candidate 大单承接候选
small_order_chasing_candidate 小单追逐候选
distribution_pressure_candidate 派发压力候选
```

示例解释：

- 大单净流入、小单净流出、价格不大涨：可能是承接或吸筹候选。
- 小单净流入强、主力净流出、价格冲高：可能是追逐和派发风险候选。
- 主力净流入连续下降、价格高位横盘：可能是动能衰减候选。

必须加边界：

```text
资金流只能反映订单行为，不等于真实持仓变化。
```

### 4.4 筹码峰应用

筹码峰适合和状态系统结合：

```text
状态向上 + 价格突破筹码峰上沿 + 成交活跃改善
状态向上 + 价格仍在筹码密集区内 + 资金分化
状态分化 + 价格接近筹码压力区 + 主力净流出
```

产品表达：

```text
价格已脱离主要成本区
价格仍处于筹码密集区
上方筹码压力仍需观察
下方成本区提供结构参考
```

不要表达为：

```text
筹码峰突破必涨
筹码峰支撑必守
```

## 5. Hermass 评分层级建议

不要把资金流合成一个“买入分”。

建议拆成 4 个子维度：

```text
flow_direction_score      资金方向
flow_persistence_score    资金持续性
flow_structure_score      大小单结构
chip_structure_score      筹码结构
```

然后只输出研究标签：

```text
energy_supportive         能量支持
energy_divergent          能量分化
energy_overheated         能量过热
energy_insufficient       能量不足
energy_unavailable        能量不可用
```

## 6. 与 State-First 的关系

主线顺序必须是：

```text
1. D1/W1/MN1 状态对齐
2. 策略条件接近
3. 成交活跃度确认
4. 资金流增量证据
5. 筹码峰结构解释
6. 观察提醒或复盘卡片
```

资金流不允许提前替代状态门。

## 7. 对普通消费者页面的价值

普通消费者更容易理解：

```text
它为什么进入观察池？
有没有资金关注？
成交是不是活跃？
是不是行业里多个股票一起动？
是不是只是短期过热？
```

所以页面可以新增三类标签：

```text
状态同向
资金关注
成交活跃
筹码结构
```

每个标签都必须有解释，不输出动作建议。

## 8. 风险与限制

1. 资金流口径由供应商定义，不同供应商不可直接混用。
2. 大单可以被拆单，主力资金可能隐藏在小单里。
3. 净流入不等于真实持仓增加。
4. 涨停、跌停、封单会扭曲资金流解释。
5. 筹码峰是历史成交成本分布，不代表真实可交易筹码。
6. 资金流更适合短中期观察，不替代长期基本面。
7. 必须和价格状态、行业状态一起看。

## 9. P106 工程落地建议

### 9.1 Codex

建立：

```text
scripts/build_p106_blackwolf_moneyflow_raw_import.py
outputs/p106_blackwolf_moneyflow_20260517/p106_blackwolf_moneyflow.duckdb
```

### 9.2 Qoder

建立：

```text
scripts/verify_p106_blackwolf_moneyflow.py
```

检查：

- 字段完整。
- 日期覆盖。
- symbol 覆盖。
- amount / turnover / moneyflow 可用性。
- 不出现动作语义。

### 9.3 Claude

输出普通消费者页面文案边界。

### 9.4 Gemini

输出“资金关注 / 成交活跃 / 筹码结构”的页面解释。

## 10. 参考资料

公开资料显示，资金流体系通常按订单规模、主动/被动方向、流入/流出/净流入等维度构建。不同数据源口径不完全相同，黑狼字段必须以实际导出为准。

