---
name: obsidian-project-wiki
version: 1.1.0
description: |
  为任意项目搭建 Obsidian + AI 的“会进化”的项目知识库。
  通过 raw（原始资料）+ wiki（整理知识）+ AGENTS.md（Agent 约定）三层结构，
  让项目决策、操作手册、架构知识随使用自然沉淀，可被团队复用。
author: jackeyunjie
repo: https://github.com/jackeyunjie/obsidian-project-wiki
---

# Obsidian Project Wiki

> 让 AI Agent 成为你的项目知识库整理助手，而不是又一个只会生成摘要的聊天机器人。

## 这个 Skill 解决什么问题

项目里常见的知识管理问题：

- 会议纪要、需求文档、故障复盘散落在各处，找的时候靠记忆
- 新成员 onboarding 成本高，老成员离职带走大量隐性知识
- AI 每次回答都是“现编”，不能引用项目里的已有结论
- 资料存了很多，但从未被整理成可连接、可复用的知识

本 Skill 提供一套**最小可行、跨项目通用**的方案：

```text
raw/（原始资料）
  → Agent 整理
  → wiki/（可复用知识页）
  → 基于 wiki 回答问题
  → 好回答再回写 wiki
```

## 适用范围

- 任何有代码、有文档、有团队协作的软件项目
- 个人想用 Obsidian 管理多个项目知识
- 团队希望把 AI 对话、会议记录、决策过程沉淀为项目资产

## 不适合的场景

- 纯个人碎片化笔记（无项目边界）
- 只需要一次性剪藏、不需要持续进化
- 对权限/审计有极高要求的企业级知识管理（本方案偏轻量）

## 前置条件

