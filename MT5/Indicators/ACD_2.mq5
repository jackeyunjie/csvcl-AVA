//+------------------------------------------------------------------+
//|                                                          ACD_2.mq5 |
//|                                    改编自 MT4 版本 ACD 2外汇期货版PJJ.mq4 |
//|                            原作者: CompanyName 2012 |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//|                            功能: 枢轴区间 + 前日高低 + MA均线 |
//+------------------------------------------------------------------+
#property copyright "Copyright 2012, CompanyName"
#property link      "http://www.companyname.net"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 8
#property indicator_plots   8
//---- 绘制属性
#property indicator_type1   DRAW_LINE
#property indicator_color1  Orchid
#property indicator_style1  STYLE_DOT
#property indicator_label1  "Pivot Point"
#property indicator_type2   DRAW_LINE
#property indicator_color2  Orchid
#property indicator_style2  STYLE_DASH
#property indicator_label2  "Pivot Range Top"
#property indicator_type3   DRAW_LINE
#property indicator_color3  Orchid
#property indicator_style3  STYLE_DASH
#property indicator_label3  "Pivot Range Bottom"
#property indicator_type4   DRAW_LINE
#property indicator_color4  Khaki
#property indicator_style4  STYLE_DASHDOT
#property indicator_label4  "Previous Day High"
#property indicator_type5   DRAW_LINE
#property indicator_color5  Khaki
#property indicator_style5  STYLE_DASHDOT
#property indicator_label5  "Previous Day Low"
#property indicator_type6   DRAW_LINE
#property indicator_color6  Red
#property indicator_label6  "14 MA"
#property indicator_type7   DRAW_LINE
#property indicator_color7  Blue
#property indicator_label7  "30 MA"
#property indicator_type8   DRAW_LINE
#property indicator_color8  Orchid
#property indicator_label8  "50 MA"

//---- 输入参数
input string PivotRangeStart="09:30";   // 枢轴区间起始时间
input string PivotRangeEnd="15:00";     // 枢轴区间结束时间
input bool   DisplayPivotPoint=true;    // 显示枢轴点
input bool   DisplayPreviousHighLow=true; // 显示前日高低
input bool   DisplayMAs=true;           // 显示MA均线
input bool   交易时间智能=true;          // 智能交易时间

//---- 指标缓冲区
double Buffer1[];
double Buffer2[];
double Buffer3[];
double Buffer4[];
double Buffer5[];
double Buffer6[];
double Buffer7[];
double Buffer8[];

//---- 全局变量
double pivots[150];
int    barsjs=9060;
double pivotRangeHigh;
double pivotRangeLow;
double pivotRangeClose;
double pivotPoint;
double pivotDiff;
double pivotTop=0;
double pivotBottom=0;
double pivot14MA;
double pivot30MA;
double pivot50MA;
int    openBar;

