"""
Strategy Miner - 科研级策略发现机器

输入: state_pattern (如 "D1=6,H1=4" 或 "H1+H4 squeeze")
市场: 当前已有数据 (股指/外汇/商品)
方向: long / short
持仓: 5 / 10 / 20 bars
过滤: 样本数、年份稳定性、品种稳定性
输出: experiments.db + Top results CSV/Markdown report

核心问题:
1. 今天哪些 State 出现?
2. 这些 State 历史上对应哪些有效策略?
3. 当前策略池应该启用、降权还是禁用?

实验设计:
- 每个 state_pattern × direction × hold_bars = 一个实验
- 评估指标: 胜率、盈亏比、夏普比率、最大回撤、样本数
- 过滤条件: min_samples=30, min_win_rate=0.55, max_drawdown=0.10
"""

import sys
import re
import json
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from collections import defaultdict

import duckdb
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))

from h1_state_db import H1StateDB
from m15_state_db import M15StateDB, M15_TIMEFRAMES
from d1_risk_officer import D1RiskOfficer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 实验数据库路径
EXPERIMENT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "experiments.db"


@dataclass
class ExperimentConfig:
    """实验配置"""
    name: str                    # 实验名称
    state_pattern: str           # State模式 (如 "D1=6,H1=4" 或 "squeeze")
    direction: str               # "long" | "short" | "both"
    hold_bars: int               # 持仓周期 (5, 10, 20)
    markets: List[str]           # 目标市场 ["US_30", "US_500", "EURUSD"]
    min_samples: int = 30        # 最小样本数
    min_win_rate: float = 0.55   # 最小胜率
    max_drawdown: float = 0.10   # 最大回撤
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@dataclass
class ExperimentResult:
    """实验结果"""
    experiment_id: str
    config: ExperimentConfig
    total_samples: int
    win_count: int
    loss_count: int
    win_rate: float
    avg_return: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_consecutive_losses: int
    yearly_stability: Dict[str, float]   # 各年胜率
    market_stability: Dict[str, float]   # 各品种胜率
    created_at: datetime
    
    def is_valid(self) -> bool:
        """是否通过过滤条件"""
        return (
            self.total_samples >= self.config.min_samples and
            self.win_rate >= self.config.min_win_rate and
            self.max_drawdown <= self.config.max_drawdown
        )
    
    def score(self) -> float:
        """综合评分 (0-100)"""
        if not self.is_valid():
            return 0.0
        # 加权评分
        s = (
            self.win_rate * 30 +                    # 胜率权重30%
            min(self.profit_factor, 5) / 5 * 25 +   # 盈亏比权重25%
            min(self.sharpe_ratio, 3) / 3 * 20 +    # 夏普权重20%
            (1 - self.max_drawdown / 0.10) * 15 +   # 回撤权重15%
            min(self.total_samples / 100, 1) * 10   # 样本权重10%
        )
        return min(100, max(0, s))


