//+------------------------------------------------------------------+
//| AI Trading Bridge EA for MT5 - ZeroMQ Connector                  |
//| 功能：1. PUB行情数据 2. REP接收交易指令 3. 心跳检测               |
//|                                                                    |
//| 依赖库：                                                            |
//|   - mql-zmq (https://github.com/dingmaotu/mql-zmq)               |
//|     需要: MQL5/Include/Zmq/Zmq.mqh                                |
//|     需要: MQL5/Libraries/libzmq.dll (Windows)                     |
//|   - JSON 指令使用本文件内置的轻量字段解析函数                       |
//|                                                                    |
//| 安全说明：                                                          |
//|   - 本EA只负责行情转发和指令执行，不生成交易信号                    |
//|   - 所有交易决策由Python AI系统做出                                 |
//|   - 首次使用请在模拟账户测试                                        |
//|   - 需要在EA属性中勾选"允许DLL导入"                                 |
//+------------------------------------------------------------------+
#property copyright "AI Quant Trading System"
#property version   "1.00"
#property strict
#property link      "https://github.com/dingmaotu/mql-zmq"

#include <Zmq/Zmq.mqh>

//--- 输入参数
input string   InpZmqHost      = "*";           // ZMQ绑定地址
input int      InpPubPort      = 5565;          // 行情发布端口 (AVATRADE)
input int      InpRepPort      = 5566;          // 交易指令端口 (AVATRADE)
input int      InpHeartbeatInterval = 5000;     // 心跳间隔(ms)
input int      InpMaxSlippage  = 10;            // 最大滑点(points)
input bool     InpEnableLogging = true;         // 启用日志

//--- ZMQ对象
Context zmqContext;
Socket  pubSocket(zmqContext, ZMQ_PUB);    // PUB - 行情广播
Socket  repSocket(zmqContext, ZMQ_REP);    // REP - 交易指令响应

//--- 状态变量
bool     g_isRunning = false;
ulong    g_lastHeartbeat = 0;
string   g_heartbeatMsg = "{\"type\":\"heartbeat\",\"time\":0}";

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    if(!InitZmqSockets())
    {
        Print("[ERROR] ZMQ初始化失败");
        return INIT_FAILED;
    }
    
    g_isRunning = true;
    g_lastHeartbeat = GetTickCount64();
    
    Print("[INFO] AI Trading Bridge 启动成功");
    Print("[INFO] PUB端口: ", InpPubPort, " | REP端口: ", InpRepPort);
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    g_isRunning = false;
    
    if(pubSocket.valid())
    {
        Print("[INFO] PUB socket 已关闭");
    }
    if(repSocket.valid())
    {
        Print("[INFO] REP socket 已关闭");
    }
    
    zmqContext.shutdown();
    Print("[INFO] AI Trading Bridge 已停止");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    if(!g_isRunning) return;
    
    // 1. 发布行情数据
    PublishTickData();
    
    // 2. 处理交易指令（非阻塞）
    ProcessTradeCommands();
    
    // 3. 发送心跳
    SendHeartbeat();
}

//+------------------------------------------------------------------+
//| 初始化ZMQ Sockets                                                |
//+------------------------------------------------------------------+
bool InitZmqSockets()
{
    // 创建PUB socket用于行情广播
    if(!pubSocket.valid())
    {
        Print("[ERROR] 创建PUB socket失败");
        return false;
    }
    
    string pubAddr = "tcp://" + InpZmqHost + ":" + IntegerToString(InpPubPort);
    if(!pubSocket.bind(pubAddr))
    {
        Print("[ERROR] PUB socket绑定失败: ", pubAddr);
        return false;
    }
    Print("[INFO] PUB socket绑定成功: ", pubAddr);
    
    // 创建REP socket用于交易指令
    if(!repSocket.valid())
    {
        Print("[ERROR] 创建REP socket失败");
        return false;
    }
    
    string repAddr = "tcp://" + InpZmqHost + ":" + IntegerToString(InpRepPort);
    if(!repSocket.bind(repAddr))
    {
        Print("[ERROR] REP socket绑定失败: ", repAddr);
        return false;
    }
    Print("[INFO] REP socket绑定成功: ", repAddr);
    
    return true;
}

