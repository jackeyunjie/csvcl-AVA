# csvcl - AVA 项目知识库 Agent 约定

## 项目概述

本项目为 CSV/Excel 颜色标记与 MT4/MT5 数据处理系统，核心功能包括：

1. 扫描 MT4 `MQL4/Files` 目录下最新生成的 CSV 数据文件。
2. 对状态码/指标列按规则着色，生成 `_colored.xlsx`。
3. 生成指定范围的截图（JPG）。
4. 分析数据变化，识别关键位/趋势触发信号。
5. 在 7:00-22:00 时段内自动发送邮件报告。

## 目录约定

- `raw/` 存放原始项目资料，允许未整理、允许混乱。
- `wiki/` 存放经过整理的项目知识，必须可追溯来源。
- 根目录只放本规则文件和 README，不放具体笔记。
- 同一份资料在 `wiki/` 中只保留一份权威版本，旧版移动到 `raw/archived/`。

### 子目录说明

- `raw/meetings/`：会议纪要、需求讨论
- `raw/requirements/`：PRD、方案草稿、功能说明
- `raw/research/`：技术调研、竞品分析、MQL5/MQL4 技术文章
- `raw/incidents/`：故障、复盘、告警记录
- `raw/conversations/`：AI 对话导出
- `wiki/decisions/`：ADR / 项目决策记录
- `wiki/runbooks/`：操作手册 / SOP（如 MT4 数据处理流程）
- `wiki/architecture/`：系统架构 / 模块边界
- `wiki/concepts/`：核心概念（如 state_hex、KVB 平台时间）
- `wiki/conventions/`：代码规范 / 命名约定
- `wiki/patterns/`：常见模式 / 最佳实践
- `wiki/onboarding/`：新人上手

## Ingest 原则

当有新资料进入 `raw/` 后，Agent 需要按以下步骤处理：

1. **生成来源总结页**：在 `wiki/` 下创建 `source-{slug}.md`，说明这份资料讲了什么、为什么保留、关键结论是什么。
2. **提炼关键概念**：把资料中的概念、决策、约束、待办提取出来。
3. **新建或更新概念页**：如果概念足够重要，在 `wiki/concepts/`、`wiki/decisions/` 或对应分类下创建独立页面。
4. **增加交叉链接**：为新页面和已有页面添加 `[[...]]` 双向链接。
5. **汇报改动**：最后列出新增、更新、移动了哪些文件。

## Query Rule

回答项目相关问题时：

1. 优先搜索 `wiki/` 中已整理过的页面。
2. 如果能引用 wiki 页面，必须引用。
3. 如果 wiki 中没有相关内容，再回看 `raw/`。
4. 如果基于 raw 推断，需标注“待整理入 wiki”。

## 命名规范

- raw 文件：`{日期}-{主题}.md`，例如 `2026-06-22-kvb-timezone.md`
- wiki 来源页：`source-{主题}.md`
- wiki 决策页：`wiki/decisions/adr-{编号}-{主题}.md`
- wiki 手册页：`wiki/runbooks/{操作名}.md`
- wiki 概念页：`wiki/concepts/{概念名}.md`

## 时区与数据规范

- KVB 平台时间 = 北京时间 + 6 小时
- 处理数据前统一转换到同一时区（建议北京时间）
- CSV `TIME` 列为平台时间，文件名时间戳通常为北京时间

## 归档规则

- 超过 180 天未更新的 raw 资料，移动到 `raw/archived/`。
- 已被 wiki 完全覆盖的 raw 资料，可归档或删除。
- 删除前必须确认 wiki 中有来源链接。
