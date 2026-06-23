# obsidian-project-wiki

> 为任意项目搭建 Obsidian + AI 的“会进化”的项目知识库。

## 一句话说明

通过 `raw/`（原始资料）+ `wiki/`（整理知识）+ `AGENTS.md`（Agent 约定）三层结构，让项目决策、操作手册、架构知识随使用自然沉淀，可被团队复用。

## 适用场景

- 软件项目需要集中管理会议纪要、需求、决策、手册
- 团队希望把 AI 对话、调研资料沉淀为可复用知识
- 个人想用 Obsidian 管理多个项目知识

## 快速安装

### 一键安装（推荐）

```bash
# 克隆本仓库
git clone https://github.com/jackeyunjie/obsidian-project-wiki.git
cd obsidian-project-wiki

# 运行安装脚本，自动创建目录结构并填充项目名
bash scripts/install.sh --project-name your-project-name
```

安装脚本会自动创建 `docs/project-wiki/` 下的所有目录，复制模板文件并替换项目名占位符。

### 项目级使用（手动）

把本 Skill 复制到项目仓库：

```bash
mkdir -p .qoder/skills/obsidian-project-wiki
cp -r /path/to/obsidian-project-wiki/* .qoder/skills/obsidian-project-wiki/
```

然后初始化项目 wiki：

```bash
bash .qoder/skills/obsidian-project-wiki/scripts/install.sh --project-name your-project-name
```

### 全局使用

```bash
bash scripts/install.sh --global
```

Skill 将安装到 `~/.qoder/skills/obsidian-project-wiki`，之后可在任意项目中使用。

### 从 GitHub 安装

```bash
mkdir -p ~/.qoder/skills/obsidian-project-wiki
cd ~/.qoder/skills/obsidian-project-wiki
git clone https://github.com/jackeyunjie/obsidian-project-wiki.git .
```

## 文件结构

```text
obsidian-project-wiki/
├── SKILL.md              # Skill 主文件
├── README.md             # 本文件
├── LICENSE               # MIT License
├── _meta.json            # Skill 元数据
├── scripts/
│   ├── install.sh        # 一键初始化脚本
│   └── check.sh          # 知识库体检脚本
├── templates/
│   ├── AGENTS.md         # 项目级 Agent 约定模板
│   ├── README.md         # 项目 wiki README 模板
│   ├── prompts.md        # 标准 Prompt 模板
│   └── obsidian-config.json  # Obsidian 推荐配置
└── examples/
    └── sample-vault/     # 可直接打开的示例知识库
        ├── raw/           # 示例原始资料
        └── wiki/          # 示例整理后的知识
```

## 核心工作流

```text
raw/（原始资料）
  → Agent 整理
  → wiki/（可复用知识页）
  → 基于 wiki 回答问题
  → 好回答再回写 wiki
```

## 更多信息

详见 `SKILL.md`。

## 示例体验

本仓库包含一个可直接打开的示例 vault，展示 raw → wiki 的完整整理效果：

1. 用 Obsidian 打开 `examples/sample-vault/` 作为 vault
2. 浏览 `raw/meetings/` 中的原始会议纪要
3. 查看 `wiki/` 中整理后的来源页、决策页、架构页
4. 观察页面之间的 `[[...]]` 双向链接

## 知识库体检

使用内置体检脚本检查知识库健康状态：

```bash
bash scripts/check.sh docs/project-wiki
```

脚本会检查目录结构完整性、过期文件、孤立页面、重复文件名等，并输出结构化报告。

## License

MIT