//+------------------------------------------------------------------+
//| 发布Tick数据                                                     |
//+------------------------------------------------------------------+
void PublishTickData()
{
    MqlTick tick;
    if(!SymbolInfoTick(_Symbol, tick)) return;
    
    // 构建JSON行情数据
    string json = StringFormat(
        "{"
        "\"type\":\"tick\","
        "\"symbol\":\"%s\","
        "\"bid\":%.5f,"
        "\"ask\":%.5f,"
        "\"last\":%.5f,"
        "\"volume\":%I64u,"
        "\"time\":%I64d,"
        "\"time_msc\":%I64d,"
        "\"spread\":%.5f"
        "}",
        _Symbol,
        tick.bid,
        tick.ask,
        tick.last,
        tick.volume,
        tick.time,
        tick.time_msc,
        tick.ask - tick.bid
    );
    
    ZmqMsg msg(json);
    pubSocket.send(msg);
    
    if(InpEnableLogging)
        Print("[PUB] ", json);
}

//+------------------------------------------------------------------+
//| 处理交易指令                                                     |
//+------------------------------------------------------------------+
void ProcessTradeCommands()
{
    ZmqMsg request;
    
    // 非阻塞接收
    if(!repSocket.recv(request, true))
        return;
    
    string cmd = request.getData();
    if(InpEnableLogging)
        Print("[REP] 收到指令: ", cmd);
    
    // 解析并执行指令
    string response = ExecuteCommand(cmd);
    
    // 发送响应
    ZmqMsg reply(response);
    repSocket.send(reply);
    
    if(InpEnableLogging)
        Print("[REP] 发送响应: ", response);
}

//+------------------------------------------------------------------+
//| 执行交易指令                                                     |
//+------------------------------------------------------------------+
string ExecuteCommand(string json)
{
    string cmdType = JsonGetString(json, "type", "");
    if(cmdType == "")
    {
        return BuildErrorResponse("JSON解析失败或缺少type字段");
    }

    string result;
    
    if(cmdType == "order" || cmdType == "trade_signal")
        result = ExecuteOrder(json);
    else if(cmdType == "close" || cmdType == "close_position")
        result = ExecuteCloseBySymbol(json);
    else if(cmdType == "modify")
        result = ExecuteModify(json);
    else if(cmdType == "info")
        result = GetAccountInfo();
    else if(cmdType == "positions")
        result = GetPositions();
    else if(cmdType == "fundamental_signal")
        result = RecordFundamentalSignal(json);
    else if(cmdType == "ping")
        result = StringFormat("{\"type\":\"pong\",\"time\":%I64u}", GetTickCount64());
    else
        result = BuildErrorResponse("未知指令类型: " + cmdType);

    return result;
}

//+------------------------------------------------------------------+
//| 执行订单 (支持止损/止盈点数)                                     |
//+------------------------------------------------------------------+
string ExecuteOrder(string json)
{
    string symbol = JsonGetString(json, "symbol", "");
    if(symbol == "") symbol = _Symbol;
    
    string action = JsonGetString(json, "action", "");  // BUY/SELL
    double volume = JsonGetDouble(json, "volume", 0.0);
    double sl = JsonGetDouble(json, "sl", 0.0);
    double tp = JsonGetDouble(json, "tp", 0.0);
    int sl_pips = (int)JsonGetLong(json, "sl_pips", 0);
    int tp_pips = (int)JsonGetLong(json, "tp_pips", 0);
    string comment = JsonGetString(json, "comment", "");
    if(comment == "") comment = "AI_Trading";
    
    // 确定订单类型
    ENUM_ORDER_TYPE orderType;
    if(action == "BUY")
        orderType = ORDER_TYPE_BUY;
    else if(action == "SELL")
        orderType = ORDER_TYPE_SELL;
    else
        return BuildErrorResponse("无效的action: " + action);
    
    // 填充请求结构
    MqlTradeRequest request = {};
    request.action = TRADE_ACTION_DEAL;
    request.symbol = symbol;
    request.volume = volume;
    request.type = orderType;
    request.deviation = InpMaxSlippage;
    request.magic = 123456;  // EA Magic Number
    request.comment = comment;
    
    // 设置价格
    MqlTick tick;
    SymbolInfoTick(symbol, tick);
    if(orderType == ORDER_TYPE_BUY)
        request.price = tick.ask;
    else
        request.price = tick.bid;
    
    // 计算止损/止盈价格
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    
    if(sl_pips > 0)
    {
        // 根据点数计算SL价格
        double sl_distance = sl_pips * point * 10; // pips to price (1 pip = 10 points for 5-digit brokers)
        if(orderType == ORDER_TYPE_BUY)
            request.sl = NormalizeDouble(request.price - sl_distance, digits);
        else
            request.sl = NormalizeDouble(request.price + sl_distance, digits);
    }
    else if(sl > 0)
    {
        request.sl = sl;
    }
    
    if(tp_pips > 0)
    {
        double tp_distance = tp_pips * point * 10;
        if(orderType == ORDER_TYPE_BUY)
            request.tp = NormalizeDouble(request.price + tp_distance, digits);
        else
            request.tp = NormalizeDouble(request.price - tp_distance, digits);
    }
    else if(tp > 0)
    {
        request.tp = tp;
    }
    
    // 发送订单
    MqlTradeResult result = {};
    if(!OrderSend(request, result))
    {
        return BuildErrorResponse("订单发送失败: " + IntegerToString(GetLastError()));
    }
    
    // 构建成功响应
    string response = StringFormat(
        "{"
        "\"type\":\"order_result\","
        "\"success\":true,"
        "\"ticket\":%I64u,"
        "\"volume\":%.2f,"
        "\"price\":%.5f,"
        "\"sl\":%.5f,"
        "\"tp\":%.5f,"
        "\"symbol\":\"%s\","
        "\"action\":\"%s\","
        "\"comment\":\"%s\""
        "}",
        result.order,
        result.volume,
        result.price,
        request.sl,
        request.tp,
        symbol,
        action,
        comment
    );
    
    return response;
}

