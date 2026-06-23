# 弘运混沌交易系统 — 全量指标清单

> 版本: 2026-05-09 | 对齐用, 找缺失, 定优先级

---

## 目录

1. [MT4 原生指标 (mq4 源码)](#1-mt4-原生指标-mq4-源码)
2. [Python 移植/核心指标引擎](#2-python-移植核心指标引擎)
3. [指标派生层 (P23 Indicator Library)](#3-指标派生层-p23-indicator-library)
4. [策略层用到的指标](#4-策略层用到的指标)
5. [待派生字段 (P23.1 计划)](#5-待派生字段-p231-计划)
6. [应用场景矩阵](#6-应用场景矩阵)

---

## 1. MT4 原生指标 (mq4 源码)

存放: `/Users/lv111101/Documents/yiclaw/MT4 指标/`

| 文件名 | 类型 | 核心逻辑 | 输出 | 备注 |
|---|---|---|---|---|
| **SqFractal.mq4** | 分形 | Bill Williams 分形: `Fractal=3/5/...` 奇数窗口, 找局部最高/最低 | 上分形(红色箭头), 下分形(蓝色箭头) | 被 SqSr_mtf_eli_2 调用 |
| **SqSr_mtf_eli_2.mq4** | 多周期 SR | 调用 SqFractal 计算 4 个周期的分形, 用 persistence 填充非分形 bar | 4 个周期的阻力和支撑线 (D1/W1/MN1 等自适应) | 自动判断当前图表周期, 映射高周期分形 |
| **RSIOMA_v2HHLSX.mq4** | RSI 衍生 | RSI(14) + EMA(21) + 触发信号 | RSI 线, MA(RSI), 80/20 触发, 金叉/死叉, 趋势方向柱 | 含 20/80 触发, 50 分界, 70/30 趋势判断 |
| **GLI Bollinger Bands v2.0.ex4** | 布林带 | 编译版 ex4, 无源码 | 布林带上中下轨 | 具体逻辑待反编译或从 Python 版推断 |

### 1.1 SqFractal 算法
```
窗口 = Fractal 参数 (默认 3, 即左右各 1 根)
上分形 = High[middle] 是窗口内最高
下分形 = Low[middle] 是窗口内最低
```
Python 版在 mtf_fractal_sr_indicator.py 的 `compute_fractal_levels()` (499行)

### 1.2 SqSr_mtf 多周期映射
```
当前周期 → 自动选 4 个高周期 (例如 D1 图显示 MN1/W1/D1/D1)
每个周期调用 SqFractal
persistence 填充: 非分形 bar 沿用上一个分形值
```

### 1.3 RSIOMA 信号体系
```
RSI(14) → MA(21) → 信号:
  - 柱状图: >50 多头, <50 空头; >70 强多, <30 强空
  - 触发: 上穿 20 做多信号, 下穿 80 做空信号
  - 交叉: RSI 上穿/下穿 MA(RSI) 金叉/死叉
  - 磁铁: RSI<20 且回升 → 吸多; RSI>80 且回落 → 吸空
```

---

## 2. Python 移植/核心指标引擎

核心文件: `/Users/lv111101/Documents/hongrun-chaos-trading-system/scripts/mtf_fractal_sr_indicator.py` (2645 行)

### 2.1 分形/支撑阻力

| 函数 | 行号 | 功能 |
|---|---|---|
| `compute_fractal_levels()` | 499 | 全量 OHLC 数据计算分形, 输出 FractalLevel: symbol/time/resistance/support |
| `build_latest_level_rows()` | 928 | 每个 symbol+timeframe 最新分形 SR 层 |
| `build_span_process_rows()` | 1008 | SR 区间演变过程: 收缩计数/扩张/突破 |
| `build_important_price_comparisons()` | 2006 | 用户标记关键价 vs 最新 SR 对比 |

### 2.2 指标计算引擎 (核心)

#### 字段级指标

函数 `compute_bar_metrics()` (692行), 每根 bar 产出:

| 指标名 | 参数 | 说明 |
|---|---|---|
| `atr14` | 14 | 平均真实波幅 |
| `atr_ratio_pct` | 14 | ATR/收盘价 % |
| `atr_rank_20` | 20 | ATR 百分位排名 |
| `atr_state_code` | - | 1=高ATR(≥80%分位), 0=正常 |
| `plus_di_14` | 14 | +DI 方向指标 |
| `minus_di_14` | 14 | -DI 方向指标 |
| `adx14` | 14 | 平均趋向指数 |
| `adx_slope` | 3 | ADX 斜率 |
| `adx_rising` | - | ADX 上升 |
| `adx_falling` | - | ADX 下降 |
| `adx_trend_on` | - | ADX≥25 且上升 → 趋势状态 |
| `adx_squeeze_on` | - | ADX≤13 且下降 → 挤压状态 |
| `bb_middle_20` | 20 | 布林带中轨 (SMA) |
| `bb_upper_20` | 20 | 布林带上轨 (+2σ) |
| `bb_lower_20` | 20 | 布林带下轨 (-2σ) |
| `bb_width_pct` | 20 | 带宽 % (上-下)/中轨 |
| `bb_width_rank_20` | 20 | 带宽百分位排名 |
| `bb_width_vs_median` | 20 | 带宽 vs 中位数比率 |
| `bb_width_expanding` | - | 带宽扩张 |
| `bb_width_trend_on` | - | 带宽≥80%分位 且扩张 → 趋势 |
| `bb_width_squeeze_on` | - | 带宽≤20%分位 或 ≤中位85% → 收缩 |
| `data_quality_flag` | - | 数据质量标记 |
| `data_quality_valid` | - | 数据有效 |

#### 收缩/扩张过程监控

| 指标 | 阈值 | 说明 |
|---|---|---|
| `contraction_score` | 多窗口(10/30/60/120) | SR 区间在各窗口是否收缩 |
| `contraction_streak` | ≥2 | 连续收缩计数 |
| `tightest_span_rank` | rank=1 | 区间宽度是否为最近 N 根最窄 |
| `span_to_close_pct` | - | SR 区间/收盘价 % |
| `span_vs_median` | ≤0.85 tight, ≤0.65 very_tight | 区间 vs 中位数 |

#### 阶段分类

| 阶段 | 条件 |
|---|---|
| `contraction` | contraction_score>0 或 streak≥2 |
| `critical_contraction` | tightest_span_rank==1 |
| `breakout_up` | 价格突破阻力 |
| `breakout_down` | 价格跌破支撑 |
| `range_tracking` | 正常区间 |
| `invalid_range` | SR 无效 |

### 2.3 状态编码系统 (Chaos Code)

函数 `build_chaos_snapshot_rows()` (1280行)

```
chaos_code = atr_state_code(1) + sr_relation_code(2) + trend_state_code(4) + squeeze_state_code(8)

组件:
  - 1 = ATR 扩张 (高波动)
  - 2 = SR 关系 (2=above_resistance, -2=below_support)
  - 4 = ADX 趋势 (>0 uptrend, <0 downtrend)
  - 8 = 收缩/挤压 (BB squeeze 或 ADX squeeze)

示例:
  chaos_code=0  → 无状态 (平静)
  chaos_code=1  → 仅波动扩张
  chaos_code=8  → 仅压缩
  chaos_code=9  → 1+8 波动扩张+压缩 (矛盾状态)
  chaos_code=15 → 1+2+4+8 全状态
```

### 2.4 全局视图

函数 `build_chaos_global_view_rows()` (1320行)

| 字段 | 说明 |
|---|---|
| `chaos_signature` | 多周期 chaos_code 组合 (D1=9\|W1=8\|MN1=0) |
| `dominant_bias` | bullish/bearish/neutral (根据 SR 方向累加) |
| `global_focus` | 全局焦点: compression_to_release / multi_tf_compression / uptrend / downtrend / inside_range / mixed_transition |
| `active_timeframes` | 有非零 chaos_code 的周期 |
| `contracting_timeframes` | 收缩中的周期 |
| `squeeze_timeframes` | 挤压中的周期 |
| `breakout_up/down_timeframes` | 突破中的周期 |
| `trend_up/down_timeframes` | 趋势中的周期 |

### 2.5 Watchlist 优先级

函数 `build_chaos_watchlist_rows()` (1496行)

```
attention_score = base_score + compression_score + release_score + trend_score + direction_score - conflict_penalty

优先级桶:
  - critical (≥90)
  - high (70-89)
  - medium (50-69)
  - low (30-49)
  - monitor (<30)

profile: "global" / "daily" / "hourly" (不同周期权重不同)
```

### 2.6 策略适配

函数 `build_chaos_strategy_fit_rows()` (1670行)

| 策略族 | 适配条件 |
|---|---|
| PIRATE_BOLLINGER | 最少 1 个高周期收缩/挤压 + 1 个低周期释放 |
| ACD | opening range 计算, 日线范围 |
| TREND_FOLLOWING | ADX trend_on 且方向一致 |

---

## 3. 指标派生层 (P23 Indicator Library)

构建脚本: `scripts/build_p23_indicator_library_mvp.py`
DuckDB 表: `outputs/global_hermass_futu_20260509/global_hermass_futu.duckdb`

### 3.1 已落地表

| 表名 | 行数 | 字段数 | 说明 |
|---|---|---|---|
| `indicator_field_catalog` | 218 | 多列 | 覆盖 hk_state_d1_multitf_asof_preopen 全部字段, 含分组/周期/是否 as-of safe |
| `vcp_required_feature_map` | 36 | 多列 | VCP 所需 36 个字段可用性: 14 available + 20 derivable + 2 derivable_requires_universe |
| `indicator_latest_snapshot` | 10 | 多列 | 每只股票最新一行状态快照 (HK10) |
| `state_transition_events` | 9,145 | 多列 | 状态突变事件: 含 prev/current 状态、跳变原因、跳变幅度 |

### 3.2 VCP 字段可用性分布

| 状态 | 数量 | 示例字段 |
|---|---|---|
| `available` | 14 | pivot_3k_high/low, atr_14, OHLCV, close_pct_change |
| `derivable` | 20 | sma_50/150/200, volume_sma_*, bb_width_pct, volume_ratio, pct_from_252d_high |
| `derivable_requires_universe` | 2 | rs_rank (需要全市场横截面) |
| **合计** | 36 | VCP 全部必选字段 |

### 3.3 状态突变事件

`state_transition_events` 触发原因分布:

| 原因 | 数量 |
|---|---|
| `mwd_score_delta_abs_ge_6` | 5,126 |
| `decision_bucket_changed` | 954 |
| `decision_bucket_changed,mwd_score_delta_abs_ge_6` | 919 |
| `close_gap_abs_ge_8pct` | 662 |
| `mwd_score_delta_abs_ge_6,close_gap_abs_ge_8pct` | 619 |

---

## 4. 策略层用到的指标

### 4.1 PIRATE_BOLLINGER (海盗布林)
脚本: `ashare_daily_pirate_bollinger_backtest.py`
依赖指标:
- `bb_width_squeeze_on` → 布林收缩 (开仓条件)
- `bb_width_expanding` → 布林扩张 (突破确认)
- `bb_width_vs_median` → 带宽 vs 中位数
- `atr_14` → 止损/仓位
- `adx_trend_on` → 趋势过滤

### 4.2 TREND_FOLLOWING (趋势跟随)
脚本: `trend_following_donchian_backtest.py` / `run_donchian_domain_backtest_pipeline.py`
依赖指标:
- Donchian 通道 (20/50/120)
- `adx_trend_on` → 趋势确认
- 周线突破年龄 (donchian_w1_breakout_age)

### 4.3 ACD 动态库存
脚本: `hongrun_acd_dynamic_library.py`
依赖指标:
- Opening Range (开盘区间)
- `calc_pivot_range` → 枢轴点
- `calc_contraction_streak` → 收缩计数
- `calc_rolling_pivot` → 滚动枢轴
- `derive_stage` → 阶段分类
- `derive_priority` → 优先级

### 4.4 VCP (波动收缩形态) — P19b
概念文档: `wiki/concepts/hongrun-vcp-standalone-strategy-schema-v0-1.md`
待建字段:
- VCP 候选事件 (需要 P23.1 派生字段落地后)
- 收缩计数 (已有 contraction_streak)
- pivot 高低点 (已有 pivot_3k_high/low)
- 成交量萎缩 (需要 volume_sma_5/10/50)
- 相对强度 (需要 rs_rank, 全市场)

### 4.5 多周期共振 (Cross-Strategy Resonance)
文档: `CROSS_STRATEGY_RESONANCE_FILTER_DESIGN_V1.md`
依赖: 多个策略信号 + W1/MN1 混沌值状态组合

---

## 5. 待派生字段 (P23.1 计划)

从 `vcp_required_feature_map` 中 derivable 的 20 个字段:

| 字段 | 派生方式 | 策略用途 |
|---|---|---|
| `sma_50` | rolling mean close, 50 | VCP 基底/趋势确认 |
| `sma_150` | rolling mean close, 150 | 中期趋势 |
| `sma_200` | rolling mean close, 200 | 长期趋势/牛熊分界 |
| `volume_sma_5` | rolling mean volume, 5 | 短期成交量基准 |
| `volume_sma_10` | rolling mean volume, 10 | 中期成交量基准 |
| `volume_sma_50` | rolling mean volume, 50 | 长期成交量基准 |
| `volume_ratio` | volume / volume_sma_50 | 放量/缩量判断 |
| `bb_width_pct` | (bb_upper-bb_lower)/bb_middle | 波动率宽度 |
| `pct_from_252d_high` | (close-252d_high)/252d_high | 接近年内高点 |
| `pct_above_252d_low` | (close-252d_low)/252d_low | 在年内低位上方多少 |

---

## 6. 应用场景矩阵

### 6.1 每种场景 → 核心指标

| 场景 | 核心指标 | 用途 |
|---|---|---|
| **趋势识别** | ADX(14), +DI/-DI, BB trend_on, trend_state_code | 是否处于趋势, 方向 |
| **收缩压缩** | BB squeeze_on, contraction_streak, tightest_span_rank, squeeze_state_code | VCP 基底, 布林收缩 |
| **波动放大** | ATR rank, bb_width_expanding, atr_state_code | 突破确认 |
| **支撑阻力** | fractal SR (resistance/support), sr_relation_code | 当前价格在 SR 内/上/下 |
| **多周期状态** | chaos_signature, global_focus | 单股多周期全景 |
| **状态突变** | state_transition_events, close_gap_pct | 跳空/状态跳变 |
| **Watchlist** | attention_score, priority_bucket | 重点关注排序 |
| **RSI 超买超卖** | RSIOMA (RSI(14)+MA+信号) | 短期反转 |
| **Opening Range** | ACD library: calc_opening_range | 日内突破交易 |
| **枢轴点** | ACD: calc_pivot_range, MN1: pivot_12m | 日/月/年级别支撑阻力 |
| **EMA 均线** | build_mn1_indicators: ema_20/50/200 | 趋势跟随 |

### 6.2 每类交易员 → 推荐指标

| 角色 | 优先看 | 辅助看 |
|---|---|---|
| **日内交易员** | H1/M15 SR, RSIOMA 信号, ACD opening range | Watchlist, attention_score |
| **波段交易员** | D1/H4 chaos_signature, global_focus, contraction_streak | PIRATE 信号, VCP 候选 |
| **基金经理** | latest_snapshot, 多周期 global_focus, strategy_fit | priority_bucket, PF |
| **研究员** | indicator_field_catalog, state_transition_events, P23 表 | vcp_required_feature_map |

---

## 7. 缺失/待建指标

| 缺失指标 | 优先级 | 原因 |
|---|---|---|
| **RS Rank (相对强度排名)** | P0 | VCP/Minervini 必需, 需全市场横截面 |
| **成交量萎缩判定** | P1 | VCP 形态核心条件之一 |
| **机构积累/派发 (OBV/ADL)** | P2 | SMC 分析用 |
| **资金流向 (MFI)** | P2 | 辅助成交量分析 |
| **VCP 候选事件生成** | P1 (P19b) | 需要 P23.1 完成 |
| **Qoder 截图 ML 分析** | P3 | P22 视觉证据层后续 |
| **Ichimoku 云** | P3 | 多周期辅助 |
| **自定义波动率模型** | P3 | ATR 替代方案 |

---

> **下一步建议**: 你读完这个清单后, 确认:
> 1. 少了哪些你认为重要的指标
> 2. 哪些场景分类需要调整
> 3. 优先补哪些缺失指标
