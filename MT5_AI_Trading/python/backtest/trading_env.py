"""
强化学习环境 - OpenAI Gym兼容
功能：
1. 交易环境模拟
2. 状态空间定义
3. 奖励函数设计
4. 与回测系统集成
"""

import gym
from gym import spaces
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """交易记录"""
    entry_price: float
    exit_price: Optional[float]
    position_type: int  # 1=多, -1=空
    volume: float
    entry_time: int
    exit_time: Optional[int]
    profit: float = 0
    is_open: bool = True


class TradingEnv(gym.Env):
    """
    交易强化学习环境
    
    状态空间：31维特征向量
    - 28个技术指标特征
    - 3个账户状态特征
    
    动作空间：
    - 0: HOLD (持仓)
    - 1: BUY (买入)
    - 2: SELL (卖出)
    - 3: CLOSE (平仓)
    """
    
    metadata = {'render.modes': ['human']}
    
    def __init__(
        self,
        df: pd.DataFrame,
        initial_balance: float = 10000.0,
        max_position_size: float = 1.0,
        commission: float = 0.0001,  # 手续费比例
        spread: float = 0.0002,      # 点差
        reward_scaling: float = 1.0,
        window_size: int = 50
    ):
        super(TradingEnv, self).__init__()
        
        self.df = df.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.max_position_size = max_position_size
        self.commission = commission
        self.spread = spread
        self.reward_scaling = reward_scaling
        self.window_size = window_size
        
        # 计算技术指标
        self.df = self._calculate_features(self.df)
        
        # 定义状态空间 (31维)
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(31,),
            dtype=np.float32
        )
        
        # 定义动作空间
        self.action_space = spaces.Discrete(4)
        
        # 状态变量
        self.current_step = 0
        self.balance = initial_balance
        self.position = 0  # 0=无, 1=多, -1=空
        self.entry_price = 0.0
        self.trades: list = []
        self.total_reward = 0.0
        
        # 特征列名
        self.feature_cols = [
            'EMA_10', 'EMA_50', 'RSI', 'ATR', 'MACD',
            'BB_upper', 'BB_lower', 'ADX', 'CCI', 'MOM',
            'Volume_MA', 'Volatility', 'Returns', 'Log_Returns',
            'High_Low', 'Open_Close', 'SMA_20', 'SMA_200',
            'Stoch_K', 'Stoch_D', 'Williams_R', 'OBV',
            'MFI', 'ROC', 'TSI', 'UO', 'Keltner', 'Donchian'
        ]
        
        logger.info(f"TradingEnv初始化完成 | 数据长度: {len(df)} | 初始资金: {initial_balance}")
    
    def _calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算特征"""
        df = df.copy()
        
        # 移动平均线
        df['EMA_10'] = df['close'].ewm(span=10).mean()
        df['EMA_50'] = df['close'].ewm(span=50).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['SMA_200'] = df['close'].rolling(200).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + gain / loss))
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['MACD'] = ema12 - ema26
        
        # ATR
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        
        # 布林带
        df['BB_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['BB_upper'] = df['BB_middle'] + 2 * bb_std
        df['BB_lower'] = df['BB_middle'] - 2 * bb_std
        
        # ADX
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        tr_smooth = tr.rolling(14).mean()
        plus_di = 100 * plus_dm.rolling(14).mean() / tr_smooth
        minus_di = 100 * minus_dm.rolling(14).mean() / tr_smooth
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        df['ADX'] = dx.rolling(14).mean()
        
        # CCI
        tp = (df['high'] + df['low'] + df['close']) / 3
        df['CCI'] = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())
        
        # 动量指标
        df['MOM'] = df['close'].diff(10)
        df['ROC'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10) * 100
        
        # 成交量指标
        df['Volume_MA'] = df['volume'].rolling(20).mean()
        df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        df['MFI'] = 100 - (100 / (1 + (df['volume'] * (df['close'] - df['low'])).rolling(14).mean() / 
                                   (df['volume'] * (df['high'] - df['close'])).rolling(14).mean()))
        
        # 波动率
        df['Volatility'] = df['close'].pct_change().rolling(20).std()
        df['Returns'] = df['close'].pct_change()
        df['Log_Returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # 价格特征
        df['High_Low'] = (df['high'] - df['low']) / df['close']
        df['Open_Close'] = (df['close'] - df['open']) / df['open']
        
        # 随机指标
        low_min = df['low'].rolling(14).min()
        high_max = df['high'].rolling(14).max()
        df['Stoch_K'] = 100 * (df['close'] - low_min) / (high_max - low_min)
        df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
        
        # Williams %R
        df['Williams_R'] = -100 * (high_max - df['close']) / (high_max - low_min)
        
        # TSI
        pc = df['close'].diff()
        df['TSI'] = 100 * pc.ewm(span=25).mean() / abs(pc).ewm(span=25).mean()
        
        # Ultimate Oscillator
        bp = df['close'] - pd.concat([df['low'], df['close'].shift()], axis=1).min(axis=1)
        tr_ = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        ], axis=1).max(axis=1)
        avg7 = bp.rolling(7).sum() / tr_.rolling(7).sum()
        avg14 = bp.rolling(14).sum() / tr_.rolling(14).sum()
        avg28 = bp.rolling(28).sum() / tr_.rolling(28).sum()
        df['UO'] = 100 * (4 * avg7 + 2 * avg14 + avg28) / 7
        
        # Keltner Channel
        df['Keltner'] = df['close'].ewm(span=20).mean() + 2 * df['ATR']
        
        # Donchian Channel
        df['Donchian'] = df['high'].rolling(20).max() - df['low'].rolling(20).min()
        
        return df
    
    def reset(self) -> np.ndarray:
        """重置环境"""
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.position = 0
        self.entry_price = 0.0
        self.trades = []
        self.total_reward = 0.0
        
        return self._get_observation()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        执行动作
        
        Args:
            action: 0=HOLD, 1=BUY, 2=SELL, 3=CLOSE
        
        Returns:
            observation, reward, done, info
        """
        current_price = self.df.iloc[self.current_step]['close']
        
        # 执行交易动作
        reward = 0.0
        trade_executed = False
        
        if action == 1 and self.position == 0:  # BUY
            self.position = 1
            self.entry_price = current_price + self.spread
            trade = Trade(
                entry_price=self.entry_price,
                exit_price=None,
                position_type=1,
                volume=self.max_position_size,
                entry_time=self.current_step,
                exit_time=None
            )
            self.trades.append(trade)
            trade_executed = True
            
        elif action == 2 and self.position == 0:  # SELL
            self.position = -1
            self.entry_price = current_price - self.spread
            trade = Trade(
                entry_price=self.entry_price,
                exit_price=None,
                position_type=-1,
                volume=self.max_position_size,
                entry_time=self.current_step,
                exit_time=None
            )
            self.trades.append(trade)
            trade_executed = True
            
        elif action == 3 and self.position != 0:  # CLOSE
            exit_price = current_price - self.spread if self.position == 1 else current_price + self.spread
            pnl = (exit_price - self.entry_price) * self.position * self.max_position_size
            pnl -= abs(pnl) * self.commission  # 扣除手续费
            
            self.balance += pnl
            reward = pnl
            
            # 更新最后一笔交易
            if self.trades:
                last_trade = self.trades[-1]
                last_trade.exit_price = exit_price
                last_trade.exit_time = self.current_step
                last_trade.profit = pnl
                last_trade.is_open = False
            
            self.position = 0
            self.entry_price = 0.0
            trade_executed = True
        
        # 计算持仓浮动盈亏
        unrealized_pnl = 0.0
        if self.position != 0:
            mark_price = current_price - self.spread if self.position == 1 else current_price + self.spread
            unrealized_pnl = (mark_price - self.entry_price) * self.position * self.max_position_size
        
        # 综合奖励函数
        if not trade_executed:
            # 持仓奖励：鼓励盈利持仓，惩罚亏损持仓
            reward = unrealized_pnl * 0.1
        
        # 回撤惩罚
        drawdown = max(0, self.initial_balance - self.balance)
        reward -= drawdown * 0.01
        
        # 缩放奖励
        reward *= self.reward_scaling
        
        self.total_reward += reward
        self.current_step += 1
        
        # 检查是否结束
        done = self.current_step >= len(self.df) - 1
        
        # 如果结束还有持仓，强制平仓
        if done and self.position != 0:
            final_price = self.df.iloc[self.current_step]['close']
            exit_price = final_price - self.spread if self.position == 1 else final_price + self.spread
            final_pnl = (exit_price - self.entry_price) * self.position * self.max_position_size
            self.balance += final_pnl
            reward += final_pnl
        
        observation = self._get_observation()
        
        info = {
            'balance': self.balance,
            'position': self.position,
            'unrealized_pnl': unrealized_pnl,
            'total_trades': len(self.trades),
            'current_step': self.current_step
        }
        
        return observation, reward, done, info
    
    def _get_observation(self) -> np.ndarray:
        """获取当前状态观测"""
        if self.current_step >= len(self.df):
            return np.zeros(31, dtype=np.float32)
        
        # 获取特征
        features = self.df.iloc[self.current_step][self.feature_cols].values
        
        # 处理NaN
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        # 账户状态
        account_state = np.array([
            self.balance / self.initial_balance,
            float(self.position),
            self.current_step / len(self.df)
        ], dtype=np.float32)
        
        # 合并
        observation = np.concatenate([features, account_state]).astype(np.float32)
        
        return observation
    
    def render(self, mode='human'):
        """渲染当前状态"""
        if self.current_step >= len(self.df):
            return
        
        current_price = self.df.iloc[self.current_step]['close']
        print(f"Step: {self.current_step} | Price: {current_price:.5f} | "
              f"Balance: {self.balance:.2f} | Position: {self.position} | "
              f"Trades: {len(self.trades)}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        closed_trades = [t for t in self.trades if not t.is_open]
        
        if not closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_profit': 0,
                'final_balance': self.balance
            }
        
        profits = [t.profit for t in closed_trades]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p <= 0]
        
        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(closed_trades) if closed_trades else 0,
            'total_profit': sum(profits),
            'avg_profit': np.mean(profits) if profits else 0,
            'avg_win': np.mean(wins) if wins else 0,
            'avg_loss': np.mean(losses) if losses else 0,
            'profit_factor': abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf'),
            'max_drawdown': self._calculate_max_drawdown(),
            'final_balance': self.balance,
            'return_pct': (self.balance - self.initial_balance) / self.initial_balance * 100
        }
    
    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.trades:
            return 0.0
        
        equity_curve = [self.initial_balance]
        for trade in self.trades:
            if not trade.is_open:
                equity_curve.append(equity_curve[-1] + trade.profit)
        
        peak = equity_curve[0]
        max_dd = 0.0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)
        
        return max_dd


if __name__ == "__main__":
    # 测试代码
    np.random.seed(42)
    n = 500
    prices = 1.0850 + np.cumsum(np.random.randn(n) * 0.001)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(n) * 0.0005,
        'high': prices + abs(np.random.randn(n)) * 0.001,
        'low': prices - abs(np.random.randn(n)) * 0.001,
        'close': prices,
        'volume': np.random.randint(1000, 10000, n)
    })
    
    env = TradingEnv(df, initial_balance=10000)
    obs = env.reset()
    
    print(f"状态空间维度: {obs.shape}")
    print(f"动作空间: {env.action_space}")
    
    # 随机测试
    for _ in range(100):
        action = env.action_space.sample()
        obs, reward, done, info = env.step(action)
        if done:
            break
    
    summary = env.get_performance_summary()
    print("\n性能摘要:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