//+------------------------------------------------------------------+
//| 按品种平仓 (支持 close_position 指令)                            |
//+------------------------------------------------------------------+
string ExecuteCloseBySymbol(string json)
{
    string symbol = JsonGetString(json, "symbol", "");
    if(symbol == "") symbol = _Symbol;
    
    // 查找该品种的持仓并平仓
    bool found = false;
    string resultStr = "{";
    
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        ulong ticket = PositionGetTicket(i);
        if(PositionSelectByTicket(ticket))
        {
            if(PositionGetString(POSITION_SYMBOL) == symbol)
            {
                found = true;
                ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
                double volume = PositionGetDouble(POSITION_VOLUME);
                
                MqlTradeRequest request = {};
                request.action = TRADE_ACTION_DEAL;
                request.position = ticket;
                request.symbol = symbol;
                request.volume = volume;
                request.deviation = InpMaxSlippage;
                request.magic = 123456;
                
                MqlTick tick;
                SymbolInfoTick(symbol, tick);
                
                if(posType == POSITION_TYPE_BUY)
                {
                    request.type = ORDER_TYPE_SELL;
                    request.price = tick.bid;
                }
                else
                {
                    request.type = ORDER_TYPE_BUY;
                    request.price = tick.ask;
                }
                
                MqlTradeResult result = {};
                if(!OrderSend(request, result))
                {
                    return BuildErrorResponse("平仓失败: " + IntegerToString(GetLastError()));
                }
            }
        }
    }
    
    if(!found)
    {
        return StringFormat("{\"type\":\"close_result\",\"success\":true,\"symbol\":\"%s\",\"message\":\"无持仓\"}", symbol);
    }
    
    return StringFormat("{\"type\":\"close_result\",\"success\":true,\"symbol\":\"%s\"}", symbol);
}

//+------------------------------------------------------------------+
//| 平仓 (按ticket)                                                  |
//+------------------------------------------------------------------+
string ExecuteClose(string json)
{
    ulong ticket = (ulong)JsonGetLong(json, "ticket", 0);
    
    if(!PositionSelectByTicket(ticket))
    {
        return BuildErrorResponse(StringFormat("持仓不存在: %I64u", ticket));
    }
    
    string symbol = PositionGetString(POSITION_SYMBOL);
    ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    double volume = PositionGetDouble(POSITION_VOLUME);
    
    MqlTradeRequest request = {};
    request.action = TRADE_ACTION_DEAL;
    request.position = ticket;
    request.symbol = symbol;
    request.volume = volume;
    request.deviation = InpMaxSlippage;
    request.magic = 123456;
    
    MqlTick tick;
    SymbolInfoTick(symbol, tick);
    
    if(posType == POSITION_TYPE_BUY)
    {
        request.type = ORDER_TYPE_SELL;
        request.price = tick.bid;
    }
    else
    {
        request.type = ORDER_TYPE_BUY;
        request.price = tick.ask;
    }
    
    MqlTradeResult result = {};
    if(!OrderSend(request, result))
    {
        return BuildErrorResponse("平仓失败: " + IntegerToString(GetLastError()));
    }
    
    return StringFormat(
        "{\"type\":\"close_result\",\"success\":true,\"ticket\":%I64u}",
        ticket
    );
}

