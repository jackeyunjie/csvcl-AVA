"""
保存本次关键三天观察到数据库

数据来源: three_day_observation.py 输出
观察周期: 2026-06-03 至 2026-06-05（非农前3天）
"""

import sys
sys.path.insert(0, '.')

from observation_db import save_current_observation, init_db

# ========================================================================
# 本次观察数据（2026-06-03 至 2026-06-05）
# ========================================================================

OBSERVATION_DATA = {
    'start_date': '2026-06-03',
    'end_date': '2026-06-05',
    'context': '非农前3天关键观察：周四集中收缩，周五DXY与US30同步收缩，M15多品种拉出横线',
    
    # 每日收缩特征
    'profiles': [
        # === H1视角 ===
        # XAUUSD
        {'symbol': 'XAUUSD', 'timeframe': 'H1', 'date': '2026-06-03', 'total_bars': 21, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'XAUUSD', 'timeframe': 'H1', 'date': '2026-06-04', 'total_bars': 23, 'contraction_bars': 4, 'contraction_pct': 17.4, 'transitions': 0},
        {'symbol': 'XAUUSD', 'timeframe': 'H1', 'date': '2026-06-05', 'total_bars': 21, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        # XAGUSD
        {'symbol': 'XAGUSD', 'timeframe': 'H1', 'date': '2026-06-03', 'total_bars': 21, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'XAGUSD', 'timeframe': 'H1', 'date': '2026-06-04', 'total_bars': 23, 'contraction_bars': 5, 'contraction_pct': 21.7, 'transitions': 0},
        {'symbol': 'XAGUSD', 'timeframe': 'H1', 'date': '2026-06-05', 'total_bars': 21, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        # EURUSD
        {'symbol': 'EURUSD', 'timeframe': 'H1', 'date': '2026-06-03', 'total_bars': 22, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'EURUSD', 'timeframe': 'H1', 'date': '2026-06-04', 'total_bars': 24, 'contraction_bars': 4, 'contraction_pct': 16.7, 'transitions': 0},
        {'symbol': 'EURUSD', 'timeframe': 'H1', 'date': '2026-06-05', 'total_bars': 21, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        # GBPUSD
        {'symbol': 'GBPUSD', 'timeframe': 'H1', 'date': '2026-06-03', 'total_bars': 22, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'GBPUSD', 'timeframe': 'H1', 'date': '2026-06-04', 'total_bars': 24, 'contraction_bars': 8, 'contraction_pct': 33.3, 'transitions': 0},
        {'symbol': 'GBPUSD', 'timeframe': 'H1', 'date': '2026-06-05', 'total_bars': 21, 'contraction_bars': 3, 'contraction_pct': 14.3, 'transitions': 0},
        # USDJPY
        {'symbol': 'USDJPY', 'timeframe': 'H1', 'date': '2026-06-03', 'total_bars': 22, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'USDJPY', 'timeframe': 'H1', 'date': '2026-06-04', 'total_bars': 24, 'contraction_bars': 3, 'contraction_pct': 12.5, 'transitions': 0},
        {'symbol': 'USDJPY', 'timeframe': 'H1', 'date': '2026-06-05', 'total_bars': 21, 'contraction_bars': 3, 'contraction_pct': 14.3, 'transitions': 0},
        # US30
        {'symbol': 'US30', 'timeframe': 'H1', 'date': '2026-06-03', 'total_bars': 21, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'US30', 'timeframe': 'H1', 'date': '2026-06-04', 'total_bars': 23, 'contraction_bars': 3, 'contraction_pct': 13.0, 'transitions': 0},
        {'symbol': 'US30', 'timeframe': 'H1', 'date': '2026-06-05', 'total_bars': 21, 'contraction_bars': 11, 'contraction_pct': 52.4, 'transitions': 0},
        # NAS100
        {'symbol': 'NAS100', 'timeframe': 'H1', 'date': '2026-06-03', 'total_bars': 21, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'NAS100', 'timeframe': 'H1', 'date': '2026-06-04', 'total_bars': 23, 'contraction_bars': 3, 'contraction_pct': 13.0, 'transitions': 0},
        {'symbol': 'NAS100', 'timeframe': 'H1', 'date': '2026-06-05', 'total_bars': 21, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        # GER40
        {'symbol': 'GER40', 'timeframe': 'H1', 'date': '2026-06-03', 'total_bars': 18, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'GER40', 'timeframe': 'H1', 'date': '2026-06-04', 'total_bars': 20, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'GER40', 'timeframe': 'H1', 'date': '2026-06-05', 'total_bars': 20, 'contraction_bars': 4, 'contraction_pct': 20.0, 'transitions': 0},
        # DXY
        {'symbol': 'DXY', 'timeframe': 'H1', 'date': '2026-06-03', 'total_bars': 19, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'DXY', 'timeframe': 'H1', 'date': '2026-06-04', 'total_bars': 21, 'contraction_bars': 1, 'contraction_pct': 4.8, 'transitions': 0},
        {'symbol': 'DXY', 'timeframe': 'H1', 'date': '2026-06-05', 'total_bars': 21, 'contraction_bars': 5, 'contraction_pct': 23.8, 'transitions': 0},
        
        # === M15视角 ===
        {'symbol': 'XAUUSD', 'timeframe': 'M15', 'date': '2026-06-03', 'total_bars': 96, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'XAUUSD', 'timeframe': 'M15', 'date': '2026-06-04', 'total_bars': 92, 'contraction_bars': 68, 'contraction_pct': 73.9, 'transitions': 0},
        {'symbol': 'XAUUSD', 'timeframe': 'M15', 'date': '2026-06-05', 'total_bars': 53, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'EURUSD', 'timeframe': 'M15', 'date': '2026-06-03', 'total_bars': 96, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'EURUSD', 'timeframe': 'M15', 'date': '2026-06-04', 'total_bars': 96, 'contraction_bars': 83, 'contraction_pct': 86.5, 'transitions': 0},
        {'symbol': 'EURUSD', 'timeframe': 'M15', 'date': '2026-06-05', 'total_bars': 57, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'USDJPY', 'timeframe': 'M15', 'date': '2026-06-03', 'total_bars': 96, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'USDJPY', 'timeframe': 'M15', 'date': '2026-06-04', 'total_bars': 96, 'contraction_bars': 79, 'contraction_pct': 82.3, 'transitions': 0},
        {'symbol': 'USDJPY', 'timeframe': 'M15', 'date': '2026-06-05', 'total_bars': 57, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'GBPUSD', 'timeframe': 'M15', 'date': '2026-06-03', 'total_bars': 96, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'GBPUSD', 'timeframe': 'M15', 'date': '2026-06-04', 'total_bars': 96, 'contraction_bars': 64, 'contraction_pct': 66.7, 'transitions': 0},
        {'symbol': 'GBPUSD', 'timeframe': 'M15', 'date': '2026-06-05', 'total_bars': 57, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'US30', 'timeframe': 'M15', 'date': '2026-06-03', 'total_bars': 96, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'US30', 'timeframe': 'M15', 'date': '2026-06-04', 'total_bars': 92, 'contraction_bars': 45, 'contraction_pct': 48.9, 'transitions': 0},
        {'symbol': 'US30', 'timeframe': 'M15', 'date': '2026-06-05', 'total_bars': 53, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'NAS100', 'timeframe': 'M15', 'date': '2026-06-03', 'total_bars': 96, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'NAS100', 'timeframe': 'M15', 'date': '2026-06-04', 'total_bars': 92, 'contraction_bars': 32, 'contraction_pct': 34.8, 'transitions': 0},
        {'symbol': 'NAS100', 'timeframe': 'M15', 'date': '2026-06-05', 'total_bars': 53, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'GER40', 'timeframe': 'M15', 'date': '2026-06-03', 'total_bars': 84, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'GER40', 'timeframe': 'M15', 'date': '2026-06-04', 'total_bars': 84, 'contraction_bars': 29, 'contraction_pct': 34.5, 'transitions': 0},
        {'symbol': 'GER40', 'timeframe': 'M15', 'date': '2026-06-05', 'total_bars': 43, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'XAGUSD', 'timeframe': 'M15', 'date': '2026-06-03', 'total_bars': 96, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'XAGUSD', 'timeframe': 'M15', 'date': '2026-06-04', 'total_bars': 92, 'contraction_bars': 55, 'contraction_pct': 59.8, 'transitions': 0},
        {'symbol': 'XAGUSD', 'timeframe': 'M15', 'date': '2026-06-05', 'total_bars': 53, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'DXY', 'timeframe': 'M15', 'date': '2026-06-03', 'total_bars': 84, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
        {'symbol': 'DXY', 'timeframe': 'M15', 'date': '2026-06-04', 'total_bars': 84, 'contraction_bars': 59, 'contraction_pct': 70.2, 'transitions': 0},
        {'symbol': 'DXY', 'timeframe': 'M15', 'date': '2026-06-05', 'total_bars': 57, 'contraction_bars': 0, 'contraction_pct': 0.0, 'transitions': 0},
    ],
    
    # 品种收缩签名
    'signatures': [
        # H1签名
        {'symbol': 'XAUUSD', 'timeframe': 'H1', 'total_bars': 65, 'total_contraction_bars': 4, 
         'overall_contraction_pct': 6.2, 'total_transitions': 0, 
         'daily_pattern': '0,17.4,0', 'max_daily_pct': 17.4, 'min_daily_pct': 0.0, 'std_daily_pct': 10.0},
        {'symbol': 'GBPUSD', 'timeframe': 'H1', 'total_bars': 67, 'total_contraction_bars': 11, 
         'overall_contraction_pct': 16.4, 'total_transitions': 0, 
         'daily_pattern': '0,33.3,14.3', 'max_daily_pct': 33.3, 'min_daily_pct': 0.0, 'std_daily_pct': 18.0},
        {'symbol': 'US30', 'timeframe': 'H1', 'total_bars': 65, 'total_contraction_bars': 14, 
         'overall_contraction_pct': 21.5, 'total_transitions': 0, 
         'daily_pattern': '0,13.0,52.4', 'max_daily_pct': 52.4, 'min_daily_pct': 0.0, 'std_daily_pct': 28.0},
        {'symbol': 'DXY', 'timeframe': 'H1', 'total_bars': 61, 'total_contraction_bars': 6, 
         'overall_contraction_pct': 9.8, 'total_transitions': 0, 
         'daily_pattern': '0,4.8,23.8', 'max_daily_pct': 23.8, 'min_daily_pct': 0.0, 'std_daily_pct': 12.0},
        # M15签名（关键：周四拉出横线）
        {'symbol': 'EURUSD', 'timeframe': 'M15', 'total_bars': 249, 'total_contraction_bars': 83, 
         'overall_contraction_pct': 33.3, 'total_transitions': 0, 
         'daily_pattern': '0,86.5,0', 'max_daily_pct': 86.5, 'min_daily_pct': 0.0, 'std_daily_pct': 49.9,
         'threshold': 80.0},  # 高阈值，因为86.5%非常极端
        {'symbol': 'USDJPY', 'timeframe': 'M15', 'total_bars': 249, 'total_contraction_bars': 79, 
         'overall_contraction_pct': 31.7, 'total_transitions': 0, 
         'daily_pattern': '0,82.3,0', 'max_daily_pct': 82.3, 'min_daily_pct': 0.0, 'std_daily_pct': 47.5,
         'threshold': 80.0},
        {'symbol': 'XAUUSD', 'timeframe': 'M15', 'total_bars': 241, 'total_contraction_bars': 68, 
         'overall_contraction_pct': 28.2, 'total_transitions': 0, 
         'daily_pattern': '0,73.9,0', 'max_daily_pct': 73.9, 'min_daily_pct': 0.0, 'std_daily_pct': 42.7,
         'threshold': 70.0},
        {'symbol': 'GBPUSD', 'timeframe': 'M15', 'total_bars': 249, 'total_contraction_bars': 64, 
         'overall_contraction_pct': 25.7, 'total_transitions': 0, 
         'daily_pattern': '0,66.7,0', 'max_daily_pct': 66.7, 'min_daily_pct': 0.0, 'std_daily_pct': 38.5,
         'threshold': 70.0},
        {'symbol': 'DXY', 'timeframe': 'M15', 'total_bars': 225, 'total_contraction_bars': 59, 
         'overall_contraction_pct': 26.2, 'total_transitions': 0, 
         'daily_pattern': '0,70.2,0', 'max_daily_pct': 70.2, 'min_daily_pct': 0.0, 'std_daily_pct': 40.5,
         'threshold': 70.0},
    ],
    
    # 关键观察事件
    'key_observations': [
        {
            'date': '2026-06-04',
            'symbol': 'EURUSD',
            'timeframe': 'M15',
            'type': 'extreme_contraction',
            'description': 'M15收缩占比86.5%，几乎全天处于收缩状态，肉眼可见拉出横线',
            'severity': 3,
            'tags': ['M15', '横线', '极端收缩', '非农前']
        },
        {
            'date': '2026-06-04',
            'symbol': 'USDJPY',
            'timeframe': 'M15',
            'type': 'extreme_contraction',
            'description': 'M15收缩占比82.3%，与EURUSD同步极端收缩',
            'severity': 3,
            'tags': ['M15', '横线', '极端收缩', '非农前', '同步']
        },
        {
            'date': '2026-06-04',
            'symbol': 'XAUUSD',
            'timeframe': 'M15',
            'type': 'heavy_contraction',
            'description': 'M15收缩占比73.9%，黄金在非农前出现显著收缩',
            'severity': 2,
            'tags': ['M15', '黄金', '收缩', '非农前']
        },
        {
            'date': '2026-06-05',
            'symbol': 'US30',
            'timeframe': 'H1',
            'type': 'sudden_contraction',
            'description': 'H1收缩占比从13%激增至52.4%，道指在非农日出现突然收缩',
            'severity': 3,
            'tags': ['H1', '道指', '激增', '非农日']
        },
        {
            'date': '2026-06-05',
            'symbol': 'DXY',
            'timeframe': 'H1',
            'type': 'synchronized_contraction',
            'description': 'H1收缩占比从4.8%增至23.8%，与US30同步收缩，美元资产方向选择',
            'severity': 2,
            'tags': ['H1', '美元指数', '同步', 'US30', '方向选择']
        },
        {
            'date': '2026-06-04',
            'symbol': 'ALL',
            'timeframe': 'H1',
            'type': 'universal_contraction_day',
            'description': '周四所有品种同步出现收缩，是非农数据发布前的典型市场蓄力行为',
            'severity': 3,
            'tags': ['H1', '全品种', '同步', '非农前', '蓄力']
        },
        {
            'date': '2026-06-04',
            'symbol': 'DXY',
            'timeframe': 'M15',
            'type': 'heavy_contraction',
            'description': 'M15收缩占比70.2%，美元指数在小周期也出现显著收缩',
            'severity': 2,
            'tags': ['M15', '美元指数', '收缩']
        },
    ]
}


def main():
    print("=" * 70)
    print("保存关键三天观察到数据库")
    print("=" * 70)
    
    # 初始化数据库
    init_db()
    
    # 保存观察数据
    session_id = save_current_observation(OBSERVATION_DATA)
    
    print(f"\n✅ 观察数据已保存")
    print(f"   会话ID: {session_id}")
    print(f"   观察周期: {OBSERVATION_DATA['start_date']} 至 {OBSERVATION_DATA['end_date']}")
    print(f"   背景: {OBSERVATION_DATA['context']}")
    print(f"   每日特征记录: {len(OBSERVATION_DATA['profiles'])} 条")
    print(f"   品种签名: {len(OBSERVATION_DATA['signatures'])} 个")
    print(f"   关键观察: {len(OBSERVATION_DATA['key_observations'])} 条")
    
    print("\n" + "=" * 70)
    print("数据库位置: data/observation_db.duckdb")
    print("=" * 70)


if __name__ == "__main__":
    main()
