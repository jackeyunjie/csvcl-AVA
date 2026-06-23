# Hermass State 系统 — MT5 移植核心信息卡

> **阅读顺序：这个文件最先读，然后看 PORTING_GUIDE，最后看 common_mistakes**
> 版本：v1.0
> 日期：2026-05-26

---

## 第一条：废弃混沌值，统一到 State

**混沌值系统已终止。所有新代码只用 State 4-bit 编码。**

| 混沌值 | State | 为什么改 |
|--------|-------|----------|
| 每个周期有各自的编码规则 | 所有周期统一 4-bit 编码 | 规则不一致导致多周期对比无意义 |
| 综合评分是连续值（如 0-100） | State 是离散值 0-15（可带负号） | 连续值不可复现，离散值可严格验证 |
| 没有"视角"概念 | D1/W1/H1 视角独立计算 | 视角是 State 系统的灵魂，详见第二条 |
| 混沌值高低没有明确阈值 | E(14)/F(15) 有精确定义 | E/F 是交易信号的核心触发器 |

**迁移方法**：历史数据全部按 State 公式重新计算，不与混沌值做映射。验证用 validation_samples.csv（100 个样本，已知正确答案）。

→ 详细编码表见 `state_encoding_table.md`

---

## 第二条：视角决定基准价 — 最核心概念

**一句话：你在哪个周期的图表上，就用哪个周期的收盘价计算所有 position_bit。**

```
D1 视角（日线图）：
  MN1 position = D1 close vs MN1 SR
  W1  position = D1 close vs W1  SR
  D1  position = D1 close vs D1  SR

W1 视角（周线图）：
  MN1 position = W1 close vs MN1 SR
  W1  position = W1 close vs W1  SR
  D1  position = W1 close vs D1  SR

H1 视角（小时图）：
  所有 position = H1 close vs 各周期 SR
```

**正确理解**：
- D1 视角 W1 State = "日线价格在周线结构中的位置"
- W1 视角 W1 State = "周线自身的趋势和位置"
- 两者回答不同问题，**可以不同**，不是 bug

**trend / base / volatility 始终用各自周期的指标，不随视角变化。只有 position 的基准价随视角变化。**

→ 详细设计说明见 `HERMASS_STATE_MT5_PORTING_GUIDE.md` 第二章

---

## 第三条：验证方法 — 用 validation_samples.csv 逐行对比

### 操作步骤

```
1. 在 MT5 上用日线图（D1 视角）跑 100 个样本的 State 计算
2. 对每个样本，输出：mn1_score, w1_score, d1_score, mn1_base, mn1_trend, mn1_pos, mn1_vol, w1_base, w1_trend, w1_pos, w1_vol, d1_base, d1_trend, d1_pos, d1_vol
3. 与 validation_samples.csv 中的对应列逐行对比
4. 任一列不一致 → 检查 common_mistakes.md 中对应错误
```

### 验证通过标准

- 100 个样本全部完全一致
- 不一致时禁止"差不多就行"
- 先查 position_bit（最常见出错点），再查 base（第二常见）

### validation_samples.csv 列说明

| 列 | 含义 |
|----|------|
| stock_code | 股票代码（MT5 对应品种名） |
| date | 基准日期 |
| d1_close | D1 视角基准价（D1 close） |
| mn1_hex / w1_hex / d1_hex | 三周期 State hex |
| mn1_score / w1_score / d1_score | 三周期 score |
| mn1/w1/d1_base, trend, pos, vol | 各周期四维展开 |
| ef_count | E/F 状态计数 |

→ 文件路径：`validation_samples.csv`

---

## 第四条：11 个不可变参数

**以下参数是 State 公式的组成部分，不可改、不可调、不可"优化"。**

| # | 参数 | 值 | 用途 |
|---|------|-----|------|
| 1 | BB 周期 | 20 | 布林带计算 |
| 2 | BB 标准差倍数 | 2.0 | 布林带宽度 |
| 3 | BB 分位窗口 | 20（不含当前 bar） | base 判定 |
| 4 | ATR 周期 | 14 | volatility_bit 判定 |
| 5 | ADX 周期 | 14 | trend_bit 判定 |
| 6 | ADX slope 窗口 | 3 bar | 趋势斜率 |
| 7 | 分形周期 k | 5（左右各 2 根） | SR 关键位识别 |
| 8 | 分形确认延迟 | 3 bar | SR 确认 |
| 9 | 编码位数 | 4-bit | base+trend×4+pos+vol |
| 10 | base 值 | 仅 0 或 8 | 收缩=0, 扩张=8 |
| 11 | 视角 | 由图表周期决定 | 日线图=D1视角, 周线图=W1视角 |

**为什么 11 个参数不可变**：
- 改任何一个参数，State 值就变了，与 Python 参考实现不一致
- 历史 State 数据全部作废，需要重新计算
- 如果确实需要调参，那是 State 2.0 的事，本版 State 1.0 锁定这 11 个值

→ 参数详细说明见 `common_mistakes.md` 最后一节

---

## 第五条：常见错误速查

| 错误 | 症状 | 修复 |
|------|------|------|
| position 用错收盘价 | W1/MN1 position 与验证样本不一致 | 改用视角基准价（见第二条） |
| ADX 参数不对 | trend_bit 不一致 | ADX=14, slope窗口=3 |
| BB 分位计算错误 | base 位不一致 | 窗口=20且不含当前bar |
| 分形确认延迟不对 | position_bit 在某些日期不一致 | 确认延迟=3, 前向填充 |
| 混合视角 | 日线图的W1 State与周线图的W1 State不同 | 这不是错误（见第二条） |

→ 完整清单见 `common_mistakes.md`

---

## 文件索引

| 文件 | 用途 | 阅读顺序 |
|------|------|----------|
| `START_HERE_核心信息卡.md` | 本文 — 核心规则一览 | 第 1 |
| `HERMASS_STATE_MT5_PORTING_GUIDE.md` | 完整移植指南（公式、视角、SR计算） | 第 2 |
| `common_mistakes.md` | 常见错误与混沌值统一方案 | 第 3 |
| `state_encoding_table.md` | State 编码速查表（16 种状态） | 参考 |
| `validation_samples.csv` | 100 样本验证数据 | 验证用 |

---

## 一句话总结

> **废弃混沌值，切换到 State 4-bit 编码。11 个参数不可变。视角决定 position 基准价。用 validation_samples.csv 的 100 个样本逐行对比验证。**