- 已安装 [Obsidian](https://obsidian.md/)
- 已安装任意 Local Agent（Claude Code / Codex / Qoder / Kimi CLI 等）
- 项目仓库已使用 Git（用于跨设备同步 markdown 文件）

## 核心结构

在任意项目根目录下创建：

```text
docs/project-wiki/          # Obsidian vault 根目录
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

> 原则：目录只保留必要层级，raw 和 wiki 绝不混放。

## 快速开始

### 第一步：创建项目知识库

在项目根目录执行：

```bash
mkdir -p docs/project-wiki/raw/{meetings,requirements,research,incidents,conversations}
mkdir -p docs/project-wiki/wiki/{decisions,runbooks,architecture,conventions,patterns,onboarding}
touch docs/project-wiki/AGENTS.md
```

### 第二步：写入 AGENTS.md

复制本 Skill 提供的模板：

```bash
cp <skill-path>/templates/AGENTS.md docs/project-wiki/AGENTS.md
```

核心作用：告诉 Agent 这是 wiki 仓库，不是随手记笔记，整理时必须遵守分层、链接、来源追溯规则。

### 第三步：用 Obsidian 打开 vault

在 Obsidian 中选择 **Open folder as vault**，打开 `docs/project-wiki/`。

建议：第一次不要急着装插件，先保证空间干净。

### 第四步：放入第一份 raw 资料

把一份会议纪要、需求文档或技术文章放进 `raw/`。例如：

```text
raw/meetings/2026-06-22-okr-review.md
```

### 第五步：让 Agent 整理

使用本 Skill 提供的标准 prompt：

```text
请读取 docs/project-wiki/raw/meetings/2026-06-22-okr-review.md。
基于其中内容：
1. 在 wiki/ 下创建一页来源总结页
2. 提炼关键概念、决策、待办
3. 如果需要，新建相关概念页或决策页
4. 为新旧页面增加交叉链接 [[...]]
5. 最后告诉我新增和更新了哪些文件
```

### 第六步：检查结果

确认 wiki/ 下出现：

- **来源页**：说明这份资料讲了什么、为什么保留
- **概念页/决策页**：可复用的知识，而不只是一篇摘要
- **双链**：页面之间至少出现 `[[...]]` 链接

### 第七步：提问并回写

```text
基于 wiki/ 里的内容，回答：我们为什么选 PostgreSQL 而不是 MySQL？
请引用具体页面。回答后，把这次结论补充到 wiki/decisions/ 的对应页面。
```

## Agent 工作约定（AGENTS.md）

项目级 `AGENTS.md` 是这套方案能跑通的关键。它通常包含：

- **目录约定**：raw 和 wiki 的分工
- **Ingest 原则**：新资料进入后必须做什么
- **Query Rule**：回答问题时先看 wiki 还是 raw
- **命名规范**：文件命名、标签、链接格式
- **归档规则**：旧资料怎么处理

本 Skill 提供了一份通用模板，见 `templates/AGENTS.md`。

## 标准 Prompt 模板

### 模板 1：整理一份 raw 资料

```text
请读取 docs/project-wiki/raw/{path}。
基于其中内容：
1. 在 wiki/ 下创建一页来源总结页
2. 提炼关键概念、决策、待办
3. 如果需要，新建相关概念页或决策页
4. 为新旧页面增加交叉链接 [[...]]
5. 最后告诉我新增和更新了哪些文件
```

### 模板 2：基于 wiki 回答问题

```text
在回答之前，请先搜索 docs/project-wiki/wiki/ 中是否有相关内容。
如果有，基于 wiki 页面回答并引用页面链接；
如果没有，基于 raw/ 资料推断，但标注“待整理入 wiki”。
```

### 模板 3：月度知识库体检

```text
请对 docs/project-wiki/ 执行一次体检：
1. 列出过去 30 天新增的 raw 文件
2. 列出超过 90 天未更新的 wiki 页面
3. 找出没有 outbound/inbound links 的孤立页面
4. 找出标题或内容可能重复的页面
5. 生成一份简短报告和改进建议
```

## 文件命名建议

| 类型 | 命名示例 |
|------|----------|
| 会议纪要 | `raw/meetings/2026-06-22-okr-review.md` |
| 需求 | `raw/requirements/2026-06-22-user-auth-prd.md` |
| 调研 | `raw/research/2026-06-22-vector-db-comparison.md` |
| 决策 | `wiki/decisions/adr-026-why-duckdb.md` |
| 手册 | `wiki/runbooks/deploy-foundation-db.md` |
| 规范 | `wiki/conventions/python-import-order.md` |

## wiki 页面推荐结构

每页 wiki 笔记建议包含：

```markdown
# 页面标题

## 一句话定义

## 为什么重要

## 具体内容

## 关联页面
- [[相关概念 A]]
- [[相关决策 B]]

## 来源
- [原始资料](raw/xxx.md)
```

## 标签规范（可选，起步阶段可不加）

| 标签 | 含义 |
|------|------|
| `#decision` | 决策记录 |
| `#runbook` | 操作手册 |
| `#pattern` | 可复用模式 |
| `#concept` | 概念说明 |
| `#onboarding` | 新人相关 |
| `#raw` | 未整理原始资料 |

## 常见误区

- **误区 1**：raw 层要很整齐。→ 错，raw 可以乱，整理交给 wiki。
- **误区 2**：一次整理完所有资料。→ 错，先跑通一篇，再批量处理。
- **误区 3**：让 AI 替代自己思考。→ 错，AI 整理，人做价值判断。
- **误区 4**：只生成摘要不建链接。→ 错，没有双链的整理只完成一半。
- **误区 5**：raw 和 wiki 混放。→ 错，一旦混放，整理边界就模糊了。

## 跨电脑 / 团队共享

### 方案 A：把项目 wiki 提交进项目仓库

最简单的方式：

```bash
git add docs/project-wiki
git commit -m "add project wiki"
git push
```

任何 clone 这个项目的人都能直接打开 `docs/project-wiki/` 作为 Obsidian vault。

### 方案 B：把本 Skill 安装到全局

如果你想在所有项目都用同一套方法论：

```bash
# 从 GitHub 安装本 Skill
mkdir -p ~/.qoder/skills/obsidian-project-wiki
cd ~/.qoder/skills/obsidian-project-wiki
git clone https://github.com/jackeyunjie/obsidian-project-wiki.git .
```

> 如果你的 skillhub 仓库包含多个 Skill，建议把本 Skill 放到 `obsidian-project-wiki/` 子目录下，然后 clone 到 `~/.qoder/skills/obsidian-project-wiki/`。

### 方案 C：每个项目独立安装 Skill

把本 Skill 复制到项目仓库：

```bash
mkdir -p .qoder/skills/obsidian-project-wiki
cp -r ~/.qoder/skills/obsidian-project-wiki/* .qoder/skills/obsidian-project-wiki/
```

这样 Skill 会随项目一起提交，团队成员无需额外配置。

## 进阶用法

- **Obsidian Web Clipper**：把网页资料直接剪藏到 `raw/research/`
- **对话导出**：将 Claude/Codex/Kimi 的有价值对话保存到 `raw/conversations/`，再让 Agent 整理
- **定期体检**：每月跑一次"知识库体检" prompt，或运行 `bash scripts/check.sh` 脚本
- **模板化**：把常用的 wiki 页面结构存为 Obsidian 模板

### 推荐 Obsidian 配置

起步阶段建议使用默认设置，后续可按需安装以下插件（详见 `templates/obsidian-config.json`）：

| 插件 | 用途 |
|------|------|
| **Dataview** | 用 DQL 语言查询 vault，自动统计文件、生成索引 |
| **Templater** | 创建标准化 wiki 页面模板（来源页、ADR 页等） |
| **Calendar** | 日历视图浏览按日期组织的会议纪要 |
| **Obsidian Git** | 在 Obsidian 内直接 commit/push，方便团队同步 |

> 第一次不要急着装插件，先保证空间干净、跑通一篇整理流程。

## 验收清单

一个跑通的项目 wiki 应该满足：

- [ ] 项目仓库里有 `docs/project-wiki/`，且目录结构清晰
- [ ] 根目录有 `AGENTS.md`，Agent 能读到
- [ ] 至少有一份 raw 资料被整理成 wiki 页面
- [ ] wiki 页面有来源页、概念页和双向链接
- [ ] 能基于 wiki 回答一个项目具体问题
- [ ] 有价值的新结论被回写到 wiki

## 常见问题（FAQ）

**Q: Obsidian 找不到 vault 怎么办？**
A: 确认你打开的是 `docs/project-wiki/` 目录（而非其父目录）。在 Obsidian 中选择 **Open folder as vault** → 选择 `docs/project-wiki/`。

**Q: Git 合并冲突导致 wiki 页面损坏怎么处理？**
A: 先用 `git diff` 查看冲突标记（`<<<<<<<`），手动选择保留哪一版本。建议在 `.gitattributes` 中设置 `*.md merge=union` 让 Git 自动合并非冲突行。

**Q: 多人协作时如何避免同时编辑同一个 wiki 页面？**
A: 约定"谁整理谁负责"原则 — 每次整理前在对应 wiki 页面顶部加 `> 正在由 @xxx 编辑`，完成后移除。或使用 Obsidian Git 插件频繁 commit 减少冲突窗口。

**Q: raw 资料是 PDF/图片怎么办？**
A: Obsidian 支持内嵌 PDF 和图片。把文件放进 `raw/` 后，在 wiki 页面中用 `![[文件名.pdf]]` 引用。Agent 整理时可基于文件名和上下文描述内容。

**Q: 知识库超过 1000 页后 Obsidian 变慢怎么办？**
A: 1) 关闭不必要的插件（特别是 Graph View 的实时渲染）；2) 把已归档的 raw 文件移到 `raw/archived/` 并加入 `.gitignore`；3) 拆分大项目为多个 vault。

## 故障排查

**Agent 未遵守 AGENTS.md 约定**
→ 确认 AGENTS.md 位于 vault 根目录（Agent 会从项目根目录的 `AGENTS.md` 或 `docs/project-wiki/AGENTS.md` 读取约定）。如果 Agent 仍不遵守，在 prompt 中显式引用：`请先阅读 docs/project-wiki/AGENTS.md 中的约定，然后...`。

**双链显示为红色（目标页不存在）**
→ 在 Obsidian 中搜索该链接名，确认是文件名拼写错误还是页面确实未创建。如果是未创建的页面，可以让 Agent 补充创建，或手动创建一个带占位内容的页面。

**体检脚本报告孤立页面**
→ 运行 `bash scripts/check.sh` 后，对每个孤立页面：1) 判断它是否应该被其他页面引用；2) 添加至少一个 `[[...]]` 链接到相关页面；3) 如果页面确实独立，可添加标签 `#standalone` 标注。

## 参考资源

- 本 Skill 仓库：https://github.com/jackeyunjie/obsidian-project-wiki
- Obsidian 官方文档：https://help.obsidian.md/
- 卡片盒笔记法 / Zettelkasten 方法论
