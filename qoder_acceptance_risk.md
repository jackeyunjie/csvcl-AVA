# Qoder AI量化多周期交易平台 - 验收标准和风险评估

**版本**: V1.0  
**日期**: 2026-06-06  
**文档编号**: QODER-AR-001  

---

## 一、验收标准总览

### 1.1 验收原则

| 原则 | 说明 |
|------|------|
| **可量化** | 每个验收标准必须有明确的量化指标 |
| **可验证** | 每个标准必须有明确的验证方法和工具 |
| **可重复** | 验证过程可重复执行，结果一致 |
| **全覆盖** | 覆盖功能、性能、安全、稳定性所有维度 |

### 1.2 验收维度

```
┌─────────────────────────────────────────────────────────────┐
│                     验收维度矩阵                             │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   功能验收    │   性能验收    │   安全验收    │   稳定性验收   │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ • 功能完整性  │ • 响应时间   │ • 认证授权   │ • 可用性      │
│ • 正确性     │ • 吞吐量    │ • 数据安全   │ • 故障恢复    │
│ • 易用性     │ • 资源占用   │ • 交易安全   │ • 数据一致性  │
│ • 兼容性     │ • 可扩展性   │ • 审计合规   │ • 长期运行    │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

---

## 二、功能验收标准

### 2.1 自然语言策略生成模块

| 验收项 | 验收标准 | 验证方法 | 通过阈值 |
|--------|----------|----------|----------|
| **FR-NL-001** 意图解析 | 常见策略描述解析准确率 | 测试集100条策略描述 | >90% |
| **FR-NL-002** 代码生成 | 生成代码语法正确率 | 自动编译/解析验证 | >95% |
| **FR-NL-003** 策略验证 | 语法错误检出率 | 注入错误代码测试 | 100% |
| **FR-NL-004** 模板库 | 内置模板数量 | 统计 | ≥20个 |
| **FR-NL-005** 参数优化 | 参数建议合理性 | 专家评估 | >80%认可 |

**详细测试用例**:

```python
# 测试用例: 自然语言策略生成
TEST_CASES = [
    {
        "input": "创建一个均线金叉策略，MA5上穿MA20时买入，跌破MA10时卖出",
        "expected_type": "trend_following",
        "expected_indicators": ["MA"],
        "expected_entry": "MA5 crosses above MA20",
        "expected_exit": "Price crosses below MA10"
    },
    {
        "input": "当RSI低于30时买入，高于70时卖出",
        "expected_type": "mean_reversion",
        "expected_indicators": ["RSI"],
        "expected_entry": "RSI < 30",
        "expected_exit": "RSI > 70"
    },
    {
        "input": "基于State Hex多周期共振，D1/W1/MN1同时为bullish_trend时买入",
        "expected_type": "multi_factor",
        "expected_indicators": ["state_hex"],
        "expected_entry": "D1_hex == W1_hex == MN1_hex == bullish"
    }
]
```

### 2.2 智能策略回测模块

| 验收项 | 验收标准 | 验证方法 | 通过阈值 |
|--------|----------|----------|----------|
| **FR-BT-001** 回测速度 | H1数据5年量回测时间 | 计时测试 | <30秒 |
| **FR-BT-002** 数据对齐 | 多周期对齐误差 | 对比验证 | <0.01% |
| **FR-BT-003** 滑点模拟 | 滑点计算准确性 | 与实盘对比 | 误差<20% |
| **FR-BT-004** 绩效指标 | 指标计算准确性 | 与已知工具对比 | 误差<0.1% |
| **FR-BT-005** 报告生成 | HTML报告生成时间 | 计时测试 | <5秒 |
| **FR-BT-006** 多策略对比 | 同时回测策略数 | 压力测试 | ≥5个 |
| **FR-BT-007** 参数优化 | 网格搜索完成时间 | 计时测试 | <5分钟 |

**回测准确性验证**:

```python
def verify_backtest_accuracy():
    """验证回测引擎准确性"""
    
    # 1. 与已知结果对比
    known_strategy = SimpleMAStrategy(fast=5, slow=20)
    known_result = load_known_backtest_result("MA5_20_EURUSD_H1_2020_2023")
    
    our_result = engine.run(known_strategy, data)
    
    # 验证关键指标
    assert abs(our_result.total_return - known_result.total_return) < 0.1
    assert abs(our_result.sharpe_ratio - known_result.sharpe_ratio) < 0.01
    assert our_result.total_trades == known_result.total_trades
    
    # 2. 逐笔交易对比
    for our_trade, known_trade in zip(our_result.trades, known_result.trades):
        assert our_trade.entry_time == known_trade.entry_time
        assert abs(our_trade.pnl - known_trade.pnl) < 0.01
    
    print("回测准确性验证通过")
