"""
复现观察Agent - 持续扫描市场，检测历史观察模式的复现

功能:
1. 定期扫描各品种当前收缩状态
2. 与历史签名对比，计算匹配度
3. 当匹配度超过阈值时生成提醒
4. 支持H1和M15双周期监控

用法:
    python reification_agent.py --scan  # 单次扫描
    python reification_agent.py --watch  # 持续监控（每30分钟）
"""

import sys
sys.path.insert(0, '.')

import argparse
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from observation_db import check_reification, save_reification_alert, get_pending_alerts, DB_PATH
from three_day_observation import fetch_h1_quintuplets, fetch_m15_triplets, analyze_contraction_breakout_process
from python.backtest_platform.data_layer import MT5DataBridge

# 监控品种（含DXY）
SYMBOLS = {
    "XAUUSD": "GOLD",
    "XAGUSD": "SILVER",
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "US30": "US_30",
    "NAS100": "US_TECH100",
    "GER40": "GERMANY_40",
    "DXY": "DOLLAR_INDX",
}


def scan_symbol(symbol_name: str, mt5_symbol: str, bridge: MT5DataBridge, 
                timeframe: str = "H1", days: int = 3) -> Dict:
    """扫描单个品种当前状态"""
    if timeframe == "H1":
        df = fetch_h1_quintuplets(symbol_name, mt5_symbol, bridge, days=days)
    else:
        df = fetch_m15_triplets(symbol_name, mt5_symbol, bridge, days=days)
    
    if df.empty:
        return {}
    
    results = analyze_contraction_breakout_process(df, timeframe)
    return results


# 注意：匹配算法已统一移至 observation_db.py 的 _calculate_match_score()
# 此处保留函数签名作为兼容接口，实际逻辑委托给 observation_db
def calculate_match_score(current: Dict, reference: Dict) -> Tuple[float, Dict]:
    """
    计算当前状态与历史签名的匹配度（兼容接口）
    
    实际算法见 observation_db._calculate_match_score()
    """
    from observation_db import _calculate_match_score
    return _calculate_match_score(current, reference)


def run_scan(bridge: MT5DataBridge = None, auto_alert: bool = True) -> List[Dict]:
    """
    运行一次全品种扫描
    
    Returns:
        提醒列表
    """
    close_bridge = False
    if bridge is None:
        bridge = MT5DataBridge()
        if not bridge.connect():
            print("MT5连接失败")
            return []
        close_bridge = True
    
    alerts = []
    
    print(f"\n{'='*70}")
    print(f"复现扫描启动 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}")
    
    for symbol_name, mt5_symbol in SYMBOLS.items():
        for tf in ["H1", "M15"]:
            print(f"\n扫描 {symbol_name} ({tf})...", end=" ")
            
            results = scan_symbol(symbol_name, mt5_symbol, bridge, tf, days=3)
            
            if not results:
                print("无数据")
                continue
            
            # 检查复现
            daily_pcts = [
                day.get('contraction_pct', 0)
                for day in results.get('daily_summary', [])
            ]
            current_profile = {
                'contraction_pct': results.get('contraction_pct', 0),
                'max_daily_pct': max(daily_pcts) if daily_pcts else 0,
                'std_daily_pct': float(np.std(daily_pcts)) if daily_pcts else 0,
                'max_contraction_streak': results.get('max_contraction_streak', 0),
            }
            
            reification_results = check_reification(
                symbol_name, tf, current_profile
                # 不再传入统一阈值，由 check_reification 读取签名自己的阈值
            )
            
            if reification_results:
                for alert in reification_results:
                    print(f"⚠️ 复现 detected! 匹配度: {alert['match_score']}%")
                    alerts.append({
                        'symbol': symbol_name,
                        'timeframe': tf,
                        'match_score': alert['match_score'],
                        'reference_period': alert['reference_period'],
                        'reference_context': alert['reference_context'],
                        'current_contraction_pct': alert['current_contraction_pct'],
                        'reference_contraction_pct': alert['reference_contraction_pct'],
                    })
                    
                    if auto_alert:
                        save_reification_alert(alert)
            else:
                print(f"收缩占比: {results.get('contraction_pct', 0):.1f}% | 无复现")
    
    if close_bridge:
        bridge.disconnect()
    
    print(f"\n{'='*70}")
    print(f"扫描完成 | 发现 {len(alerts)} 个复现信号")
    print(f"{'='*70}")
    
    return alerts


def run_watch(interval_minutes: int = 30):
    """持续监控模式"""
    print(f"\n{'='*70}")
    print(f"复现观察Agent启动")
    print(f"监控间隔: {interval_minutes} 分钟")
    print(f"监控品种: {', '.join(SYMBOLS.keys())}")
    print(f"数据库: {DB_PATH}")
    print(f"{'='*70}")
    
    bridge = MT5DataBridge()
    if not bridge.connect():
        print("MT5连接失败，无法启动监控")
        return
    
    try:
        while True:
            alerts = run_scan(bridge, auto_alert=True)
            
            if alerts:
                print("\n⚠️ 复现提醒:")
                for alert in alerts:
                    print(f"  [{alert['symbol']} {alert['timeframe']}] "
                          f"匹配度: {alert['match_score']}% | "
                          f"参考: {alert['reference_context']}")
            
            next_scan = datetime.now() + timedelta(minutes=interval_minutes)
            print(f"\n下次扫描: {next_scan.strftime('%H:%M')}")
            print(f"{'-'*70}")
            
            time.sleep(interval_minutes * 60)
            
    except KeyboardInterrupt:
        print("\n监控已停止")
    finally:
        bridge.disconnect()


def generate_alert_report():
    """生成复现提醒报告"""
    df = get_pending_alerts()
    
    if df.empty:
        print("无待处理提醒")
        return
    
    print(f"\n{'='*70}")
    print(f"复现提醒报告 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}")
    
    for _, row in df.iterrows():
        print(f"\n⚠️ 提醒 #{row['id']}")
        print(f"  品种: {row['reference_symbol']}")
        print(f"  匹配度: {row['match_score']:.1f}%")
        print(f"  参考周期: {row['start_date']} to {row['end_date']}")
        print(f"  参考背景: {row['context']}")
        print(f"  当前收缩: {row['current_contraction_pct']:.1f}%")
        print(f"  参考收缩: {row['reference_contraction_pct']:.1f}%")
        print(f"  提醒时间: {row['alert_date']}")


def main():
    parser = argparse.ArgumentParser(description='复现观察Agent')
    parser.add_argument('--scan', action='store_true', help='单次扫描')
    parser.add_argument('--watch', action='store_true', help='持续监控')
    parser.add_argument('--interval', type=int, default=30, help='监控间隔(分钟)')
    parser.add_argument('--report', action='store_true', help='生成提醒报告')
    
    args = parser.parse_args()
    
    if args.report:
        generate_alert_report()
    elif args.watch:
        run_watch(args.interval)
    elif args.scan:
        alerts = run_scan()
        if alerts:
            print("\n复现信号:")
            for alert in alerts:
                print(f"  {alert['symbol']} {alert['timeframe']}: {alert['match_score']}%")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
