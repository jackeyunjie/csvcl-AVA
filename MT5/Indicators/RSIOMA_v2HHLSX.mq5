//+--------------------------------------------------------------------------------+
//|                                                       RSIOMA v2HHLSX (MT5)     |
//|                                                            Kalenzo - fxtsd.com |
//|     Hornet(i-RSI)2007, FxTSD.com;                 MetaQuotes Software Corp. ik |
//|     Hist & Levels 20/80;30/70 CrossSig            web: http://www.fxservice.eu |
//|     Rsioma/MaRsioma X sig                   email: bartlomiej.gorski@gmail.com |
//|                                                                                |
//|     鏀圭紪鑷?MT4 鐗堟湰 RSIOMA_v2HHLSX_e021c1.mq4锛屼娇鐢?MQL5 鍘熺敓鎸囨爣鍙ユ焺瀹炵幇        |
//+--------------------------------------------------------------------------------+
#property copyright "Copyright ?2007, MetaQuotes Software Corp."
#property link      "http://www.metaquotes.net/"
#property version   "1.00"
//----
#property indicator_separate_window
#property indicator_minimum -20
#property indicator_maximum 120
#property indicator_buffers 7
#property indicator_plots   7
//----
#property indicator_type1   DRAW_LINE
#property indicator_color1  Aqua
#property indicator_label1  "Rsioma"
#property indicator_width1  2

#property indicator_type2   DRAW_HISTOGRAM
#property indicator_color2  Red
#property indicator_label2  "TrendDn"

#property indicator_type3   DRAW_HISTOGRAM
#property indicator_color3  Green
#property indicator_label3  "TrendUp"

#property indicator_type4   DRAW_HISTOGRAM
#property indicator_color4  Magenta
#property indicator_label4  "SellTrigger"

#property indicator_type5   DRAW_HISTOGRAM
#property indicator_color5  DodgerBlue
#property indicator_label5  "BuyTrigger"
#property indicator_width5  2

#property indicator_type6   DRAW_LINE
#property indicator_color6  Yellow
#property indicator_label6  "MaRsioma"

#property indicator_type7   DRAW_ARROW
#property indicator_color7  SlateBlue
#property indicator_label7  "Up/DnXsig"
#property indicator_width7  2

//---- 姘村钩鍙傝€冪嚎
#property indicator_level1 100
#property indicator_level2 80
#property indicator_level3 50
#property indicator_level4 20
#property indicator_level5 0
#property indicator_levelcolor SlateGray

//---- input parameters
input int                RSIOMA              = 14;             // RSIOMA鍛ㄦ湡
input ENUM_MA_METHOD     RSIOMA_MODE         = MODE_EMA;       // RSIOMA鍧囩嚎妯″紡
input ENUM_APPLIED_PRICE RSIOMA_PRICE        = PRICE_CLOSE;    // RSIOMA浠锋牸绫诲瀷
input int                Ma_RSIOMA           = 21;             // 骞虫粦RSI鐨凪A鍛ㄦ湡
input ENUM_MA_METHOD     Ma_RSIOMA_MODE      = MODE_EMA;       // 骞虫粦RSI鐨凪A妯″紡
input double             BuyTrigger          = 80.00;          // 涔板叆瑙﹀彂姘村钩
input double             SellTrigger         = 20.00;          // 鍗栧嚭瑙﹀彂姘村钩
input color              BuyTriggerColor     = DodgerBlue;  // 涔板叆瑙﹀彂绾块鑹?
input color              SellTriggerColor    = Magenta;     // 鍗栧嚭瑙﹀彂绾块鑹?
input double             MainTrendLong       = 70.00;          // 涓昏秼鍔垮澶存按骞?
input double             MainTrendShort      = 30.00;          // 涓昏秼鍔跨┖澶存按骞?
input color              MainTrendLongColor  = Red;         // 涓昏秼鍔垮澶寸嚎棰滆壊
input color              MainTrendShortColor = Green;       // 涓昏秼鍔跨┖澶寸嚎棰滆壊
input double             MajorTrend          = 50;             // 涓昏瓒嬪娍鍒嗙晫绾?
input color              marsiomaXSigColor   = SlateBlue;   // 浜ゅ弶淇″彿棰滆壊

//---- buffers
double RSIBuffer[];
double bdn[], bup[];
double sdn[], sup[];
double marsioma[];
double marsiomaXSig[];

