import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "python"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from ai_engine.strategy_miner import StrategyMiner, ExperimentConfig

# 扩展的patterns，覆盖更多高胜率可能性
patterns = [
    # 趋势跟随
    "D1=6,H1=4",
    "D1=6,H1=2",
    "D1=8,H1=4",
    "D1=8,H1=6",
    "D1=8,H1=8",
    "H1=4",
    "H1=6",
    "H1=8",
    "H4=8,H1=8",
    "H4=6,H1=4",
    # 看跌
    "D1=-E,H1=-4",
    "D1=-E,H1=-6",
    "D1=-E,H1=-8",
    "D1=-F,H1=-4",
    "D1=-F,H1=-6",
    "D1=-F,H1=-8",
    "D1=-F,H1=-F",
    "H1=-4",
    "H1=-6",
    "H1=-8",
    "H1=-E",
    "H1=-F",
    "H4=-E,H1=-4",
    "H4=-F,H1=-F",
    # 收缩/突破
    "H1+H4 squeeze",
    "D1+H4+H1 squeeze",
    # 多周期共振
    "multi_bull(3+)",
    "multi_bear(3+)",
    "H1 trend+",
    "H1 trend-",
    # 特定组合
    "D1=8,H4=8,H1=8",
    "D1=-F,H4=-F,H1=-F",
    "D1=8,H4=8,H1=-F",
    "D1=-F,H4=-F,H1=8",
]

markets = [
    'US_30','US_500','US_TECH100',
    'EURUSD','GBPUSD','USDJPY',
    'XAUUSD','USOIL','BTCUSD',
    'HK_50','CHINA_A50','GER30','JP225',
    'SILVER','BRENT_OIL','NATURAL_GAS',
    # 欧洲股指 (6只)
    'UK_100','FRANCE_40','EUROPE_50','SWISS_20','ITALY_40','GERMANY_TECH30',
    # 亚太/中国股指 (1只)
    'CHINA_INTERNET',
    '#APPLE','#MICROSOFT','#NVIDIA','#TESLA',
    '#AMAZON','#GOOGLE','#META','#NETFLIX','#AMD',
    '#JPMORGAN','#BERKSHIRE','#JOHNSON','#EXXON','#WALMART',
    # 美国大型科技股/金融 (8只)
    '#ALIBABA','#ADOBE','#SALESFORCE','#ZOOM','#UBER',
    '#AIRBNB','#SNAPCHAT','#COINBASE',
    # 美国传统行业 (5只)
    '#PEPSICO','#MCDONALDS','#STARBUCKS','#NIKE','#DISNEY',
    # 日本/亚太 (3只)
    '#SONY','#TAIWANSEMI','#PINDUODUO',
    # === 第三批：美股/中概 新增20只 ===
    # 科技/半导体 (5只)
    '#ORACLE','#INTEL','#CISCO','#QUALCOMM','#BROADCOM',
    # 金融/支付 (4只)
    '#VISA','#MASTERCARD','#BLACKROCK','#CITIGROUP',
    # 医疗/制药 (4只)
    '#PFIZER','#MERCK','#ABBVIE','#THERMOFISHER',
    # 消费/零售 (3只)
    '#COSTCO','#HOMEDEPOT','#TARGET',
    # 能源/工业/通信 (3只)
    '#CHEVRON','#BOEING','#VERIZON',
    # 中概股 (1只)
    '#BAIDU',
]

logger.info("=" * 60)
logger.info("Strategy Miner - 全品种深度扫描")
logger.info("=" * 60)
logger.info(f"品种: {len(markets)} 个")
logger.info(f"模式: {len(patterns)} 个")
logger.info(f"方向: long, short")
logger.info(f"持仓: 5, 10, 20 bars")
logger.info("=" * 60)

miner = StrategyMiner(state_db_path="data/h1_state.duckdb", mode="h1")

results = miner.batch_mine(
    patterns=patterns,
    directions=['long', 'short'],
    hold_bars_list=[5, 10, 20],
    markets=markets,
)

csv_path, md_path = miner.generate_report(results)

valid = [r for r in results if r.is_valid()]
logger.info("=" * 60)
logger.info("挖掘完成!")
logger.info(f"总实验: {len(results)}")
logger.info(f"有效策略: {len(valid)}")
logger.info(f"报告: {csv_path}")
logger.info("=" * 60)

# 打印Top 10
print("\n=== Top 10 策略 ===")
for i, r in enumerate(valid[:10], 1):
    print(f"#{i} | {r.config.state_pattern:20} | {r.config.direction:5} | {r.config.hold_bars:2}bars | 胜率:{r.win_rate:.1%} | 盈亏比:{r.profit_factor:.2f} | 评分:{r.score():.1f}")
