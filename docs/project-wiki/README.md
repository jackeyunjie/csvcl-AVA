# csvcl - AVA 项目知识库

这是 csvcl - AVA（CSV/Excel 颜色标记与 MT4/MT5 数据处理系统）的 Obsidian 项目知识库，采用 `raw/` + `wiki/` 双层结构。

## 目录说明

```text
docs/project-wiki/
├── AGENTS.md               # 本项目 Agent 工作约定
├── raw/                    # 原始资料层
│   ├── meetings/           # 会议纪要
│   ├── requirements/       # 需求、PRD、方案草稿
│   ├── research/           # 调研、竞品、技术文章（含 MQL5 技术文档）
│   ├── incidents/          # 故障、复盘、告警记录
│   └── conversations/      # AI 对话导出
└── wiki/                   # 整理后的知识层
    ├── decisions/          # ADR / 决策记录
    ├── runbooks/           # 操作手册 / SOP
    ├── architecture/       # 架构说明 / 模块边界
    ├── concepts/           # 核心概念（state_hex、KVB 时间等）
    ├── conventions/        # 代码规范 / 命名约定
    ├── patterns/           # 常见模式 / 最佳实践
    └── onboarding/         # 新人上手
```

## 使用方式

1. 用 Obsidian 打开 `docs/project-wiki/` 作为 vault。
2. 新资料先放进 `raw/` 对应子目录。
3. 需要整理时，让 Agent 读取 raw 文件并按 `AGENTS.md` 约定写入 `wiki/`。
4. 基于 `wiki/` 提问，把好回答再回写到 `wiki/`。

## 第一次整理示例

把一份技术文章放进 `raw/research/2026-06-23-mql5-article-18911.md`，然后对 Agent 说：

```text
请读取 docs/project-wiki/raw/research/2026-06-23-mql5-article-18911.md。
基于其中内容：
1. 在 wiki/ 下创建一页来源总结页
2. 提炼关键概念、决策、待办
3. 如果需要，新建相关概念页或决策页
4. 为新旧页面增加交叉链接 [[...]]
5. 最后告诉我新增和更新了哪些文件
```

## 检查整理质量

整理完成后，确认 wiki/ 里同时出现：

- **来源页**：说明这份资料讲了什么、为什么保留
- **概念页/决策页**：可复用的知识，而不只是一篇摘要
- **双向链接**：页面之间至少有 `[[...]]` 连接

## 与 Skill 的关系

本项目知识库基于 `obsidian-project-wiki` Skill：

https://github.com/jackeyunjie/obsidian-project-wiki