//+------------------------------------------------------------------+
//| 自定义指标初始化函数                                              |
//+------------------------------------------------------------------+
int OnInit()
  {
//---- 设置指标缓冲区
   SetIndexBuffer(0,Buffer1,INDICATOR_DATA);
   SetIndexBuffer(1,Buffer2,INDICATOR_DATA);
   SetIndexBuffer(2,Buffer3,INDICATOR_DATA);
   SetIndexBuffer(3,Buffer4,INDICATOR_DATA);
   SetIndexBuffer(4,Buffer5,INDICATOR_DATA);
   SetIndexBuffer(5,Buffer6,INDICATOR_DATA);
   SetIndexBuffer(6,Buffer7,INDICATOR_DATA);
   SetIndexBuffer(7,Buffer8,INDICATOR_DATA);

//---- 设置绘制线宽
   PlotIndexSetInteger(0,PLOT_LINE_WIDTH,1);
   PlotIndexSetInteger(1,PLOT_LINE_WIDTH,1);
   PlotIndexSetInteger(2,PLOT_LINE_WIDTH,1);
   PlotIndexSetInteger(3,PLOT_LINE_WIDTH,1);
   PlotIndexSetInteger(4,PLOT_LINE_WIDTH,1);

//---- 设置指标简称
   IndicatorSetString(INDICATOR_SHORTNAME,"ACD_2 Pivot Range");

//---- 设置智能交易时间
   if(交易时间智能)
      SetSmartTimes();

   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| 智能设置各品种交易时间                                            |
//+------------------------------------------------------------------+
void SetSmartTimes()
  {
   string sym=_Symbol;

   if(sym=="NZDUSD")                              {PivotRangeStart="00:00"; PivotRangeEnd="00:00";}
   else if(sym=="AUDUSD")                         {PivotRangeStart="01:00"; PivotRangeEnd="01:00";}
   else if(sym=="USDJPY"||sym=="AUDJPY"||sym=="EURJPY"||sym=="GBPJPY")
                                                   {PivotRangeStart="02:30"; PivotRangeEnd="02:30";}
   else if(sym=="NIK225")                         {PivotRangeStart="01:31"; PivotRangeEnd="08:00";}
   else if(sym=="NKD"||sym=="NIKKEI.p")           {PivotRangeStart="01:30"; PivotRangeEnd="23:30";}
   else if(sym=="HSI.p")                          {PivotRangeStart="03:16"; PivotRangeEnd="10:15";}
   else if(sym=="HSI")                            {PivotRangeStart="04:31"; PivotRangeEnd="18:30";}
   else if(sym=="CHINA300"||sym=="CHINA300.p")    {PivotRangeStart="03:31"; PivotRangeEnd="08:45";}
   else if(sym=="CHINA-A50")                      {PivotRangeStart="03:01"; PivotRangeEnd="19:45";}
   else if(sym=="XU")                             {PivotRangeStart="04:01"; PivotRangeEnd="22:30";}
   else if(sym=="TCTZ"||sym=="LNVG"||sym=="IDCB"){PivotRangeStart="04:31"; PivotRangeEnd="10:45";}
   else if(sym=="EURUSD"||sym=="USDCHF"||sym=="EURGBP")
                                                   {PivotRangeStart="09:30"; PivotRangeEnd="09:30";}
   else if(sym=="GBPUSD")                         {PivotRangeStart="09:30"; PivotRangeEnd="09:30";}
   else if(sym=="FCE")                            {PivotRangeStart="09:31"; PivotRangeEnd="22:30";}
   else if(sym=="FTI")                            {PivotRangeStart="09:06"; PivotRangeEnd="22:45";}
   else if(sym=="Russia50")                       {PivotRangeStart="10:01"; PivotRangeEnd="23:45";}
   else if(sym=="FDAX"||sym=="DAX.p")             {PivotRangeStart="09:31"; PivotRangeEnd="22:30";}
   else if(sym=="FESX")                           {PivotRangeStart="09:06"; PivotRangeEnd="22:50";}
   else if(sym=="Z")                              {PivotRangeStart="10:06"; PivotRangeEnd="22:50";}
   else if(sym=="IBX")                            {PivotRangeStart="10:01"; PivotRangeEnd="20:55";}
   else if(sym=="MIB")                            {PivotRangeStart="10:01"; PivotRangeEnd="18:45";}
   else if(sym=="DBK"||sym=="BMW"||sym=="ADS"||sym=="DAI"||sym=="VOW"||sym=="BAYN"||sym=="ENI")
                                                   {PivotRangeStart="11:01"; PivotRangeEnd="19:25";}
   else if(sym=="XAUUSD"||sym=="XAGUSD"||sym=="COPPER"||sym=="HG"||sym=="PA"||sym=="PL")
                                                   {PivotRangeStart="15:00"; PivotRangeEnd="15:00";}
   else if(sym=="USDX")                           {PivotRangeStart="15:05"; PivotRangeEnd="22:00";}
   else if(sym=="USDCAD")                         {PivotRangeStart="15:20"; PivotRangeEnd="15:20";}
   else if(sym=="USCRUDE"||sym=="CL"||sym=="WT"||sym=="NG"||sym=="HO")
                                                   {PivotRangeStart="15:30"; PivotRangeEnd="15:30";}
   else if(sym=="NQ100"||sym=="SPX500"||sym=="DJI30"||sym=="NAS100.p"||sym=="SPX500.p"||sym=="DOW.p")
                                                   {PivotRangeStart="16:30"; PivotRangeEnd="23:00";}
   else if(sym=="NQ"||sym=="ES"||sym=="YM")       {PivotRangeStart="16:15"; PivotRangeEnd="23:45";}
   else if(sym=="SOYBEAN"||sym=="CORN"||sym=="WHEAT")
                                                   {PivotRangeStart="17:30"; PivotRangeEnd="17:15";}
   else if(sym=="SUGAR"||sym=="COFFEE"||sym=="COCOA")
                                                   {PivotRangeStart="15:30"; PivotRangeEnd="15:15";}
   else if(sym=="BIDU"||sym=="AMZN"||sym=="BABA"||sym=="GS"||sym=="NVDA"||sym=="WFC")
                                                   {PivotRangeStart="16:31"; PivotRangeEnd="22:45";}
   // 国内期货
   else if(sym=="淀粉主连"||sym=="玉米主连"||sym=="PVC主连"||sym=="锰硅主连"||sym=="鸡蛋主连"||sym=="聚丙烯主连"||sym=="塑料主连")
                                                   {PivotRangeStart="09:01"; PivotRangeEnd="14:55";}
   else if(sym=="PTA主连"||sym=="白糖主连"||sym=="玻璃主连"||sym=="菜粕主连"||sym=="菜油主连"||sym=="动煤主连"||sym=="甲醇主连")
                                                   {PivotRangeStart="09:01"; PivotRangeEnd="23:25";}
   else if(sym=="棉花主连"||sym=="新强麦主连"||sym=="豆粕主连"||sym=="豆油主连"||sym=="黄豆主连"||sym=="焦煤主连"||sym=="焦炭主连")
                                                   {PivotRangeStart="09:01"; PivotRangeEnd="23:25";}
   else if(sym=="棕榈主连"||sym=="铁矿主连")      {PivotRangeStart="09:01"; PivotRangeEnd="23:25";}
   else if(sym=="沥青主连"||sym=="螺纹主连"||sym=="橡胶主连"||sym=="轧板主连")
                                                   {PivotRangeStart="09:00"; PivotRangeEnd="22:55";}
   else if(sym=="航发动力"||sym=="工商银行"||sym=="双鹭药业"||sym=="广发证券")
                                                   {PivotRangeStart="09:30"; PivotRangeEnd="15:00";}
  }
//+------------------------------------------------------------------+
//| 自定义指标计算函数                                                |
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
   string barTime="",lastBarTime="";
   string barDay="",lastBarDay="";
   int closeBar;
   openBar=0;
   int calc_bars=MathMin(barsjs,rates_total);

//---- 初始化
   if(prev_calculated==0)
     {
      for(int i=0; i<rates_total; i++)
        {
         Buffer1[i]=EMPTY_VALUE; Buffer2[i]=EMPTY_VALUE;
         Buffer3[i]=EMPTY_VALUE; Buffer4[i]=EMPTY_VALUE;
         Buffer5[i]=EMPTY_VALUE; Buffer6[i]=EMPTY_VALUE;
         Buffer7[i]=EMPTY_VALUE; Buffer8[i]=EMPTY_VALUE;
        }
     }

//---- 扫描查找枢轴区间
   for(int i=calc_bars-1; i>=0; i--)
     {
      barTime=TimeToString(time[i],TIME_MINUTES);
      lastBarTime=TimeToString(time[i+1],TIME_MINUTES);
      barDay=TimeToString(time[i],TIME_DATE);
      lastBarDay=TimeToString(time[i+1],TIME_DATE);

      // 检测枢轴区间结束
      if((PivotRangeEnd=="00:00" && barTime>=PivotRangeEnd && barDay>lastBarDay) ||
         (barTime>=PivotRangeEnd && lastBarTime<PivotRangeEnd))
        {
         closeBar=i+1;
         if(openBar>0)
            CalculatePivotRangeValues(openBar,closeBar,high,low,close);
        }

      // 检测枢轴区间开始
      if((PivotRangeStart=="00:00" && barTime>=PivotRangeStart && barDay>lastBarDay) ||
         (barTime>=PivotRangeStart && lastBarTime<PivotRangeStart))
        {
         openBar=i;
        }

      // 绘制指标
      if(openBar>0)
         DrawIndicators(i);
     }

   return(rates_total);
  }
