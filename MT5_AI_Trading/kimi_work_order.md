# KIMI 工作指令 - 基本面数据管道

## 你的角色
你是数据工程师，负责拉取美股基本面数据并生成分析报告。
所有文件位于 `d:\qoder\csvcl - AVA\MT5_AI_Trading\`

## 数据源架构
- **主数据源**: SEC EDGAR（官方，免费，10次/秒）
- **备用数据源**: yfinance（实时价格/PE/PB）
- **宏观数据**: FRED API 或 yfinance ^TNX/^VIX

## 任务清单

### 任务1: 数据拉取（每次必做）
```bash
cd "d:\qoder\csvcl - AVA\MT5_AI_Trading"
python python/data/fundamental_pipeline.py --force
```

**成功标准**：输出 "个股基本面更新完成: X/30 条"

**数据源优先级**：
1. SEC EDGAR → 营收、净利润、负债率、流动比率
2. yfinance 备用 → PE、PB、市值、实时价格

### 任务2: 数据验证
```python
import duckdb
conn = duckdb.connect("data/fundamental_duckdb.db")
# 检查个股数据
eq = conn.execute("SELECT COUNT(*), COUNT(DISTINCT symbol) FROM equity_fundamentals").fetchone()
print(f"总记录: {eq[0]}, 股票数: {eq[1]}/30")
# 检查宏观数据
macro = conn.execute("SELECT COUNT(*), MAX(date) FROM macro_indicators").fetchone()
print(f"宏观记录: {macro[0]}, 最新日期: {macro[1]}")
# 检查数据质量
null_check = conn.execute("""
    SELECT symbol, pe, pb, market_cap
    FROM equity_fundamentals
    WHERE date = (SELECT MAX(date) FROM equity_fundamentals)
    AND (pe IS NULL OR pb IS NULL OR market_cap IS NULL)
""").fetchdf()
if not null_check.empty:
    print(f"警告: {len(null_check)} 只股票缺少关键数据")
    print(null_check)
conn.close()
```

### 任务3: 策略分析
```bash
python python/strategies/fundamental_strategy.py --analyze-all
```
- 记录所有 BUY 和 SELL 信号
- 输出格式：
  ```
  BUY信号: AAPL(score=75), MSFT(score=68)...
  SELL信号: TSLA(score=25)...
  ```

### 任务4: 生成报告
将以上结果整理为简洁报告，包含：
1. 数据更新状态（成功/失败/部分）
2. 数据来源统计（SEC EDGAR X条，yfinance Y条）
3. 数据质量（空值情况）
4. 交易信号（按score排序）
5. 异常告警（如某只股票连续拉取失败）

## 注意事项
- 遇到错误先记录，不要修改源代码
- SEC EDGAR 限流时：等待1秒后重试（10次/秒）
- yfinance 限流时：等待60秒后重试
- 每次运行结果保存到 `logs/kimi_run_YYYYMMDD.log`

## 文件清单
| 文件 | 用途 |
|------|------|
| `python/data/sec_edgar_fetcher.py` | SEC EDGAR 数据拉取器 |
| `python/data/fundamental_pipeline.py` | 主管道（多数据源） |
| `python/strategies/fundamental_strategy.py` | 策略引擎 |
| `test_sec_edgar.py` | SEC EDGAR 测试脚本 |
