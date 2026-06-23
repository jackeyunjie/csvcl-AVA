"""
State Hex 自主回测平台

五层架构:
- 数据层 (data_layer): MT5数据提取 + DuckDB本地存储
- 计算层 (compute_layer): State Hex + MISS融合引擎
- 策略层 (strategy_layer): 策略注册与执行
- 执行层 (execution_layer): 模拟撮合与绩效统计
- 展示层 (presentation_layer): 报告生成与可视化

核心原则:
- 最小分析单元: 三元组(MN1, W1, D1)
- Price State 决定观察环境
- 资金流/筹码只做二级确认
"""

__version__ = "1.0.0"
