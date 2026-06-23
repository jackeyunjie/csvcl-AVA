"""
M15 收缩突破 Phase 1 快速诊断

执行5步诊断流程，判断M15是否值得投入：
1. 获取14品种M15数据（365天）+ H1/H4数据
2. M15收缩密度扫描（6分制squeeze_score分布）
3. M15 vs H1特征对比（EURUSD/XAUUSD/US30）
4. 跨周期共振初步检验（M15 squeeze≥4 vs H1/H4）
5. 生成诊断报告

用法:
    python squeeze_m15_phase1_diagnosis.py
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np

from squeeze_multi_timeframe_research_v5 import SYMBOL_MAP, SYMBOL_WHITELIST_V5
from python.analytics.squeeze_observer import SqueezeObserver

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("m15_phase1")


class M15Phase1Diagnosis:
    """M15 Phase 1 诊断"""
    
    def __init__(self):
        self.observer = SqueezeObserver()
        self.data = {}  # symbol -> {tf: df}
        self.density_results = {}
        self.comparison_results = {}
        self.resonance_results = {}
        
    # ========================================================================
    # Step 1: 获取数据
    # ========================================================================
    
    def step1_fetch_data(self, lookback_days: int = 365) -> Dict[str, Dict[str, pd.DataFrame]]:
        """获取14品种M15/H1/H4数据"""
        logger.info("=" * 60)
        logger.info("[Phase 1 - Step 1] 获取M15/H1/H4数据")
        logger.info("=" * 60)
        
        data_summary = []
        
        for symbol in sorted(SYMBOL_WHITELIST_V5):
            mt5_name = SYMBOL_MAP.get(symbol, symbol)
            self.data[symbol] = {}
            
            for tf in ["M15", "H1", "H4"]:
                try:
                    logger.info(f"获取 {symbol} ({mt5_name}) {tf} ({lookback_days}天)...")
                    df = self.observer._fetch_from_mt5(mt5_name, tf, lookback_days)
                    
                    if df.empty:
                        logger.warning(f"  {symbol}@{tf}: 无数据")
                        continue
                    
                    # 确保timestamp列
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                    
                    self.data[symbol][tf] = df
                    data_summary.append({
                        'symbol': symbol,
                        'tf': tf,
                        'rows': len(df),
                        'start': df['timestamp'].min().strftime('%Y-%m-%d') if 'timestamp' in df.columns else '-',
                        'end': df['timestamp'].max().strftime('%Y-%m-%d') if 'timestamp' in df.columns else '-',
                    })
                    logger.info(f"  成功: {len(df)}条")
                    
                except Exception as e:
                    logger.error(f"  失败: {e}")
        
        # 数据质量检查
        summary_df = pd.DataFrame(data_summary)
        logger.info("\n数据获取汇总:")
        for _, row in summary_df.iterrows():
            logger.info(f"  {row['symbol']}@{row['tf']}: {row['rows']}条 ({row['start']} ~ {row['end']})")
        
        # 检查M15数据量
        m15_summary = summary_df[summary_df['tf'] == 'M15']
        valid_symbols = m15_summary[m15_summary['rows'] >= 5000]['symbol'].tolist()
        skipped_symbols = m15_summary[m15_summary['rows'] < 5000]['symbol'].tolist()
        
        if skipped_symbols:
            logger.warning(f"数据不足(<5000条)跳过: {skipped_symbols}")
        
        logger.info(f"有效品种: {len(valid_symbols)}/14")
        logger.info(f"[Phase 1 - Step 1 完成]")
        
        return self.data
    
    # ========================================================================
    # Step 2: M15收缩密度扫描
    # ========================================================================
    
    def step2_density_scan(self) -> pd.DataFrame:
        """扫描M15收缩密度（6分制）"""
        logger.info("\n" + "=" * 60)
        logger.info("[Phase 1 - Step 2] M15收缩密度扫描")
        logger.info("=" * 60)
        
        results = []
        
        for symbol in sorted(self.data.keys()):
            if "M15" not in self.data[symbol]:
                continue
            
            df = self.data[symbol]["M15"].copy()
            if len(df) < 30:
                continue
            
            logger.info(f"扫描 {symbol} M15 ({len(df)}条)...")
            
            # 计算指标
            df['bb_width'] = SqueezeObserver.compute_bb_width(df['close'])
            df['sr_range'] = SqueezeObserver.compute_sr_range(df['high'], df['low'], df['close'])
            df['pivot_range'] = SqueezeObserver.compute_pivot_range(df['high'], df['low'], df['close'])
            df['adx'] = SqueezeObserver.compute_adx(df['high'], df['low'], df['close'])
            
            # 计算expanding分位数（从第30根开始）
            df['bb_20pct'] = df['bb_width'].expanding(min_periods=30).quantile(0.20)
            df['sr_20pct'] = df['sr_range'].expanding(min_periods=30).quantile(0.20)
            df['pivot_20pct'] = df['pivot_range'].expanding(min_periods=30).quantile(0.20)
            
            # 计算squeeze_score（6分制）
            df['bb_squeeze'] = df['bb_width'] <= df['bb_20pct']
            df['sr_squeeze'] = df['sr_range'] <= df['sr_20pct']
            df['pivot_squeeze'] = df['pivot_range'] <= df['pivot_20pct']
            df['adx_lt_20'] = df['adx'] < 20
            df['adx_lt_13'] = df['adx'] < 13
            df['adx_lt_9'] = df['adx'] < 9
            
            df['squeeze_score'] = (
                df['bb_squeeze'].astype(int) +
                df['sr_squeeze'].astype(int) +
                df['pivot_squeeze'].astype(int) +
                df['adx_lt_20'].astype(int) +
                df['adx_lt_13'].astype(int) +
                df['adx_lt_9'].astype(int)
            )
            
            # 统计（从第30根开始）
            valid_df = df.iloc[30:]
            total = len(valid_df)
            
            score_counts = valid_df['squeeze_score'].value_counts().sort_index()
            
            row = {'symbol': symbol, 'total': total}
            for score in range(7):
                row[f'score_{score}'] = score_counts.get(score, 0)
                row[f'pct_{score}'] = score_counts.get(score, 0) / total * 100
            
            row['density_ge2'] = (valid_df['squeeze_score'] >= 2).sum() / total * 100
            row['density_ge3'] = (valid_df['squeeze_score'] >= 3).sum() / total * 100
            row['density_ge4'] = (valid_df['squeeze_score'] >= 4).sum() / total * 100
            
            results.append(row)
            logger.info(f"  density(≥3): {row['density_ge3']:.1f}%")
        
        self.density_results = pd.DataFrame(results)
        
        # 打印汇总表
        logger.info("\nM15收缩密度分布:")
        logger.info(f"{'品种':<10} {'总bar':>8} {'=0':>6} {'=1':>6} {'=2':>6} {'=3':>6} {'=4':>6} {'=5':>6} {'=6':>6} {'≥3%':>6}")
        logger.info("-" * 80)
        for _, row in self.density_results.iterrows():
            logger.info(f"{row['symbol']:<10} {row['total']:>8} {row['score_0']:>6} {row['score_1']:>6} "
                       f"{row['score_2']:>6} {row['score_3']:>6} {row['score_4']:>6} {row['score_5']:>6} "
                       f"{row['score_6']:>6} {row['density_ge3']:>5.1f}%")
        
        avg_density = self.density_results['density_ge3'].mean()
        logger.info(f"\n平均 density(≥3): {avg_density:.1f}%")
        
        if avg_density >= 12:
            logger.info("判断: 正常密度")
        elif avg_density < 8:
            logger.info("判断: 太稀 — 建议停止")
        elif avg_density > 25:
            logger.info("判断: 太密 — 建议提高门槛到≥4")
        else:
            logger.info("判断: 可接受")
        
        logger.info(f"[Phase 1 - Step 2 完成]")
        return self.density_results
    
    # ========================================================================
    # Step 3: M15 vs H1 特征对比
    # ========================================================================
    
    def step3_feature_comparison(self, symbols: List[str] = None) -> Dict:
        """M15 vs H1 特征对比"""
        logger.info("\n" + "=" * 60)
        logger.info("[Phase 1 - Step 3] M15 vs H1 特征对比")
        logger.info("=" * 60)
        
        if symbols is None:
            symbols = ["EURUSD", "XAUUSD", "US30"]
        
        comparison = {}
        
        for symbol in symbols:
            if symbol not in self.data:
                continue
            if "M15" not in self.data[symbol] or "H1" not in self.data[symbol]:
                continue
            
            logger.info(f"\n对比 {symbol}...")
            comp = {}
            
            for tf in ["M15", "H1"]:
                df = self.data[symbol][tf].copy()
                if len(df) < 30:
                    continue
                
                # 计算指标
                df['bb_width'] = SqueezeObserver.compute_bb_width(df['close'])
                df['sr_range'] = SqueezeObserver.compute_sr_range(df['high'], df['low'], df['close'])
                df['pivot_range'] = SqueezeObserver.compute_pivot_range(df['high'], df['low'], df['close'])
                df['adx'] = SqueezeObserver.compute_adx(df['high'], df['low'], df['close'])
                
                valid = df.iloc[30:]
                
                # ADX分布
                adx_dist = {
                    '<10': (valid['adx'] < 10).sum() / len(valid) * 100,
                    '10-15': ((valid['adx'] >= 10) & (valid['adx'] < 15)).sum() / len(valid) * 100,
                    '15-20': ((valid['adx'] >= 15) & (valid['adx'] < 20)).sum() / len(valid) * 100,
                    '20-25': ((valid['adx'] >= 20) & (valid['adx'] < 25)).sum() / len(valid) * 100,
                    '>25': (valid['adx'] >= 25).sum() / len(valid) * 100,
                }
                
                # BB_width分位数
                bb_dist = {
                    'P10': valid['bb_width'].quantile(0.10),
                    'P25': valid['bb_width'].quantile(0.25),
                    'P50': valid['bb_width'].quantile(0.50),
                    'P75': valid['bb_width'].quantile(0.75),
                    'P90': valid['bb_width'].quantile(0.90),
                }
                
                # SR_range分位数
                sr_dist = {
                    'P10': valid['sr_range'].quantile(0.10),
                    'P25': valid['sr_range'].quantile(0.25),
                    'P50': valid['sr_range'].quantile(0.50),
                    'P75': valid['sr_range'].quantile(0.75),
                    'P90': valid['sr_range'].quantile(0.90),
                }
                
                # Pivot_range分位数
                pivot_dist = {
                    'P10': valid['pivot_range'].quantile(0.10),
                    'P25': valid['pivot_range'].quantile(0.25),
                    'P50': valid['pivot_range'].quantile(0.50),
                    'P75': valid['pivot_range'].quantile(0.75),
                    'P90': valid['pivot_range'].quantile(0.90),
                }
                
                # squeeze_score分布
                if tf == "M15":
                    # 6分制
                    df['bb_20pct'] = df['bb_width'].expanding(min_periods=30).quantile(0.20)
                    df['sr_20pct'] = df['sr_range'].expanding(min_periods=30).quantile(0.20)
                    df['pivot_20pct'] = df['pivot_range'].expanding(min_periods=30).quantile(0.20)
                    df['bb_squeeze'] = df['bb_width'] <= df['bb_20pct']
                    df['sr_squeeze'] = df['sr_range'] <= df['sr_20pct']
                    df['pivot_squeeze'] = df['pivot_range'] <= df['pivot_20pct']
                    df['adx_lt_20'] = df['adx'] < 20
                    df['adx_lt_13'] = df['adx'] < 13
                    df['adx_lt_9'] = df['adx'] < 9
                    df['squeeze_score'] = (
                        df['bb_squeeze'].astype(int) +
                        df['sr_squeeze'].astype(int) +
                        df['pivot_squeeze'].astype(int) +
                        df['adx_lt_20'].astype(int) +
                        df['adx_lt_13'].astype(int) +
                        df['adx_lt_9'].astype(int)
                    )
                    valid = df.iloc[30:]  # 重新获取valid（包含squeeze_score）
                    score_dist = {i: (valid['squeeze_score'] == i).sum() / len(valid) * 100 for i in range(7)}
                    score_ge2 = (valid['squeeze_score'] >= 2).sum() / len(valid) * 100
                    score_ge3 = (valid['squeeze_score'] >= 3).sum() / len(valid) * 100
                    score_ge4 = (valid['squeeze_score'] >= 4).sum() / len(valid) * 100
                else:
                    # H1 5分制（无Pivot）
                    df['bb_20pct'] = df['bb_width'].expanding(min_periods=30).quantile(0.20)
                    df['sr_20pct'] = df['sr_range'].expanding(min_periods=30).quantile(0.20)
                    df['bb_squeeze'] = df['bb_width'] <= df['bb_20pct']
                    df['sr_squeeze'] = df['sr_range'] <= df['sr_20pct']
                    df['adx_lt_20'] = df['adx'] < 20
                    df['adx_lt_13'] = df['adx'] < 13
                    df['adx_lt_9'] = df['adx'] < 9
                    df['squeeze_score'] = (
                        df['bb_squeeze'].astype(int) +
                        df['sr_squeeze'].astype(int) +
                        df['adx_lt_20'].astype(int) +
                        df['adx_lt_13'].astype(int) +
                        df['adx_lt_9'].astype(int)
                    )
                    valid = df.iloc[30:]  # 重新获取valid（包含squeeze_score）
                    score_dist = {i: (valid['squeeze_score'] == i).sum() / len(valid) * 100 for i in range(6)}
                    score_ge2 = (valid['squeeze_score'] >= 2).sum() / len(valid) * 100
                    score_ge3 = (valid['squeeze_score'] >= 3).sum() / len(valid) * 100
                
                comp[tf] = {
                    'adx_dist': adx_dist,
                    'bb_dist': bb_dist,
                    'sr_dist': sr_dist,
                    'pivot_dist': pivot_dist,
                    'score_dist': score_dist,
                    'score_ge2': score_ge2,
                    'score_ge3': score_ge3,
                }
                if tf == "M15":
                    comp[tf]['score_ge4'] = score_ge4
            
            # Pivot vs SR 相关系数（仅M15）
            if "M15" in comp:
                m15_df = self.data[symbol]["M15"].copy()
                m15_df['pivot_range'] = SqueezeObserver.compute_pivot_range(m15_df['high'], m15_df['low'], m15_df['close'])
                m15_df['sr_range'] = SqueezeObserver.compute_sr_range(m15_df['high'], m15_df['low'], m15_df['close'])
                corr = m15_df['pivot_range'].corr(m15_df['sr_range'])
                comp['pivot_sr_corr'] = corr
                logger.info(f"  Pivot/SR 相关系数: {corr:.3f}")
                if corr > 0.8:
                    logger.info(f"  → 高度等价，Phase 2建议只保留一个")
                else:
                    logger.info(f"  → 不完全等价，Phase 2可保留两者")
            
            comparison[symbol] = comp
            
            # 打印对比表
            logger.info(f"\n{symbol} 对比:")
            logger.info(f"{'指标':<20} {'M15':>12} {'H1':>12}")
            logger.info("-" * 50)
            logger.info(f"{'ADX<10':<20} {comp['M15']['adx_dist']['<10']:>11.1f}% {comp['H1']['adx_dist']['<10']:>11.1f}%")
            logger.info(f"{'ADX 10-15':<20} {comp['M15']['adx_dist']['10-15']:>11.1f}% {comp['H1']['adx_dist']['10-15']:>11.1f}%")
            logger.info(f"{'ADX 15-20':<20} {comp['M15']['adx_dist']['15-20']:>11.1f}% {comp['H1']['adx_dist']['15-20']:>11.1f}%")
            logger.info(f"{'squeeze≥2':<20} {comp['M15']['score_ge2']:>11.1f}% {comp['H1']['score_ge2']:>11.1f}%")
            logger.info(f"{'squeeze≥3':<20} {comp['M15']['score_ge3']:>11.1f}% {comp['H1']['score_ge3']:>11.1f}%")
            if 'score_ge4' in comp['M15']:
                logger.info(f"{'squeeze≥4 (M15)':<20} {comp['M15']['score_ge4']:>11.1f}% {'-':>12}")
        
        self.comparison_results = comparison
        logger.info(f"\n[Phase 1 - Step 3 完成]")
        return comparison
    
    # ========================================================================
    # Step 4: 跨周期共振检验
    # ========================================================================
    
    def step4_resonance_check(self) -> Dict:
        """M15 squeeze≥4 与 H1/H4 共振检验"""
        logger.info("\n" + "=" * 60)
        logger.info("[Phase 1 - Step 4] 跨周期共振检验")
        logger.info("=" * 60)
        
        all_m15_bars = []
        
        for symbol in sorted(self.data.keys()):
            if "M15" not in self.data[symbol]:
                continue
            
            df_m15 = self.data[symbol]["M15"].copy()
            if len(df_m15) < 30:
                continue
            
            # 计算M15 squeeze_score（6分制）
            df_m15['bb_width'] = SqueezeObserver.compute_bb_width(df_m15['close'])
            df_m15['sr_range'] = SqueezeObserver.compute_sr_range(df_m15['high'], df_m15['low'], df_m15['close'])
            df_m15['pivot_range'] = SqueezeObserver.compute_pivot_range(df_m15['high'], df_m15['low'], df_m15['close'])
            df_m15['adx'] = SqueezeObserver.compute_adx(df_m15['high'], df_m15['low'], df_m15['close'])
            
            df_m15['bb_20pct'] = df_m15['bb_width'].expanding(min_periods=30).quantile(0.20)
            df_m15['sr_20pct'] = df_m15['sr_range'].expanding(min_periods=30).quantile(0.20)
            df_m15['pivot_20pct'] = df_m15['pivot_range'].expanding(min_periods=30).quantile(0.20)
            
            df_m15['bb_squeeze'] = df_m15['bb_width'] <= df_m15['bb_20pct']
            df_m15['sr_squeeze'] = df_m15['sr_range'] <= df_m15['sr_20pct']
            df_m15['pivot_squeeze'] = df_m15['pivot_range'] <= df_m15['pivot_20pct']
            df_m15['adx_lt_20'] = df_m15['adx'] < 20
            df_m15['adx_lt_13'] = df_m15['adx'] < 13
            df_m15['adx_lt_9'] = df_m15['adx'] < 9
            df_m15['squeeze_score'] = (
                df_m15['bb_squeeze'].astype(int) +
                df_m15['sr_squeeze'].astype(int) +
                df_m15['pivot_squeeze'].astype(int) +
                df_m15['adx_lt_20'].astype(int) +
                df_m15['adx_lt_13'].astype(int) +
                df_m15['adx_lt_9'].astype(int)
            )
            
            # 筛选squeeze≥4的bar
            high_quality = df_m15[df_m15['squeeze_score'] >= 4].copy()
            
            if len(high_quality) == 0:
                continue
            
            logger.info(f"{symbol}: {len(high_quality)} 个M15 squeeze≥4 bar")
            
            # 获取H1和H4数据
            h1_df = self.data[symbol].get("H1")
            h4_df = self.data[symbol].get("H4")
            
            if h1_df is not None and len(h1_df) > 0:
                h1_df = h1_df.copy()
                h1_df['timestamp'] = pd.to_datetime(h1_df['timestamp'])
                
                # 先计算H1指标
                h1_df['bb_width'] = SqueezeObserver.compute_bb_width(h1_df['close'])
                h1_df['sr_range'] = SqueezeObserver.compute_sr_range(h1_df['high'], h1_df['low'], h1_df['close'])
                h1_df['adx'] = SqueezeObserver.compute_adx(h1_df['high'], h1_df['low'], h1_df['close'])
                
                # merge_asof 找到最近的H1 bar (adx)
                high_quality['timestamp'] = pd.to_datetime(high_quality['timestamp'])
                merged = pd.merge_asof(
                    high_quality.sort_values('timestamp'),
                    h1_df[['timestamp', 'adx']].rename(columns={'adx': 'h1_adx'}).sort_values('timestamp'),
                    on='timestamp',
                    direction='backward'
                )
                
                # 计算H1的squeeze_score（简化版）
                h1_df['bb_20pct'] = h1_df['bb_width'].expanding(min_periods=30).quantile(0.20)
                h1_df['sr_20pct'] = h1_df['sr_range'].expanding(min_periods=30).quantile(0.20)
                h1_df['bb_squeeze'] = h1_df['bb_width'] <= h1_df['bb_20pct']
                h1_df['sr_squeeze'] = h1_df['sr_range'] <= h1_df['sr_20pct']
                h1_df['adx_lt_20'] = h1_df['adx'] < 20
                h1_df['adx_lt_13'] = h1_df['adx'] < 13
                h1_df['adx_lt_9'] = h1_df['adx'] < 9
                h1_df['h1_squeeze_score'] = (
                    h1_df['bb_squeeze'].astype(int) +
                    h1_df['sr_squeeze'].astype(int) +
                    h1_df['adx_lt_20'].astype(int) +
                    h1_df['adx_lt_13'].astype(int) +
                    h1_df['adx_lt_9'].astype(int)
                )
                
                merged = pd.merge_asof(
                    merged.sort_values('timestamp'),
                    h1_df[['timestamp', 'h1_squeeze_score']].sort_values('timestamp'),
                    on='timestamp',
                    direction='backward'
                )
            else:
                merged = high_quality.copy()
                merged['h1_adx'] = np.nan
                merged['h1_squeeze_score'] = np.nan
            
            if h4_df is not None and len(h4_df) > 0:
                h4_df = h4_df.copy()
                h4_df['timestamp'] = pd.to_datetime(h4_df['timestamp'])
                
                h4_df['bb_width'] = SqueezeObserver.compute_bb_width(h4_df['close'])
                h4_df['sr_range'] = SqueezeObserver.compute_sr_range(h4_df['high'], h4_df['low'], h4_df['close'])
                h4_df['adx'] = SqueezeObserver.compute_adx(h4_df['high'], h4_df['low'], h4_df['close'])
                h4_df['bb_20pct'] = h4_df['bb_width'].expanding(min_periods=30).quantile(0.20)
                h4_df['sr_20pct'] = h4_df['sr_range'].expanding(min_periods=30).quantile(0.20)
                h4_df['bb_squeeze'] = h4_df['bb_width'] <= h4_df['bb_20pct']
                h4_df['sr_squeeze'] = h4_df['sr_range'] <= h4_df['sr_20pct']
                h4_df['adx_lt_20'] = h4_df['adx'] < 20
                h4_df['adx_lt_13'] = h4_df['adx'] < 13
                h4_df['adx_lt_9'] = h4_df['adx'] < 9
                h4_df['h4_squeeze_score'] = (
                    h4_df['bb_squeeze'].astype(int) +
                    h4_df['sr_squeeze'].astype(int) +
                    h4_df['adx_lt_20'].astype(int) +
                    h4_df['adx_lt_13'].astype(int) +
                    h4_df['adx_lt_9'].astype(int)
                )
                
                merged = pd.merge_asof(
                    merged.sort_values('timestamp'),
                    h4_df[['timestamp', 'h4_squeeze_score']].sort_values('timestamp'),
                    on='timestamp',
                    direction='backward'
                )
            else:
                merged['h4_squeeze_score'] = np.nan
            
            all_m15_bars.append(merged)
        
        if not all_m15_bars:
            logger.warning("没有M15 squeeze≥4的bar")
            return {}
        
        combined = pd.concat(all_m15_bars, ignore_index=True)
        total = len(combined)
        
        # 共振统计
        h1_squeeze = (combined['h1_squeeze_score'] >= 2).sum()
        h4_squeeze = (combined['h4_squeeze_score'] >= 2).sum()
        both_squeeze = ((combined['h1_squeeze_score'] >= 2) & (combined['h4_squeeze_score'] >= 2)).sum()
        h1_only = ((combined['h1_squeeze_score'] >= 2) & (combined['h4_squeeze_score'] < 2)).sum()
        h4_only = ((combined['h1_squeeze_score'] < 2) & (combined['h4_squeeze_score'] >= 2)).sum()
        neither = ((combined['h1_squeeze_score'] < 2) & (combined['h4_squeeze_score'] < 2)).sum()
        
        # H1趋势方向
        h1_bullish = ((combined['h1_adx'] > 20) & (combined.get('h1_trend', 'neutral') == 'bullish')).sum() if 'h1_trend' in combined.columns else 0
        
        self.resonance_results = {
            'total_m15_high_quality': total,
            'h1_also_squeeze': h1_squeeze,
            'h4_also_squeeze': h4_squeeze,
            'both_squeeze': both_squeeze,
            'both_squeeze_pct': both_squeeze / total * 100 if total > 0 else 0,
            'h1_only': h1_only,
            'h4_only': h4_only,
            'neither': neither,
        }
        
        logger.info(f"\nM15 squeeze≥4 bar总数: {total}")
        logger.info(f"\n高周期共振情况:")
        logger.info(f"  H1也收缩 + H4也收缩: {both_squeeze} ({both_squeeze/total*100:.1f}%)  ← 最强共振")
        logger.info(f"  H1也收缩 + H4未收缩: {h1_only} ({h1_only/total*100:.1f}%)")
        logger.info(f"  H1未收缩 + H4也收缩: {h4_only} ({h4_only/total*100:.1f}%)")
        logger.info(f"  H1未收缩 + H4未收缩: {neither} ({neither/total*100:.1f}%)")
        
        if both_squeeze / total * 100 > 15:
            logger.info("\n判断: M15高质量收缩常与更高周期共振 → 值得继续")
        elif both_squeeze / total * 100 < 5:
            logger.info("\n判断: M15收缩基本独立于更高周期 → 与多周期视角不匹配")
        else:
            logger.info("\n判断: 中等程度共振 → 可继续但需关注")
        
        logger.info(f"\n[Phase 1 - Step 4 完成]")
        return self.resonance_results
    
    # ========================================================================
    # Step 5: 生成诊断报告
    # ========================================================================
    
    def step5_generate_report(self) -> Path:
        """生成诊断报告"""
        logger.info("\n" + "=" * 60)
        logger.info("[Phase 1 - Step 5] 生成诊断报告")
        logger.info("=" * 60)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_dir = Path("reports/squeeze")
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / f"squeeze_m15_phase1_diagnosis_{timestamp}.md"
        
        lines = []
        lines.append("# M15 收缩突破 Phase 1 诊断报告")
        lines.append(f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 数据窗口: 365天")
        lines.append(f"> 品种: 14个白名单")
        
        # 一、数据概览
        lines.append("\n## 一、数据概览")
        lines.append("\n| 品种 | M15条数 | H1条数 | H4条数 |")
        lines.append("|------|---------|--------|--------|")
        for symbol in sorted(self.data.keys()):
            m15_len = len(self.data[symbol].get("M15", pd.DataFrame()))
            h1_len = len(self.data[symbol].get("H1", pd.DataFrame()))
            h4_len = len(self.data[symbol].get("H4", pd.DataFrame()))
            lines.append(f"| {symbol} | {m15_len} | {h1_len} | {h4_len} |")
        
        # 二、收缩密度扫描
        lines.append("\n## 二、收缩密度扫描")
        if hasattr(self, 'density_results') and not self.density_results.empty:
            lines.append("\n| 品种 | 总bar | =0 | =1 | =2 | =3 | =4 | =5 | =6 | ≥3% |")
            lines.append("|------|-------|----|----|----|----|----|----|----|-----|")
            for _, row in self.density_results.iterrows():
                lines.append(f"| {row['symbol']} | {row['total']} | {row['score_0']} | {row['score_1']} | "
                           f"{row['score_2']} | {row['score_3']} | {row['score_4']} | {row['score_5']} | "
                           f"{row['score_6']} | {row['density_ge3']:.1f}% |")
            
            avg_density = self.density_results['density_ge3'].mean()
            lines.append(f"\n平均 density(≥3): {avg_density:.1f}%")
            
            if avg_density >= 12:
                lines.append("\n**判断: 正常密度**")
            elif avg_density < 8:
                lines.append("\n**判断: 太稀 — 不建议继续**")
            elif avg_density > 25:
                lines.append("\n**判断: 太密 — 建议提高门槛到≥4**")
            else:
                lines.append("\n**判断: 可接受**")
        
        # 三、M15 vs H1 特征对比
        lines.append("\n## 三、M15 vs H1 特征对比")
        for symbol, comp in self.comparison_results.items():
            lines.append(f"\n### {symbol}")
            lines.append("\n| 指标 | M15 | H1 |")
            lines.append("|------|-----|-----|")
            if 'M15' in comp and 'H1' in comp:
                lines.append(f"| ADX<10 | {comp['M15']['adx_dist']['<10']:.1f}% | {comp['H1']['adx_dist']['<10']:.1f}% |")
                lines.append(f"| ADX 10-15 | {comp['M15']['adx_dist']['10-15']:.1f}% | {comp['H1']['adx_dist']['10-15']:.1f}% |")
                lines.append(f"| ADX 15-20 | {comp['M15']['adx_dist']['15-20']:.1f}% | {comp['H1']['adx_dist']['15-20']:.1f}% |")
                lines.append(f"| squeeze≥2 | {comp['M15']['score_ge2']:.1f}% | {comp['H1']['score_ge2']:.1f}% |")
                lines.append(f"| squeeze≥3 | {comp['M15']['score_ge3']:.1f}% | {comp['H1']['score_ge3']:.1f}% |")
                if 'score_ge4' in comp['M15']:
                    lines.append(f"| squeeze≥4 | {comp['M15']['score_ge4']:.1f}% | - |")
            
            if 'pivot_sr_corr' in comp:
                lines.append(f"\nPivot/SR 相关系数: {comp['pivot_sr_corr']:.3f}")
                if comp['pivot_sr_corr'] > 0.8:
                    lines.append("→ 高度等价，Phase 2建议只保留一个")
                else:
                    lines.append("→ 不完全等价，Phase 2可保留两者")
        
        # 四、跨周期共振
        lines.append("\n## 四、跨周期共振初步检验")
        if self.resonance_results:
            r = self.resonance_results
            lines.append(f"\nM15 squeeze≥4 bar总数: {r['total_m15_high_quality']}")
            lines.append("\n| 共振情况 | 数量 | 占比 |")
            lines.append("|----------|------|------|")
            lines.append(f"| H1也收缩 + H4也收缩 | {r['both_squeeze']} | {r['both_squeeze_pct']:.1f}% |")
            lines.append(f"| H1也收缩 + H4未收缩 | {r['h1_only']} | {r['h1_only']/r['total_m15_high_quality']*100:.1f}% |")
            lines.append(f"| H1未收缩 + H4也收缩 | {r['h4_only']} | {r['h4_only']/r['total_m15_high_quality']*100:.1f}% |")
            lines.append(f"| H1未收缩 + H4未收缩 | {r['neither']} | {r['neither']/r['total_m15_high_quality']*100:.1f}% |")
            
            if r['both_squeeze_pct'] > 15:
                lines.append("\n**判断: M15高质量收缩常与更高周期共振 → 值得继续**")
            elif r['both_squeeze_pct'] < 5:
                lines.append("\n**判断: M15收缩基本独立于更高周期 → 与多周期视角不匹配**")
            else:
                lines.append("\n**判断: 中等程度共振 → 可继续但需关注**")
        
        # 五、结论
        lines.append("\n## 五、结论与建议")
        lines.append("\n### 是否值得继续？")
        
        # 综合判断
        worth_continuing = True
        reasons = []
        
        if hasattr(self, 'density_results') and not self.density_results.empty:
            avg_density = self.density_results['density_ge3'].mean()
            if avg_density < 8:
                worth_continuing = False
                reasons.append(f"density(≥3)={avg_density:.1f}% < 8%，太稀")
            elif avg_density > 25:
                reasons.append(f"density(≥3)={avg_density:.1f}% > 25%，太密需调参")
        
        if self.resonance_results and self.resonance_results.get('both_squeeze_pct', 0) < 5:
            worth_continuing = False
            reasons.append(f"共振占比={self.resonance_results['both_squeeze_pct']:.1f}% < 5%，与多周期视角不匹配")
        
        if worth_continuing:
            lines.append("- [x] **值得继续** → Phase 2: M15 v1研究")
            if reasons:
                lines.append(f"\n注意: {', '.join(reasons)}")
        else:
            lines.append("- [ ] **不必继续** → M15不适合当前框架")
            lines.append(f"\n原因: {', '.join(reasons)}")
        
        lines.append("\n### 如果继续，Phase 2需要调整什么？")
        lines.append("- 根据density分布调整squeeze_score门槛")
        lines.append("- 根据Pivot/SR相关性决定是否保留Pivot")
        lines.append("- M15参数调优（anchor窗口、突破等待bar数）")
        lines.append("- 出场匹配用户风格：小止损 + 3R目标")
        
        lines.append("\n---")
        lines.append("> **免责声明**: 本报告仅供研究参考，不构成投资建议。")
        
        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"\n报告已生成: {report_path}")
        logger.info(f"[Phase 1 - Step 5 完成]")
        
        return report_path
    
    # ========================================================================
    # 主流程
    # ========================================================================
    
    def run(self):
        """执行完整诊断流程"""
        logger.info("=" * 60)
        logger.info("M15 收缩突破 Phase 1 快速诊断")
        logger.info("=" * 60)
        
        try:
            self.step1_fetch_data(lookback_days=365)
            self.step2_density_scan()
            self.step3_feature_comparison()
            self.step4_resonance_check()
            report_path = self.step5_generate_report()
            
            logger.info("\n" + "=" * 60)
            logger.info("Phase 1 诊断完成")
            logger.info(f"报告: {report_path}")
            logger.info("=" * 60)
            
            return report_path
            
        except Exception as e:
            logger.error(f"诊断中断: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    diagnosis = M15Phase1Diagnosis()
    diagnosis.run()