//+------------------------------------------------------------------+
//| 修改订单                                                         |
//+------------------------------------------------------------------+
string ExecuteModify(string json)
{
    ulong ticket = (ulong)JsonGetLong(json, "ticket", 0);
    double sl = JsonGetDouble(json, "sl", 0.0);
    double tp = JsonGetDouble(json, "tp", 0.0);
    
    if(!PositionSelectByTicket(ticket))
    {
        return BuildErrorResponse(StringFormat("持仓不存在: %I64u", ticket));
    }
    
    MqlTradeRequest request = {};
    request.action = TRADE_ACTION_SLTP;
    request.position = ticket;
    request.symbol = PositionGetString(POSITION_SYMBOL);
    
    if(sl > 0) request.sl = sl;
    if(tp > 0) request.tp = tp;
    
    MqlTradeResult result = {};
    if(!OrderSend(request, result))
    {
        return BuildErrorResponse("修改失败: " + IntegerToString(GetLastError()));
    }
    
    return "{\"type\":\"modify_result\",\"success\":true}";
}

//+------------------------------------------------------------------+
//| 获取账户信息                                                     |
//+------------------------------------------------------------------+
string GetAccountInfo()
{
    return StringFormat(
        "{"
        "\"type\":\"account_info\","
        "\"balance\":%.2f,"
        "\"equity\":%.2f,"
        "\"margin\":%.2f,"
        "\"free_margin\":%.2f,"
        "\"margin_level\":%.2f,"
        "\"profit\":%.2f,"
        "\"currency\":\"%s\""
        "}",
        AccountInfoDouble(ACCOUNT_BALANCE),
        AccountInfoDouble(ACCOUNT_EQUITY),
        AccountInfoDouble(ACCOUNT_MARGIN),
        AccountInfoDouble(ACCOUNT_MARGIN_FREE),
        AccountInfoDouble(ACCOUNT_MARGIN_LEVEL),
        AccountInfoDouble(ACCOUNT_PROFIT),
        AccountInfoString(ACCOUNT_CURRENCY)
    );
}

//+------------------------------------------------------------------+
//| 获取持仓列表                                                     |
//+------------------------------------------------------------------+
string GetPositions()
{
    string positions = "[";
    int total = PositionsTotal();
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        
        if(i > 0) positions += ",";
        
        positions += StringFormat(
            "{"
            "\"ticket\":%I64u,"
            "\"symbol\":\"%s\","
            "\"type\":\"%s\","
            "\"volume\":%.2f,"
            "\"open_price\":%.5f,"
            "\"current_price\":%.5f,"
            "\"sl\":%.5f,"
            "\"tp\":%.5f,"
            "\"profit\":%.2f,"
            "\"swap\":%.2f"
            "}",
            ticket,
            PositionGetString(POSITION_SYMBOL),
            PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? "BUY" : "SELL",
            PositionGetDouble(POSITION_VOLUME),
            PositionGetDouble(POSITION_PRICE_OPEN),
            PositionGetDouble(POSITION_PRICE_CURRENT),
            PositionGetDouble(POSITION_SL),
            PositionGetDouble(POSITION_TP),
            PositionGetDouble(POSITION_PROFIT),
            PositionGetDouble(POSITION_SWAP)
        );
    }
    
    positions += "]";
    
    return "{\"type\":\"positions\",\"count\":" + IntegerToString(total) + ",\"positions\":" + positions + "}";
}

