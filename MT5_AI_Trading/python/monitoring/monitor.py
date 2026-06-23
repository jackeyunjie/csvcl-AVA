"""
实时监控与告警系统
功能：
1. 实时P&L监控
2. 风险指标监控
3. 策略性能监控
4. 智能告警
"""

import time
import json
import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """告警信息"""
    level: str  # INFO/WARNING/CRITICAL
    category: str
    message: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskMetrics:
    """风险指标"""
    var_95: float = 0.0          # 95% VaR
    var_99: float = 0.0          # 99% VaR
    cvar_95: float = 0.0         # 95% CVaR
    max_drawdown: float = 0.0    # 最大回撤
    current_drawdown: float = 0.0 # 当前回撤
    sharpe_ratio: float = 0.0    # 夏普比率
    sortino_ratio: float = 0.0   # 索提诺比率
    win_rate: float = 0.0        # 胜率
    profit_factor: float = 0.0   # 盈亏比


class TradingMonitor:
    """
    交易监控系统
    
    监控内容：
    - 账户权益变化
    - 持仓风险
    - 策略表现
    - 系统健康状态
    """
    
    def __init__(
        self,
        max_history: int = 10000,
        alert_cooldown: int = 300,  # 告警冷却时间(秒)
        risk_check_interval: int = 60  # 风险检查间隔(秒)
    ):
        self.max_history = max_history
        self.alert_cooldown = alert_cooldown
        self.risk_check_interval = risk_check_interval
        
        # 历史数据
        self.equity_history: deque = deque(maxlen=max_history)
        self.pnl_history: deque = deque(maxlen=max_history)
        self.trade_history: deque = deque(maxlen=max_history)
        self.price_history: deque = deque(maxlen=max_history)
        
        # 告警记录
        self.alerts: deque = deque(maxlen=1000)
        self.last_alert_time: Dict[str, datetime] = {}
        
        # 风险阈值
        self.risk_thresholds = {
            'max_drawdown': 0.10,      # 最大回撤10%
            'daily_loss': 0.05,        # 单日亏损5%
            'var_95': 0.03,            # 95% VaR 3%
            'margin_level': 1.5,       # 保证金水平150%
            'consecutive_losses': 5    # 连续亏损5次
        }
        
        # 回调函数
        self.on_alert: Optional[Callable[[Alert], None]] = None
        self.on_risk_breach: Optional[Callable[[str, float], None]] = None
        
        # 监控线程
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # 峰值权益
        self.peak_equity = 0.0
        
        logger.info("TradingMonitor初始化完成")
    
    def start(self):
        """启动监控"""
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("监控已启动")
    
    def stop(self):
        """停止监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        logger.info("监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                self._check_risk_metrics()
                time.sleep(self.risk_check_interval)
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(5)
    
    def update_equity(self, equity: float, timestamp: Optional[datetime] = None):
        """
        更新权益数据
        
        Args:
            equity: 当前权益
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        self.equity_history.append({
            'timestamp': timestamp,
            'equity': equity
        })
        
        # 更新峰值
        if equity > self.peak_equity:
            self.peak_equity = equity
        
        # 检查回撤
        current_drawdown = (self.peak_equity - equity) / self.peak_equity if self.peak_equity > 0 else 0
        
        if current_drawdown > self.risk_thresholds['max_drawdown']:
            self._send_alert(
                level="CRITICAL",
                category="DRAWDOWN",
                message=f"最大回撤超限: {current_drawdown:.2%} > {self.risk_thresholds['max_drawdown']:.2%}",
                data={'current_drawdown': current_drawdown, 'threshold': self.risk_thresholds['max_drawdown']}
            )
    
    def update_trade(self, trade: Dict[str, Any]):
        """
        更新交易记录
        
        Args:
            trade: 交易信息字典
        """
        self.trade_history.append(trade)
        
        if 'profit' in trade:
            self.pnl_history.append(trade['profit'])
        
        # 检查连续亏损
        self._check_consecutive_losses()
    
    def update_price(self, symbol: str, price: float, timestamp: Optional[datetime] = None):
        """
        更新价格数据
        
        Args:
            symbol: 品种
            price: 价格
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        self.price_history.append({
            'symbol': symbol,
            'price': price,
            'timestamp': timestamp
        })
    
    def _check_risk_metrics(self):
        """检查风险指标"""
        if len(self.equity_history) < 2:
            return
        
        # 计算风险指标
        metrics = self.calculate_risk_metrics()
        
        # 检查VaR
        if metrics.var_95 > self.risk_thresholds['var_95']:
            self._send_alert(
                level="WARNING",
                category="VAR",
                message=f"VaR(95%)超限: {metrics.var_95:.2%}",
                data={'var_95': metrics.var_95}
            )
        
        # 检查夏普比率
        if metrics.sharpe_ratio < -1:
            self._send_alert(
                level="WARNING",
                category="PERFORMANCE",
                message=f"夏普比率过低: {metrics.sharpe_ratio:.2f}",
                data={'sharpe_ratio': metrics.sharpe_ratio}
            )
    
    def _check_consecutive_losses(self):
        """检查连续亏损"""
        if len(self.trade_history) < self.risk_thresholds['consecutive_losses']:
            return
        
        recent_trades = list(self.trade_history)[-self.risk_thresholds['consecutive_losses']:]
        losses = [t for t in recent_trades if t.get('profit', 0) < 0]
        
        if len(losses) >= self.risk_thresholds['consecutive_losses']:
            self._send_alert(
                level="CRITICAL",
                category="CONSECUTIVE_LOSSES",
                message=f"连续亏损{len(losses)}次，建议暂停交易",
                data={'consecutive_losses': len(losses)}
            )
    
    def calculate_risk_metrics(self) -> RiskMetrics:
        """计算风险指标"""
        metrics = RiskMetrics()
        
        if len(self.pnl_history) < 10:
            return metrics
        
        pnl = np.array(list(self.pnl_history))
        equity = np.array([e['equity'] for e in self.equity_history])
        
        # VaR & CVaR
        if len(pnl) > 0:
            metrics.var_95 = np.percentile(pnl, 5)
            metrics.var_99 = np.percentile(pnl, 1)
            metrics.cvar_95 = pnl[pnl <= metrics.var_95].mean() if any(pnl <= metrics.var_95) else 0
        
        # 最大回撤
        if len(equity) > 0:
            peak = np.maximum.accumulate(equity)
            drawdown = (peak - equity) / peak
            metrics.max_drawdown = np.max(drawdown)
            metrics.current_drawdown = drawdown[-1]
        
        # 夏普比率
        if len(pnl) > 1:
            returns = np.diff(equity) / equity[:-1]
            if len(returns) > 1 and np.std(returns) > 0:
                metrics.sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
        
        # 胜率
        wins = len([p for p in pnl if p > 0])
        metrics.win_rate = wins / len(pnl) if len(pnl) > 0 else 0
        
        # 盈亏比
        profits = [p for p in pnl if p > 0]
        losses = [p for p in pnl if p < 0]
        if losses:
            metrics.profit_factor = abs(sum(profits)) / abs(sum(losses))
        
        return metrics
    
    def _send_alert(self, level: str, category: str, message: str, data: Dict[str, Any]):
        """
        发送告警
        
        Args:
            level: 告警级别
            category: 告警类别
            message: 告警消息
            data: 附加数据
        """
        # 检查冷却时间
        alert_key = f"{level}:{category}"
        now = datetime.now()
        
        if alert_key in self.last_alert_time:
            elapsed = (now - self.last_alert_time[alert_key]).total_seconds()
            if elapsed < self.alert_cooldown:
                return
        
        self.last_alert_time[alert_key] = now
        
        alert = Alert(
            level=level,
            category=category,
            message=message,
            timestamp=now,
            data=data
        )
        
        self.alerts.append(alert)
        
        # 调用回调
        if self.on_alert:
            self.on_alert(alert)
        
        # 记录日志
        if level == "CRITICAL":
            logger.critical(f"[{category}] {message}")
            if self.on_risk_breach:
                self.on_risk_breach(category, data.get('current_drawdown', 0))
        elif level == "WARNING":
            logger.warning(f"[{category}] {message}")
        else:
            logger.info(f"[{category}] {message}")
    
    def get_status_report(self) -> Dict[str, Any]:
        """获取状态报告"""
        metrics = self.calculate_risk_metrics()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'equity': self.equity_history[-1]['equity'] if self.equity_history else 0,
            'peak_equity': self.peak_equity,
            'risk_metrics': {
                'var_95': metrics.var_95,
                'max_drawdown': metrics.max_drawdown,
                'current_drawdown': metrics.current_drawdown,
                'sharpe_ratio': metrics.sharpe_ratio,
                'win_rate': metrics.win_rate,
                'profit_factor': metrics.profit_factor
            },
            'trade_summary': {
                'total_trades': len(self.trade_history),
                'recent_alerts': len([a for a in self.alerts if 
                                     (datetime.now() - a.timestamp).total_seconds() < 3600])
            }
        }
    
    def get_recent_alerts(self, level: Optional[str] = None, limit: int = 50) -> List[Alert]:
        """
        获取最近告警
        
        Args:
            level: 过滤级别
            limit: 数量限制
        """
        alerts = list(self.alerts)
        if level:
            alerts = [a for a in alerts if a.level == level]
        return alerts[-limit:]
    
    def set_risk_threshold(self, key: str, value: float):
        """
        设置风险阈值
        
        Args:
            key: 阈值名称
            value: 阈值数值
        """
        if key in self.risk_thresholds:
            self.risk_thresholds[key] = value
            logger.info(f"风险阈值已更新: {key} = {value}")
        else:
            logger.warning(f"未知的风险阈值: {key}")


if __name__ == "__main__":
    # 测试代码
    monitor = TradingMonitor()
    
    def on_alert(alert: Alert):
        print(f"[{alert.level}] {alert.category}: {alert.message}")
    
    monitor.on_alert = on_alert
    monitor.start()
    
    # 模拟数据
    equity = 10000
    for i in range(100):
        equity += np.random.randn() * 50
        monitor.update_equity(equity)
        
        if np.random.random() > 0.5:
            profit = np.random.randn() * 100
            monitor.update_trade({'profit': profit})
        
        time.sleep(0.1)
    
    report = monitor.get_status_report()
    print("\n状态报告:")
    print(json.dumps(report, indent=2, default=str))
    
    monitor.stop()
