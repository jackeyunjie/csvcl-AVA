"""
v5 模拟盘扫描脚本

功能:
1. 每小时扫描14品种白名单的H1数据
2. 识别当前是否处于收缩setup状态
3. 生成候选信号列表(不自动交易)
4. 输出到控制台 + 保存到CSV日志

用法:
    python run_v5_simulation.py [--once] [--output-dir ./simulation_logs]
    
    --once: 只运行一次扫描(用于测试)
    不加--once: 每小时运行一次, 持续扫描

信号格式:
    每个候选信号包含:
    - 品种、时间、方向(预测)
    - 收缩分数、ADX、BB宽度、SR间距
    - 锚定区间、入场参考价、止损参考价
    - 趋势共振状态(H4/D1趋势)
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from squeeze_multi_timeframe_research_v5 import (
    MultiTimeframeSqueezeResearchV5, SYMBOL_MAP, SYMBOL_WHITELIST_V5
)
from squeeze_multi_timeframe_research_v4 import SYMBOL_WHITELIST
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("squeeze_simulation")

# v5最优参数 (敏感性分析: 保守稳健, Test期望0.377%, n=54)
DEFAULT_PARAMS = {
    "min_squeeze_score": 2,
    "cooldown_bars": 5,
    "max_adx": 12.0,
    "min_anchor_range_pct": 0.50,
    "max_wait_bars": 30,
    "min_breakout_anchor_multiple": 0.1,
    "require_1bar_confirmation": True,
}


def scan_for_setups(output_dir: str = "simulation_logs", params: dict = None):
    """
    扫描当前市场状态, 识别收缩setup
    
    Returns:
        List[dict]: 候选信号列表
    """
    if params is None:
        params = DEFAULT_PARAMS
    
    logger.info("="*80)
    logger.info(f" 模拟盘扫描 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    research = MultiTimeframeSqueezeResearchV5()
    
    # 临时设置白名单
    orig_whitelist = SYMBOL_WHITELIST.copy()
    SYMBOL_WHITELIST.clear()
    SYMBOL_WHITELIST.update(SYMBOL_WHITELIST_V5)
    
    candidates = []
    
    try:
        # 获取最近7天数据(足够识别setup)
        logger.info("获取数据(7天lookback)...")
        data = research.fetch_multi_timeframe_data(SYMBOL_MAP, lookback_days=7)
        
        if not data:
            logger.warning("未能获取数据")
            return candidates
        
        # 识别setups
        research.find_setups(
            min_squeeze_score=params["min_squeeze_score"],
            cooldown_bars=params["cooldown_bars"],
            require_structural=False,
            use_whitelist=True,
            max_adx=params["max_adx"],
            min_anchor_range_pct=params["min_anchor_range_pct"]
        )
        
        logger.info(f"识别到 {len(research.setups)} 个收缩setup")
        
        # 对每个setup分析当前状态
        for setup in research.setups:
            # 只关注最新的setup(最近2小时内)
            if datetime.now() - setup.timestamp > timedelta(hours=2):
                continue
            
            # 获取该品种数据
            symbol_data = data.get(setup.symbol)
            if not symbol_data:
                continue
            
            h1_df = symbol_data.get("H1")
            if h1_df is None or len(h1_df) < 2:
                continue
            
            # 最新bar
            latest = h1_df.iloc[-1]
            prev = h1_df.iloc[-2]
            
            # 检查是否已突破(1bar确认)
            entry_price = None
            direction = None
            confirmed = False
            
            # 向上突破检查
            if latest['close'] > setup.anchor_high + setup.anchor_range * 0.1:
                if latest['close'] > latest['open']:  # 阳线确认
                    entry_price = latest['close']
                    direction = "up"
                    confirmed = True
            
            # 向下突破检查
            elif latest['close'] < setup.anchor_low - setup.anchor_range * 0.1:
                if latest['close'] < latest['open']:  # 阴线确认
                    entry_price = latest['close']
                    direction = "down"
                    confirmed = True
            
            # 构建候选信号
            signal = {
                "scan_time": datetime.now().isoformat(),
                "symbol": setup.symbol,
                "setup_time": setup.timestamp.isoformat(),
                "direction": direction if confirmed else "pending",
                "confirmed": confirmed,
                "squeeze_score": setup.squeeze_score,
                "adx": round(setup.adx, 2),
                "bb_width": round(setup.bb_width, 4),
                "sr_range": round(setup.sr_range, 4),
                "anchor_range_pct": round(setup.anchor_range_pct, 3),
                "anchor_high": round(setup.anchor_high, 5),
                "anchor_low": round(setup.anchor_low, 5),
                "entry_price": round(entry_price, 5) if entry_price else None,
                "stop_price": round(setup.anchor_low, 5) if direction == "up" else round(setup.anchor_high, 5) if direction == "down" else None,
                "h4_trend": setup.h4_trend_bias,
                "d1_trend": setup.d1_trend_bias,
                "conditions": ";".join(setup.conditions),
                "latest_close": round(latest['close'], 5),
                "latest_high": round(latest['high'], 5),
                "latest_low": round(latest['low'], 5),
            }
            
            candidates.append(signal)
            
            status = "✓ 已确认" if confirmed else "⏳ 待突破"
            logger.info(f"  {setup.symbol}: {status} | 分数={setup.squeeze_score}, ADX={setup.adx:.1f}, "
                       f"区间={setup.anchor_range_pct:.2f}% | H4={setup.h4_trend_bias}, D1={setup.d1_trend_bias}")
            
            if confirmed:
                logger.info(f"    -> 方向: {direction}, 入场: {entry_price:.5f}, "
                           f"止损: {signal['stop_price']:.5f}")
        
        # 保存到CSV
        if candidates:
            _save_candidates(candidates, output_dir)
        else:
            logger.info("无候选信号")
            
    except Exception as e:
        logger.error(f"扫描错误: {e}", exc_info=True)
    finally:
        SYMBOL_WHITELIST.clear()
        SYMBOL_WHITELIST.update(orig_whitelist)
    
    return candidates


def _save_candidates(candidates, output_dir):
    """保存候选信号到CSV"""
    import pandas as pd
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y%m%d")
    csv_path = output_path / f"simulation_signals_{date_str}.csv"
    
    df = pd.DataFrame(candidates)
    
    # 如果文件存在则追加
    if csv_path.exists():
        df.to_csv(csv_path, mode='a', header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    
    logger.info(f"候选信号已保存: {csv_path} ({len(candidates)}条)")


def run_continuous_scan(interval_minutes: int = 60, output_dir: str = "simulation_logs"):
    """持续扫描模式"""
    logger.info(f"启动持续扫描模式 | 间隔: {interval_minutes}分钟")
    logger.info(f"输出目录: {output_dir}")
    logger.info("按 Ctrl+C 停止")
    
    while True:
        try:
            scan_for_setups(output_dir)
            
            next_scan = datetime.now() + timedelta(minutes=interval_minutes)
            logger.info(f"下次扫描: {next_scan.strftime('%H:%M:%S')}")
            time.sleep(interval_minutes * 60)
            
        except KeyboardInterrupt:
            logger.info("扫描已停止")
            break
        except Exception as e:
            logger.error(f"扫描循环错误: {e}")
            time.sleep(60)  # 出错后1分钟重试


def main():
    parser = argparse.ArgumentParser(description="v5 模拟盘扫描脚本")
    parser.add_argument("--once", action="store_true", help="只运行一次扫描")
    parser.add_argument("--interval", type=int, default=60, help="扫描间隔(分钟), 默认60")
    parser.add_argument("--output-dir", default="simulation_logs", help="输出目录")
    parser.add_argument("--max-adx", type=float, default=12.0, help="max_adx参数")
    parser.add_argument("--min-range", type=float, default=0.50, help="min_anchor_range_pct参数")
    parser.add_argument("--cooldown", type=int, default=5, help="cooldown_bars参数")
    
    args = parser.parse_args()
    
    # 更新参数
    params = DEFAULT_PARAMS.copy()
    params["max_adx"] = args.max_adx
    params["min_anchor_range_pct"] = args.min_range
    params["cooldown_bars"] = args.cooldown
    
    logger.info(f"参数: max_adx={params['max_adx']}, min_range={params['min_anchor_range_pct']}%, cooldown={params['cooldown_bars']}")
    
    if args.once:
        scan_for_setups(args.output_dir, params)
    else:
        run_continuous_scan(args.interval, args.output_dir)


if __name__ == "__main__":
    main()
