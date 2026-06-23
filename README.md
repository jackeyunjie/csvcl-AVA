# csvcl-AVA · MT4/CSV 数据自动处理系统

[![CI](https://github.com/jackeyunjie/csvcl-AVA/actions/workflows/ci.yml/badge.svg)](https://github.com/jackeyunjie/csvcl-AVA/actions/workflows/ci.yml)

本项目用于扫描 MT4 `MQL4/Files` 目录下最新生成的 CSV 数据文件，按规则进行着色的 Excel 报告、生成截图、识别关键状态变化，并在指定时段自动发送邮件报告。同时包含将 YouTube / MQL5 交易研究资料沉淀到 Obsidian wiki 的辅助流水线。

## 🎯 核心功能

- 📊 **智能数据筛选**：按文件名模式与时间窗口扫描 CSV。
- 🎨 **颜色标记**：对状态码/指标列按规则着色（红、淡红、绿、淡绿、黄）。
- 📸 **高清截图**：生成指定范围的表格截图（JPG）。
- 📧 **自动邮件**：7:00–22:00 时段自动发送处理结果与截图。
- 📈 **机会识别**：监控状态值从非重要值变为 `2 / -2 / 6 / -6` 的触发信号。
- 🎬 **研究沉淀**：下载 YouTube 字幕、MQL5 文章并写入 Obsidian wiki。

> ⚠️ **风险提示**：`state_hex` 为状态体检码，不是买卖指令。H1 级别信号噪音大，请结合更高周期与策略验证。

## 🚀 快速开始

### 1. 克隆与安装依赖

```bash
git clone https://github.com/jackeyunjie/csvcl-AVA.git
cd csvcl-AVA
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，至少填写 MT4_FILES_PATH 与邮箱信息
```

`.env` 已被 `.gitignore` 排除，不会误提交。

### 3. 运行

```bash
# 手动处理模式
python process_real_mt4_data.py

# 自动邮件模式（7:00-22:00 发送）
python auto_email_config.py

# 仅生成着色 Excel
python csv_color_marker.py
```

## ⚙️ 配置说明

### 环境变量（推荐）

| 变量 | 说明 | 示例 |
|------|------|------|
| `MT4_FILES_PATH` | MT4 `MQL4/Files` 目录 | `C:\Users\...\MQL4\Files` |
| `EMAIL_RECIPIENTS` | 收件人，逗号分隔 | `a@qq.com,b@qq.com` |
| `EMAIL_USERNAME` | SMTP 发件邮箱 | `your_email@qq.com` |
| `EMAIL_PASSWORD` | 邮箱授权码/密码 | - |
| `WIKI_RESEARCH_DIR` | 研究资料输出目录 | `docs/project-wiki/raw/research` |

### 配置文件

- `configs/mt4_config.yaml` — 文件筛选、颜色规则、截图范围、收件人等兜底配置。
- `email_config.ini` — SMTP 详细配置（从 `email_config.ini.template` 复制）。

配置优先级：**环境变量 > YAML 配置 > 代码默认值**。

## 🎨 颜色规则

| 颜色 | 数值 |
|------|------|
| 🔴 红色背景 | 2, 3, 4, 5, 6, 7 |
| 🌸 淡红色背景 | 10, 11, 12, 13, 14, 15 |
| 🟢 绿色背景 | -2, -3, -4, -5, -6, -7 |
| 🍃 淡绿色背景 | -10, -11, -12, -13, -14, -15 |
| 🟡 黄色背景 | 8 |

默认处理区域：日线状态文件为 `E2:G40`（MN1/W1/D1）；H1 状态文件为 `I2:M43`。

## 📁 项目结构

```
csvcl-AVA/
├── .github/workflows/ci.yml   # GitHub Actions CI
├── configs/                    # YAML 配置模板
├── core/                       # 配置/环境变量助手
├── docs/project-wiki/          # Obsidian wiki（raw + wiki）
├── tests/                      # 单元测试
├── csv_color_marker.py         # CSV → 着色 Excel
├── process_real_mt4_data.py    # 完整 MT4 处理流程
├── auto_email_config.py        # 自动邮件调度入口
├── email_sender.py             # 邮件发送模块
├── run_mt4_marker.py           # 简化入口
├── yt_transcript_fetcher.py    # YouTube 字幕下载
├── run_tests.py                # 统一测试入口
├── requirements.txt
├── .env.example
└── README.md
```

## 🧪 测试

```bash
python run_tests.py
```

`run_tests.py` 仅执行 `tests/` 下的单元测试，不会触发需要真实 MT4 数据、邮箱或外部网络请求的脚本。

## 🛡️ 安全与注意事项

1. **敏感信息**：`email_config.ini`、`.env`、授权码等不要提交到仓库。
2. **时区**：KVB 平台时间比北京时间快 6 小时。CSV `TIME` 列为平台时间，文件名/文件系统时间通常为北京时间，处理时请统一换算。
3. **Windows 路径**：所有硬编码的 MT4/QQ 路径已抽离到 `.env` / `configs/mt4_config.yaml`，运行前请务必填写实际路径。

## 📦 主要依赖

- Python 3.11+
- pandas, openpyxl, Pillow, numpy
- schedule, pyyaml, python-dotenv
- matplotlib, plotly
- requests, beautifulsoup4, markdownify, youtube-transcript-api
- pytest（测试）

完整列表见 [`requirements.txt`](requirements.txt)。

## 📞 支持

如遇问题，请检查：

1. Python 版本是否为 3.11+。
2. `pip install -r requirements.txt` 是否成功。
3. `.env` 或 `email_config.ini` 是否配置正确。
4. MT4 是否正在运行并生成数据。

---

💡 **提示**：本项目为交易数据处理工具，输出结果仅供参考，不构成投资建议。
