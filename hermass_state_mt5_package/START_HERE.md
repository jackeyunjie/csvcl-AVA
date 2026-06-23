# Hermass State 系统 — 开始之前（核心信息卡）

> 在阅读任何详细文档之前，请先看这张卡片。
> 如果你只有 5 分钟，只看这一页就够了。

---

## 四条核心规则

### 1. 视角决定基准价

```
D1 视角（日线图）→ 所有周期 position 用 D1 close
W1 视角（周线图）→ 所有周期 position 用 W1 close
H1 视角（小时图）→ 所有周期 position 用 H1 close

同一标的、同一天、D1图和W1图上的 W1 State 可以不同 → 不是bug，是设计。
```

### 2. position 是唯一随视角变的维度

| 维度 | 计算来源 |
|------|----------|
| base（布林带宽分位） | 该周期的布林带，不变 |
| trend（ADX方向） | 该周期的ADX，不变 |
| volatility（ATR） | 该周期的ATR，不变 |
| **position（价格位置）** | **视角基准价 vs 该周期SR** ← 唯一随视角变化 |

### 3. 用 validation_samples.csv 逐行验证

打开 `validation_samples.csv` 和 `validation_samples_supplement.csv`：
- 第一列是输入
- mn1_hex/w1_hex/d1_hex 是期望输出（正解）
- 连续 10 行一致 → 实现正确

### 4. 11 个参数不可变

| BB周期 | BB倍数 | BB分位窗口 | ATR | ADX | ADX slope | 分形k | 确认延迟 | 编码位 | base值 | 视角 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 20 | 2 | 20 | 14 | 14 | 3 | 5 | 3 | 4-bit | 0/8 | 由视角 Agent 决定 |

---

## State 本质

```
一个 State hex = 一个交易品种在某一周期上的综合状态

State = base + trend_bit×4 + position_bit + volatility_bit

范围: -15 ~ +15
E=14, F=15 是最优状态
ef_count = 三周期中处于E或F的周期数 (0-3)
负值 -E/-F 不参与 ef_count 统计
```

---

## 混沌值 → State 迁移

| 混沌值（旧） | State（新） | 
|-------------|------------|
| 各周期编码不统一 | 统一 4-bit 编码 |
| 连续值 0-100 | 离散 0-15 |
| 无视角概念 | 视角决定 position 基准价 |
| 主观判断 | 可逐行验证 |

**迁移策略：State 稳定运行后，混沌值停用。不要混用。**

---

## 常见陷阱速查

| 陷阱 | 正解 |
|------|------|
| W1 position 用了 W1 close | 用视角基准价（默认 D1 close） |
| 布林带宽分位含当前 bar | 不含当前 bar |
| SR 分形没有确认延迟 | 3 根 bar 确认延迟 |
| 负值 E/F 参与 ef_count | 只有正值参与 |
| sign 裁决未检查 MN1 SR 优先级 | 先检查价格 vs MN1 SR，再查大周期方向 |

---

## 验证清单

```
□ position_bit 用了视角基准价（非各自周期 close）
□ base 用布林带宽分位（不含当前 bar）
□ trend_bit 含 "closed" 状态（ADX≤13 且 slope<0）
□ SR 分形确认延迟 3 根 bar + 前向填充
□ sign 裁决：价格 vs MN1 SR → 大周期框架方向
□ 负值 E/F 不参与 ef_count 统计
□ validation_samples.csv 连续 10 行一致
```