```

### 2.3 多Agent协作系统

| 验收项 | 验收标准 | 验证方法 | 通过阈值 |
|--------|----------|----------|----------|
| **AG-001** 研究Agent | 信号生成延迟 | 计时测试 | <30秒 |
| **AG-002** 执行Agent | 订单执行延迟 | 计时测试 | <2秒 |
| **AG-003** 风控Agent | 风险检查延迟 | 计时测试 | <1秒 |
| **AG-004** 交易员Agent | 信号到订单延迟 | 端到端测试 | <5秒 |
| **AG-005** 组合经理Agent | 再平衡触发准确性 | 模拟测试 | 100% |
| **AG-006** 观察Agent | 收缩检测准确率 | 历史数据回测 | >80% |
| **协作协议** | 消息传递可靠性 | 压力测试 | 100% |

**Agent协作验证场景**:

```python
# 场景1: 收缩→突破→交易完整链路
def test_contraction_to_trade_pipeline():
    """测试收缩到交易的完整链路"""
    
    # 1. 模拟收缩状态
    inject_market_data(symbol="EURUSD", contraction=True)
    
    # 2. 验证观察Agent检测收缩
    assert wait_for_agent_message("observer", "CONTRACTION_ALERT", timeout=10)
    
    # 3. 模拟突破
    inject_market_data(symbol="EURUSD", breakout=True, direction="UP")
    
    # 4. 验证突破确认
    assert wait_for_agent_message("observer", "BREAKOUT_CONFIRMED", timeout=10)
    
    # 5. 验证交易员Agent生成订单
    assert wait_for_agent_message("trader", "ORDER", timeout=15)
    
    # 6. 验证风控Agent检查
    assert wait_for_agent_message("risk", "RISK_RESPONSE", timeout=5)
    
    # 7. 验证执行Agent执行
    assert wait_for_execution(timeout=10)
    
    print("完整链路验证通过")

# 场景2: 风控拦截
def test_risk_interception():
    """测试风控拦截"""
    
    # 设置日亏损限额为0
    set_daily_loss_limit(0)
    
    # 触发亏损
    inject_market_data(symbol="EURUSD", price_drop=0.05)
    
    # 验证风控阻止新订单
    result = submit_order(symbol="EURUSD", volume=1.0)
    assert result.approved == False
    assert "日亏损限额" in result.reason
    
    print("风控拦截验证通过")
```

### 2.4 实时市场分析模块

| 验收项 | 验收标准 | 验证方法 | 通过阈值 |
|--------|----------|----------|----------|
| **FR-AN-001** 共振检测 | 共振检测准确率 | 历史数据验证 | >75% |
| **FR-AN-002** 收缩追踪 | 突破预警提前量 | 计时测试 | >10秒 |
| **FR-AN-003** 行业轮动 | 轮动信号准确率 | 历史回测 | >60% |
| **FR-AN-004** 状态卡片 | 状态更新延迟 | 计时测试 | <5秒 |
| **FR-AN-005** 实时数据 | 数据延迟 | 对比MT5时间戳 | <100ms |

---

## 三、性能验收标准

### 3.1 响应时间

| 操作 | 目标响应时间 | 可接受范围 | 测试方法 |
|------|-------------|-----------|----------|
| API登录 | <500ms | <1s | 100次请求平均 |
| 策略创建 | <3s | <5s | 100次请求平均 |
| 回测执行(5年H1) | <30s | <60s | 10次执行平均 |
| 报告生成 | <5s | <10s | 10次生成平均 |
| 行情查询 | <100ms | <200ms | 100次请求平均 |
| Agent状态查询 | <200ms | <500ms | 100次请求平均 |
| 订单提交 | <500ms | <1s | 100次请求平均 |

### 3.2 并发能力

| 指标 | 目标值 | 测试方法 |
|------|--------|----------|
| 并发回测数 | ≥5个 | 同时提交5个回测 |
| 并发Agent数 | ≥10个 | 启动10个Agent |
| API并发请求 | ≥100/秒 | 压力测试 |
| WebSocket连接 | ≥50个 | 并发连接测试 |

### 3.3 资源占用

| 资源 | 目标值 | 测试方法 |
|------|--------|----------|
| 内存占用(空闲) | <500MB | 系统监控 |
| 内存占用(回测中) | <2GB | 系统监控 |
| CPU占用(空闲) | <5% | 系统监控 |
| CPU占用(回测中) | <50% | 系统监控 |
| 磁盘I/O | <50MB/s | 系统监控 |

### 3.4 性能测试脚本

```python
import time
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor

