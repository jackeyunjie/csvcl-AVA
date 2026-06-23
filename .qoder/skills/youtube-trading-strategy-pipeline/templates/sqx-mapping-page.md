# SQX 模块映射：{strategy-name}

## 一句话定义

将 YouTube 第 {index} 个视频中的 **{strategy-name}** 拆解为 **StrategyQuant X (SQX)** 的指标、条件、入场、出场模块组合。

## SQX 模块拆分

### 1. 指标模块（Indicators）

| SQX 指标 | 参数 | 对应视频指标 |
|----------|------|--------------|
| {indicator} | {params} | {video indicator} |
| {indicator} | {params} | {video indicator} |

### 2. 入场条件模块（Entry Conditions）

#### 多头入场

```text
{condition}
AND {condition}
```

#### 空头入场（如适用）

```text
{condition}
AND {condition}
```

### 3. 入场动作模块（Entry Order）

| 设置 | 建议值 |
|------|--------|
| 入场类型 | {Market at Close / Next Bar Open} |
| 方向 | Long / Short |

### 4. 出场模块（Exit Conditions）

#### 止损（Stop Loss）

| 方案 | SQX 设置 |
|------|----------|
| {scheme} | {setting} |
| {scheme} | {setting} |

#### 止盈（Take Profit）

| 批次 | 方案 | SQX 设置 |
|------|------|----------|
| 第一批 | {scheme} | {setting} |
| 第二批 | {scheme} | {setting} |

### 5. 过滤模块（Filters）

- {filter}
- {filter}

## 参数优化建议

| 参数 | 优化范围 | 说明 |
|------|----------|------|
| {param} | {range} | {note} |
| {param} | {range} | {note} |

## 代码输出方向

### MQL5 (MT5)

- {implementation note}

### MQL4 (MT4)

- {implementation note}

### Python

- {implementation note}

## 与本项目 CSV/Excel 流程的结合

1. SQX 生成 MQL5 EA 导出到 MT5
2. MT5 输出信号状态到 CSV
3. 本项目对以下字段着色：
   - {field}
   - {field}
4. 生成邮件报告与截图

## 关联页面

- [[trading-sop-{slug}]]
- [[{concept-slug}]]
- [[source-youtube-trading-sop-{index}]]
- [[sqx-module-mapping]]