//+------------------------------------------------------------------+
//| 记录基本面信号 (仅记录，不直接交易)                                |
//+------------------------------------------------------------------+
string RecordFundamentalSignal(string json)
{
    string symbol = JsonGetString(json, "symbol", "");
    string signal = JsonGetString(json, "signal", "");
    double score = JsonGetDouble(json, "score", 0.0);
    string reason = JsonGetString(json, "reason", "");
    double pe = JsonGetDouble(json, "pe", 0.0);
    double pb = JsonGetDouble(json, "pb", 0.0);
    
    // 记录到日志文件
    string filename = "FundamentalSignals_" + IntegerToString((int)TimeCurrent()) + ".csv";
    string header = "time,symbol,signal,score,reason,pe,pb\n";
    string data = StringFormat(
        "%s,%s,%s,%.1f,%s,%.2f,%.2f\n",
        TimeToString(TimeCurrent()),
        symbol,
        signal,
        score,
        reason,
        pe,
        pb
    );
    
    int handle = FileOpen(filename, FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_READ);
    if(handle != INVALID_HANDLE)
    {
        FileSeek(handle, 0, SEEK_END);
        if(FileTell(handle) == 0)
            FileWriteString(handle, header);
        FileWriteString(handle, data);
        FileClose(handle);
    }
    
    Print("[FUNDAMENTAL] ", symbol, " | ", signal, " | score=", score, " | ", reason);
    
    return StringFormat(
        "{\"type\":\"fundamental_ack\",\"symbol\":\"%s\",\"signal\":\"%s\",\"score\":%.1f}",
        symbol, signal, score
    );
}

//+------------------------------------------------------------------+
//| 发送心跳                                                         |
//+------------------------------------------------------------------+
void SendHeartbeat()
{
    ulong now = GetTickCount64();
    if(now - g_lastHeartbeat < (ulong)InpHeartbeatInterval) return;
    
    g_lastHeartbeat = now;
    
    string hb = StringFormat(
        "{\"type\":\"heartbeat\",\"time\":%I64u,\"symbol\":\"%s\"}",
        now,
        _Symbol
    );
    
    ZmqMsg msg(hb);
    pubSocket.send(msg);
}

//+------------------------------------------------------------------+
//| 构建错误响应                                                     |
//+------------------------------------------------------------------+
string BuildErrorResponse(string error)
{
    return StringFormat(
        "{\"type\":\"error\",\"success\":false,\"error\":\"%s\"}",
        JsonEscape(error)
    );
}

//+------------------------------------------------------------------+
//| Lightweight JSON helpers for flat Python command messages         |
//+------------------------------------------------------------------+
string JsonEscape(string value)
{
    StringReplace(value, "\\", "\\\\");
    StringReplace(value, "\"", "\\\"");
    return value;
}

string JsonGetRawValue(string json, string key, string defaultValue = "")
{
    string pattern = "\"" + key + "\"";
    int keyPos = StringFind(json, pattern);
    if(keyPos < 0) return defaultValue;

    int colonPos = StringFind(json, ":", keyPos + StringLen(pattern));
    if(colonPos < 0) return defaultValue;

    int pos = colonPos + 1;
    int length = StringLen(json);
    while(pos < length)
    {
        ushort ch = StringGetCharacter(json, pos);
        if(ch != ' ' && ch != '\t' && ch != '\r' && ch != '\n')
            break;
        pos++;
    }
    if(pos >= length) return defaultValue;

    if(StringGetCharacter(json, pos) == '"')
    {
        pos++;
        string value = "";
        bool escaped = false;
        for(int i = pos; i < length; i++)
        {
            ushort ch = StringGetCharacter(json, i);
            if(escaped)
            {
                value += ShortToString(ch);
                escaped = false;
                continue;
            }
            if(ch == '\\')
            {
                escaped = true;
                continue;
            }
            if(ch == '"')
                return value;
            value += ShortToString(ch);
        }
        return defaultValue;
    }

    int endPos = pos;
    while(endPos < length)
    {
        ushort ch = StringGetCharacter(json, endPos);
        if(ch == ',' || ch == '}' || ch == '\r' || ch == '\n')
            break;
        endPos++;
    }

    string value = StringSubstr(json, pos, endPos - pos);
    StringTrimLeft(value);
    StringTrimRight(value);
    return value == "" ? defaultValue : value;
}

string JsonGetString(string json, string key, string defaultValue = "")
{
    return JsonGetRawValue(json, key, defaultValue);
}

double JsonGetDouble(string json, string key, double defaultValue = 0.0)
{
    string raw = JsonGetRawValue(json, key, "");
    if(raw == "") return defaultValue;
    return StringToDouble(raw);
}

long JsonGetLong(string json, string key, long defaultValue = 0)
{
    string raw = JsonGetRawValue(json, key, "");
    if(raw == "") return defaultValue;
    return StringToInteger(raw);
}
//+------------------------------------------------------------------+
