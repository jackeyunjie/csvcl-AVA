"""
实时监控面板

显示内容:
- 当前持仓 (品种/方向/盈亏/持仓时间)
- 最新信号 (时间/品种/信号/置信度)
- 账户状态 (余额/净值/可用保证金)
- 今日统计 (交易次数/盈亏/胜率)

用法:
    python monitor.py           # 监控模式
    python monitor.py --live    # 实盘监控
"""

import sys
import argparse
import logging
import json
import time
import curses
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque

sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "strategies"))

from mt5_bridge import MT5Bridge
from integrated_strategy import IntegratedStrategy

# 信号历史 (保留最近20条)
signal_history = deque(maxlen=20)

# 今日统计
daily_stats = {
    "trades": 0,
    "wins": 0,
    "losses": 0,
    "pnl": 0.0,
}


def format_time_ago(dt: datetime) -> str:
    """格式化时间差"""
    if not dt:
        return "N/A"
    diff = datetime.now() - dt
    hours = int(diff.total_seconds() // 3600)
    mins = int((diff.total_seconds() % 3600) // 60)
    if hours > 0:
        return f"{hours}h{mins}m"
    return f"{mins}m"


def get_color_pair(stdscr, name: str):
    """获取颜色对"""
    colors = {
        "green": curses.color_pair(1),
        "red": curses.color_pair(2),
        "yellow": curses.color_pair(3),
        "cyan": curses.color_pair(4),
        "white": curses.color_pair(5),
    }
    return colors.get(name, curses.color_pair(5))


def init_colors():
    """初始化颜色"""
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # 盈利/买入
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)     # 亏损/卖出
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # 警告
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)    # 信息
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)   # 默认


def draw_header(stdscr, live: bool):
    """绘制头部"""
    mode = "实盘" if live else "模拟"
    header = f" MT5 AI 交易监控 [{mode}] - {datetime.now().strftime('%H:%M:%S')} "
    stdscr.addstr(0, 0, header.center(80, "="), get_color_pair(stdscr, "cyan") | curses.A_BOLD)


def draw_positions(stdscr, start_y: int, positions: dict):
    """绘制持仓区域"""
    stdscr.addstr(start_y, 0, "【当前持仓】", get_color_pair(stdscr, "cyan") | curses.A_BOLD)
    
    if not positions:
        stdscr.addstr(start_y + 1, 2, "无持仓", get_color_pair(stdscr, "yellow"))
        return start_y + 3
    
    # 表头
    stdscr.addstr(start_y + 1, 2, f"{'品种':<12} {'方向':<8} {'置信度':<8} {'持仓时间':<10} {'状态':<10}",
                  get_color_pair(stdscr, "white") | curses.A_DIM)
    
    row = start_y + 2
    for symbol, pos in positions.items():
        direction = "BUY" if pos['action'] == 'BUY' else "SELL"
        color = "green" if direction == "BUY" else "red"
        hold_time = format_time_ago(pos['entry_time'])
        
        # 检查是否接近12小时
        status = "正常"
        if pos['entry_time']:
            elapsed = datetime.now() - pos['entry_time']
            if elapsed >= timedelta(hours=11):
                status = "即将平仓"
            elif elapsed >= timedelta(hours=12):
                status = "已过期"
        
        stdscr.addstr(row, 2, f"{symbol:<12} ", get_color_pair(stdscr, color))
        stdscr.addstr(row, 14, f"{direction:<8} ", get_color_pair(stdscr, color))
        stdscr.addstr(row, 22, f"{pos['confidence']:.2f}    ", get_color_pair(stdscr, "white"))
        stdscr.addstr(row, 30, f"{hold_time:<10} ", get_color_pair(stdscr, "white"))
        
        status_color = "yellow" if "即将" in status or "过期" in status else "white"
        stdscr.addstr(row, 40, f"{status:<10}", get_color_pair(stdscr, status_color))
        row += 1
    
    return row + 1


def draw_signals(stdscr, start_y: int):
    """绘制信号历史"""
    stdscr.addstr(start_y, 0, "【信号历史】", get_color_pair(stdscr, "cyan") | curses.A_BOLD)
    
    if not signal_history:
        stdscr.addstr(start_y + 1, 2, "无信号", get_color_pair(stdscr, "yellow"))
        return start_y + 3
    
    # 表头
    stdscr.addstr(start_y + 1, 2, f"{'时间':<10} {'品种':<12} {'信号':<10} {'置信度':<8} {'原因':<30}",
                  get_color_pair(stdscr, "white") | curses.A_DIM)
    
    row = start_y + 2
    for sig in list(signal_history)[-8:]:  # 显示最近8条
        sig_color = "green" if "BUY" in sig['signal'] else "red" if "SELL" in sig['signal'] else "white"
        time_str = sig['time'].strftime('%H:%M:%S')
        
        stdscr.addstr(row, 2, f"{time_str:<10} ", get_color_pair(stdscr, "white"))
        stdscr.addstr(row, 12, f"{sig['symbol']:<12} ", get_color_pair(stdscr, "white"))
        stdscr.addstr(row, 24, f"{sig['signal']:<10} ", get_color_pair(stdscr, sig_color))
        stdscr.addstr(row, 34, f"{sig['confidence']:.2f}    ", get_color_pair(stdscr, "white"))
        
        reason = sig['reason'][:28] + ".." if len(sig['reason']) > 30 else sig['reason']
        stdscr.addstr(row, 42, reason, get_color_pair(stdscr, "white"))
        row += 1
    
    return row + 1


