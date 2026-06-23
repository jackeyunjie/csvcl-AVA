"""
MT5 数据导出脚本
基于官方 MetaTrader5 Python API

导出品种:
- XAUUSD H1
- US500 H1
- EURUSD M15

字段:
symbol, datetime, open, high, low, close, tick_volume, volume, spread,
broker_name, server_timezone, source_name = MT5_AVATRADE

保存到: D:\HermassData\mt5\raw\sample\
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MT5DataExporter:
    """MT5 数据导出器"""

    def __init__(self, output_dir: str = r"D:\HermassData\mt5\raw\sample"):
        self.output_dir = output_dir
        self.manifest_dir = os.path.join(os.path.dirname(output_dir), "manifest")
        self.mt5 = None
        self.broker_name = ""
        self.server_timezone = ""

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.manifest_dir, exist_ok=True)

    def connect(self, terminal_path: Optional[str] = None,
                login: Optional[int] = None,
                password: Optional[str] = None,
                server: Optional[str] = None) -> bool:
        """连接MT5终端"""
        try:
            import MetaTrader5 as mt5
        except ImportError:
            logger.error("MetaTrader5包未安装，请运行: pip install MetaTrader5")
            return False

        self.mt5 = mt5

        kwargs = {"timeout": 60000}
        if terminal_path:
            kwargs["path"] = terminal_path
        if login:
            kwargs["login"] = login
        if password:
            kwargs["password"] = password
        if server:
            kwargs["server"] = server

        if not mt5.initialize(**kwargs):
            logger.error(f"MT5初始化失败: {mt5.last_error()}")
            return False

        account = mt5.account_info()
        if account is None:
            logger.error("无法获取账户信息")
            mt5.shutdown()
            return False

        self.broker_name = getattr(account, "company", "Unknown")
        self.server_timezone = "EET"  # MT5常用时区，实际应从symbol_info获取

        logger.info(f"MT5连接成功 | 经纪商: {self.broker_name} | 账号: {account.login}")
        return True

    def disconnect(self):
        """断开MT5连接"""
        if self.mt5:
            self.mt5.shutdown()
            logger.info("MT5已断开")

    def export_symbol(self, symbol: str, timeframe_str: str,
                      date_from: datetime, date_to: datetime) -> Optional[str]:
        """
        导出单个品种数据

        Args:
            symbol: 品种名，如 "XAUUSD"
            timeframe_str: 周期，如 "H1", "M15", "D1"
            date_from: 起始日期
            date_to: 结束日期

        Returns:
            保存的CSV文件路径
        """
        if not self.mt5:
            logger.error("MT5未连接")
            return None

        # 确保品种可见
        if not self._select_symbol(symbol):
            return None

        # 转换timeframe
        tf_map = {
            "M1": self.mt5.TIMEFRAME_M1,
            "M5": self.mt5.TIMEFRAME_M5,
            "M15": self.mt5.TIMEFRAME_M15,
            "M30": self.mt5.TIMEFRAME_M30,
            "H1": self.mt5.TIMEFRAME_H1,
            "H4": self.mt5.TIMEFRAME_H4,
            "D1": self.mt5.TIMEFRAME_D1,
            "W1": self.mt5.TIMEFRAME_W1,
            "MN1": self.mt5.TIMEFRAME_MN1,
        }
        timeframe = tf_map.get(timeframe_str.upper())
        if not timeframe:
            logger.error(f"不支持的周期: {timeframe_str}")
            return None

        logger.info(f"正在导出 {symbol} {timeframe_str} ({date_from.date()} ~ {date_to.date()})")

        # 获取历史数据
        rates = self.mt5.copy_rates_range(symbol, timeframe, date_from, date_to)
        if rates is None or len(rates) == 0:
            logger.error(f"无数据: {symbol} {timeframe_str}")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        # 标准化字段名
        df = df.rename(columns={
            'time': 'datetime',
            'tick_volume': 'tick_volume',
        })

        # 添加元数据字段
        df['symbol'] = symbol
        df['broker_name'] = self.broker_name
        df['server_timezone'] = self.server_timezone
        df['source_name'] = "MT5_AVATRADE"

        # 确保字段顺序
        columns = [
            'symbol', 'datetime', 'open', 'high', 'low', 'close',
            'tick_volume', 'volume', 'spread',
            'broker_name', 'server_timezone', 'source_name'
        ]
        for col in columns:
            if col not in df.columns:
                df[col] = None
        df = df[columns]

        # 保存CSV
        date_from_str = date_from.strftime("%Y%m%d")
        date_to_str = date_to.strftime("%Y%m%d") if date_to.date() != datetime.now().date() else "latest"
        filename = f"MT5_AVATRADE_{symbol}_{timeframe_str}_{date_from_str}_{date_to_str}.csv"
        filepath = os.path.join(self.output_dir, filename)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')

        logger.info(f"导出完成: {filepath} | {len(df)} 行")
        return filepath

    def _select_symbol(self, symbol: str) -> bool:
        """确保品种在MT5中可见"""
        info = self.mt5.symbol_info(symbol)
        if info is None:
            logger.error(f"品种不存在: {symbol}")
            return False
        if not info.visible:
            if not self.mt5.symbol_select(symbol, True):
                logger.error(f"无法选择品种: {symbol}")
                return False
        return True

    def export_batch(self, configs: List[Dict]) -> List[str]:
        """批量导出"""
        exported = []
        for cfg in configs:
            filepath = self.export_symbol(
                symbol=cfg['symbol'],
                timeframe_str=cfg['timeframe'],
                date_from=cfg['date_from'],
                date_to=cfg.get('date_to', datetime.now())
            )
            if filepath:
                exported.append(filepath)
        return exported

    def generate_manifest(self, exported_files: List[str]) -> str:
        """生成manifest JSON"""
        manifests = []
        for filepath in exported_files:
            df = pd.read_csv(filepath)
            symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else "unknown"
            timeframe = os.path.basename(filepath).split('_')[3]

            manifest = {
                "source_name": "MT5_KVB",
                "broker_name": self.broker_name,
                "symbol": symbol,
                "timeframe": timeframe,
                "timezone": self.server_timezone,
                "bar_type": "CFD" if symbol in ["XAUUSD", "EURUSD", "US500"] else "unknown",
                "date_from": df['datetime'].min() if 'datetime' in df.columns else None,
                "date_to": df['datetime'].max() if 'datetime' in df.columns else None,
                "rows": len(df),
                "fields": list(df.columns),
                "volume_semantics": "tick_volume for forex/CFD; not real exchange volume",
                "contract_type": "CFD",
                "notes": "MT5 tick_volume is tick count, not real traded volume. CFD is not exchange-traded stock."
            }
            manifests.append(manifest)

        manifest_path = os.path.join(self.manifest_dir, f"mt5_manifest_{datetime.now().strftime('%Y%m%d')}.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifests, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Manifest已生成: {manifest_path}")
        return manifest_path

    def generate_field_mapping(self) -> str:
        """生成字段说明文档"""
        content = """# MT5 字段映射说明

