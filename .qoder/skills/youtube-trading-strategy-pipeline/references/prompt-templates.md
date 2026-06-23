# Prompt 模板

## 模板 1：从视频 URL 开始完整流程

```text
请处理 YouTube 视频：
- URL：https://www.youtube.com/watch?v={VIDEO_ID}
- playlist index：{INDEX}

执行以下步骤：
1. 提取中文字幕并保存到 docs/project-wiki/raw/research/
2. 创建/更新 wiki 来源页 source-youtube-trading-sop-{INDEX}.md
3. 提炼核心交易逻辑，创建 SOP runbook
4. 提炼可复用概念，创建概念页
5. 拆解 SQX 模块映射
6. 给出 MQL5 / MQL4 / Python 实现方向
7. 为所有页面添加 [[...]] 交叉链接
8. 更新相关旧页面的关联列表
9. 报告新增和更新的文件
```

## 模板 2：已有 transcript，整理 wiki

```text
请读取 docs/project-wiki/raw/research/{transcript-filename}.txt。
基于其中内容：
1. 在 wiki/ 下创建一页来源总结页
2. 提炼核心交易逻辑，创建 SOP runbook
3. 提炼可复用概念，创建概念页
4. 创建 SQX 模块映射页
5. 给出 MQL5 / MQL4 / Python 实现方向
6. 为新旧页面增加交叉链接 [[...]]
7. 最后告诉我新增和更新了哪些文件
```

## 模板 3：从策略生成代码

```text
基于 wiki runbook [[trading-sop-{slug}]] 和 SQX 映射 [[sqx-module-mapping-{slug}]]，
生成：
1. MQL5 EA 代码框架
2. MQL4 EA 代码框架
3. Python 回测脚本框架
4. 说明如何接入本项目的 CSV/Excel 着色流程
```
