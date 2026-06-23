//+------------------------------------------------------------------+
//|                                    Hermass_EF2_JPY_Trader.mq5     |
//|                                    v1.0  基于81,322条历史验证      |
//|                                                                   |
//|  入场规则: EF>=2 + EURJPY/USDJPY/GBPJPY                          |
//|  验证数据: EURJPY WR20=71% (179次), USDJPY WR20=64% (208次)      |
//|  止损: 2倍ATR(14)   止盈: 3倍ATR(14)                             |
//|  仓位: 2%风险                                                     |
//+------------------------------------------------------------------+
#property copyright "Hermass AI Trading"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
CTrade trade;

// === 不可变参数 (11个) ===
input int   InpBBPeriod      = 20;    // BB周期
input double InpBBStdDev     = 2.0;   // BB标准差
input int   InpBBPercentileW = 20;    // BB分位窗口
input double InpBBCompressQ  = 0.20;  // BB收缩分位
input int   InpATRPeriod     = 14;    // ATR周期
input int   InpADXPeriod     = 14;    // ADX周期
input int   InpADXSlope      = 3;     // ADX斜率窗口
input int   InpFractalK      = 5;     // 分形K
input int   InpFractalLag    = 3;     // 分形确认延迟
input int   InpMN1Scale      = 22;    // MN1缩放
input int   InpW1Scale       = 5;     // W1缩放

// === 交易参数 ===
input double InpRiskPct      = 2.0;   // 风险%
input double InpATRMultSL    = 2.0;   // ATR止损倍数
input double InpATRMultTP    = 3.0;   // ATR止盈倍数
input int    InpMaxHoldBars  = 20;    // 最大持仓(天)
input double InpMaxSpread    = 5.0;   // 最大点差(pips)
input bool   InpTradeEURJPY  = true;
input bool   InpTradeUSDJPY  = true;
input bool   InpTradeGBPJPY  = true;

// === 全局 ===
string TradeSymbols[3] = {"EURJPY", "USDJPY", "GBPJPY"};
bool   TradeActive[3]  = {false, false, false};
double Lots[3]         = {0, 0, 0};
int    HoldBars[3]     = {0, 0, 0};
datetime LastCheckTime;

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit() {
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) {
      Print("交易被禁用");
      return INIT_FAILED;
   }

   TradeActive[0] = InpTradeEURJPY;
   TradeActive[1] = InpTradeUSDJPY;
   TradeActive[2] = InpTradeGBPJPY;

   int active = 0;
   for(int i=0; i<3; i++) { if(TradeActive[i]) active++; }
   if(active == 0) {
      Print("无品种启用, 请设置 InpTradeXXX=true");
      return INIT_FAILED;
   }

   LastCheckTime = 0;
   Print("Hermass EF2 JPY Trader 已启动 | 品种:", active);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick() {
   datetime now = TimeCurrent();
   if(now - LastCheckTime < 60) return;
   LastCheckTime = now;

   for(int s=0; s<3; s++) {
      if(!TradeActive[s]) continue;

      string sym = TradeSymbols[s];
      double bid = SymbolInfoDouble(sym, SYMBOL_BID);
      double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
      double spread = (ask - bid) / SymbolInfoDouble(sym, SYMBOL_POINT);

      // 点差过滤
      if(spread > InpMaxSpread) continue;

      // 检查是否在交易中
      if(IsSymbolOpen(sym)) {
         HoldBars[s]++;
         // 最大持仓天数平仓
         if(HoldBars[s] >= InpMaxHoldBars) {
            CloseAll(sym);
            HoldBars[s] = 0;
         }
         continue;
      }

      // 每天只检查一次 (D1 bar close)
      static datetime lastBar[3] = {0,0,0};
      datetime barTime = iTime(sym, PERIOD_D1, 0);
      if(barTime == lastBar[s]) continue;
      lastBar[s] = barTime;

      // 计算State
      int mn1_score, w1_score, d1_score;
      if(!CalcHermassState(sym, mn1_score, w1_score, d1_score)) continue;

      int ef = 0;
      if(mn1_score == 14 || mn1_score == 15) ef++;  // 正E/F才计入
      if(w1_score  == 14 || w1_score  == 15) ef++;
      if(d1_score  == 14 || d1_score  == 15) ef++;
      // 注意: 负值(-14/-15)不算E/F，符合State规范

      if(ef < 2) continue;

      // 方向判定
      int direction = 0;
      if(d1_score >= 14) direction = 1;       // D1=E/F → 多头
      else if(d1_score <= -14) direction = -1; // D1=-E/-F → 空头
      else direction = ((mn1_score + w1_score + d1_score) > 0) ? 1 : -1;

      // ATR止损
      double atr = iATR(sym, PERIOD_D1, InpATRPeriod);
      if(atr <= 0) continue;
      atr = NormalizeDouble(atr, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS));

      // 仓位计算
      double accountEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      double riskAmount = accountEquity * InpRiskPct / 100.0;
      double slDistance = atr * InpATRMultSL;
      double tickVal = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
      double tickSize = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
      double pointVal = tickVal * (slDistance / tickSize);
      double lotSize = (pointVal > 0) ? riskAmount / pointVal : 0.01;
      lotSize = NormalizeDouble(MathMax(lotSize, SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN)),
                                (int)SymbolInfoInteger(sym, SYMBOL_DIGITS));

      double sl, tp, entryPrice;
      if(direction > 0) {
         entryPrice = ask;
         sl = entryPrice - slDistance;
         tp = entryPrice + slDistance * InpATRMultTP / InpATRMultSL;
         trade.Buy(lotSize, sym, 0, sl, tp, "EF2_JPY_Buy");
      } else {
         entryPrice = bid;
         sl = entryPrice + slDistance;
         tp = entryPrice - slDistance * InpATRMultTP / InpATRMultSL;
         trade.Sell(lotSize, sym, 0, sl, tp, "EF2_JPY_Sell");
      }

      Lots[s] = lotSize;
      HoldBars[s] = 0;
      PrintFormat("[EF2] %s %s %.2flots EF=%d(MN1=%d,W1=%d,D1=%d) SL=%f TP=%f",
                  sym, direction>0?"BUY":"SELL", lotSize,
                  ef, mn1_score, w1_score, d1_score, sl, tp);
   }
}

