# Obsidian Project Wiki 标准 Prompt

## 1. 整理一份 raw 资料

```text
请读取 docs/project-wiki/raw/{path}。
基于其中内容：
1. 在 wiki/ 下创建一页来源总结页
2. 提炼关键概念、决策、待办
3. 如果需要，新建相关概念页或决策页
4. 为新旧页面增加交叉链接 [[...]]
5. 最后告诉我新增和更新了哪些文件
```

## 2. 基于 wiki 回答问题

```text
在回答之前，请先搜索 docs/project-wiki/wiki/ 中是否有相关内容。
如果有，基于 wiki 页面回答并引用页面链接；
如果没有，基于 raw/ 资料推断，但标注“待整理入 wiki”。
```

## 3. 月度知识库体检

```text
请对 docs/project-wiki/ 执行一次体检：
1. 列出过去 30 天新增的 raw 文件
2. 列出超过 90 天未更新的 wiki 页面
3. 找出没有 outbound/inbound links 的孤立页面
4. 找出标题或内容可能重复的页面
5. 生成一份简短报告和改进建议
```

## 4. 新人 onboarding 生成

```text
基于 docs/project-wiki/wiki/ 的内容，生成一份新人 onboarding 指南：
1. 项目目标与核心概念
2. 必读 wiki 页面清单
3. 常见操作对应的 runbook
4. 最近的重要决策
5. 需要进一步补充的内容
```

## 5. 决策记录生成

```text
请把 docs/project-wiki/raw/{path} 中的决策整理成 ADR：
1. 标题与编号
2. 背景
3. 考虑的选项
4. 最终决策与理由
5. 影响范围
6. 相关链接

输出到 wiki/decisions/adr-{编号}-{slug}.md
```
