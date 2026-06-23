"""
周五下跌特征分析：GOLD / GER40 / NAS100
数据窗口：过去3天（周三至周五）
视角：H1 + M15
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from python.backtest_platform.data_layer import MT5DataBridge
from python.analytics.squeeze_observer import SqueezeObserver

# 品种映射 (MT5内部名称)
SYMBOLS = {
    "GOLD": "GOLD",
    "GER40": "GERMANY_40", 
    "NAS100": "US_TECH100"
}

# 过去3天
end = datetime.now()
start = end - timedelta(days=3)

print(f"数据窗口: {start.strftime('%Y-%m-%d %H:%M')} ~ {end.strftime('%Y-%m-%d %H:%M')}")
print("=" * 60)

bridge = MT5DataBridge()
if not bridge.connect():
    print("MT5连接失败")
    sys.exit(1)

results = {}

for name, mt5_symbol in SYMBOLS.items():
    print(f"\n{'='*60}")
    print(f"分析 {name} ({mt5_symbol})")
    print('='*60)
    
    results[name] = {}
    
    for tf in ["H1", "M15"]:
        print(f"\n--- {tf} 视角 ---")
        df = bridge.fetch_ohlcv(mt5_symbol, tf, start, end)
        
        if df.empty:
            print(f"  无数据")
            continue
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print(f"  数据条数: {len(df)}")
        print(f"  时间范围: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
        
        # 计算指标
        df['bb_width'] = SqueezeObserver.compute_bb_width(df['close'])
        df['sr_range'] = SqueezeObserver.compute_sr_range(df['high'], df['low'], df['close'])
        df['adx'] = SqueezeObserver.compute_adx(df['high'], df['low'], df['close'])
        
        # 价格变化
        df['return_pct'] = df['close'].pct_change() * 100
        
        # 周五数据筛选（假设今天是周五或最近一个周五）
        df['dayofweek'] = df['timestamp'].dt.dayofweek  # 4=Friday
        df['hour'] = df['timestamp'].dt.hour
        friday_df = df[df['dayofweek'] == 4].copy()
        
        print(f"  周五数据条数: {len(friday_df)}")
        if len(friday_df) > 0:
            friday_return = (friday_df['close'].iloc[-1] / friday_df['close'].iloc[0] - 1) * 100
            print(f"  周五涨跌幅: {friday_return:.2f}%")
        
        # 过去3天整体变化
        total_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
        print(f"  3天总涨跌幅: {total_return:.2f}%")
        
        # ADX统计
        print(f"  ADX均值: {df['adx'].mean():.1f}")
        print(f"  ADX最小值: {df['adx'].min():.1f}")
        print(f"  ADX<20占比: {(df['adx'] < 20).mean()*100:.1f}%")
        print(f"  ADX<15占比: {(df['adx'] < 15).mean()*100:.1f}%")
        print(f"  ADX<12占比: {(df['adx'] < 12).mean()*100:.1f}%")
        
        # 收缩指标（用过去3天的分位数，因为数据量小）
        if len(df) >= 20:
            bb_20 = df['bb_width'].quantile(0.20)
            sr_20 = df['sr_range'].quantile(0.20)
            
            df['bb_squeeze'] = df['bb_width'] <= bb_20
            df['sr_squeeze'] = df['sr_range'] <= sr_20
            df['adx_lt_20'] = df['adx'] < 20
            df['adx_lt_15'] = df['adx'] < 15
            df['adx_lt_12'] = df['adx'] < 12
            
            # 5分制squeeze_score
            df['squeeze_score'] = (
                df['bb_squeeze'].astype(int) +
                df['sr_squeeze'].astype(int) +
                df['adx_lt_20'].astype(int) +
                df['adx_lt_15'].astype(int) +
                df['adx_lt_12'].astype(int)
            )
            
            print(f"  BB收缩占比: {df['bb_squeeze'].mean()*100:.1f}%")
            print(f"  SR收缩占比: {df['sr_squeeze'].mean()*100:.1f}%")
            print(f"  squeeze_score分布:")
            for score in range(6):
                pct = (df['squeeze_score'] == score).mean() * 100
                print(f"    ={score}: {pct:.1f}%")
            print(f"  density(≥3): {(df['squeeze_score'] >= 3).mean()*100:.1f}%")
            
            # 周五的squeeze情况
            if len(friday_df) > 0:
                friday_df['squeeze_score'] = df.loc[df['dayofweek'] == 4, 'squeeze_score'].values
                print(f"  周五squeeze_score分布:")
                for score in range(6):
                    pct = (friday_df['squeeze_score'] == score).mean() * 100
                    print(f"    ={score}: {pct:.1f}%")
        
        results[name][tf] = {
            'df': df,
            'friday_df': friday_df,
            'total_return': total_return,
        }

bridge.disconnect()

print("\n" + "=" * 60)
print("分析完成")
print("=" * 60)
