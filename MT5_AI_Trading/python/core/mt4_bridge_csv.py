"""
AI交易平台 — MT4 CSV数据接入模块

MT4端: AI_MT4_Bridge.mq4 每60秒写入 MT4\MQL4\Files\mt4_export.csv
Python端: 本模块读取该CSV，统一纳入AI分析管道

与MT5并行：最终信号 = 权重50%*MT5_State + 权重50%*MT4_State
"""

import os
import time
import pandas as pd
import logging

logger = logging.getLogger("MT4_Bridge")

# MT4 数据导出路径
MT4_EXPORT_DIR = r"C:\Users\MECHREVO\AppData\Roaming\MetaQuotes\Terminal\1F7FB83FCE28CDC848B46CF4612D1D35\MQL4\Files"
MT4_EXPORT_FILE = "mt4_export.csv"

class MT4DataSource:
    def __init__(self):
        self.filepath = os.path.join(MT4_EXPORT_DIR, MT4_EXPORT_FILE)
        self.last_mtime = 0
        self.data = None

    def available(self):
        return os.path.exists(self.filepath)

    def refresh(self):
        try:
            mtime = os.path.getmtime(self.filepath)
            if mtime == self.last_mtime:
                return False  # 无新数据
            self.last_mtime = mtime
            self.data = pd.read_csv(
                self.filepath,
                names=["symbol", "time", "open", "high", "low", "close",
                       "volume", "spread", "atr14", "adx14",
                       "boll_upper", "boll_lower", "bb_width"],
                skiprows=1
            )
            total = len(self.data)
            syms = self.data["symbol"].unique()
            logger.info(f"[MT4] 收到数据: {total}行 / {len(syms)}品种: {list(syms)}")
            return True
        except Exception as e:
            logger.warning(f"[MT4] 读取失败: {e}")
            return False

    def calc_state(self, symbol="EURUSD"):
        if self.data is None:
            return 0

        df = self.data[self.data["symbol"] == symbol].tail(20)
        if len(df) < 20:
            return 0

        last = df.iloc[-1]
        bb_widths = df["bb_width"].values
        bb_w_percentile = (bb_widths < last["bb_width"]).sum() / 20

        base = 8 if bb_w_percentile > 0.2 else 0  # 扩张/收缩
        trend = 4 if last["adx14"] > 20 else 0     # 趋势/无趋势
        pos = 2 if last["close"] > last["boll_upper"] else (
            -2 if last["close"] < last["boll_lower"] else 0)
        vol = 1 if last["atr14"] > df["atr14"].iloc[-2] else 0

        return base + trend + pos + vol

    def get_all_states(self):
        if self.data is None:
            return {}
        states = {}
        for sym in self.data["symbol"].unique():
            states[sym] = self.calc_state(sym)
        return states

mt4_source = MT4DataSource()