//+------------------------------------------------------------------+
//| 计算枢轴区间值                                                    |
//+------------------------------------------------------------------+
void CalculatePivotRangeValues(int openBar1,int closeBar,const double &high[],const double &low[],const double &close[])
  {
   int count=openBar1-closeBar+1;
   if(count<=0) return;

   pivotRangeHigh=high[openBar1];
   pivotRangeLow=low[openBar1];
   for(int i=openBar1-1; i>=closeBar; i--)
     {
      if(high[i]>pivotRangeHigh) pivotRangeHigh=high[i];
      if(low[i]<pivotRangeLow)   pivotRangeLow=low[i];
     }
   pivotRangeClose=close[closeBar];
   pivotPoint=(pivotRangeHigh+pivotRangeLow+pivotRangeClose)/3;
   pivotDiff=MathAbs(((pivotRangeHigh+pivotRangeLow)/2)-pivotPoint);
   pivotTop=pivotPoint+pivotDiff;
   pivotBottom=pivotPoint-pivotDiff;

   if(DisplayMAs) CalcPivotMA();
  }
//+------------------------------------------------------------------+
//| 计算枢轴点的移动平均线                                            |
//+------------------------------------------------------------------+
void CalcPivotMA()
  {
   double pivs[50];
   ArrayCopy(pivs,pivots,1,0,49);
   pivs[0]=pivotPoint;
   ArrayCopy(pivots,pivs,0,0,WHOLE_ARRAY);

   double pivSum=0;
   int count=ArraySize(pivots);
   for(int p=0; p<count; p++)
     {
      pivSum+=pivots[p];
      if(p==13) pivot14MA=pivSum/14;
      if(p==29) pivot30MA=pivSum/30;
      if(p==49) pivot50MA=pivSum/50;
     }
  }
//+------------------------------------------------------------------+
//| 绘制指标                                                          |
//+------------------------------------------------------------------+
void DrawIndicators(int curBar)
  {
   if(DisplayPivotPoint)
      Buffer1[curBar]=pivotPoint;
   Buffer2[curBar]=pivotTop;
   Buffer3[curBar]=pivotBottom;

   if(DisplayPreviousHighLow)
     {
      Buffer4[curBar]=pivotRangeHigh;
      Buffer5[curBar]=pivotRangeLow;
     }

   if(DisplayMAs)
     {
      Buffer6[curBar]=pivot14MA;
      Buffer7[curBar]=pivot30MA;
      Buffer8[curBar]=pivot50MA;
     }
  }
//+------------------------------------------------------------------+
