# 吾家有老 项目知识库

这是「吾家有老」社区养老平台的 Obsidian 项目知识库，采用 `raw/` + `wiki/` 双层结构。

## 目录说明

```text
sample-vault/
├── AGENTS.md               # 本项目 Agent 工作约定
├── raw/                    # 原始资料层
│   ├── meetings/           # 会议纪要
│   ├── requirements/       # 需求、PRD、方案草稿
│   ├── research/           # 调研、竞品、技术文章
│   ├── incidents/          # 故障、复盘、告警记录
│   └── conversations/      # AI 对话导出
└── wiki/                   # 整理后的知识层
    ├── decisions/          # ADR / 决策记录
    ├── runbooks/           # 操作手册 / SOP
    ├── architecture/       # 架构说明 / 模块边界
    ├── conventions/        # 代码规范 / 命名约定
    ├── patterns/           # 常见模式 / 最佳实践
    └── onboarding/         # 新人上手
```

## 使用方式

1. 用 Obsidian 打开本目录作为 vault。
2. 浏览 `raw/` 中的原始资料和 `wiki/` 中的整理知识。
3. 注意观察 wiki 页面中的 `[[...]]` 双向链接 — 这是知识网络的核心。
4. 查看 `wiki/source-*.md` 来源页如何从 raw 提炼为 wiki。

## 这是一个示例

本目录是 `obsidian-project-wiki` Skill 的示例 vault，展示 raw → wiki 的整理效果。

实际使用时，请通过 `install.sh` 脚本初始化你自己的项目知识库。
