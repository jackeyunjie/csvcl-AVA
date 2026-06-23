"""
主控制器 - 系统核心编排
功能：
1. 协调各模块工作
2. 交易循环管理
3. 配置加载
4. 异常处理
"""

import os
import sys
import yaml
import time
import signal
import logging
import argparse
import glob
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import pandas as pd

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mt5_bridge import MT5Bridge, TickData
from core.mt5_python_api import MT5PythonAPIBridge
from ai_engine.trading_strategy import TradingStrategy, RiskParameters
from ai_engine.llm_analyzer import LLMAnalyzer
from ai_engine.multi_symbol_manager import MultiSymbolStrategyManager, SymbolConfig, load_symbol_configs_from_dict
from ai_engine.signal_scorer import SignalScorer, SignalOutcome
from ai_engine.d1_risk_officer import D1RiskOfficer, latest_d1_hex_from_duckdb
from monitoring.monitor import TradingMonitor, Alert

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/trading.log')
    ]
)
logger = logging.getLogger(__name__)


class TradingSystem:
    """
    AI 量化交易系统主控制器
    
    工作流程：
    1. 连接MT5终端
    2. 接收实时行情
    3. AI分析生成信号
    4. 风控检查
    5. 执行交易
    6. 监控与告警
    """
    
    def __init__(self, config_path: str = "config/trading_config.yaml"):
        self.config = self._load_config(config_path)
        self.running = False
        
        # 初始化组件
        self.bridge: Optional[MT5Bridge] = None
        self.strategy: Optional[TradingStrategy] = None
        self.analyzer: Optional[LLMAnalyzer] = None
        self.monitor: Optional[TradingMonitor] = None
        self.multi_symbol_manager: Optional[MultiSymbolStrategyManager] = None
        self.signal_scorer: Optional[SignalScorer] = None

        # 状态
        self.current_symbol = self.config.get('trading', {}).get('symbol', 'EURUSD')
        self.current_tick: Optional[TickData] = None
        self.price_history = []

        # 安全状态
        self._last_trade_time: Dict[str, float] = {}  # 品种->上次交易时间
        self._signal_id_map: Dict[str, str] = {}  # ticket -> signal_id 映射
        
        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("TradingSystem初始化完成")
    
    def _load_config(self, path: str) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            'mt5': {
                'connection_mode': 'zeromq',
                'host': 'localhost',
                'pub_port': 5565,
                'req_port': 5566,
                'heartbeat_interval': 5,
                'auto_reconnect': True,
                'label': 'AVATRADE',
                'python_api': {
                    'terminal_path': '',
                    'login': None,
                    'password_env': 'MT5_PASSWORD',
                    'server': '',
                    'symbols': ['EURUSD'],
                    'poll_interval': 1.0,
                    'timeout': 60000,
                    'portable': False,
                    'deviation': 20,
                    'magic': 20260517,
                    'fill_policy': 'auto'
                }
            },
            'trading': {
                'symbol': 'EURUSD',
                'timeframe': 'H1',
                'min_confidence': 0.6,
                'enable_llm': False,
                'live_trading': False,      # 默认关闭真实交易
                'dry_run': True,            # 默认只模拟
                'max_lot_size': 0.1,        # 默认最大手数
                'signal_cooldown_seconds': 300  # 默认冷却期5分钟
            },
            'risk': {
                'max_risk_per_trade': 0.02,
                'max_risk_per_day': 0.06,
                'max_drawdown': 0.10,
                'max_positions': 5,
                'min_risk_reward': 1.5
            },
            'monitoring': {
                'alert_cooldown': 300,
                'risk_check_interval': 60
            }
        }
        
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    # 合并默认配置
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                        elif isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                if sub_key not in config[key]:
                                    config[key][sub_key] = sub_value
                logger.info(f"配置文件加载成功: {path}")
                return config
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}，使用默认配置")
        
        return default_config
    
    def initialize(self):
        """初始化所有组件"""
        logger.info("正在初始化系统组件...")
        
        # 1. 初始化MT5桥接
        mt5_config = self.config['mt5']
        connection_mode = mt5_config.get('connection_mode', 'zeromq')
        if connection_mode == 'python_api':
            api_config = mt5_config.get('python_api', {})
            symbols = api_config.get('symbols') or [self.current_symbol]
            if self.current_symbol not in symbols:
                symbols = [self.current_symbol] + list(symbols)
            self.bridge = MT5PythonAPIBridge(
                terminal_path=api_config.get('terminal_path') or None,
                login=api_config.get('login'),
                password_env=api_config.get('password_env', 'MT5_PASSWORD'),
                server=api_config.get('server') or None,
                symbols=symbols,
                poll_interval=api_config.get('poll_interval', 1.0),
                timeout=api_config.get('timeout', 60000),
                portable=api_config.get('portable', False),
                deviation=api_config.get('deviation', 20),
                magic=api_config.get('magic', 20260517),
                fill_policy=api_config.get('fill_policy', 'auto'),
                auto_reconnect=mt5_config.get('auto_reconnect', True)
            )
        else:
            self.bridge = MT5Bridge(
                mt5_host=mt5_config['host'],
                pub_port=mt5_config['pub_port'],
                req_port=mt5_config['req_port'],
                heartbeat_interval=mt5_config['heartbeat_interval']
            )
        
        # 设置行情回调
        self.bridge.on_tick = self._on_tick
        self.bridge.on_heartbeat = self._on_heartbeat
        self.bridge.on_disconnect = self._on_disconnect
        
        # 2. 初始化交易策略（State Hex）
        risk_params = RiskParameters(
            max_risk_per_trade=self.config['risk']['max_risk_per_trade'],
            max_risk_per_day=self.config['risk']['max_risk_per_day'],
            max_drawdown=self.config['risk']['max_drawdown'],
            max_positions=self.config['risk']['max_positions'],
            min_risk_reward=self.config['risk']['min_risk_reward'],
            max_lot_size=self.config['trading'].get('max_lot_size', 0.1)
        )
        self.strategy = TradingStrategy(
            risk_params=risk_params,
            min_confidence=self.config['trading']['min_confidence'],
            state_alignment_mode=self.config['trading'].get('state_alignment_mode', 'loose')
        )

        # 2.1 加载D1历史数据到State引擎
        d1_df = self._load_d1_data_for_symbol(self.current_symbol)
        if d1_df is not None and len(d1_df) > 0:
            self.strategy.load_d1_data(d1_df)
            logger.info(f"D1历史数据已加载到State引擎: {len(d1_df)}条")
        else:
            logger.warning("未能加载D1历史数据，State引擎将在首次信号时尝试用tick数据初始化")
        
        # 3. 初始化LLM分析器（可选）
        if self.config['trading'].get('enable_llm', False):
            try:
                self.analyzer = LLMAnalyzer()
                logger.info("LLM分析器已启用")
            except Exception as e:
                logger.warning(f"LLM分析器初始化失败: {e}")
        
        # 4. 初始化监控
        monitor_config = self.config['monitoring']
        self.monitor = TradingMonitor(
            alert_cooldown=monitor_config['alert_cooldown'],
            risk_check_interval=monitor_config['risk_check_interval']
        )
        self.monitor.on_alert = self._on_alert
        self.monitor.on_risk_breach = self._on_risk_breach

        # 5. 初始化信号评分系统（Phase 2）- 先初始化，以便多品种管理器可以引用
        scoring_cfg = self.config.get('trading', {}).get('signal_scoring', {})
        if scoring_cfg.get('enabled', False):
            self.signal_scorer = SignalScorer(
                max_history=scoring_cfg.get('max_history', 10000)
            )
            logger.info("信号评分系统已启用")

        # 6. 初始化多品种管理器（Phase 2）
        multi_cfg = self.config.get('trading', {}).get('multi_symbol', {})
        if multi_cfg.get('enabled', False):
            symbol_configs = load_symbol_configs_from_dict(
                multi_cfg.get('symbols', [])
            )
            self.multi_symbol_manager = MultiSymbolStrategyManager(
                symbol_configs=symbol_configs,
                risk_params=risk_params,
                global_max_positions=multi_cfg.get('global_max_positions', 5),
                signal_scorer=self.signal_scorer
            )
            logger.info(f"多品种管理器已启用 | 品种数: {len(symbol_configs)}")

            # 更新桥接品种列表（Python API模式）
            if connection_mode == 'python_api':
                all_symbols = [cfg.symbol for cfg in symbol_configs if cfg.enabled]
                if hasattr(self.bridge, 'symbols'):
                    self.bridge.symbols = all_symbols
                    logger.info(f"桥接品种列表已更新: {all_symbols}")

        logger.info("所有组件初始化完成")
    
    def start(self):
        """启动交易系统"""
        if not self.bridge:
            logger.error("系统未初始化")
            return
        
        logger.info("=" * 50)
        logger.info("AI 量化交易系统启动")
        logger.info("=" * 50)
        
        # 连接MT5
        if not self.bridge.connect():
            logger.error("无法连接到MT5终端")
            return
        
        # 启动监控
        self.monitor.start()
        
        # 获取账户信息
        try:
            d1_hex = None
            triplet = getattr(signal, "triplet", None)
            if triplet is not None:
                d1_hex = getattr(triplet, "d1_hex", None)
            if d1_hex is None:
                d1_hex = latest_d1_hex_from_duckdb(getattr(signal, "symbol", ""))

            d1_decision = D1RiskOfficer().assess(
                d1_hex,
                getattr(signal, "signal_type", None),
                lower_timeframe=self.config.get("trading", {}).get("timeframe", "H1"),
            )
            if not d1_decision.allowed:
                logger.error(
                    "[D1RiskOfficer] blocked %s %s | d1_hex=%s | reason=%s",
                    getattr(signal, "symbol", ""),
                    getattr(getattr(signal, "signal_type", None), "value", getattr(signal, "signal_type", "")),
                    d1_decision.d1_hex or "N/A",
                    d1_decision.reason,
                )
                return False

            account_info = self.bridge.get_account_info()
            logger.info(f"账户余额: {account_info.get('balance', 0):.2f}")
            logger.info(f"账户净值: {account_info.get('equity', 0):.2f}")
        except Exception as e:
            logger.warning(f"获取账户信息失败: {e}")
        
        self.running = True
        
        # 主循环
        logger.info("系统运行中，按Ctrl+C停止...")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("用户中断")
        finally:
            self.stop()
    
    def stop(self):
        """停止交易系统"""
        logger.info("正在停止系统...")
        self.running = False
        
        if self.monitor:
            self.monitor.stop()
        
        if self.bridge:
            self.bridge.disconnect()
        
        logger.info("系统已停止")
    
    def _on_tick(self, tick: TickData):
        """行情回调"""
        self.current_tick = tick
        mid_price = (tick.bid + tick.ask) / 2

        # 多品种模式：更新对应品种的价格历史
        if self.multi_symbol_manager:
            self.multi_symbol_manager.update_price(tick.symbol, {
                'timestamp': tick.timestamp,
                'bid': tick.bid,
                'ask': tick.ask,
                'mid': mid_price,
                'open': tick.bid,
                'high': tick.ask,
                'low': tick.bid,
                'close': mid_price,
                'volume': tick.volume
            })

            # 生成多品种信号
            self._process_multi_symbol_signals()
        else:
            # 单品种模式（向后兼容）
            self.price_history.append({
                'timestamp': tick.timestamp,
                'open': tick.bid,
                'high': tick.ask,
                'low': tick.bid,
                'close': mid_price,
                'volume': tick.volume
            })

            # 保持历史数据长度
            if len(self.price_history) > 500:
                self.price_history = self.price_history[-500:]

            # 更新State Hex策略的D1聚合（tick -> D1 bar）
            if self.strategy:
                new_d1 = self.strategy.update_with_tick(
                    timestamp=tick.timestamp,
                    price=mid_price,
                    volume=tick.volume
                )
                if new_d1:
                    logger.info(f"[StateHex] 新D1 bar完成: {new_d1['date']} | "
                               f"O={new_d1['open']:.5f} H={new_d1['high']:.5f} "
                               f"L={new_d1['low']:.5f} C={new_d1['close']:.5f}")

            # 更新监控
            if self.monitor:
                self.monitor.update_price(tick.symbol, mid_price)

            # 生成交易信号（数据足够时）
            if len(self.price_history) >= 50:
                self._process_trading_signal()
    
    def _process_multi_symbol_signals(self):
        """处理多品种交易信号（Phase 2）"""
        if not self.multi_symbol_manager:
            return

        try:
            # 获取账户信息
            account_info = self.bridge.get_account_info()
            balance = account_info.get('balance', 10000)

            # 获取各品种持仓数
            positions = self.bridge.get_positions()
            current_positions = {}
            if isinstance(positions, dict) and 'positions' in positions:
                for pos in positions['positions']:
                    sym = pos.get('symbol', '')
                    current_positions[sym] = current_positions.get(sym, 0) + 1

            # 生成所有品种的信号
            signals = self.multi_symbol_manager.generate_all_signals(
                account_balance=balance,
                current_positions=current_positions
            )

            if not signals:
                return

            # 检查全局持仓限制
            filtered = self.multi_symbol_manager.check_global_position_limit(
                current_positions, signals
            )

            for agg in filtered:
                signal = agg.signal

                # 记录信号到SignalScorer
                if self.signal_scorer:
                    sid = self.signal_scorer.register_signal_from_trading_signal(signal)
                    self._signal_id_map[sid] = signal.symbol

                triplet_info = ""
                if signal.triplet:
                    triplet_info = (f" | 三元组: ({signal.triplet.mn1_hex},"
                                   f"{signal.triplet.w1_hex},{signal.triplet.d1_hex})")

                logger.info(f"[MultiSymbol] 排名#{agg.rank} | "
                           f"{signal.signal_type.value} {signal.symbol} | "
                           f"评分: {agg.score:.3f} | "
                           f"信心度: {signal.confidence:.2%} | "
                           f"仓位: {signal.position_size:.2f}{triplet_info}")

                # 执行交易
                if signal.confidence >= self.strategy.min_confidence:
                    self._execute_signal(signal)
                else:
                    logger.info(f"[{signal.symbol}] 信心度不足，跳过交易")

        except Exception as e:
            logger.error(f"处理多品种信号失败: {e}")

    def _process_trading_signal(self):
        """处理单品种交易信号（State Hex，向后兼容）"""
        try:
            df = pd.DataFrame(self.price_history)

            # 获取账户信息
            account_info = self.bridge.get_account_info()
            balance = account_info.get('balance', 10000)

            # 获取持仓
            positions = self.bridge.get_positions()
            existing_positions = positions.get('count', 0)

            # 生成信号
            current_price = (self.current_tick.bid + self.current_tick.ask) / 2
            signal = self.strategy.generate_signal(
                df=df,
                symbol=self.current_symbol,
                current_price=current_price,
                account_balance=balance,
                existing_positions=existing_positions
            )

            if signal:
                # 记录信号到SignalScorer
                if self.signal_scorer:
                    self.signal_scorer.register_signal_from_trading_signal(signal)

                triplet_info = ""
                if signal.triplet:
                    triplet_info = (f" | 三元组: ({signal.triplet.mn1_hex},"
                                   f"{signal.triplet.w1_hex},{signal.triplet.d1_hex})")
                tags_info = f" | 标签: {', '.join(signal.state_tags)}" if signal.state_tags else ""

                logger.info(f"[StateHex] 信号: {signal.signal_type.value} | "
                           f"信心度: {signal.confidence:.2%} | "
                           f"对齐: {signal.state_alignment}{triplet_info}{tags_info}")

                # LLM分析（如果启用）
                if self.analyzer:
                    analysis = self.analyzer.analyze_market(
                        symbol=self.current_symbol,
                        current_price=current_price,
                        technical_indicators={}
                    )
                    logger.info(f"LLM分析: {analysis.sentiment.value} | "
                               f"风险等级: {analysis.risk_level}")
                    if analysis.risk_level == "HIGH":
                        signal.confidence *= 0.5
                        logger.warning("LLM检测到高风险，降低交易信心度")

                # 执行交易
                if signal.confidence >= self.strategy.min_confidence:
                    self._execute_signal(signal)
                else:
                    logger.info("信心度不足，跳过交易")

        except Exception as e:
            logger.error(f"处理交易信号失败: {e}")
    
    def _can_trade(self, symbol: str) -> bool:
        """
        检查是否可以交易（冷却期检查）
        
        Args:
            symbol: 交易品种
        
        Returns:
            是否允许交易
        """
        cooldown = self.config.get('trading', {}).get('signal_cooldown_seconds', 300)
        now = time.time()
        last_time = self._last_trade_time.get(symbol, 0)
        
        if now - last_time < cooldown:
            remaining = cooldown - (now - last_time)
            logger.info(f"[{symbol}] 冷却期内，还需 {remaining:.0f} 秒")
            return False
        
        return True
    
    def _is_trading_hours(self) -> bool:
        """
        检查当前是否在交易时段内
        
        规则：
        - 周末（周六、周日）不交易
        - 可扩展：添加具体交易时段限制
        
        Returns:
            是否允许交易
        """
        now = datetime.now()
        weekday = now.weekday()
        
        # 周末不交易 (5=周六, 6=周日)
        if weekday >= 5:
            logger.info(f"[时段] 周末不交易 (星期{weekday + 1})")
            return False
        
        return True
    
    def _pre_trade_risk_check(self, signal) -> bool:
        """
        执行前二次风控检查
        
        在信号生成后、订单发送前再次检查：
        1. 账户权益是否充足
        2. 当前回撤是否超限
        3. 连接状态是否正常
        
        Args:
            signal: 交易信号
        
        Returns:
            是否通过风控检查
        """
        try:
            # 检查1: 连接状态
            if not self.bridge or not self.bridge.is_connected:
                logger.error("[风控] MT5未连接，拒绝交易")
                return False
            
            # 检查2: 账户信息
            account_info = self.bridge.get_account_info()
            equity = account_info.get('equity', 0)
            balance = account_info.get('balance', 0)
            
            if equity <= 0:
                logger.error("[风控] 账户权益异常，拒绝交易")
                return False
            
            # 检查3: 回撤限制
            max_drawdown = self.config.get('risk', {}).get('max_drawdown', 0.10)
            current_drawdown = (balance - equity) / balance if balance > 0 else 0
            
            if current_drawdown > max_drawdown:
                logger.error(f"[风控] 回撤超限: {current_drawdown:.2%} > {max_drawdown:.2%}")
                return False
            
            # 检查4: 交易时段
            if not self._is_trading_hours():
                return False
            
            logger.info("[风控] 二次检查通过")
            return True
            
        except Exception as e:
            logger.error(f"[风控] 检查异常: {e}")
            return False
    
    def _execute_signal(self, signal):
        """
        执行交易信号（带安全保护）
        
        安全机制：
        1. 检查 live_trading 开关
        2. 检查 dry_run 模式
        3. 检查最大手数限制
        4. 检查冷却期
        5. 执行前二次风控
        """
        try:
            # --- 安全检查 1: live_trading 开关 ---
            live_trading = self.config.get('trading', {}).get('live_trading', False)
            if not live_trading:
                logger.warning(f"[安全] live_trading=false，跳过真实交易 | "
                              f"信号: {signal.signal_type.value} {signal.symbol}")
                return
            
            # --- 安全检查 2: dry_run 模式 ---
            dry_run = self.config.get('trading', {}).get('dry_run', True)
            if dry_run:
                logger.info(f"[DRY-RUN] 模拟执行 | 信号: {signal.signal_type.value} {signal.symbol} | "
                           f"手数: {signal.position_size:.2f} | 入场: {signal.entry_price:.5f} | "
                           f"止损: {signal.stop_loss:.5f} | 止盈: {signal.take_profit:.5f}")
                return
            
            # --- 安全检查 3: 最大手数限制 ---
            max_lot = self.config.get('trading', {}).get('max_lot_size', 0.1)
            hard_max = self.config.get('risk', {}).get('hard_max_lot_size', 0.1)
            effective_max = min(max_lot, hard_max)
            
            if signal.position_size > effective_max:
                logger.error(f"[安全] 手数超限，拒绝订单 | "
                            f"请求: {signal.position_size:.2f} | 限制: {effective_max:.2f}")
                return
            
            # --- 安全检查 4: 冷却期检查 ---
            if not self._can_trade(signal.symbol):
                return
            
            # --- 安全检查 5: 执行前二次风控 ---
            if not self._pre_trade_risk_check(signal):
                logger.warning(f"[风控] 二次检查未通过，取消交易")
                return
            
            # --- 执行真实交易 ---
            logger.warning(f"[LIVE] 执行真实交易 | {signal.signal_type.value} {signal.symbol} | "
                          f"手数: {signal.position_size:.2f}")
            
            if signal.signal_type.value in ['BUY', 'SELL']:
                result = self.bridge.send_order(
                    action=signal.signal_type.value,
                    symbol=signal.symbol,
                    volume=signal.position_size,
                    sl=signal.stop_loss,
                    tp=signal.take_profit,
                    comment=f"AI_{signal.confidence:.2f}"
                )
                
                if result.success:
                    # 记录交易时间（用于冷却期）
                    self._last_trade_time[signal.symbol] = time.time()
                    
                    logger.info(f"订单执行成功: Ticket={result.ticket}")
                    
                    # 更新监控
                    if self.monitor:
                        self.monitor.update_trade({
                            'ticket': result.ticket,
                            'symbol': result.symbol,
                            'action': result.action,
                            'volume': result.volume,
                            'price': result.price,
                            'profit': 0
                        })
                else:
                    logger.error(f"订单执行失败: {result.error}")
        
        except Exception as e:
            logger.error(f"执行交易失败: {e}")
    
    def _on_heartbeat(self, data: Dict):
        """心跳回调"""
        pass  # 心跳正常，无需处理
    
    def _on_disconnect(self):
        """断开连接回调 - 断连保护"""
        logger.warning("MT5连接断开 - 触发断连保护")
        self.running = False
        
        # 断连保护：清空价格历史，避免使用过期数据
        self.price_history = []
        self.current_tick = None
        
        # 断连保护：重置交易时间记录
        self._last_trade_time = {}
        
        logger.info("断连保护已激活：清空历史数据，停止信号生成")
    
    def _on_alert(self, alert: Alert):
        """告警回调"""
        logger.warning(f"[{alert.level}] {alert.category}: {alert.message}")
    
    def _on_risk_breach(self, category: str, value: float):
        """风险突破回调"""
        logger.critical(f"风险突破: {category} = {value:.2%}")
        
        # 紧急平仓
        try:
            positions = self.bridge.get_positions()
            for pos in positions.get('positions', []):
                self.bridge.close_position(pos['ticket'])
                logger.info(f"紧急平仓: Ticket={pos['ticket']}")
        except Exception as e:
            logger.error(f"紧急平仓失败: {e}")
    
    def _load_d1_data_for_symbol(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        加载D1历史数据用于State Hex引擎初始化

        尝试顺序:
        1. MT5 Python API直接获取（如果可用）
        2. 本地CSV文件（export_mt5_data.py导出）
        """
        # 方法1: 通过MT5 Python API获取
        try:
            if isinstance(self.bridge, MT5PythonAPIBridge):
                import MetaTrader5 as mt5
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 500)
                if rates is not None and len(rates) > 0:
                    df = pd.DataFrame(rates)
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    df = df.rename(columns={
                        'time': 'timestamp',
                        'tick_volume': 'volume'
                    })
                    logger.info(f"从MT5 API获取D1数据: {symbol} | {len(df)}条")
                    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.debug(f"从MT5 API获取D1数据失败: {e}")

        # 方法2: 从本地CSV加载
        try:
            data_dir = r"D:\HermassData\mt5\raw\sample"
            pattern = os.path.join(data_dir, f"MT5_AVATRADE_{symbol}_D1_*.csv")
            files = glob.glob(pattern)
            if files:
                latest_file = max(files, key=os.path.getmtime)
                df = pd.read_csv(latest_file)
                df['timestamp'] = pd.to_datetime(df['datetime'])
                logger.info(f"从本地CSV加载D1数据: {latest_file} | {len(df)}条")
                return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.debug(f"从本地加载D1数据失败: {e}")

        return None

    def _signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"收到信号: {signum}")
        self.stop()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI量化交易系统')
    parser.add_argument('--config', default='config/trading_config.yaml', help='配置文件路径')
    parser.add_argument('--symbol', default='EURUSD', help='交易品种')
    args = parser.parse_args()

    # 创建日志目录（必须在日志配置前创建）
    os.makedirs('logs', exist_ok=True)

    # 创建系统实例
    system = TradingSystem(config_path=args.config)

    # 初始化
    system.initialize()

    # 启动
    system.start()


if __name__ == "__main__":
    main()
