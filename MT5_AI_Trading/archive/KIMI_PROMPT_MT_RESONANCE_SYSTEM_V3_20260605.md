# 给 KIMI 的提示词: 多周期共振收缩突破 v3 与系统搭建

你是量化研究工程师和交易系统工程师。请在 `D:\qoder\csvcl - AVA\MT5_AI_Trading` 项目中推进多周期共振收缩突破 v3。目标是修正 v2 研究口径，并搭建可回测、可观察、但不自动实盘的系统。

## 背景

已有文件:

- `squeeze_multi_timeframe_research.py`
- `reports/squeeze/squeeze_mt_research_20260605_1215.md`
- `reports/squeeze/squeeze_mt_samples_20260605_1215.csv`
- `reports/squeeze/squeeze_mt_param_sweep_20260605_1215.csv`
- `python/analytics/multi_timeframe_squeeze.py`
- `test_multi_timeframe_breakout.py`

v2 报告结果:

- 24 个品种。
- 365 天。
- H1/H4/D1。
- setup 数 7928。
- 报告突破样本 5608。
- 报告 5bar 胜率 49.1%。
- 报告期望 0.019%。
- 顺势胜率 50.7%，逆势胜率 47.6%。
- 状态: 逻辑需要调整。

审计复核发现:

1. `unique_breakouts=5608` 不是真实事件去重。按 `symbol + breakout_timestamp + breakout_direction` 复核只有约 3520 个真实唯一突破键。
2. 多周期趋势存在 look-ahead bias: 当前 H4/D1 趋势是用完整样本计算后赋给所有 H1 setup。
3. short 方向 1R/2R/3R 目标判断仍使用 `.min()`，应改为 `.max()`。
4. `min_breakout_atr` 实际使用 anchor_range，不是 ATR。
5. Pivot Range 和 SR Range 仍重复计分。
6. v2 是事件统计，不是完整交易级回测。

## 总目标

新增 v3，不破坏 v1/v2 交付物。v3 必须回答:

- 无未来信息泄漏后，多周期共振是否仍有统计优势？
- 真实事件去重后，with_trend 是否显著好于 neutral/against？
- 加入成本后，哪些品种仍可观察？
- 是否允许进入模拟盘观察？不得建议直接实盘自动交易。

## 必做任务

### 1. 新增 v3 研究脚本

新增:

- `squeeze_multi_timeframe_research_v3.py`
- `test_squeeze_multi_timeframe_research_v3.py`

不要删除或覆盖 v2 文件。

### 2. 修正 as-of 多周期对齐

要求:

- 对每个 H1 setup timestamp，只能使用该时间之前已经收盘的 H4/D1 bar。
- 使用时间戳对齐，不允许用 `i // 4`、`i // 24`。
- 推荐使用 `pd.merge_asof` 或明确的 timestamp <= setup_time 过滤。
- 输出每个 setup 实际使用的 `h4_bar_time`、`d1_bar_time`。
- 如果高周期数据缺失，则 trend_bias=neutral，并记录 `data_warning`。

### 3. 修正真实事件去重

要求:

- `setup_id`: 每个 setup 唯一。
- `event_id`: 真实突破事件唯一，至少包含 `symbol + breakout_timestamp + breakout_direction`。
- `cluster_id`: 相邻 setup 归属同一观察簇，可用于诊断，但不得作为真实突破事件去重主键。
- 报告同时输出 raw setup、raw breakout、unique event 三套指标。

### 4. 修正突破交易逻辑

要求:

- 入场后才计算止损、MFE、MAE、target。
- 1bar/5bar/10bar/20bar 定义为入场后第 N 根 K 线的 close 收益，不把入场 bar 当成 1bar。
- short 目标判断使用 `(entry_price - future_low).max()`。
- MFE/MAE 使用 high/low，不只用 close。
- `min_breakout_atr` 改为 `min_breakout_anchor_multiple`；若要使用 ATR，则另设 `min_breakout_atr_multiple` 并真正计算 ATR。

### 5. 修正收缩 score

处理 Pivot/SR 重复计分:

- 方案 A: 保留 SR range，移除 Pivot range。
- 方案 B: 重新定义 Pivot 为 central pivot 或 pivot band 变化。

在报告中说明采用哪个方案。

### 6. 加入交易成本与回测

新增一个轻量交易级回测:

- 输入 unique events。
- 支持 fixed_hold_5bar、fixed_hold_10bar、structure_stop、1R_partial 三类出场规则。
- 输出 gross/net PNL。
- 成本模型按 symbol class 配置，至少区分 FX、metal、index、oil、crypto。
- 输出 trades CSV。

### 7. 做 walk-forward 或时间切分

最低要求:

- train: 前 60%
- validation: 中间 20%
- test: 后 20%

只能在 train/validation 选参数，test 只评估。

报告必须输出各区间表现，不能只报全样本最优。

### 8. 增加测试

测试必须覆盖:

- H1 setup 只能拿到过去已收盘 H4/D1 bar。
- 同一突破被多个 setup 捕捉时，event_id 只计一次。
- short target 逻辑正确。
- 入场前触发 stop 不算交易止损。
- 1bar/5bar 周期语义正确。
- 成本扣减正确。
- Pivot/SR 不重复计分。

运行:

```powershell
python -m pytest .\test_squeeze_multi_timeframe_research_v3.py -q
python .\test_multi_timeframe_breakout.py
```

如果测试路径不同，请在报告中写明实际命令。

## 输出文件

请生成:

- `reports/squeeze/squeeze_mt_research_v3_YYYYMMDD_HHMM.md`
- `reports/squeeze/squeeze_mt_setups_v3_YYYYMMDD_HHMM.csv`
- `reports/squeeze/squeeze_mt_events_v3_YYYYMMDD_HHMM.csv`
- `reports/squeeze/squeeze_mt_trades_v3_YYYYMMDD_HHMM.csv`
- `reports/squeeze/squeeze_mt_param_sweep_v3_YYYYMMDD_HHMM.csv`
- `docs/SQUEEZE_MT_V3_RESEARCH_NOTES_YYYYMMDD.md`

报告必须包含:

- v2 vs v3 差异表。
- raw vs unique event 指标。
- gross vs net 指标。
- with_trend vs neutral vs against 指标。
- 分品种白名单/灰名单/黑名单。
- walk-forward train/validation/test 指标。
- 是否允许进入模拟盘观察。
- 明确禁止直接进入实盘自动交易。

## 推荐交易池初筛

仅作为研究假设，不可直接实盘:

- 优先观察: UKOIL、ETHUSD、US30、BTCUSD、NAS100、UK100、GER40、USOIL。
- 暂缓或剔除: AUDUSD、GBPJPY、XAUUSD、EURGBP、USDCHF、USDCAD、XAGUSD。

请以 v3 无泄漏、去重、净值回测结果重新确认，不要直接沿用这个名单。

## 实盘限制

不得启动实盘交易。

可以搭建实盘观察系统，但只能:

- 每小时扫描。
- 输出候选机会。
- 写入报告或 Obsidian。
- 可选发送提醒。
- 不下单。

任何“实盘”建议必须先满足:

- v3 无泄漏测试段 net expectancy > 0。
- 至少 4 周模拟盘观察。
- 风控硬限制完成。
- 用户明确授权。