日期: {date}

## 字段说明

| 字段 | 含义 | 说明 |
|---|---|---|
| symbol | 品种名称 | MT5中的品种代码 |
| datetime | K线开始时间 | 该K线的开盘时间戳 |
| open | 开盘价 | 该周期第一个报价 |
| high | 最高价 | 该周期最高报价 |
| low | 最低价 | 该周期最低报价 |
| close | 收盘价 | 该周期最后一个报价 |
| tick_volume | tick计数 | MT5外汇/CFD中的tick次数，不是真实成交量 |
| volume | 真实成交量 | 部分经纪商提供，外汇CFD常为0或tick_volume |
| spread | 点差 | 该周期平均点差（部分经纪商提供） |
| broker_name | 经纪商名称 | 数据来源经纪商 |
| server_timezone | 服务器时区 | MT5服务器时区（常为EET） |
| source_name | 数据源标识 | 固定为 MT5_AVATRADE |

## 重要边界

1. **datetime**: K线开始时间（开盘时间），不是结束时间。
2. **timezone**: MT5服务器时区，通常为 EET (Eastern European Time, UTC+2/UTC+3)。
3. **volume**: MT5外汇/CFD的volume是tick_volume（tick计数），不是交易所真实成交量。
4. **spread**: 单位为点（points），不是货币单位。
5. **品种类型**: XAUUSD/EURUSD/US500 均为CFD差价合约，不是交易所现货/期货。
6. **复权**: 外汇/CFD无需复权。
7. **price-first**: 可用于价格优先分析。
8. **volume/moneyflow**: tick_volume不能替代真实成交量做资金流分析，仅作流动性参考。

## 使用限制

- 本数据仅用于状态计算和回测研究，不生成交易建议。
- 所有时间戳必须经过审计后才能聚合到更高周期。
- CFD数据与交易所真实数据存在差异，策略验证时需注明。
""".format(date=datetime.now().strftime('%Y-%m-%d'))

        mapping_path = os.path.join(self.manifest_dir, f"mt5_field_mapping_{datetime.now().strftime('%Y%m%d')}.md")
        with open(mapping_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"字段说明已生成: {mapping_path}")
        return mapping_path


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数：导出MT5样本数据"""
    print("=" * 60)
    print("MT5 Data Exporter")
    print("=" * 60)

    exporter = MT5DataExporter()

    # 连接MT5（使用当前已打开的终端）
    if not exporter.connect():
        print("\n连接失败。请确保MT5终端已打开，或提供terminal_path参数。")
        print("用法: python export_mt5_data.py [--terminal_path PATH] [--login LOGIN] [--password PASSWORD] [--server SERVER]")
        return

    # 导出配置
    configs = [
        {
            'symbol': 'XAUUSD',
            'timeframe': 'H1',
            'date_from': datetime(2023, 1, 1),
            'date_to': datetime.now()
        },
        {
            'symbol': 'US500',
            'timeframe': 'H1',
            'date_from': datetime(2023, 1, 1),
            'date_to': datetime.now()
        },
        {
            'symbol': 'EURUSD',
            'timeframe': 'M15',
            'date_from': datetime(2023, 1, 1),
            'date_to': datetime.now()
        },
    ]

    # 批量导出
    exported = exporter.export_batch(configs)

    # 生成manifest和字段说明
    if exported:
        exporter.generate_manifest(exported)
        exporter.generate_field_mapping()

    exporter.disconnect()

    # 输出汇总
    print("\n" + "=" * 60)
    print("Export Summary")
    print("=" * 60)
    for filepath in exported:
        df = pd.read_csv(filepath)
        filename = os.path.basename(filepath)
        print(f"\n  {filename}")
        print(f"    路径: {filepath}")
        print(f"    行数: {len(df)}")
        print(f"    日期范围: {df['datetime'].min()} ~ {df['datetime'].max()}")
        print(f"    时区: {df['server_timezone'].iloc[0] if 'server_timezone' in df.columns else 'N/A'}")
        print(f"    bar_type: {df['source_name'].iloc[0] if 'source_name' in df.columns else 'N/A'}")
        print(f"    volume含义: tick_volume (tick计数)")
        print(f"    含spread: {'spread' in df.columns and df['spread'].notna().any()}")

    print("\n" + "=" * 60)
    print(f"完成 | 导出{len(exported)}个文件")
    print("=" * 60)


if __name__ == "__main__":
    main()
