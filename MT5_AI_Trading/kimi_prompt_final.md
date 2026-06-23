# KIMI 最终工作指令（已验证）

## 管道状态：已验证通过

SEC EDGAR 数据源可用，29/31只股票拉取成功。

## 执行命令

### 首次运行（合并数据）
```bash
cd "d:\qoder\csvcl - AVA\MT5_AI_Trading"
python load_enriched_data.py
```

### 后续运行（增量更新）
```bash
python python/data/fundamental_pipeline.py --force
```

### 策略分析
```bash
python python/strategies/fundamental_strategy.py --analyze-all
```

## 预期结果

数据拉取：29/31 成功（AMZN/GS 可能失败）
策略信号：BUY/SELL/REDUCE 列表

## 参考文件
- `load_enriched_data.py` - 合并数据加载器（种子估值 + SEC 财报）
- `python/data/sec_edgar_fetcher.py` - SEC EDGAR 拉取器
- `python/data/fundamental_pipeline.py` - 主管道
- `python/strategies/fundamental_strategy.py` - 策略引擎