//+------------------------------------------------------------------+
//| 计算 Hermass 4-bit State                                         |
//+------------------------------------------------------------------+
bool CalcHermassState(string sym, int &mn1, int &w1, int &d1) {
   double h[], l[], c[];
   ArraySetAsSeries(h, true); ArraySetAsSeries(l, true); ArraySetAsSeries(c, true);

   int bars = MathMax(InpMN1Scale * (InpBBPeriod + InpBBPercentileW + 10), 1000);
   if(CopyHigh(sym, PERIOD_D1, 0, bars, h) < bars) return false;
   if(CopyLow(sym,  PERIOD_D1, 0, bars, l) < bars) return false;
   if(CopyClose(sym,PERIOD_D1, 0, bars, c) < bars) return false;

   double price = c[0];
   int sign = CalcSign(h, l, c, bars);

   mn1 = sign * CalcRawScore(h, l, c, bars, InpMN1Scale);
   w1  = sign * CalcRawScore(h, l, c, bars, InpW1Scale);
   d1  = sign * CalcRawScore(h, l, c, bars, 1);

   return true;
}

//+------------------------------------------------------------------+
//| 计算RawScore (4-bit magnitude, unsigned)                          |
//+------------------------------------------------------------------+
int CalcRawScore(const double &h[], const double &l[], const double &c[],
                 int n, int scale) {
   int base   = CalcBase(c, n, scale);
   int trend  = CalcTrend(h, l, c, n, scale);
   int pos    = CalcPosition(c[0], h, l, n, scale);
   int vol    = CalcVolatility(h, l, c, n, scale);
   return base + trend*4 + pos + vol;
}

//+------------------------------------------------------------------+
//| Base: 布林带宽分位                                                |
//+------------------------------------------------------------------+
int CalcBase(const double &c[], int n, int scale) {
   int per = InpBBPeriod * scale;
   int pw  = InpBBPercentileW;
   if(n < per + pw + 2) return 0;

   double bbw[];
   ArrayResize(bbw, pw+1);
   int count = 0;

   for(int i = 0; i <= pw; i++) {
      int startIdx = n - per - i - 1;
      if(startIdx < 0 || startIdx - per + 1 < 0) break;
      double sum = 0, sqSum = 0;
      for(int j = 0; j < per; j++) {
         int idx = startIdx - j;
         if(idx < 0) break;
         sum += c[idx];
         sqSum += c[idx] * c[idx];
      }
      double avg = sum / per;
      double std = MathSqrt(MathAbs(sqSum/per - avg*avg));
      double upper = avg + InpBBStdDev * std;
      double lower = avg - InpBBStdDev * std;
      if(avg > 0) {
         ArrayResize(bbw, count+1);
         bbw[count] = (upper - lower) / avg;
         count++;
      }
   }

   if(count < 2) return 0;
   double cur = bbw[count-1];
   ArraySort(bbw);
   double q20 = bbw[(int)(count * InpBBCompressQ)];
   return (cur < q20) ? 0 : 8;
}

