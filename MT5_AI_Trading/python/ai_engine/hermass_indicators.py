"""
Hermass 技术指标系统 (Python 移植版)
基于 Hermass_EF2_JPY_Trader.mq5 的指标计算逻辑

核心指标:
- Base: 布林带宽分位 (BB Width Percentile)
- Trend: ADX 方向判断
- Position: 分形 SR 突破
- Volatility: ATR 扩张
- Sign: 符号裁决

组合成 4-bit State Score (0-15)
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional


class HermassIndicators:
    """Hermass 技术指标计算器"""
    
    def __init__(
        self,
        bb_period: int = 20,
        bb_stddev: float = 2.0,
        bb_percentile_w: int = 20,
        bb_compress_q: float = 0.20,
        atr_period: int = 14,
        adx_period: int = 14,
        adx_slope: int = 3,
        fractal_k: int = 5,
        fractal_lag: int = 3,
    ):
        self.bb_period = bb_period
        self.bb_stddev = bb_stddev
        self.bb_percentile_w = bb_percentile_w
        self.bb_compress_q = bb_compress_q
        self.atr_period = atr_period
        self.adx_period = adx_period
        self.adx_slope = adx_slope
        self.fractal_k = fractal_k
        self.fractal_lag = fractal_lag
    
    def calc_all(self, df: pd.DataFrame, scale: int = 1) -> dict:
        """
        计算所有指标
        
        Args:
            df: DataFrame with columns [open, high, low, close]
            scale: 周期缩放 (MN1=22, W1=5, D1=1)
        
        Returns:
            dict with base, trend, position, volatility, raw_score
        """
        h = df['high'].values
        l = df['low'].values
        c = df['close'].values
        n = len(c)
        
        base = self.calc_base(c, n, scale)
        trend = self.calc_trend(h, l, c, n, scale)
        pos = self.calc_position(c[-1], h, l, n, scale)
        vol = self.calc_volatility(h, l, c, n, scale)
        
        raw_score = base + trend * 4 + pos + vol
        
        return {
            'base': base,
            'trend': trend,
            'position': pos,
            'volatility': vol,
            'raw_score': raw_score,
        }
    
    def calc_base(self, c: np.ndarray, n: int, scale: int) -> int:
        """Base: 布林带宽分位"""
        per = self.bb_period * scale
        pw = self.bb_percentile_w
        
        if n < per + pw + 2:
            return 0
        
        bbw = []
        for i in range(pw + 1):
            start_idx = n - per - i - 1
            if start_idx - per + 1 < 0:
                break
            
            window = c[start_idx - per + 1:start_idx + 1]
            if len(window) < per:
                break
            
            avg = np.mean(window)
            std = np.std(window)
            if avg > 0:
                bbw.append((2 * self.bb_stddev * std) / avg)
        
        if len(bbw) < 2:
            return 0
        
        cur = bbw[-1]
        q20 = np.percentile(bbw, self.bb_compress_q * 100)
        
        return 8 if cur >= q20 else 0
    
    def calc_trend(self, h: np.ndarray, l: np.ndarray, c: np.ndarray, 
                   n: int, scale: int) -> int:
        """Trend: ADX 方向"""
        per = self.adx_period * scale
        sw = self.adx_slope * scale
        
        if n < per + sw + 3:
            return 0
        
        # 计算 ADX
        adx = []
        for i in range(per - 1, n - 1):
            tr_sum = 0
            pdm_sum = 0
            mdm_sum = 0
            
            for j in range(i - per + 1, i + 1):
                tr = max(h[j] - l[j], 
                        max(abs(h[j] - c[j+1]), abs(l[j] - c[j+1])))
                tr_sum += tr
                
                up = h[j] - h[j+1]
                dn = l[j+1] - l[j]
                pdm_sum += up if (up > dn and up > 0) else 0
                mdm_sum += dn if (dn > up and dn > 0) else 0
            
            atr = tr_sum / per
            pdi = (pdm_sum / per / atr * 100) if atr > 0 else 0
            mdi = (mdm_sum / per / atr * 100) if atr > 0 else 0
            dx = (abs(pdi - mdi) / (pdi + mdi) * 100) if (pdi + mdi) > 0 else 0
            
            if len(adx) == 0:
                adx.append(dx)
            else:
                adx.append((adx[-1] * (per - 1) + dx) / per)
        
        if len(adx) < sw + 1:
            return 0
        
        cur = adx[-1]
        prev = adx[-1 - sw] if len(adx) > sw else adx[0]
        
        if cur >= 25 and cur > prev:
            return 1
        if cur > 20:
            return 1
        if cur <= 13 and cur < prev:
            return 0
        return 0
    
    def calc_position(self, price: float, h: np.ndarray, l: np.ndarray,
                      n: int, scale: int) -> int:
        """Position: 分形 SR 突破"""
        k = self.fractal_k * scale
        lag = self.fractal_lag * scale
        
        if n < k + lag:
            return 0
        
        hk = k // 2
        sr_res = 0
        sr_sup = 0
        
        for i in range(hk, n - hk - lag):
            is_res = True
            is_sup = True
            
            for j in range(1, hk + 1):
                if h[i] <= h[i-j] or h[i] <= h[i+j]:
                    is_res = False
                if l[i] >= l[i-j] or l[i] >= l[i+j]:
                    is_sup = False
            
            if is_res:
                sr_res = h[i] if sr_res == 0 else max(sr_res, h[i])
            if is_sup:
                sr_sup = l[i] if sr_sup == 0 else min(sr_sup, l[i])
        
        if sr_res > 0 and price > sr_res:
            return 2
        if sr_sup > 0 and price < sr_sup:
            return 2
        return 0
    
    def calc_volatility(self, h: np.ndarray, l: np.ndarray, c: np.ndarray,
                        n: int, scale: int) -> int:
        """Volatility: ATR 扩张"""
        per = self.atr_period * scale
        
        if n < per + 2:
            return 0
        
        # 当前 ATR
        atr_cur = 0
        for i in range(per):
            tr = max(h[i] - l[i],
                    max(abs(h[i] - c[i+1]), abs(l[i] - c[i+1])))
            atr_cur += tr
        atr_cur /= per
        
        # 前一根 ATR
        atr_prev = 0
        for i in range(1, per + 1):
            tr = max(h[i] - l[i],
                    max(abs(h[i] - c[i+1]), abs(l[i] - c[i+1])))
            atr_prev += tr
        atr_prev /= per
        
        return 1 if atr_cur > atr_prev else 0
    
    def calc_sign(self, h: np.ndarray, l: np.ndarray, c: np.ndarray,
                  n: int, mn1_scale: int = 22) -> int:
        """Sign: 符号裁决 (MN1 SR 优先)"""
        k = self.fractal_k * mn1_scale
        hk = k // 2
        price = c[-1]
        
        sr_res = 0
        sr_sup = 0
        
        if n > k + self.fractal_lag * mn1_scale:
            for i in range(hk, n - hk - self.fractal_lag * mn1_scale):
                is_res = True
                is_sup = True
                
                for j in range(1, hk + 1):
                    if h[i] <= h[i-j] or h[i] <= h[i+j]:
                        is_res = False
                    if l[i] >= l[i-j] or l[i] >= l[i+j]:
                        is_sup = False
                
                if is_res:
                    sr_res = h[i] if sr_res == 0 else max(sr_res, h[i])
                if is_sup:
                    sr_sup = l[i] if sr_sup == 0 else min(sr_sup, l[i])
        
        if sr_res > 0 and price > sr_res:
            return 1
        if sr_sup > 0 and price < sr_sup:
            return -1
        if n >= 20:
            return 1 if c[0] > c[19] else -1
        return 1


def calc_hermass_state(df: pd.DataFrame, 
                       mn1_scale: int = 22,
                       w1_scale: int = 5) -> Tuple[int, int, int]:
    """
    计算 Hermass 4-bit State (MN1, W1, D1)
    
    Returns:
        (mn1_score, w1_score, d1_score)
        正值=多头, 负值=空头, 绝对值=0-15
    """
    ind = HermassIndicators()
    
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    n = len(c)
    
    sign = ind.calc_sign(h, l, c, n, mn1_scale)
    
    mn1_raw = ind.calc_all(df, mn1_scale)['raw_score']
    w1_raw = ind.calc_all(df, w1_scale)['raw_score']
    d1_raw = ind.calc_all(df, 1)['raw_score']
    
    mn1_score = sign * mn1_raw
    w1_score = sign * w1_raw
    d1_score = sign * d1_raw
    
    return mn1_score, w1_score, d1_score


def calc_ef_score(mn1: int, w1: int, d1: int) -> int:
    """
    计算 EF Score (E/F 计数)
    E/F = 绝对值 >= 14 的 State
    
    Returns:
        0-3 的 EF 计数
    """
    ef = 0
    if abs(mn1) >= 14:
        ef += 1
    if abs(w1) >= 14:
        ef += 1
    if abs(d1) >= 14:
        ef += 1
    return ef


def state_to_signal(mn1: int, w1: int, d1: int) -> str:
    """
    将 Hermass State 转换为交易信号
    
    Returns:
        "BUY" | "SELL" | "HOLD"
    """
    ef = calc_ef_score(mn1, w1, d1)
    
    if ef < 2:
        return "HOLD"
    
    # 方向判定
    if d1 >= 14:
        return "BUY"
    elif d1 <= -14:
        return "SELL"
    else:
        direction = 1 if (mn1 + w1 + d1) > 0 else -1
        return "BUY" if direction > 0 else "SELL"


if __name__ == "__main__":
    # 测试
    import numpy as np
    
    # 生成模拟数据
    np.random.seed(42)
    n = 1000
    data = {
        'open': np.cumsum(np.random.randn(n) * 0.1) + 100,
        'high': np.cumsum(np.random.randn(n) * 0.15) + 101,
        'low': np.cumsum(np.random.randn(n) * 0.15) + 99,
        'close': np.cumsum(np.random.randn(n) * 0.1) + 100,
    }
    df = pd.DataFrame(data)
    
    # 计算 State
    mn1, w1, d1 = calc_hermass_state(df)
    ef = calc_ef_score(mn1, w1, d1)
    sig = state_to_signal(mn1, w1, d1)
    
    print(f"MN1={mn1}, W1={w1}, D1={d1}")
    print(f"EF={ef}")
    print(f"Signal={sig}")