def draw_stats(stdscr, start_y: int):
    """绘制统计信息"""
    stdscr.addstr(start_y, 0, "【今日统计】", get_color_pair(stdscr, "cyan") | curses.A_BOLD)
    
    win_rate = (daily_stats['wins'] / daily_stats['trades'] * 100) if daily_stats['trades'] > 0 else 0
    pnl_color = "green" if daily_stats['pnl'] >= 0 else "red"
    
    stats_text = f"交易: {daily_stats['trades']} | 胜: {daily_stats['wins']} | 负: {daily_stats['losses']} | 胜率: {win_rate:.1f}% | 盈亏: {daily_stats['pnl']:+.2f}%"
    stdscr.addstr(start_y + 1, 2, stats_text, get_color_pair(stdscr, pnl_color))
    
    return start_y + 3


def draw_footer(stdscr, max_y: int):
    """绘制底部提示"""
    footer = " [Q]退出 [R]刷新 [P]平仓全部"
    stdscr.addstr(max_y - 1, 0, footer.center(80, "-"), get_color_pair(stdscr, "cyan"))


def add_signal(symbol: str, signal: str, confidence: float, reason: str):
    """添加信号到历史"""
    signal_history.append({
        'time': datetime.now(),
        'symbol': symbol,
        'signal': signal,
        'confidence': confidence,
        'reason': reason,
    })


def update_daily_stats(pnl: float, win: bool):
    """更新每日统计"""
    daily_stats['trades'] += 1
    daily_stats['pnl'] += pnl
    if win:
        daily_stats['wins'] += 1
    else:
        daily_stats['losses'] += 1


def monitor_loop(stdscr, live: bool):
    """主监控循环"""
    stdscr.clear()
    init_colors()
    curses.curs_set(0)  # 隐藏光标
    stdscr.nodelay(True)  # 非阻塞输入
    
    bridge = None
    strategy = IntegratedStrategy()
    
    if live:
        bridge = MT5Bridge(mt5_host="localhost", pub_port=5565, req_port=5566)
        if not bridge.connect():
            stdscr.addstr(0, 0, "MT5 连接失败!", get_color_pair(stdscr, "red"))
            stdscr.refresh()
            time.sleep(2)
            return
    
    last_scan = datetime.now()
    scan_interval = 60  # 每秒刷新显示，每分钟扫描信号
    
    try:
        while True:
            stdscr.clear()
            max_y, max_x = stdscr.getmaxyx()
            
            # 绘制界面
            draw_header(stdscr, live)
            
            # 从 run_live.py 导入 positions (简化：使用共享状态)
            # 实际运行时需要通过文件或数据库共享
            from run_live import positions as live_positions
            
            y = 2
            y = draw_positions(stdscr, y, live_positions)
            y = draw_signals(stdscr, y)
            y = draw_stats(stdscr, y)
            draw_footer(stdscr, max_y)
            
            stdscr.refresh()
            
            # 检查键盘输入
            try:
                key = stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    break
                elif key == ord('r') or key == ord('R'):
                    continue
                elif key == ord('p') or key == ord('P'):
                    # 平仓全部
                    if bridge:
                        for symbol in list(live_positions.keys()):
                            bridge.send_command({"type": "close_position", "symbol": symbol})
            except:
                pass
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        pass
    finally:
        if bridge:
            bridge.disconnect()


def simple_monitor(live: bool):
    """简化版监控（无curses，用于Windows兼容）"""
    print("=" * 80)
    print(f" MT5 AI 交易监控 [{'实盘' if live else '模拟'}] ")
    print("=" * 80)
    
    while True:
        try:
            # 清屏
            print("\033[2J\033[H", end="")
            
            now = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{now}] 监控运行中... (Ctrl+C 退出)")
            print("-" * 80)
            
            # 显示持仓
            print("【当前持仓】")
            try:
                from run_live import positions as live_positions
                if live_positions:
                    for symbol, pos in live_positions.items():
                        hold = format_time_ago(pos['entry_time'])
                        print(f"  {symbol}: {pos['action']} 置信度={pos['confidence']:.2f} 持仓={hold}")
                else:
                    print("  无持仓")
            except ImportError:
                print("  无法获取持仓数据")
            
            # 显示信号历史
            print("\n【最近信号】")
            if signal_history:
                for sig in list(signal_history)[-5:]:
                    print(f"  {sig['time'].strftime('%H:%M')} {sig['symbol']}: {sig['signal']} ({sig['confidence']:.2f})")
            else:
                print("  无信号")
            
            # 显示统计
            print(f"\n【今日统计】交易:{daily_stats['trades']} 胜:{daily_stats['wins']} 负:{daily_stats['losses']}")
            
            time.sleep(5)
        
        except KeyboardInterrupt:
            print("\n监控已停止")
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="实盘模式")
    parser.add_argument("--simple", action="store_true", help="简化模式(无curses)")
    args = parser.parse_args()
    
    # Windows 默认使用简化模式
    simple_monitor(args.live)


if __name__ == "__main__":
    main()
