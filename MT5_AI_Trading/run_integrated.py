"""
整合策略实时运行脚本 (AVATRADE 单账户)

用法:
    python run_integrated.py --live    # 实盘模式
    python run_integrated.py           # 模拟模式 (默认)
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "strategies"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "python" / "data"))

from mt5_bridge import MT5Bridge
from integrated_strategy import IntegratedStrategy, IntegratedSignal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def send_signal_to_mt5(bridge: MT5Bridge, signal: IntegratedSignal, live: bool = False):
    """发送信号到 MT5 EA"""
    if not bridge or not bridge.is_connected:
        logger.warning("MT5 未连接，信号未发送")
        return False
    
    # 构建交易指令
    action_map = {
        "强BUY": "BUY",
        "BUY": "BUY",
        "准备BUY": "BUY",
        "强SELL": "SELL",
        "SELL": "SELL",
        "REDUCE": "SELL",
        "观望": "HOLD",
        "HOLD": "HOLD",
    }
    
    action = action_map.get(signal.final_signal, "HOLD")
    
    if action == "HOLD":
        logger.info(f"[{signal.symbol}] 信号={signal.final_signal}，不交易")
        return True
    
    # 使用 send_command 发送信号 (不是 send_order)
    command = {
        "type": "trade_signal",
        "symbol": signal.symbol,
        "action": action,
        "confidence": signal.confidence,
        "reason": signal.reason,
        "fundamental_signal": signal.fundamental_signal,
        "state_trend": signal.state_trend,
        "dry_run": not live,
    }
    
    try:
        response = bridge.send_command(command)
        logger.info(f"[{signal.symbol}] 信号已发送: {action} (live={live})")
        return response.get("success", True)
    except Exception as e:
        logger.error(f"[{signal.symbol}] 发送失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="整合策略实时运行")
    parser.add_argument("--live", action="store_true", help="实盘模式 (默认模拟)")
    parser.add_argument("--host", default="localhost", help="MT5主机")
    parser.add_argument("--pub-port", type=int, default=5565, help="PUB端口")
    parser.add_argument("--req-port", type=int, default=5566, help="REQ端口")
    parser.add_argument("--interval", type=int, default=300, help="检查间隔(秒)")
    args = parser.parse_args()
    
    mode = "实盘" if args.live else "模拟"
    logger.info(f"=== 整合策略启动 | 模式: {mode} | AVATRADE ===")
    logger.info(f"MT5: {args.host}:{args.pub_port}/{args.req_port}")
    
    # 初始化组件
    strategy = IntegratedStrategy()
    bridge = MT5Bridge(
        mt5_host=args.host,
        pub_port=args.pub_port,
        req_port=args.req_port,
        label="AVATRADE"
    )
    
    # 连接 MT5
    logger.info("正在连接 MT5...")
    if not bridge.connect():
        logger.error("MT5 连接失败，请检查 EA 是否运行")
        return 1
    
    logger.info("MT5 连接成功")
    
    try:
        while True:
            now = datetime.now()
            logger.info(f"\n--- 信号检查 @ {now.strftime('%H:%M:%S')} ---")
            
            # 获取所有品种信号
            signals = strategy.analyze_all()
            
            # 筛选高置信度信号
            strong_signals = [s for s in signals if s.confidence >= 0.75]
            
            if strong_signals:
                logger.info(f"发现 {len(strong_signals)} 个强信号:")
                for sig in strong_signals:
                    logger.info(f"  {sig.symbol}: {sig.final_signal} (置信度={sig.confidence:.2f})")
                    logger.info(f"    原因: {sig.reason}")
                    
                    # 发送信号
                    send_signal_to_mt5(bridge, sig, live=args.live)
            else:
                logger.info("暂无强信号")
            
            # 等待下次检查
            logger.info(f"等待 {args.interval} 秒...")
            import time
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        logger.info("\n用户中断")
    finally:
        bridge.disconnect()
        logger.info("MT5 连接已断开")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
