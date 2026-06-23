"""测试五元组计算 - 使用模拟数据"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "python"))

from ai_engine.state_hex_engine import StateHexEngine
from data.h1_state_db import H1StateDB


def generate_ohlcv(n: int, base_price: float, volatility: float, start: datetime, freq_hours: int):
    """生成模拟 OHLCV 数据"""
    np.random.seed(42)
    data = []
    price = base_price
    for i in range(n):
        ts = start + timedelta(hours=i * freq_hours)
        change = np.random.randn() * volatility
        price += change
        high = price + abs(np.random.randn() * volatility * 0.5)
        low = price - abs(np.random.randn() * volatility * 0.5)
        open_p = price + np.random.randn() * volatility * 0.2
        data.append({
            'timestamp': ts,
            'open': open_p,
            'high': high,
            'low': low,
            'close': price,
            'volume': np.random.randint(1000, 10000),
        })
    return pd.DataFrame(data)


def test_quintuplet():
    print("=" * 60)
    print("五元组计算测试")
    print("=" * 60)

    # 生成 5 个周期的模拟数据
    base = datetime(2025, 1, 1)

    # MN1: 12 根月线
    mn1_df = generate_ohlcv(12, 1.0850, 0.005, base, 24 * 30)
    # W1: 52 根周线
    w1_df = generate_ohlcv(52, 1.0850, 0.003, base, 24 * 7)
    # D1: 250 根日线
    d1_df = generate_ohlcv(250, 1.0850, 0.002, base, 24)
    # H4: 1500 根 4 小时线
    h4_df = generate_ohlcv(1500, 1.0850, 0.001, base, 4)
    # H1: 6000 根 1 小时线
    h1_df = generate_ohlcv(6000, 1.0850, 0.0005, base, 1)

    print(f"\n数据量:")
    print(f"  MN1: {len(mn1_df)} 条")
    print(f"  W1:  {len(w1_df)} 条")
    print(f"  D1:  {len(d1_df)} 条")
    print(f"  H4:  {len(h4_df)} 条")
    print(f"  H1:  {len(h1_df)} 条")

    # 初始化 H1 视角 Agent（5 个结构周期）
    engine = StateHexEngine()

    print("\n加载数据（H1 视角 Agent 的 5 个结构周期）...")
    engine.add_mn1_dataframe(mn1_df)
    engine.add_w1_dataframe(w1_df)
    engine.add_d1_dataframe(d1_df)
    engine.add_h4_dataframe(h4_df)
    engine.add_h1_dataframe(h1_df)

    print("计算五元组...")
    quintuplets = engine.compute_quintuplets()
    print(f"五元组数量: {len(quintuplets)}")

    # 显示前 10 条
    print("\n前 10 条五元组:")
    print(f"{'timestamp':<22} {'MN1':>4} {'W1':>4} {'D1':>4} {'H4':>4} {'H1':>4}")
    print("-" * 50)
    for q in quintuplets[:10]:
        print(f"{q.timestamp.strftime('%Y-%m-%d %H:%M'):<22} {q.mn1_hex:>4} {q.w1_hex:>4} {q.d1_hex:>4} {q.h4_hex:>4} {q.h1_hex:>4}")

    # 显示最后 10 条
    print(f"\n最后 10 条五元组:")
    print(f"{'timestamp':<22} {'MN1':>4} {'W1':>4} {'D1':>4} {'H4':>4} {'H1':>4}")
    print("-" * 50)
    for q in quintuplets[-10:]:
        print(f"{q.timestamp.strftime('%Y-%m-%d %H:%M'):<22} {q.mn1_hex:>4} {q.w1_hex:>4} {q.d1_hex:>4} {q.h4_hex:>4} {q.h1_hex:>4}")

    # 测试数据库存储
    print("\n\n测试 DuckDB 存储...")
    db_path = "data/test_h1_state.duckdb"
    h1db = H1StateDB(db_path)
    saved = h1db.save_quintuplets("EURUSD", quintuplets)
    print(f"保存: {saved} 条")

    # 查询
    df = h1db.query("EURUSD", limit=5)
    print(f"\n查询结果 (最新 5 条):")
    print(df.to_string(index=False))

    # 摘要
    summary = h1db.get_summary("EURUSD")
    print(f"\n摘要: total={summary['total_rows']}, "
          f"earliest={summary['earliest']}, latest={summary['latest']}")

    h1db.close()

    # 清理测试数据库
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"\n已清理测试数据库: {db_path}")

    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    test_quintuplet()
