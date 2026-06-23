# KIMI 提示词 - OpenBB 数据源集成

## 你的角色
你是数据工程师，负责将 OpenBB SDK 集成到现有的基本面数据管道中。

## 背景
当前系统使用 SEC EDGAR + yfinance 拉取美股数据，但：
- yfinance 限流严重，几乎不可用
- SEC EDGAR 有时 SSL 连接失败
- 需要一个更稳定的数据源

OpenBB SDK 是开源金融数据终端，聚合了多个免费数据源，一个接口搞定。

## 任务清单

### 任务1: 安装 OpenBB
```bash
pip install openbb
```

### 任务2: 测试 OpenBB 数据拉取
创建测试脚本 `test_openbb.py`：
```python
from openbb import obb

# 测试股票基本面
symbol = "AAPL"

# 获取公司信息
info = obb.equity.profile(symbol)
print(f"公司: {info}")

# 获取财务报表
income = obb.equity.fundamental.income(symbol, period="quarter")
print(f"收入报表: {income}")

# 获取资产负债表
balance = obb.equity.fundamental.balance(symbol, period="quarter")
print(f"资产负债表: {balance}")

# 获取估值指标
ratios = obb.equity.fundamental.ratios(symbol)
print(f"财务比率: {ratios}")

# 获取价格数据
price = obb.equity.price.historical(symbol, start_date="2024-01-01")
print(f"价格数据: {price.tail()}")
```

### 任务3: 创建 OpenBB 数据拉取器
创建文件 `python/data/openbb_fetcher.py`，参考现有的 `sec_edgar_fetcher.py` 结构。

需要实现：
```python
class OpenBBFetcher:
    """OpenBB 数据拉取器"""

    def get_fundamentals(self, symbol: str) -> Dict:
        """获取完整基本面数据"""
        # 1. 获取公司信息 (sector, industry, market_cap)
        # 2. 获取财务比率 (PE, PB, PS, debt_to_equity, current_ratio)
        # 3. 获取增长数据 (revenue_growth, earnings_growth)
        # 4. 获取分红数据 (dividend_yield)
        # 返回格式与 SECEdgarFetcher.get_fundamentals() 一致

    def fetch_equity_batch(self, symbols: List[str]) -> List[Dict]:
        """批量拉取多只股票"""
        # 遍历 symbols，调用 get_fundamentals()
        # 处理异常，记录失败的股票
        # 返回成功拉取的数据列表
```

### 任务4: 更新 fundamental_pipeline.py
在现有的 `MultiSourceFetcher` 中添加 OpenBB 作为第三数据源：

数据源优先级：
1. SEC EDGAR (官方财报数据)
2. OpenBB (聚合多源，估值指标)
3. yfinance (备用，实时价格)

修改 `MultiSourceFetcher.fetch_equity_batch()` 方法：
```python
def fetch_equity_batch(self, symbols: List[str]) -> List[EquityFundamental]:
    records = []
    sec_failed = []
    openbb_failed = []

    for symbol in symbols:
        # 1. 尝试 SEC EDGAR
        try:
            sec_data = self.sec.get_fundamentals(symbol)
            if sec_data and sec_data.get("revenue"):
                record = self._convert_sec_to_equity(symbol, sec_data)
                if record:
                    records.append(record)
                    continue
        except:
            sec_failed.append(symbol)

        # 2. 尝试 OpenBB
        try:
            openbb_data = self.openbb.get_fundamentals(symbol)
            if openbb_data:
                record = self._convert_openbb_to_equity(symbol, openbb_data)
                if record:
                    records.append(record)
                    continue
        except:
            openbb_failed.append(symbol)

        # 3. yfinance 备用
        openbb_failed.append(symbol)

    # 批量拉取 yfinance 备用
    if openbb_failed:
        yf_records = self.yf.fetch_equity_batch(openbb_failed)
        records.extend(yf_records)

    return records
```

### 任务5: 验证完整管道
```bash
# 1. 加载种子数据（如果真实数据拉取失败）
python load_seed_data.py

# 2. 运行策略分析
python python/strategies/fundamental_strategy.py --analyze-all

# 3. 验证输出
# 应该看到 BUY/SELL 信号列表
```

### 任务6: 生成报告
输出格式：
```
=== OpenBB 集成报告 ===

1. 安装状态: [成功/失败]
2. 数据拉取测试:
   - AAPL: [成功/失败] PE=28.5, PB=45.2
   - MSFT: [成功/失败] PE=32.1, PB=12.8
   - ...
3. 管道集成: [成功/失败]
4. 策略分析: [X个BUY, Y个SELL]
5. 问题记录: [如有]
```

## 注意事项
- OpenBB 首次运行可能需要下载数据，耐心等待
- 如果 OpenBB 安装失败，可能是依赖冲突，尝试：`pip install openbb --no-deps` 然后手动安装缺失依赖
- 保持与现有代码风格一致（参考 `sec_edgar_fetcher.py`）
- 不要修改 `fundamental_pipeline.py` 的核心逻辑，只添加 OpenBB 数据源

## 参考文件
- `python/data/sec_edgar_fetcher.py` - SEC EDGAR 拉取器（参考结构）
- `python/data/fundamental_pipeline.py` - 主管道（需要修改）
- `load_seed_data.py` - 种子数据加载器（测试用）
- `kimi_work_order.md` - 完整工作指令

## 成功标准
- [ ] OpenBB 安装成功
- [ ] 至少能拉取 5 只股票的基本面数据
- [ ] 集成到 MultiSourceFetcher 后，策略分析能正常运行
- [ ] 输出 BUY/SELL 信号