//---- handles & globals
string short_name;
int    ma_handle     = INVALID_HANDLE;
int    rsi_handle    = INVALID_HANDLE;
int    ma_rsi_handle = INVALID_HANDLE;
//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   short_name = "RSIOMA(" + IntegerToString(RSIOMA) + ")";

   //---- 缁戝畾鎸囨爣缂撳啿鍖?
   SetIndexBuffer(0, RSIBuffer,      INDICATOR_DATA);
   SetIndexBuffer(1, bdn,            INDICATOR_DATA);
   SetIndexBuffer(2, bup,            INDICATOR_DATA);
   SetIndexBuffer(3, sdn,            INDICATOR_DATA);
   SetIndexBuffer(4, sup,            INDICATOR_DATA);
   SetIndexBuffer(5, marsioma,       INDICATOR_DATA);
   SetIndexBuffer(6, marsiomaXSig,   INDICATOR_DATA);

   //---- 绠ご缂栫爜锛堝疄蹇冨渾鐐癸級
   PlotIndexSetInteger(6, PLOT_ARROW, 159);

   //---- 璁剧疆缁樺埗璧峰鍋忕Щ
   PlotIndexSetInteger(0, PLOT_DRAW_BEGIN, RSIOMA);
   PlotIndexSetInteger(1, PLOT_DRAW_BEGIN, RSIOMA);
   PlotIndexSetInteger(2, PLOT_DRAW_BEGIN, RSIOMA);
   PlotIndexSetInteger(3, PLOT_DRAW_BEGIN, RSIOMA);
   PlotIndexSetInteger(4, PLOT_DRAW_BEGIN, RSIOMA);
   PlotIndexSetInteger(5, PLOT_DRAW_BEGIN, RSIOMA + Ma_RSIOMA);
   PlotIndexSetInteger(6, PLOT_DRAW_BEGIN, RSIOMA + Ma_RSIOMA);

   //---- 绌哄€煎鐞?
   PlotIndexSetDouble(6, PLOT_EMPTY_VALUE, EMPTY_VALUE);

   //---- 鎸囨爣绠€绉?
   IndicatorSetString(INDICATOR_SHORTNAME, short_name);

   //---- 鍒涘缓鎸囨爣鍙ユ焺锛氫环鏍?MA -> RSI(MA) -> MA(RSI)
   ma_handle = iMA(_Symbol, _Period, RSIOMA, 0, RSIOMA_MODE, RSIOMA_PRICE);
   if(ma_handle == INVALID_HANDLE)
     {
      Print("鏃犳硶鍒涘缓 iMA 鍙ユ焺");
      return(INIT_FAILED);
     }

   rsi_handle = iRSI(_Symbol, _Period, RSIOMA, (ENUM_APPLIED_PRICE)ma_handle);
   if(rsi_handle == INVALID_HANDLE)
     {
      Print("鏃犳硶鍒涘缓 iRSI 鍙ユ焺");
      return(INIT_FAILED);
     }

   ma_rsi_handle = iMA(_Symbol, _Period, Ma_RSIOMA, 0, Ma_RSIOMA_MODE, (ENUM_APPLIED_PRICE)rsi_handle);
   if(ma_rsi_handle == INVALID_HANDLE)
     {
      Print("鏃犳硶鍒涘缓 MA(RSI) 鍙ユ焺");
      return(INIT_FAILED);
     }

   return(INIT_SUCCEEDED);
}
//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   //---- 鍒犻櫎瑙﹀彂姘村钩绾?
   ObjectDelete(0, "BuyTrigger");
   ObjectDelete(0, "SellTrigger");
   ObjectDelete(0, "MainTrendLong");
   ObjectDelete(0, "MainTrendShort");

   //---- 閲婃斁鎸囨爣鍙ユ焺
   if(ma_handle != INVALID_HANDLE)      IndicatorRelease(ma_handle);
   if(rsi_handle != INVALID_HANDLE)     IndicatorRelease(rsi_handle);
   if(ma_rsi_handle != INVALID_HANDLE)  IndicatorRelease(ma_rsi_handle);
}
//+------------------------------------------------------------------+
//| Relative Strength Index on MA                                    |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &real_volume[],
                const int &spread[])
{
   if(rates_total <= RSIOMA)
      return(0);

   //---- 棣栨璁＄畻鏃跺垵濮嬪寲鐩存柟鍥?绠ご缂撳啿鍖猴紝骞剁粯鍒惰Е鍙戞按骞崇嚎
   if(prev_calculated == 0)
     {
      ArrayInitialize(bdn,          0);
      ArrayInitialize(bup,          0);
      ArrayInitialize(sdn,          0);
      ArrayInitialize(sup,          0);
      ArrayInitialize(marsiomaXSig, EMPTY_VALUE);

      int subwindow = ChartWindowFind(0, short_name);
      if(subwindow < 0) subwindow = 0;
      drawLine(BuyTrigger,     "BuyTrigger",     BuyTriggerColor,     subwindow);
      drawLine(SellTrigger,    "SellTrigger",    SellTriggerColor,    subwindow);
      drawLine(MainTrendLong,  "MainTrendLong",  MainTrendLongColor,  subwindow);
      drawLine(MainTrendShort, "MainTrendShort", MainTrendShortColor, subwindow);
     }

   //---- 璁＄畻璧峰浣嶇疆锛堝閲忔洿鏂帮級
   int start = (prev_calculated == 0) ? 0 : prev_calculated - 1;
   int count = rates_total - start;

   //---- 澶嶅埗 RSI(MA)
   double temp_rsi[];
   ArraySetAsSeries(temp_rsi, true);
   if(CopyBuffer(rsi_handle, 0, start, count, temp_rsi) < count)
      return(0);

   //---- 澶嶅埗 MA(RSI)
   double temp_ma_rsi[];
   ArraySetAsSeries(temp_ma_rsi, true);
   if(CopyBuffer(ma_rsi_handle, 0, start, count, temp_ma_rsi) < count)
      return(0);

   //---- 鍐欏叆鎸囨爣缂撳啿鍖?
   for(int i = 0; i < count; i++)
     {
      int idx = start + i;
      RSIBuffer[idx] = temp_rsi[i];
      marsioma[idx]  = temp_ma_rsi[i];
     }

   //---- 璁＄畻瓒嬪娍鐩存柟鍥句笌瑙﹀彂淇″彿
   for(int i = start; i < rates_total; i++)
     {
      bup[i] = 0;
      bdn[i] = 0;
      sup[i] = 0;
      sdn[i] = 0;

      if(RSIBuffer[i] > 50)             bup[i] = 6;
      if(RSIBuffer[i] < 50)             bdn[i] = -6;
      if(RSIBuffer[i] > MainTrendLong)  bup[i] = 12;
      if(RSIBuffer[i] < MainTrendShort) bdn[i] = -12;

      if(i + 1 < rates_total)
        {
         if(RSIBuffer[i] < 20 && RSIBuffer[i] > RSIBuffer[i + 1])         sup[i] = -3;
         if(RSIBuffer[i] > 80 && RSIBuffer[i] < RSIBuffer[i + 1])         sdn[i] = 4;
         if(RSIBuffer[i] > 20 && RSIBuffer[i + 1] <= 20)                  sup[i] = 5;
         if(RSIBuffer[i + 1] >= 80 && RSIBuffer[i] < 80)                  sdn[i] = -5;
         if(RSIBuffer[i + 1] <= MainTrendShort && RSIBuffer[i] > MainTrendShort) sup[i] = 12;
         if(RSIBuffer[i] < MainTrendLong && RSIBuffer[i + 1] >= MainTrendLong)   sdn[i] = -12;
        }
     }

   //---- 璁＄畻 RSI 涓?MaRsioma 鐨勪氦鍙変俊鍙?
   for(int i = start; i < rates_total - 1; i++)
     {
      marsiomaXSig[i] = EMPTY_VALUE;
      if(RSIBuffer[i + 1] <= marsioma[i + 1] && RSIBuffer[i] > marsioma[i])
         marsiomaXSig[i] = -8;
      if(RSIBuffer[i + 1] >= marsioma[i + 1] && RSIBuffer[i] < marsioma[i])
         marsiomaXSig[i] = 8;
     }

   return(rates_total);
}
//+------------------------------------------------------------------+
//| Draw horizontal line in indicator sub-window                     |
//+------------------------------------------------------------------+
void drawLine(double lvl, string name, color Col, int subwindow)
{
   ObjectDelete(0, name);
   if(!ObjectCreate(0, name, OBJ_HLINE, subwindow, TimeCurrent(), lvl))
     {
      Print("鏃犳硶鍒涘缓姘村钩绾垮璞? ", name, " 閿欒鐮? ", GetLastError());
      return;
     }
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DOT);
   ObjectSetInteger(0, name, OBJPROP_COLOR,  Col);
   ObjectSetInteger(0, name, OBJPROP_WIDTH,  1);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN,     true);
}
//+------------------------------------------------------------------+