class ExperimentDatabase:
    """实验数据库管理"""
    
    def __init__(self, db_path: Path = EXPERIMENT_DB):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                state_pattern TEXT NOT NULL,
                direction TEXT NOT NULL,
                hold_bars INTEGER NOT NULL,
                markets TEXT NOT NULL,
                config_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS experiment_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                total_samples INTEGER,
                win_count INTEGER,
                loss_count INTEGER,
                win_rate REAL,
                avg_return REAL,
                avg_win REAL,
                avg_loss REAL,
                profit_factor REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                max_consecutive_losses INTEGER,
                score REAL,
                is_valid INTEGER,
                result_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_exp_pattern ON experiments(state_pattern);
            CREATE INDEX IF NOT EXISTS idx_exp_direction ON experiments(direction);
            CREATE INDEX IF NOT EXISTS idx_res_score ON experiment_results(score);
            CREATE INDEX IF NOT EXISTS idx_res_valid ON experiment_results(is_valid);
        """)
        conn.commit()
        conn.close()
        logger.info(f"实验数据库已初始化: {self.db_path}")
    
    def save_experiment(self, result: ExperimentResult) -> str:
        """保存实验结果"""
        conn = sqlite3.connect(str(self.db_path))
        exp_id = result.experiment_id
        cfg = result.config
        
        # 保存实验配置
        conn.execute("""
            INSERT OR REPLACE INTO experiments 
            (id, name, state_pattern, direction, hold_bars, markets, config_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            exp_id, cfg.name, cfg.state_pattern, cfg.direction, 
            cfg.hold_bars, json.dumps(cfg.markets), json.dumps(asdict(cfg))
        ))
        
        # 保存实验结果
        conn.execute("""
            INSERT INTO experiment_results
            (experiment_id, total_samples, win_count, loss_count, win_rate,
             avg_return, avg_win, avg_loss, profit_factor, sharpe_ratio,
             max_drawdown, max_consecutive_losses, score, is_valid, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exp_id, result.total_samples, result.win_count, result.loss_count,
            result.win_rate, result.avg_return, result.avg_win, result.avg_loss,
            result.profit_factor, result.sharpe_ratio, result.max_drawdown,
            result.max_consecutive_losses, result.score(), 1 if result.is_valid() else 0,
            json.dumps(asdict(result), default=str)
        ))
        
        conn.commit()
        conn.close()
        return exp_id
    
    def get_top_results(self, state_pattern: Optional[str] = None, 
                        limit: int = 20) -> List[Dict]:
        """获取Top结果"""
        conn = sqlite3.connect(str(self.db_path))
        
        sql = """
            SELECT e.name, e.state_pattern, e.direction, e.hold_bars,
                   r.total_samples, r.win_rate, r.profit_factor, 
                   r.sharpe_ratio, r.max_drawdown, r.score
            FROM experiments e
            JOIN experiment_results r ON e.id = r.experiment_id
            WHERE r.is_valid = 1
        """
        params = []
        if state_pattern:
            sql += " AND e.state_pattern = ?"
            params.append(state_pattern)
        
        sql += " ORDER BY r.score DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df.to_dict('records')


class StatePatternMatcher:
    """State 模式匹配器 - 支持 H1 和 M15"""
    
    @staticmethod
    def parse_pattern(pattern: str, mode: str = "h1") -> Callable[[pd.Series], bool]:
        """
        解析 state_pattern 为匹配函数
        
        支持的模式:
        H1模式:
        - "D1=6" → D1 hex 等于 6
        - "D1=6,H1=4" → D1=6 且 H1=4
        - "H1+H4 squeeze" → H1和H4同时收缩
        - "H1 trend+" → H1有趋势且正号
        - "multi_bull(3+)" → 3+周期看涨
        
        M15模式:
        - "M15=6" → M15 hex 等于 6
        - "M15=6,H1=4" → M15=6 且 H1=4
        - "sr_breakout" → SR突破信号
        - "sr_breakout_up" → 向上突破
        - "D1_resistance_break" → D1阻力位突破
        - "multi_bull_m15(4+)" → 4+周期看涨(M15系统)
        """
        conditions = []
        
        # 解析逗号分隔的条件
        for part in pattern.split(','):
            part = part.strip()
            
            # SR突破检测 (M15特有)
            if 'sr_breakout' in part.lower():
                if 'up' in part.lower():
                    conditions.append(lambda row: row.get('sr_breakout') == True and 
                                                 str(row.get('breakout_direction', '')) == 'up')
                elif 'down' in part.lower():
                    conditions.append(lambda row: row.get('sr_breakout') == True and 
                                                 str(row.get('breakout_direction', '')) == 'down')
                else:
                    conditions.append(lambda row: row.get('sr_breakout') == True)
                continue
            
            # D1_resistance_break (M15特有)
            if 'resistance_break' in part.lower():
                conditions.append(lambda row: 
                    row.get('sr_breakout') == True and 
                    str(row.get('breakout_direction', '')) == 'up')
                continue
            
            # 精确匹配: D1=6, H1=4, M15=6 等
            m = re.match(r'(\w+)=([0-9A-Fa-f\-]+)', part)
            if m:
                col, val = m.groups()
                col_name = col.lower() + '_hex'
                conditions.append(lambda row, c=col_name, v=val: row.get(c) == v)
                continue
            
            # squeeze 检测
            if 'squeeze' in part.lower():
                cols = re.findall(r'(\w+)\+', part)
                if not cols:
                    # 默认根据模式选择
                    if mode == "m15":
                        cols = ['m15_hex', 'h1_hex', 'h4_hex']
                    else:
                        cols = ['h1_hex', 'h4_hex', 'd1_hex']
                else:
                    cols = [c.lower() + '_hex' for c in cols]
                
                conditions.append(lambda row, c=cols: 
                    all(StatePatternMatcher._is_squeeze(row.get(x, '')) for x in c))
                continue
            
            # trend+ 检测
            m = re.match(r'(\w+)\s*trend\+', part)
            if m:
                col = m.group(1).lower() + '_hex'
                conditions.append(lambda row, c=col:
                    StatePatternMatcher._has_trend(row.get(c, '')) and
                    not str(row.get(c, '')).startswith('-'))
                continue
            
            # multi_bull 多周期看涨
            m = re.match(r'multi_bull\((\d+)\+\)', part)
            if m:
                min_count = int(m.group(1))
                conditions.append(lambda row, n=min_count, m=mode:
                    StatePatternMatcher._count_bull(row, mode=m) >= n)
                continue
            
            # multi_bull_m15 (M15系统)
            m = re.match(r'multi_bull_m15\((\d+)\+\)', part)
            if m:
                min_count = int(m.group(1))
                conditions.append(lambda row, n=min_count:
                    StatePatternMatcher._count_bull_m15(row) >= n)
                continue
        
        def matcher(row):
            return all(cond(row) for cond in conditions)
        
        return matcher
    
    @staticmethod
    def _is_squeeze(hex_val: str) -> bool:
        """检测是否收缩 (bit3=0, 即值 < 8 且不含8)"""
        if not hex_val or hex_val == 'N/A':
            return True
        try:
            v = abs(int(hex_val.lstrip('-'), 16))
            return (v & 8) == 0
        except:
            return True
    
    @staticmethod
    def _has_trend(hex_val: str) -> bool:
        """检测是否有趋势 (bit2=+4)"""
        if not hex_val or hex_val == 'N/A':
            return False
        try:
            v = abs(int(hex_val.lstrip('-'), 16))
            return (v & 4) != 0
        except:
            return False
    
    @staticmethod
    def _count_bull(row, mode: str = "h1") -> int:
        """统计看涨周期数"""
        if mode == "m15":
            cols = ['mn1_hex', 'w1_hex', 'd1_hex', 'h4_hex', 'h1_hex', 'm30_hex', 'm15_hex']
        else:
            cols = ['mn1_hex', 'w1_hex', 'd1_hex', 'h4_hex', 'h1_hex']
        count = 0
        for col in cols:
            val = str(row.get(col, ''))
            if val and not val.startswith('-') and val != 'N/A':
                try:
                    v = int(val, 16)
                    if (v & 4) != 0:  # has trend
                        count += 1
                except:
                    pass
        return count
    
    @staticmethod
    def _count_bull_m15(row) -> int:
        """M15系统统计看涨周期数 (7周期)"""
        cols = ['mn1_hex', 'w1_hex', 'd1_hex', 'h4_hex', 'h1_hex', 'm30_hex', 'm15_hex']
        count = 0
        for col in cols:
            val = str(row.get(col, ''))
            if val and not val.startswith('-') and val != 'N/A':
                try:
                    v = int(val, 16)
                    if (v & 4) != 0:
                        count += 1
                except:
                    pass
        return count


class StrategyMiner:
    """策略挖掘器 - 支持 H1 和 M15 双系统"""
    
    def __init__(self, state_db_path: str = "data/h1_state.duckdb", mode: str = "h1"):
        """
        mode: "h1" | "m15"
        """
        self.mode = mode
        self.db = duckdb.connect(state_db_path, read_only=True)
        self.exp_db = ExperimentDatabase()
        
        # M15 模式使用独立数据库
        if mode == "m15":
            self.m15_db = M15StateDB("data/m15_state.duckdb")
            logger.info("Strategy Miner 初始化: M15 模式")
        else:
            logger.info("Strategy Miner 初始化: H1 模式")
    
    def run_experiment(self, config: ExperimentConfig) -> ExperimentResult:
        """执行单个实验"""
        logger.info(f"执行实验: {config.name} | {config.state_pattern} | {config.direction} | hold={config.hold_bars} | mode={self.mode}")
        
        # 根据模式选择数据源
        if self.mode == "m15":
            return self._run_m15_experiment(config)
        else:
            return self._run_h1_experiment(config)
    
    def _run_h1_experiment(self, config: ExperimentConfig) -> ExperimentResult:
        """H1 模式实验"""
        # 1. 加载数据
        markets_str = "','".join(config.markets)
        query = f"""
            SELECT symbol, timestamp, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex
            FROM h1_state_snapshot
            WHERE symbol IN ('{markets_str}')
            ORDER BY symbol, timestamp
        """
        df = self.db.execute(query).fetchdf()
        
        if df.empty:
            logger.warning(f"无数据: {config.markets}")
            return self._empty_result(config)
        
        # 2. 解析模式并匹配
        matcher = StatePatternMatcher.parse_pattern(config.state_pattern, mode="h1")
        df['signal'] = df.apply(matcher, axis=1)
        
        # 3. 模拟交易
        trades = self._simulate_trades(df, config, mode="h1")
        
        # 4. 计算指标
        result = self._calculate_metrics(trades, config)
        
        # 5. 保存结果
        self.exp_db.save_experiment(result)
        
        logger.info(f"实验完成: {config.name} | 样本={result.total_samples} | 胜率={result.win_rate:.1%} | 评分={result.score():.1f}")
        
        return result
    
    def _run_m15_experiment(self, config: ExperimentConfig) -> ExperimentResult:
        """M15 模式实验 - 支持SR突破检测"""
        # 1. 从M15数据库加载数据
        conn = self.m15_db._get_conn()
        markets_str = "','".join(config.markets)
        query = f"""
            SELECT symbol, timestamp, mn1_hex, w1_hex, d1_hex, h4_hex, h1_hex, m30_hex, m15_hex,
                   sr_breakout, breakout_direction, breakout_tf
            FROM m15_state_snapshot
            WHERE symbol IN ('{markets_str}')
            ORDER BY symbol, timestamp
        """
        df = conn.execute(query).fetchdf()
        
        if df.empty:
            logger.warning(f"M15无数据: {config.markets}")
            return self._empty_result(config)
        
        # 2. 解析模式并匹配（M15模式）
        matcher = StatePatternMatcher.parse_pattern(config.state_pattern, mode="m15")
        df['signal'] = df.apply(matcher, axis=1)
        
        # 3. 模拟交易（M15模式）
        trades = self._simulate_trades(df, config, mode="m15")
        
        # 4. 计算指标
        result = self._calculate_metrics(trades, config)
        
        # 5. 保存结果
        self.exp_db.save_experiment(result)
        
        logger.info(f"M15实验完成: {config.name} | 样本={result.total_samples} | 胜率={result.win_rate:.1%} | 评分={result.score():.1f}")
        
        return result
    
    def _simulate_trades(self, df: pd.DataFrame, config: ExperimentConfig, mode: str = "h1") -> List[Dict]:
        """模拟交易 - 支持H1和M15模式"""
        trades = []
        hold_bars = config.hold_bars
        risk_officer = D1RiskOfficer()
        
        # 按品种分组
        for symbol in df['symbol'].unique():
            sym_df = df[df['symbol'] == symbol].reset_index(drop=True)
            
            for i in range(len(sym_df) - hold_bars):
                if not sym_df.loc[i, 'signal']:
                    continue
                
                # 获取当前state_hex判断方向
                if mode == "m15":
                    # M15模式: 使用m15_hex判断方向
                    state_val = str(sym_df.loc[i, 'm15_hex'])
                    # SR突破增强
                    sr_breakout = sym_df.loc[i, 'sr_breakout']
                    breakout_dir = str(sym_df.loc[i, 'breakout_direction'])
                else:
                    # H1模式: 使用h1_hex
                    state_val = str(sym_df.loc[i, 'h1_hex'])
                    sr_breakout = False
                    breakout_dir = "none"
                
                is_bull = not state_val.startswith('-')
                
                # SR突破方向确认
                if sr_breakout:
                    if breakout_dir == "up":
                        is_bull = True
                    elif breakout_dir == "down":
                        is_bull = False
                
                # 根据实验方向过滤
                if config.direction == 'long' and not is_bull:
                    continue
                if config.direction == 'short' and is_bull:
                    continue

                trade_direction = 'long' if is_bull else 'short'
                d1_decision = risk_officer.assess(
                    sym_df.loc[i].get('d1_hex'),
                    trade_direction,
                    lower_timeframe=mode.upper(),
                )
                if not d1_decision.allowed:
                    continue
                
                # 模拟收益
                future_idx = min(i + hold_bars, len(sym_df) - 1)
                future_states = sym_df.loc[i+1:future_idx]
                trend_score = self._calc_trend_score(future_states, mode=mode)
                
                # 收益 = 趋势得分 × 方向
                if is_bull:
                    pnl = trend_score
                else:
                    pnl = -trend_score
                
                trade = {
                    'symbol': symbol,
                    'entry_time': sym_df.loc[i, 'timestamp'],
                    'exit_time': sym_df.loc[future_idx, 'timestamp'],
                    'direction': trade_direction,
                    'pnl': pnl,
                    'state_at_entry': state_val,
                    'd1_hex': d1_decision.d1_hex,
                    'd1_direction': d1_decision.d1_direction,
                    'risk_reason': d1_decision.reason,
                }
                
                # M15模式添加SR信息
                if mode == "m15":
                    trade['sr_breakout'] = sr_breakout
                    trade['breakout_direction'] = breakout_dir
                    trade['breakout_tf'] = str(sym_df.loc[i, 'breakout_tf'])
                
                trades.append(trade)
        
        return trades
    
    def _calc_trend_score(self, future_df: pd.DataFrame, mode: str = "h1") -> float:
        """计算后续趋势得分 (-1 到 +1)"""
        if future_df.empty:
            return 0
        
        # 根据模式选择参考列
        ref_col = 'm15_hex' if mode == "m15" else 'h1_hex'
        
        scores = []
        for _, row in future_df.iterrows():
            val = str(row.get(ref_col, '0'))
            if val == 'N/A':
                continue
            try:
                v = int(val.lstrip('-'), 16)
                sign = -1 if val.startswith('-') else 1
                # 有趋势得分更高
                if (v & 4) != 0:
                    scores.append(sign * 0.8)
                elif (v & 2) != 0:
                    scores.append(sign * 0.5)
                else:
                    scores.append(sign * 0.1)
            except:
                pass
        
        return np.mean(scores) if scores else 0
    
    def _calculate_metrics(self, trades: List[Dict], config: ExperimentConfig) -> ExperimentResult:
        """计算实验指标"""
        if not trades:
            return self._empty_result(config)
        
        pnls = [t['pnl'] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        total = len(pnls)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = win_count / total if total > 0 else 0
        
        avg_return = np.mean(pnls)
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        profit_factor = abs(sum(wins) / sum(losses)) if sum(losses) != 0 else float('inf')
        
        # 夏普比率 (简化)
        returns = pd.Series(pnls)
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # 最大回撤
        cumsum = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumsum)
        drawdown = (cumsum - running_max) / (running_max + 1e-10)
        max_dd = abs(drawdown.min()) if len(drawdown) > 0 else 0
        
        # 最大连续亏损
        max_consec = 0
        current = 0
        for p in pnls:
            if p <= 0:
                current += 1
                max_consec = max(max_consec, current)
            else:
                current = 0
        
        # 年份稳定性
        yearly = defaultdict(lambda: {'wins': 0, 'total': 0})
        for t in trades:
            year = pd.Timestamp(t['entry_time']).year
            yearly[year]['total'] += 1
            if t['pnl'] > 0:
                yearly[year]['wins'] += 1
        
        yearly_stability = {
            str(y): v['wins'] / v['total'] 
            for y, v in yearly.items() if v['total'] > 0
        }
        
        # 品种稳定性
        market_stats = defaultdict(lambda: {'wins': 0, 'total': 0})
        for t in trades:
            market_stats[t['symbol']]['total'] += 1
            if t['pnl'] > 0:
                market_stats[t['symbol']]['wins'] += 1
        
        market_stability = {
            m: v['wins'] / v['total']
            for m, v in market_stats.items() if v['total'] > 0
        }
        
        exp_id = f"{config.name}_{config.direction}_{config.hold_bars}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return ExperimentResult(
            experiment_id=exp_id,
            config=config,
            total_samples=total,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_rate,
            avg_return=avg_return,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            max_consecutive_losses=max_consec,
            yearly_stability=yearly_stability,
            market_stability=market_stability,
            created_at=datetime.now(),
        )
    
    def _empty_result(self, config: ExperimentConfig) -> ExperimentResult:
        """空结果"""
        return ExperimentResult(
            experiment_id=f"{config.name}_empty",
            config=config,
            total_samples=0, win_count=0, loss_count=0,
            win_rate=0, avg_return=0, avg_win=0, avg_loss=0,
            profit_factor=0, sharpe_ratio=0, max_drawdown=1.0,
            max_consecutive_losses=0,
            yearly_stability={}, market_stability={},
            created_at=datetime.now(),
        )
    
    def batch_mine(self, patterns: List[str], directions: List[str] = None,
                   hold_bars_list: List[int] = None,
                   markets: List[str] = None) -> List[ExperimentResult]:
        """批量挖掘策略"""
        if directions is None:
            directions = ['long', 'short']
        if hold_bars_list is None:
            hold_bars_list = [5, 10, 20]
        if markets is None:
            markets = [
                'US_30', 'US_500', 'US_TECH100',
                'EURUSD', 'GBPUSD', 'USDJPY',
                'XAUUSD', 'USOIL', 'BTCUSD',
                'HK_50', 'CHINA_A50', 'GER30', 'JP225',
                'SILVER', 'BRENT_OIL', 'NATURAL_GAS',
                '#APPLE', '#MICROSOFT', '#NVIDIA', '#TESLA',
                '#AMAZON', '#GOOGLE', '#META', '#NETFLIX', '#AMD',
                '#JPMORGAN', '#BERKSHIRE', '#JOHNSON', '#EXXON', '#WALMART',
            ] if self.mode == "h1" else ['EURUSD', 'XAUUSD']
        
        results = []
        
        for pattern in patterns:
            for direction in directions:
                for hold in hold_bars_list:
                    config = ExperimentConfig(
                        name=f"exp_{self.mode}_{pattern.replace('=', '_').replace(',', '_')}",
                        state_pattern=pattern,
                        direction=direction,
                        hold_bars=hold,
                        markets=markets,
                    )
                    result = self.run_experiment(config)
                    results.append(result)
        
        return results
    
    def generate_report(self, results: List[ExperimentResult], output_dir: Path = None):
        """生成报告"""
        if output_dir is None:
            output_dir = Path(__file__).resolve().parent.parent.parent / "reports"
        output_dir.mkdir(exist_ok=True)
        
        # 过滤有效结果
        valid = [r for r in results if r.is_valid()]
        valid.sort(key=lambda x: x.score(), reverse=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # CSV报告
        csv_path = output_dir / f"strategy_mining_report_{timestamp}.csv"
        rows = []
        for r in valid[:50]:  # Top 50
            rows.append({
                'experiment_id': r.experiment_id,
                'state_pattern': r.config.state_pattern,
                'direction': r.config.direction,
                'hold_bars': r.config.hold_bars,
                'total_samples': r.total_samples,
                'win_rate': f"{r.win_rate:.1%}",
                'avg_return': f"{r.avg_return:.4f}",
                'profit_factor': f"{r.profit_factor:.2f}",
                'sharpe_ratio': f"{r.sharpe_ratio:.2f}",
                'max_drawdown': f"{r.max_drawdown:.1%}",
                'score': f"{r.score():.1f}",
                'yearly_stability': json.dumps(r.yearly_stability),
                'market_stability': json.dumps(r.market_stability),
            })
        
        pd.DataFrame(rows).to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"CSV报告已保存: {csv_path}")
        
        # Markdown报告
        md_path = output_dir / f"strategy_mining_report_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Strategy Mining Report\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## 摘要\n\n")
            f.write(f"- 总实验数: {len(results)}\n")
            f.write(f"- 有效策略: {len(valid)}\n")
            best_score = valid[0].score() if valid else 0
            f.write(f"- 最佳评分: {best_score:.1f}\n\n")
            
            f.write("## Top 20 策略\n\n")
            f.write("| 排名 | State模式 | 方向 | 持仓 | 样本 | 胜率 | 盈亏比 | 夏普 | 回撤 | 评分 |\n")
            f.write("|------|-----------|------|------|------|------|--------|------|------|------|\n")
            
            for i, r in enumerate(valid[:20], 1):
                f.write(f"| {i} | {r.config.state_pattern} | {r.config.direction} | {r.config.hold_bars} | ")
                f.write(f"{r.total_samples} | {r.win_rate:.1%} | {r.profit_factor:.2f} | ")
                f.write(f"{r.sharpe_ratio:.2f} | {r.max_drawdown:.1%} | {r.score():.1f} |\n")
            
            f.write("\n## 详细结果\n\n")
            for i, r in enumerate(valid[:10], 1):
                f.write(f"### #{i} {r.experiment_id}\n\n")
                f.write(f"- **State模式**: {r.config.state_pattern}\n")
                f.write(f"- **方向**: {r.config.direction}\n")
                f.write(f"- **持仓周期**: {r.config.hold_bars} bars\n")
                f.write(f"- **样本数**: {r.total_samples}\n")
                f.write(f"- **胜率**: {r.win_rate:.1%}\n")
                f.write(f"- **平均收益**: {r.avg_return:.4f}\n")
                f.write(f"- **盈亏比**: {r.profit_factor:.2f}\n")
                f.write(f"- **夏普比率**: {r.sharpe_ratio:.2f}\n")
                f.write(f"- **最大回撤**: {r.max_drawdown:.1%}\n")
                f.write(f"- **最大连续亏损**: {r.max_consecutive_losses}\n")
                f.write(f"- **年份稳定性**: {r.yearly_stability}\n")
                f.write(f"- **品种稳定性**: {r.market_stability}\n")
                f.write(f"- **综合评分**: {r.score():.1f}\n\n")
        
        logger.info(f"Markdown报告已保存: {md_path}")
        return csv_path, md_path


def main():
    """主函数 - 支持H1和M15双模式挖掘"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["h1", "m15"], default="h1", help="挖掘模式")
    parser.add_argument("--db", default="data/h1_state.duckdb", help="State数据库路径")
    parser.add_argument("--markets", default=None, help="目标品种，逗号分隔，如 US_30,US_500,GER30")
    args = parser.parse_args()
    
    # 根据模式选择数据库
    db_path = args.db if args.mode == "h1" else "data/m15_state.duckdb"
    miner = StrategyMiner(state_db_path=db_path, mode=args.mode)
    
    # 解析命令行传入的品种列表
    if args.markets:
        markets = [s.strip() for s in args.markets.split(",")]
        logger.info(f"使用命令行指定品种: {markets}")
        # 使用H1模式默认patterns
        patterns = [
            "D1=6,H1=4",           # D1趋势+H1趋势
            "D1=6,H1=2",           # D1趋势+H1突破
            "H1=4",                # H1单纯趋势
            "H1=6",                # H1突破+趋势
            "H1+H4 squeeze",       # H1+H4收缩
            "multi_bull(3+)",      # 3+周期看涨
            "H1 trend+",           # H1正趋势
            "D1=-E,H1=-4",         # D1看跌+H1看跌
        ]
    elif args.mode == "m15":
        # M15模式: 支持SR突破的patterns
        patterns = [
            "M15=6",                    # M15趋势+突破
            "M15=4",                    # M15趋势
            "M15=6,H1=4",              # M15+H1双趋势
            "sr_breakout_up",           # SR向上突破
            "sr_breakout_down",         # SR向下突破
            "M15=6,sr_breakout_up",    # M15趋势+向上突破
            "multi_bull_m15(4+)",      # 4+周期看涨
            "M15+H1 squeeze",          # M15+H1收缩
        ]
        markets = ['EURUSD', 'XAUUSD', 'USOIL']
    else:
        # H1模式: 原有patterns
        patterns = [
            "D1=6,H1=4",           # D1趋势+H1趋势
            "D1=6,H1=2",           # D1趋势+H1突破
            "H1=4",                # H1单纯趋势
            "H1=6",                # H1突破+趋势
            "H1+H4 squeeze",       # H1+H4收缩
            "multi_bull(3+)",      # 3+周期看涨
            "H1 trend+",           # H1正趋势
            "D1=-E,H1=-4",         # D1看跌+H1看跌
        ]
        markets = ['US_30', 'US_500', 'US_TECH100']
    
    logger.info("=" * 60)
    logger.info(f"Strategy Miner - 批量策略挖掘 [{args.mode.upper()}模式]")
    logger.info("=" * 60)
    
    results = miner.batch_mine(
        patterns=patterns,
        directions=['long', 'short'],
        hold_bars_list=[5, 10, 20],
        markets=markets,
    )
    
    # 生成报告
    csv_path, md_path = miner.generate_report(results)
    
    logger.info("=" * 60)
    logger.info("挖掘完成!")
    logger.info(f"模式: {args.mode.upper()}")
    logger.info(f"总实验: {len(results)}")
    logger.info(f"有效策略: {len([r for r in results if r.is_valid()])}")
    logger.info(f"报告: {csv_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
