# 多周期共振收缩突破研究交付说明

日期: 2026-06-05

## 交付结论

多周期共振收缩突破 v2 已完成样本扩展、H1/H4/D1 共振研究、参数扫描、报告输出和 Obsidian 同步。当前系统可以作为“观察系统与研究框架”继续推进，但不能直接升级为实盘自动交易。

核心原因:

- v2 报告样本从 11 品种/180 天扩大到 24 品种/365 天，研究闭环已跑通。
- 但真实唯一突破事件口径仍需修正，报告 `5608` 条样本按真实突破键复核约为 `3520` 个唯一事件。
- H4/D1 趋势存在未来信息泄漏风险，必须改为 as-of 对齐。
- short 方向目标判断、Pivot/SR 重复计分、交易成本和 walk-forward 回测仍未完成。

## 已保存文档

项目内文档:

- `MT5_AI_Trading/docs/SQUEEZE_MT_RESONANCE_AUDIT_AND_SYSTEM_ROADMAP_20260605.md`
- `MT5_AI_Trading/docs/KIMI_PROMPT_MT_RESONANCE_SYSTEM_V3_20260605.md`
- `MT5_AI_Trading/docs/SQUEEZE_BREAKOUT_PROJECT_AUDIT_20260605.md`
- `MT5_AI_Trading/docs/KIMI_PROMPT_SQUEEZE_BREAKOUT_V2_20260605.md`
- `MT5_AI_Trading/docs/SQUEEZE_MT_RESONANCE_DELIVERY_20260605.md`

Obsidian 同步目录:

`C:\Users\MECHREVO\Documents\Obsidian Vault\Trading\SqueezeObserver\`

已同步到 Obsidian 的本轮关键文档:

- `SQUEEZE_MT_RESONANCE_AUDIT_AND_SYSTEM_ROADMAP_20260605.md`
- `KIMI_PROMPT_MT_RESONANCE_SYSTEM_V3_20260605.md`
- `SQUEEZE_MT_RESONANCE_DELIVERY_20260605.md`

## 已核对的研究产物

v2 研究模块:

- `MT5_AI_Trading/squeeze_multi_timeframe_research.py`

v2 报告与 CSV:

- `MT5_AI_Trading/reports/squeeze/squeeze_mt_research_20260605_1215.md`
- `MT5_AI_Trading/reports/squeeze/squeeze_mt_samples_20260605_1215.csv`
- `MT5_AI_Trading/reports/squeeze/squeeze_mt_param_sweep_20260605_1215.csv`

多周期观察框架:

- `MT5_AI_Trading/python/analytics/multi_timeframe_squeeze.py`

验证命令:

```powershell
python .\MT5_AI_Trading\test_multi_timeframe_breakout.py
```

验证结果:

```text
multi-timeframe resonant breakout regression passed
breakout stage=resonant_breakout, direction=long, confidence=0.95
setup stage=squeeze_setup, direction=hold
```

说明: 该验证是 smoke test，不是 pytest 单元测试套件。

## v2 关键数据

报告口径:

| 指标 | 数值 |
|---|---:|
| 品种数 | 24 |
| 回看周期 | 365 天 |
| 周期 | H1/H4/D1 |
| Setup 数 | 7928 |
| 报告突破样本 | 5608 |
| 报告突破率 | 70.7% |
| 报告 5bar 胜率 | 49.1% |
| 报告盈亏比 | 1.22 |
| 报告期望 | 0.019% |
| 报告顺势胜率 | 50.7% |
| 报告逆势胜率 | 47.6% |
| 验证状态 | 逻辑需要调整 |

复核口径:

| 指标 | 数值 |
|---|---:|
| CSV 总行数 | 5608 |
| 真实唯一突破键 | 3520 |
| 重复突破键数量 | 1249 |
| 重复键内样本行数 | 3337 |
| 单一突破最大重复计入 | 5 |
| 去重后 5bar 胜率 | 48.9% |
| 去重后平均 PNL | 0.019% |
| 去重后盈亏比 | 1.23 |
| 去重后入场后止损率 | 14.6% |

## 审计意见

当前 v2 的价值:

- 已证明系统能获取多品种 H1/H4/D1 数据。
- 已证明收缩 setup、突破事件、趋势共振、参数扫描和报告生成链路能跑通。
- 已证明样本规模可以扩大到几千级事件。
- 已形成后续系统搭建的观察框架。

当前 v2 的限制:

- 真实事件去重口径不正确。
- 高周期趋势对齐有 look-ahead bias 风险。
- short 目标判断仍需修正。
- `min_breakout_atr` 命名与实现不一致。
- Pivot/SR 仍可能重复计分。
- 未加入交易成本、滑点、手续费、walk-forward。
- 当前不是交易级回测，更不是实盘策略。

结论:

不得基于 v2 直接进入实盘自动交易。可以进入 v3 研究修正阶段；v3 通过后，才考虑搭建模拟盘观察系统。

## 下一步执行顺序

1. 新增 `squeeze_multi_timeframe_research_v3.py`，不要覆盖 v2。
2. 使用 as-of 时间戳对齐 H4/D1 趋势。
3. 使用真实 `event_id` 做突破事件去重。
4. 修正 short 方向 target 判断。
5. 修正 `min_breakout_atr` 命名或实现真实 ATR。
6. 移除或重定义 Pivot/SR 重复指标。
7. 加入交易成本和 fixed-hold/structure-stop/1R-partial 三类出场回测。
8. 做 train/validation/test 或 walk-forward。
9. 输出 v3 报告、events、trades、参数扫描 CSV。
10. 若 v3 无泄漏净收益仍为正，再搭建“只观察、不下单”的实盘观察系统。

## 给执行代理的文档

直接交给 KIMI 或其他执行代理使用:

`MT5_AI_Trading/docs/KIMI_PROMPT_MT_RESONANCE_SYSTEM_V3_20260605.md`

该提示词已明确:

- v3 必须新增，不破坏 v1/v2。
- 必须修正 as-of 对齐和真实事件去重。
- 必须加入成本、walk-forward 和测试。
- 允许搭建实盘观察系统，但禁止自动实盘交易。