//+------------------------------------------------------------------+
//| Trend: ADX方向                                                    |
//+------------------------------------------------------------------+
int CalcTrend(const double &h[], const double &l[], const double &c[],
              int n, int scale) {
   int per = InpADXPeriod * scale;
   int sw  = InpADXSlope * scale;
   if(n < per + sw + 3) return 0;

   int adxLen = n - per + 1;
   double adx[];
   ArrayResize(adx, adxLen);

   double trSum[1], pdmSum[1], mdmSum[1];

   for(int i = per-1; i < n-1; i++) {  // n-1 to avoid c[i+1] out of bounds
      trSum[0] = 0; pdmSum[0] = 0; mdmSum[0] = 0;
      for(int j = i - per + 1; j <= i; j++) {
         double tr = MathMax(h[j] - l[j], MathMax(MathAbs(h[j] - c[j+1]), MathAbs(l[j] - c[j+1])));
         trSum[0] += tr;
         double up = h[j] - h[j+1];
         double dn = l[j+1] - l[j];
         pdmSum[0] += (up > dn && up > 0) ? up : 0;
         mdmSum[0] += (dn > up && dn > 0) ? dn : 0;
      }
      double atr = trSum[0] / per;
      double pdi = (atr > 0) ? pdmSum[0] / per / atr * 100 : 0;
      double mdi = (atr > 0) ? mdmSum[0] / per / atr * 100 : 0;
      double dx  = (pdi + mdi > 0) ? MathAbs(pdi - mdi) / (pdi + mdi) * 100 : 0;
      int idx = i - per + 1;
      if(idx == 0) adx[0] = dx;
      else adx[idx] = (adx[idx-1] * (per-1) + dx) / per;
   }

   if(adxLen < sw + 1) return 0;
   double cur = adx[adxLen - 1];
   double prev = adx[adxLen - 1 - sw];

   if(cur >= 25 && cur > prev) return 1;
   if(cur > 20) return 1;
   if(cur <= 13 && cur < prev) return 0;
   return 0;
}

//+------------------------------------------------------------------+
//| Position: SR突破                                                   |
//+------------------------------------------------------------------+
int CalcPosition(double price, const double &h[], const double &l[],
                 int n, int scale) {
   int k = InpFractalK * scale;
   int lag = InpFractalLag * scale;
   if(n < k + lag) return 0;

   int hk = k / 2;
   double srRes = 0, srSup = 0;

   for(int i = hk; i < n - hk - lag; i++) {
      bool isRes = true, isSup = true;
      for(int j = 1; j <= hk; j++) {
         if(h[i] <= h[i-j] || h[i] <= h[i+j]) isRes = false;
         if(l[i] >= l[i-j] || l[i] >= l[i+j]) isSup = false;
      }
      if(isRes) srRes = (srRes == 0) ? h[i] : MathMax(srRes, h[i]);
      if(isSup) srSup = (srSup == 0) ? l[i] : MathMin(srSup, l[i]);
   }

   if(srRes > 0 && price > srRes) return 2;
   if(srSup > 0 && price < srSup) return 2;
   return 0;
}

//+------------------------------------------------------------------+
//| Volatility: ATR(14)扩张 — 当前ATR > 前一根ATR                      |
//+------------------------------------------------------------------+
int CalcVolatility(const double &h[], const double &l[], const double &c[],
                   int n, int scale) {
   int per = InpATRPeriod * scale;
   if(n < per + 2) return 0;

   // 计算当前和前一根的ATR
   double atrCur = 0, atrPrev = 0;
   for(int i = 0; i < per; i++) {
      double tr = MathMax(h[i] - l[i], MathMax(MathAbs(h[i] - c[i+1]), MathAbs(l[i] - c[i+1])));
      atrCur += tr;
   }
   atrCur /= per;

   for(int i = 1; i <= per; i++) {
      double tr = MathMax(h[i] - l[i], MathMax(MathAbs(h[i] - c[i+1]), MathAbs(l[i] - c[i+1])));
      atrPrev += tr;
   }
   atrPrev /= per;

   return (atrCur > atrPrev) ? 1 : 0;
}

//+------------------------------------------------------------------+
//| Sign: 符号裁决 (MN1 SR优先)                                       |
//+------------------------------------------------------------------+
int CalcSign(const double &h[], const double &l[], const double &c[], int n) {
   int k = InpFractalK * InpMN1Scale;
   int hk = k / 2;
   double srRes = 0, srSup = 0;
   double price = c[0];

   if(n > k + InpFractalLag * InpMN1Scale) {
      for(int i = hk; i < n - hk - InpFractalLag; i++) {
         bool isRes = true, isSup = true;
         for(int j = 1; j <= hk; j++) {
            if(h[i] <= h[i-j] || h[i] <= h[i+j]) isRes = false;
            if(l[i] >= l[i-j] || l[i] >= l[i+j]) isSup = false;
         }
         if(isRes) srRes = (srRes == 0) ? h[i] : MathMax(srRes, h[i]);
         if(isSup) srSup = (srSup == 0) ? l[i] : MathMin(srSup, l[i]);
      }
   }

   if(srRes > 0 && price > srRes) return 1;
   if(srSup > 0 && price < srSup) return -1;
   if(n >= 20) return (c[0] > c[19]) ? 1 : -1;
   return 1;
}

//+------------------------------------------------------------------+
//| 辅助函数                                                          |
//+------------------------------------------------------------------+
bool IsSymbolOpen(string sym) {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      if(PositionSelectByTicket(PositionGetTicket(i)) &&
         PositionGetString(POSITION_SYMBOL) == sym)
         return true;
   }
   return false;
}

void CloseAll(string sym) {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL) == sym) {
         trade.PositionClose(ticket);
         PrintFormat("[CLOSE] %s %s", sym, PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? "BUY" : "SELL");
      }
   }
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   for(int i=0; i<3; i++) {
      if(TradeActive[i]) CloseAll(TradeSymbols[i]);
   }
   Print("Hermass EF2 JPY Trader 已停止");
}
//+------------------------------------------------------------------+
