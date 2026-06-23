# Agent 项目知识库

## 项目概述

本项目为 CSV/Excel 颜色标记与 MT4/MT5 数据处理系统，核心功能包括：

1. 扫描 MT4 `MQL4/Files` 目录下最新生成的 CSV 数据文件。
2. 对状态码/指标列按规则着色，生成 `_colored.xlsx`。
3. 生成指定范围的截图（JPG）。
4. 分析数据变化，识别关键位/趋势触发信号。
5. 在 7:00-22:00 时段内自动发送邮件报告。

## KVB 平台时间与时区

> **关键事实**：KVB 平台记录的时间晚于北京时间（本地时间）**6 个小时**。

### 换算关系

```text
KVB 平台时间 = 北京时间 + 6 小时
北京时间     = KVB 平台时间 - 6 小时
```

例如：

- CSV 中记录的时间为 `2026.06.17 12:04` 时，对应的北京时间约为 `2026.06.17 06:04`。
- 本地文件生成/修改时间（如文件名中的 `17点44`、文件系统 `LastWriteTime`）通常使用北京时间。

### 数据处理注意事项

1. **CSV `TIME` 列**：来自 MT4/KVB 平台，属于平台时间，比北京时间快 6 小时。
2. **文件名时间戳**与**文件系统修改时间**：通常为本地北京时间，与 CSV `TIME` 列存在约 6 小时时区差。
3. 进行数据新鲜度判断、定时任务或邮件报告时，应统一转换到同一时区（建议统一为北京时间）。
4. 若后续需要根据北京时间筛选"最近 N 分钟"的数据，需先将 CSV `TIME` 列减去 6 小时再比较。

## MT4 数据路径与文件模式

### 当前有效路径

```text
C:\Users\MECHREVO\AppData\Roaming\MetaQuotes\Terminal\
  1F7FB83FCE28CDC848B46CF4612D1D35\MQL4\Files
```

### 配置方式（已消除硬编码）

核心脚本（`csv_color_marker.py`、`process_real_mt4_data.py`、`run_mt4_marker.py`、`auto_email_config.py`）已移除硬编码 MT4 路径与默认收件人，按以下优先级读取：

1. **环境变量**：`.env` 中的 `MT4_FILES_PATH`、`EMAIL_RECIPIENTS` 等。
2. **YAML 配置**：`configs/mt4_config.yaml` 中的 `file_selection.search_paths`、`email.recipients`。
3. **命令行参数**：如 `--path`、`--recipients`。
4. **代码默认值**：最后保留少量兜底默认值，便于首次体验。

快速配置：

```bash
cp .env.example .env
# 编辑 .env 填写 MT4_FILES_PATH 与邮箱信息
```

> 注意：旧的硬编码 Terminal ID `50D8083188871EAB17316B22F188CFF7` 已被移除，
> `configs/mt4_config.yaml` 中的默认路径已更新为 `1F7FB83FCE28CDC848B46CF4612D1D35`。

### 文件名模式

- 日线状态数据：`KVBL_@_D1_*.csv`
- 小时状态数据：`KVBt_@_H1_#3_*.csv`（状态码：MN1/W1/D1/H4/H1）
- 小时指标数据：`KVBt_@_H1_#6_*.csv`（技术指标：EMA/RSI/MACD/ADX/布林带/CCI 等）

## 数据更新与机会扫描流程

1. 使用 `process_real_mt4_data.py` 扫描并处理 CSV：
   ```bash
   python process_real_mt4_data.py \
     --path "C:\Users\MECHREVO\AppData\Roaming\MetaQuotes\Terminal\1F7FB83FCE28CDC848B46CF4612D1D35\MQL4\Files" \
     --string "KVBt_@_H1_#3" \
     --minutes 10000
   ```
2. 程序默认对 `E2:G43` 上色，适用于日线状态文件（MN1/W1/D1 位于 E/F/G 列）。
3. 对于 `#3` 等 H1 状态文件，状态列位于 `I2:M43`，需要单独对 I-M 列着色才能正确显示。
4. 机会识别规则：关注 MN1/W1/D1/H4/H1 中从非重要值变为 `[2, -2, 6, -6]` 的情况。
   - `2 / -2`：位置触发（多向/空向）
   - `6 / -6`：趋势确认（多向/空向）

## 项目知识库（Obsidian Wiki）

本项目已接入 `obsidian-project-wiki` 工作流，统一存放原始资料与整理后的知识：

```text
docs/project-wiki/
├── AGENTS.md          # Wiki 内 Agent 约定
├── README.md          # Wiki 说明
├── raw/               # 原始资料
│   ├── meetings/      # 会议纪要
│   ├── requirements/  # 需求/PRD
│   ├── research/      # 技术调研、MQL5 文章等
│   ├── incidents/     # 故障复盘
│   └── conversations/ # AI 对话导出
└── wiki/              # 整理后的知识
    ├── decisions/     # 决策记录
    ├── runbooks/      # 操作手册
    ├── architecture/  # 架构说明
    ├── concepts/      # 核心概念
    ├── conventions/   # 规范约定
    ├── patterns/      # 最佳实践
    └── onboarding/    # 新人上手
```

### Agent 使用规则

1. 回答项目相关问题时，优先搜索 `docs/project-wiki/wiki/` 中的已整理页面。
2. 新资料进入 `docs/project-wiki/raw/` 后，按 `docs/project-wiki/AGENTS.md` 约定整理为 wiki 页面。
3. Wiki 页面之间应使用 `[[...]]` 双向链接建立关联。
4. 已入库资料示例：[[source-mql5-article-18911]]、[[candle-range-theory]]。

### 如何打开

用 Obsidian 选择 **Open folder as vault**，打开 `docs/project-wiki/` 目录。

### YouTube 交易策略入库流水线

本项目已新增 `youtube-trading-strategy-pipeline` Skill，用于把 YouTube 交易教学视频自动沉淀为策略资产：

- 提取中文字幕到 `docs/project-wiki/raw/research/`
- 生成/更新 wiki 来源页、SOP runbook、概念页、SQX 模块映射
- 输出 MQL5（MT5）、MQL4（MT4）、Python 实现方向
- 所有页面使用 `[[...]]` 交叉链接

使用方法见 `.qoder/skills/youtube-trading-strategy-pipeline/SKILL.md`。

## 风险提示

- `state_hex` 为状态体检码，不是买卖指令。
- H1 级别信号频率高、噪音大，需结合更高周期与策略验证。
- 数据处理前务必确认时区转换，避免将平台时间误判为本地时间。
