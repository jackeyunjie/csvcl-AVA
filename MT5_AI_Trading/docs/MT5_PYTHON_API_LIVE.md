# MT5 官方 Python API 实盘接入

本项目现在支持两种 MT5 接入方式：

- `python_api`：通过 MetaQuotes 官方 `MetaTrader5` Python 包连接本机 MT5 终端。
- `zeromq`：通过项目原有 EA + ZeroMQ 桥接。

实盘建议优先用 `python_api` 做账户、行情、下单闭环，因为链路更短；跨机器部署或需要 EA 主动推送 tick 时再用 ZeroMQ。

## 前置条件

1. Windows 机器已安装 MetaTrader 5 终端。
2. MT5 终端里已登录对应实盘或模拟账户。
3. 终端允许自动交易，并确认经纪商允许该账户交易。
4. 安装 Python 依赖：

```powershell
pip install -r requirements.txt
```

## 配置

编辑 `config/trading_config.yaml`：

```yaml
mt5:
  connection_mode: python_api
  python_api:
    terminal_path: ""
    login: null
    password_env: MT5_PASSWORD
    server: ""
    symbols: [EURUSD]

trading:
  live_trading: false
  dry_run: true
```

如果需要脚本自动登录：

```powershell
$env:MT5_PASSWORD="你的密码"
python .\connect_mt5_api.py --login 123456 --server "Broker-Live" --symbol EURUSD
```

## 只验证连接，不下单

```powershell
python .\connect_mt5_api.py --symbol EURUSD
```

这个脚本只会读取账户和 tick，不会发送订单。

## 开启实盘下单

先至少跑通模拟盘和 `dry_run` 日志。确认后再同时满足以下两个条件：

```yaml
trading:
  live_trading: true
  dry_run: false
  max_lot_size: 0.01

risk:
  hard_max_lot_size: 0.01
```

`live_trading=false` 或 `dry_run=true` 任一存在时，主流程都不会调用 `order_send()`。

## 重要说明

- 不要把实盘密码写进 YAML 或提交到 Git。
- 先用最小手数和模拟账户验证 `fill_policy`、品种名、点差、交易权限。
- `fill_policy: auto` 会按 FOK、IOC、RETURN 尝试经纪商可接受的成交方式。
- 本系统不是投资建议工具，实盘风险由账户持有人自行承担。
