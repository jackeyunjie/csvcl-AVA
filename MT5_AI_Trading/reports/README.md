# MT5 每日报告

生成类似“今天先看这几个方向”的普通投资者观察版 HTML 报告。

## 生成示例报告

```powershell
cd MT5_AI_Trading
python .\python\daily_report\generate_report.py --input .\examples\daily_report_snapshot.json
```

默认输出到：

```text
MT5_AI_Trading\reports\daily\mt5_daily_report_YYYYMMDD.html
```

也可以不传 `--input`，直接用内置示例数据预览版式：

```powershell
python .\python\daily_report\generate_report.py
```

## 输入数据格式

最小可用字段：

```json
{
  "date": "2026-05-17",
  "total_products": 18,
  "account": {"equity": 10042.8},
  "risk_metrics": {
    "current_drawdown": 0.012,
    "max_drawdown": 0.047,
    "win_rate": 0.56,
    "profit_factor": 1.38
  },
  "watchlist": [
    {
      "symbol": "XAUUSD",
      "name": "黄金",
      "theme": "贵金属",
      "state": "趋势 / 风险 / 信号同向",
      "price": 2385.42,
      "spread": 18,
      "confidence": 0.72,
      "tags": ["避险资产", "强趋势"],
      "note": "黄金进入多层观察状态，适合先看避险方向是否延续。"
    }
  ]
}
```

后续可以把 `TradingMonitor.get_status_report()`、信号历史、持仓和最新 tick 合并成这个 JSON，再定时生成日报。