class PerformanceTest:
    """性能测试套件"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = {}
    
    async def test_api_latency(self, endpoint: str, n_requests: int = 100):
        """测试API延迟"""
        latencies = []
        
        for _ in range(n_requests):
            start = time.time()
            await self._make_request(endpoint)
            latency = (time.time() - start) * 1000  # ms
            latencies.append(latency)
        
        self.results[endpoint] = {
            "avg": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": sorted(latencies)[int(n_requests * 0.95)],
            "p99": sorted(latencies)[int(n_requests * 0.99)],
            "min": min(latencies),
            "max": max(latencies)
        }
        
        return self.results[endpoint]
    
    async def test_backtest_performance(self, strategy_id: str, n_runs: int = 10):
        """测试回测性能"""
        durations = []
        
        for _ in range(n_runs):
            start = time.time()
            await self._run_backtest(strategy_id)
            duration = time.time() - start
            durations.append(duration)
        
        self.results["backtest"] = {
            "avg": statistics.mean(durations),
            "median": statistics.median(durations),
            "min": min(durations),
            "max": max(durations)
        }
        
        return self.results["backtest"]
    
    async def test_concurrent_backtests(self, n_concurrent: int = 5):
        """测试并发回测"""
        start = time.time()
        
        tasks = [self._run_backtest(f"strategy_{i}") for i in range(n_concurrent)]
        await asyncio.gather(*tasks)
        
        total_time = time.time() - start
        
        self.results["concurrent_backtest"] = {
            "n_concurrent": n_concurrent,
            "total_time": total_time,
            "avg_per_backtest": total_time / n_concurrent
        }
        
        return self.results["concurrent_backtest"]
    
    def generate_report(self) -> str:
        """生成性能测试报告"""
        report = []
        report.append("# 性能测试报告")
        report.append(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        for test_name, metrics in self.results.items():
            report.append(f"## {test_name}")
            for metric, value in metrics.items():
                if isinstance(value, float):
                    report.append(f"- {metric}: {value:.3f}")
                else:
                    report.append(f"- {metric}: {value}")
            report.append("")
        
        return "\n".join(report)
```

---

## 四、安全验收标准

### 4.1 认证授权

| 验收项 | 验收标准 | 验证方法 |
|--------|----------|----------|
| 密码强度 | 强制8位以上，含大小写+数字 | 尝试弱密码注册 |
| Token过期 | Access Token 1小时过期 | 等待1小时后访问 |
| Token刷新 | Refresh Token可刷新 | 使用Refresh Token |
| API Key安全 | 只显示一次，支持撤销 | 创建后尝试再次查看 |
| 权限控制 | 不同角色访问不同资源 | 越权访问测试 |

### 4.2 数据安全

| 验收项 | 验收标准 | 验证方法 |
|--------|----------|----------|
| 密码存储 | bcrypt哈希，不可反解 | 检查数据库 |
| API Key存储 | SHA256哈希 | 检查数据库 |
| 传输加密 | HTTPS/TLS | 抓包检查 |
| 敏感数据 | 加密存储 | 检查数据库 |

### 4.3 交易安全

| 验收项 | 验收标准 | 验证方法 |
|--------|----------|----------|
| 日亏损限额 | 触发后阻止新订单 | 模拟触发测试 |
| 最大回撤 | 触发后强制平仓 | 模拟触发测试 |
| 持仓限额 | 超过后拒绝订单 | 提交超额订单 |
| 异常检测 | 异常交易100%拦截 | 注入异常数据 |

### 4.4 安全测试用例

```python
class SecurityTest:
    """安全测试套件"""
    
    def test_sql_injection(self):
        """SQL注入测试"""
        malicious_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE strategies; --",
            "1' UNION SELECT * FROM users--"
        ]
        
        for payload in malicious_inputs:
            response = self.client.get(f"/strategies?name={payload}")
            assert response.status_code != 200 or "error" not in response.text.lower()
    
    def test_xss_protection(self):
        """XSS防护测试"""
        xss_payload = "<script>alert('xss')</script>"
        
        response = self.client.post("/strategies", json={
            "name": xss_payload,
            "description": xss_payload
        })
        
        # 验证响应中不包含未转义的脚本
        assert "<script>" not in response.text
    
    def test_unauthorized_access(self):
        """未授权访问测试"""
        # 不带Token访问
        response = self.client.get("/account/positions")
        assert response.status_code == 401
        
        # 使用无效Token
        response = self.client.get("/account/positions", 
                                    headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == 401
    
    def test_rate_limiting(self):
        """限流测试"""
        # 快速发送超过限流的请求
        responses = []
        for _ in range(150):  # 超过100/分钟限制
            responses.append(self.client.get("/market/quotes"))
        
        # 验证部分请求被限流
        assert any(r.status_code == 429 for r in responses)
    
    def test_risk_limits(self):
        """风控限额测试"""
        # 设置日亏损限额
        self.set_daily_loss_limit(-100)
        
        # 模拟亏损
        self.simulate_loss(150)
        
        # 验证新订单被拒绝
        response = self.place_order(symbol="EURUSD", volume=1.0)
        assert response.status_code == 403
        assert "日亏损限额" in response.json()["message"]
```

---

## 五、稳定性验收标准

### 5.1 可用性

| 指标 | 目标值 | 测试方法 |
|------|--------|----------|
| 系统可用性 | >99.5% | 7x24小时监控 |
| MT5连接稳定性 | 断线<1次/天 | 7天监控 |
| 数据完整性 | 100% | 数据校验 |

### 5.2 故障恢复

| 场景 | 目标恢复时间 | 测试方法 |
|------|-------------|----------|
| MT5断线 | <30秒 | 手动断开测试 |
| 数据库故障 | <60秒 | 模拟故障测试 |
| Agent崩溃 | <10秒 | 手动kill测试 |
| 系统重启 | <60秒 | 重启测试 |

### 5.3 长期运行

| 指标 | 目标值 | 测试方法 |
|------|--------|----------|
| 7天无崩溃 | 通过 | 7x24小时运行 |
| 内存泄漏 | 增长<10%/天 | 内存监控 |
| 日志增长 | <1GB/天 | 磁盘监控 |

### 5.4 稳定性测试脚本

```python
import time
import psutil
import asyncio
from datetime import datetime, timedelta

class StabilityTest:
    """稳定性测试套件"""
    
    def __init__(self, duration_hours: int = 168):  # 7天
        self.duration = duration_hours
        self.metrics = []
        self.errors = []
    
    async def run(self):
        """运行稳定性测试"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=self.duration)
        
        print(f"开始稳定性测试，预计运行到 {end_time}")
        
        while datetime.now() < end_time:
            try:
                # 收集系统指标
                metric = self._collect_metrics()
                self.metrics.append(metric)
                
                # 执行常规操作
                await self._perform_operations()
                
                # 每10分钟输出一次状态
                if len(self.metrics) % 10 == 0:
                    self._print_status()
                
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                self.errors.append({
                    "time": datetime.now(),
                    "error": str(e)
                })
                print(f"错误: {e}")
        
        return self._generate_report()
    
    def _collect_metrics(self) -> dict:
        """收集系统指标"""
        return {
            "timestamp": datetime.now(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": psutil.virtual_memory().used / 1024 / 1024,
            "disk_percent": psutil.disk_usage('/').percent,
            "connections": len(psutil.net_connections()),
        }
    
    async def _perform_operations(self):
        """执行常规操作"""
        # 模拟正常交易流程
        await self._simulate_tick()
        await self._check_agents()
        await self._query_status()
    
    def _print_status(self):
        """打印当前状态"""
        latest = self.metrics[-1]
        elapsed = (datetime.now() - self.metrics[0]["timestamp"]).total_seconds() / 3600
        
        print(f"运行时间: {elapsed:.1f}小时")
        print(f"CPU: {latest['cpu_percent']:.1f}%")
        print(f"内存: {latest['memory_percent']:.1f}%")
        print(f"错误数: {len(self.errors)}")
        print("-" * 40)
    
    def _generate_report(self) -> dict:
        """生成测试报告"""
        if not self.metrics:
            return {}
        
        memory_values = [m["memory_used_mb"] for m in self.metrics]
        
        return {
            "duration_hours": self.duration,
            "total_errors": len(self.errors),
            "error_rate": len(self.errors) / len(self.metrics) if self.metrics else 0,
            "avg_cpu": sum(m["cpu_percent"] for m in self.metrics) / len(self.metrics),
            "avg_memory": sum(memory_values) / len(memory_values),
            "memory_growth": memory_values[-1] - memory_values[0],
            "uptime_percent": (1 - len(self.errors) / len(self.metrics)) * 100 if self.metrics else 100,
            "errors": self.errors[:10]  # 前10个错误
        }
```

---

## 六、风险评估

### 6.1 技术风险矩阵

| 风险ID | 风险描述 | 概率 | 影响 | 风险等级 | 应对措施 | 责任人 |
|--------|----------|------|------|----------|----------|--------|
| R-001 | LLM生成代码质量不稳定，导致策略逻辑错误 | 高 | 高 | **严重** | 增加规则引擎校验，Fallback到模板，人工复核 | 架构师 |
| R-002 | 回测引擎性能不达标，无法满足30秒要求 | 中 | 高 | **高** | 提前POC验证，Numba加速，并行计算 | 后端工程师 |
| R-003 | MT5通信不稳定，导致交易延迟或失败 | 中 | 高 | **高** | 断线重连机制，本地缓存，备用通道 | 后端工程师 |
| R-004 | 多Agent协作复杂度高，出现死锁或消息丢失 | 中 | 中 | **中** | 简化协作协议，消息确认机制，超时重试 | 架构师 |
| R-005 | DuckDB并发性能瓶颈 | 低 | 中 | **低** | 读写分离，连接池，必要时迁移到TimescaleDB | 后端工程师 |
| R-006 | 历史数据质量差，影响回测准确性 | 中 | 中 | **中** | 数据质量检查，多数据源交叉验证 | 量化研究员 |
| R-007 | 安全漏洞被利用 | 低 | 高 | **中** | 安全审计，渗透测试，定期更新依赖 | 安全工程师 |
| R-008 | 第三方LLM API服务中断 | 中 | 中 | **中** | 多提供商备份，本地模型Fallback | 架构师 |
| R-009 | 团队成员流失 | 低 | 高 | **中** | 知识文档化，代码规范化，交叉培训 | 项目经理 |
| R-010 | 需求变更导致范围蔓延 | 高 | 中 | **高** | 敏捷开发，每2周评审，变更控制流程 | 项目经理 |

### 6.2 市场风险

| 风险ID | 风险描述 | 概率 | 影响 | 应对措施 |
|--------|----------|------|------|----------|
| M-001 | 策略实盘表现与回测差异大 | 高 | 高 | Walk-Forward验证，模拟盘验证，小资金实盘 |
| M-002 | 市场制度变化导致策略失效 | 中 | 高 | 策略衰减监控，定期重新优化 |
| M-003 | 黑天鹅事件导致大额亏损 | 低 | 高 | 严格风控，仓位分散，止损纪律 |
| M-004 | 流动性不足导致滑点过大 | 中 | 中 | 流动性监控，小单拆分，避开低流动性时段 |

### 6.3 风险监控机制

```python
class RiskMonitor:
    """风险监控器"""
    
    def __init__(self):
        self.risk_thresholds = {
            "code_quality": 0.90,      # 代码质量阈值
            "backtest_accuracy": 0.99,  # 回测准确性阈值
            "system_uptime": 0.995,     # 系统可用性阈值
            "test_coverage": 0.80,      # 测试覆盖率阈值
        }
        self.alerts = []
    
    def monitor(self, metrics: dict):
        """监控风险指标"""
        for metric, threshold in self.risk_thresholds.items():
            if metric in metrics:
                actual = metrics[metric]
                if actual < threshold:
                    self._alert(metric, actual, threshold)
    
    def _alert(self, metric: str, actual: float, threshold: float):
        """发送风险告警"""
        alert = {
            "time": datetime.now(),
            "metric": metric,
            "actual": actual,
            "threshold": threshold,
            "severity": "warning" if actual > threshold * 0.9 else "critical"
        }
        self.alerts.append(alert)
        
        # 发送通知
        print(f"风险告警: {metric} = {actual:.3f}, 阈值 = {threshold:.3f}")
    
    def get_risk_report(self) -> dict:
        """生成风险报告"""
        return {
            "total_alerts": len(self.alerts),
            "critical_alerts": len([a for a in self.alerts if a["severity"] == "critical"]),
            "warning_alerts": len([a for a in self.alerts if a["severity"] == "warning"]),
            "alerts": self.alerts
        }
```

---

## 七、验收流程

### 7.1 验收阶段

```
┌─────────────────────────────────────────────────────────────┐
│                     验收流程                                 │
├─────────────────────────────────────────────────────────────┤
│  1. 开发自测                                                 │
│     └── 开发人员完成单元测试和集成测试                        │
│                                                              │
│  2. 测试团队验收                                             │
│     └── 执行验收测试用例，生成测试报告                        │
│                                                              │
│  3. 性能验收                                                 │
│     └── 执行性能测试，验证性能指标                            │
│                                                              │
│  4. 安全验收                                                 │
│     └── 执行安全测试，修复漏洞                                │
│                                                              │
│  5. 用户验收(UAT)                                            │
│     └── 用户参与验收，确认满足需求                            │
│                                                              │
│  6. 上线审批                                                 │
│     └── 管理层审批，确认可上线                                │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 验收检查清单

#### 功能验收清单

- [ ] 自然语言策略生成：10种常见策略描述测试通过
- [ ] 代码生成：Python/MQL5/Pine Script三种格式生成正确
- [ ] 策略验证：语法错误100%检出
- [ ] 回测引擎：5年H1数据回测<30秒
- [ ] 回测准确性：与已知结果误差<0.1%
- [ ] 绩效指标：所有指标计算正确
- [ ] 报告生成：HTML报告生成<5秒
- [ ] Agent协作：收缩→突破→交易完整链路测试通过
- [ ] 风控系统：所有风控规则生效
- [ ] 实时分析：共振检测准确率>75%

#### 性能验收清单

- [ ] API平均响应时间<500ms
- [ ] 回测引擎5年数据<30秒
- [ ] 支持5个并发回测
- [ ] 支持10个并发Agent
- [ ] 内存占用<2GB
- [ ] CPU占用<50%

#### 安全验收清单

- [ ] 所有API需认证
- [ ] 密码bcrypt存储
- [ ] API Key哈希存储
- [ ] HTTPS传输
- [ ] SQL注入防护
- [ ] XSS防护
- [ ] 请求限流生效
- [ ] 风控限额生效
- [ ] 审计日志完整

#### 稳定性验收清单

- [ ] 7天无崩溃
- [ ] MT5断线30秒内恢复
- [ ] Agent崩溃10秒内重启
- [ ] 内存增长<10%/天
- [ ] 数据完整性100%

---

## 八、附录

### 8.1 测试环境要求

| 组件 | 配置 |
|------|------|
| 测试服务器 | 16核64G内存，500GB SSD |
| 操作系统 | Windows Server 2022 / Ubuntu 22.04 |
| Python | 3.11+ |
| MT5终端 | 2个实例 |
| 网络 | 100Mbps，延迟<10ms |

### 8.2 测试数据要求

| 数据类型 | 要求 |
|----------|------|
| 历史数据 | 5年H1数据，至少10个品种 |
| 实时数据 | MT5模拟账户 |
| 测试账户 | 模拟账户，余额$10000 |

### 8.3 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| V1.0 | 2026-06-06 | 初始版本 | Qoder AI |
