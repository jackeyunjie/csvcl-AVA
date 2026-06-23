---
name: youtube-trading-strategy-pipeline
description: |
  从 YouTube 交易教学视频中提取中文字幕，自动生成结构化的交易策略文档：
  Obsidian 来源页 / SOP 手册 / 概念页 / SQX 模块映射，并输出可复用的 MQL5(MT5)、MQL4(MT4)、Python 代码方向。
  用于把交易视频沉淀为可回测、可执行、可连接的项目知识库。
---

# YouTube 交易策略流水线

## 这个 Skill 解决什么问题

交易教学视频看完就忘、无法落地。本 Skill 把 YouTube 视频自动转化为：

1. **原始字幕**（`raw/research/`）
2. **来源总结页**（`wiki/source-youtube-trading-sop-{index}.md`）
3. **可执行 SOP 手册**（`wiki/runbooks/trading-sop-*.md`）
4. **概念模型页**（`wiki/concepts/*.md`）
5. **SQX 模块映射**（`wiki/concepts/sqx-module-mapping-*.md`）
6. **代码方向**：MQL5 / MQL4 / Python

最终形成一套可在 StrategyQuant X、MT5、MT4、Python 中复用的交易策略资产。

## 适用场景

- 交易博主分享了一套完整策略，需要沉淀到项目知识库
- 想把视频策略转化为 SQX 可回测模块
- 需要为同一类视频建立统一的整理格式
- 希望自动生成 MT5/MT4/Python 代码实现方向

## 前置条件

- 项目根目录已有 `docs/project-wiki/` Obsidian vault（可用 [[obsidian-project-wiki]] 初始化）
- Python 3.10+ 及 `youtube-transcript-api` 可用
- 熟悉 StrategyQuant X、MT5/MT4、Python 中的至少一种

## 标准工作流程

```text
用户提供 YouTube URL + playlist index
  → 提取中文字幕
  → 读取 transcript，理解策略核心
  → 创建/更新 wiki 来源页
  → 创建/更新 SOP runbook
  → 创建/更新概念页
  → 创建/更新 SQX 模块映射
  → 输出 MQL5 / MQL4 / Python 代码方向
  → 为所有页面添加 [[...]] 交叉链接
```

## Step 1：提取字幕

使用本 Skill 提供的脚本：

```powershell
cd <project-root>
python .qoder/skills/youtube-trading-strategy-pipeline/scripts/fetch_youtube_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" INDEX
```

输出：

```text
docs/project-wiki/raw/research/YYYY-MM-DD-youtube-trading-sop-{INDEX}-transcript.txt
```

> 若 `youtube-transcript-api` 未安装，先执行：
> `python -m pip install youtube-transcript-api`

## Step 2：人工理解 + 自动生成 wiki 页

阅读 transcript 后，基于本 Skill 的模板创建以下页面：

| 页面类型 | 路径模板 | 作用 |
|----------|----------|------|
| 来源页 | `wiki/source-youtube-trading-sop-{index}.md` | 一句话定义、关键结论、来源 |
| SOP 手册 | `wiki/runbooks/trading-sop-{slug}.md` | 可执行的交易步骤、参数、纪律 |
| 概念页 | `wiki/concepts/{core-concept}.md` | 提炼可复用的交易模型 |
| SQX 映射 | `wiki/concepts/sqx-module-mapping-{slug}.md` | 指标、条件、入场、出场的 SQX 实现 |

模板位于 `templates/` 目录。

## Step 3：代码输出方向

每个 SOP 都应给出三类代码实现方向：

### MQL5 (MT5)

- EA 框架：`OnInit`, `OnTick`, `OnTrade`
- 指标调用：`iMACD`, `iRSI`, `iMA`, `iATR`, `iVolumes`
- 订单管理：`CTrade` 类
- 输出信号 CSV：`MQL4/Files` 或 `MQL5/Files`

### MQL4 (MT4)

- EA 框架：`OnInit`, `OnTick`, `start`
- 指标调用：`iMACD`, `iRSI`, `iMA`, `iATR`, `iVolumes`
- 订单管理：`OrderSend`, `OrderClose`, `OrderModify`
- 输出信号 CSV：`MQL4/Files`

### Python

- 数据源：yfinance、CCXT、akshare、tushare
- 回测框架：Backtrader、Zipline、VectorBT
- 扫描脚本：每日主题识别、龙头筛选、信号生成
- 输出：CSV / Excel（供本项目着色流程使用）

## Step 4：添加交叉链接

每个新页面底部必须包含：

```markdown
## 关联页面

- [[source-youtube-trading-sop-{index}]]
- [[trading-sop-{slug}]]
- [[{core-concept}]]
- [[sqx-module-mapping-{slug}]]
- [[sqx-module-mapping]]
```

同时更新相关旧页面，把新页面加入它们的关联列表。

## 模板使用说明

详见：

- `templates/source-page.md` — 来源页模板
- `templates/runbook-page.md` — SOP 手册模板
- `templates/concept-page.md` — 概念页模板
- `templates/sqx-mapping-page.md` — SQX 映射模板
- `references/prompt-templates.md` — 给 Agent 的标准 prompt 模板

## 与项目 CSV/Excel 流程的结合

1. SQX/MQL5/Python 生成信号 CSV
2. 本项目 `process_real_mt4_data.py` 扫描 CSV
3. 对信号列按规则着色，生成 `_colored.xlsx`
4. 生成截图与邮件报告

## 输出检查清单

- [ ] 字幕文件已保存到 `raw/research/`
- [ ] 来源页已创建并引用 transcript
- [ ] SOP 手册包含入场、出场、止损、止盈、仓位、回测要点
- [ ] 概念页提炼了可复用的交易模型
- [ ] SQX 映射拆分了指标、条件、入场、出场、过滤模块
- [ ] 给出了 MQL5 / MQL4 / Python 实现方向
- [ ] 所有页面都添加了 `[[...]]` 交叉链接
- [ ] 已更新相关旧页面的关联列表

## 关联 Skill

- [[obsidian-project-wiki]]
