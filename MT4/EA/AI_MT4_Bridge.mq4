//+------------------------------------------------------------------+
//|                                              AI_MT4_Bridge.mq4    |
//|                                   MT4数据桥接EA (CSV导出方式)     |
//|                            功能: 将MT4行情+指标数据实时写入CSV     |
//|                            Python端每60秒读取一次CSV进行分析       |
//+------------------------------------------------------------------+
#property copyright "AI Trading Platform"
#property version   "1.00"

extern string ExportFile = "mt4_export.csv";   // 导出文件名
extern int    ExportInterval = 60;              // 导出间隔(秒)
extern string Symbols = "EURUSD,GBPUSD,USDJPY,XAUUSD,BTCUSD"; // 导出品种
extern int    MaxBars = 100;                    // 每品种导出K线数

datetime lastExport = 0;
int fileHandle = -1;
string fullPath = "";

//+------------------------------------------------------------------+
int init()
  {
   fullPath = TerminalPath() + "\\MQL4\\Files\\" + ExportFile;
   return(0);
  }

int deinit()
  {
   if(fileHandle >= 0) FileClose(fileHandle);
   return(0);
  }

int start()
  {
   if(TimeCurrent() - lastExport < ExportInterval)
      return(0);
   
   lastExport = TimeCurrent();

   // 删除旧文件重新写入
   FileDelete(ExportFile);
   fileHandle = FileOpen(ExportFile, FILE_CSV|FILE_WRITE, ',');
   if(fileHandle < 0)
     {
      Print("AI_Bridge: 无法写入 ", ExportFile);
      return(0);
     }

   // 写入表头
   FileWrite(fileHandle, "symbol,time,open,high,low,close,volume,spread,atr14,adx14,boll_upper,boll_lower,bb_width");

   // 按逗号分割品种列表
   string symList = Symbols;
   while(StringLen(symList) > 0)
     {
      string sym = "";
      int commaPos = StringFind(symList, ",");
      if(commaPos >= 0)
        {
         sym = StringSubstr(symList, 0, commaPos);
         symList = StringSubstr(symList, commaPos + 1);
        }
      else
        {
         sym = symList;
         symList = "";
        }
      
      if(StringLen(sym) == 0) continue;

      // 导出该品种的K线数据
      for(int i = MaxBars; i >= 1; i--)
        {
         datetime t = iTime(sym, PERIOD_H1, i);
         if(t == 0) continue;

         double o = iOpen(sym, PERIOD_H1, i);
         double h = iHigh(sym, PERIOD_H1, i);
         double l = iLow(sym, PERIOD_H1, i);
         double c = iClose(sym, PERIOD_H1, i);
         double v = iVolume(sym, PERIOD_H1, i);
         double sp = MarketInfo(sym, MODE_SPREAD);

         // 计算ATR
         double atr = iATR(sym, PERIOD_H1, 14, i);
         
         // 计算ADX
         double adx = iADX(sym, PERIOD_H1, 14, PRICE_CLOSE, MODE_MAIN, i);

         // 计算布林带
         double bbUp = iBands(sym, PERIOD_H1, 20, 2, 0, PRICE_CLOSE, MODE_UPPER, i);
         double bbLo = iBands(sym, PERIOD_H1, 20, 2, 0, PRICE_CLOSE, MODE_LOWER, i);
         double bbMid = iMA(sym, PERIOD_H1, 20, 0, MODE_SMA, PRICE_CLOSE, i);
         double bbW = (bbMid > 0) ? (bbUp - bbLo) / bbMid : 0;

         FileWrite(fileHandle,
            sym, TimeToStr(t, TIME_DATE|TIME_MINUTES),
            DoubleToStr(o, Digits),
            DoubleToStr(h, Digits),
            DoubleToStr(l, Digits),
            DoubleToStr(c, Digits),
            DoubleToStr(v, 0),
            DoubleToStr(sp, 0),
            DoubleToStr(atr, Digits),
            DoubleToStr(adx, 1),
            DoubleToStr(bbUp, Digits),
            DoubleToStr(bbLo, Digits),
            DoubleToStr(bbW, 6)
         );
        }
     }

   FileClose(fileHandle);
   Comment("AI_Bridge: 已导出 ", TimeToStr(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS));
   return(0);
  }
//+------------------------------------------------------------------+
