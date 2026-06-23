//+------------------------------------------------------------------+
//|                                                          ACD_1.mq5 |
//|                                    改编自 MT4 版本 ACD 1外汇期货版PJJ.mq4 |
//|                            原作者: CompanyName 2012 |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//|                            功能: ACD开盘区间 A值和C值 计算 |
//+------------------------------------------------------------------+
#property copyright "Copyright 2012, CompanyName"
#property link      "http://www.companyname.net"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 6
#property indicator_plots   6
//---- 绘制属性
#property indicator_type1   DRAW_ARROW
#property indicator_color1  White
#property indicator_label1  "O/R High"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  White
#property indicator_label2  "O/R Low"
#property indicator_type3   DRAW_ARROW
#property indicator_color3  Yellow
#property indicator_label3  "A Up"
#property indicator_type4   DRAW_ARROW
#property indicator_color4  Yellow
#property indicator_label4  "A Down"
#property indicator_type5   DRAW_ARROW
#property indicator_color5  Aqua
#property indicator_label5  "C Up"
#property indicator_type6   DRAW_ARROW
#property indicator_color6  Aqua
#property indicator_label6  "C Down"

//---- 输入参数
input string OpenRangeStart="09:30";    // 开盘区间起始时间
input string OpenRangeEnd="09:45";      // 开盘区间结束时间
input bool   Use_Default_A_and_C_Values=false; // 使用手动输入A/C值
input double A_Value_Pips=0;           // 手动A值(点数)
input double C_Value_Pips=0;           // 手动C值(点数)
input bool   UseAlerts=false;          // 使用报警
input bool   DisplayOpeningRange=true; // 显示开盘区间
input bool   DisplayAs=true;           // 显示A值
input bool   DisplayCs=true;           // 显示C值
input bool   使用外部开盘时间输入=false; // 使用外部开盘时间
input bool   EmailAlert=false;         // 邮件报警
input bool   pmAlert=false;            // 弹窗报警
input int    NumberOfDays=50;          // 计算天数
input string periodBegin="00:00";      // 周期开始时间
input string periodEnd="05:30";        // 周期结束时间
input string BoxEnd="23:00";           // 箱体结束时间
input int    BoxBreakOut_Offset=10;    // 箱体突破偏移
input color  BoxHLColor=clrMidnightBlue;     // 箱体高低点颜色
input color  BoxBreakOutColor=clrLimeGreen;  // 箱体突破颜色
input color  BoxPeriodColor=clrOrangeRed;    // 箱体周期颜色

//---- 指标缓冲区
double Buffer1[];
double Buffer2[];
double Buffer3[];
double Buffer4[];
double Buffer5[];
double Buffer6[];

//---- 全局变量
double aValue;
double cValue;
double aUp=0;
double aDown=0;
double cUp=0;
double cDown=0;
double openRangeHigh;
double openRangeLow;
datetime jiaocha=0;
int    barsjs=3060;
bool   aUpBefore=false;
bool   aDownBefore=false;
bool   cUpBefore=false;
bool   cDownBefore=false;

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

//---- 设置箭头编码
   PlotIndexSetInteger(0,PLOT_ARROW,158);
   PlotIndexSetInteger(1,PLOT_ARROW,158);
   PlotIndexSetInteger(2,PLOT_ARROW,159);
   PlotIndexSetInteger(3,PLOT_ARROW,159);
   PlotIndexSetInteger(4,PLOT_ARROW,159);
   PlotIndexSetInteger(5,PLOT_ARROW,159);

//---- 设置默认A/C值（根据品种）
   SetDefaultACValues();

   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| 根据品种设置默认A值和C值                                          |
//+------------------------------------------------------------------+
void SetDefaultACValues()
  {
   if(Use_Default_A_and_C_Values)
     {
      aValue=A_Value_Pips;
      cValue=C_Value_Pips;
      return;
     }

   string sym=_Symbol;

   if(sym=="AUSSIE200")                 {aValue=7;       cValue=9;}
   else if(sym=="NIK225" || sym=="NKD" || sym=="NIKKEI.p") {aValue=32;      cValue=5;}
   else if(sym=="HSI.p" || sym=="HSI")  {aValue=28;      cValue=100;}
   else if(sym=="CHINA300" || sym=="CHINA300.p") {aValue=10; cValue=3;}
   else if(sym=="CHINA-A50" || sym=="XU") {aValue=32;    cValue=5;}
   else if(sym=="EURUSD")              {aValue=0.0031;  cValue=0.0041;}
   else if(sym=="USDJPY")              {aValue=0.08;    cValue=0.15;}
   else if(sym=="EURJPY")              {aValue=0.08;    cValue=0.15;}
   else if(sym=="GBPJPY")              {aValue=0.08;    cValue=0.15;}
   else if(sym=="USDCHF")              {aValue=0.0011;  cValue=0.0022;}
   else if(sym=="AUDUSD")              {aValue=0.0026;  cValue=0.0026;}
   else if(sym=="NZDUSD")              {aValue=0.0026;  cValue=0.0026;}
   else if(sym=="GBPUSD")              {aValue=0.0028;  cValue=0.0056;}
   else if(sym=="USDX")                {aValue=12;      cValue=21;}
   else if(sym=="USDCAD")              {aValue=0.0007;  cValue=0.0007;}
   else if(sym=="FDAX" || sym=="DAX.p"){aValue=24;      cValue=2;}
   else if(sym=="Z")                   {aValue=7;       cValue=1;}
   else if(sym=="FESX")                {aValue=7;       cValue=1;}
   else if(sym=="FCE")                 {aValue=15;      cValue=2;}
   else if(sym=="IBX")                 {aValue=7;       cValue=1;}
   else if(sym=="MIB")                 {aValue=7;       cValue=1;}
   else if(sym=="Russia50")            {aValue=2;       cValue=0.5;}
   else if(sym=="DOW.p" || sym=="YM")  {aValue=35;      cValue=15;}
   else if(sym=="SPX500.p" || sym=="ES"){aValue=3.5;    cValue=0.5;}
   else if(sym=="NQ100" || sym=="NQ" || sym=="NAS100.p"){aValue=7; cValue=4;}
   else if(sym=="XAUUSD")              {aValue=3;       cValue=2;}
   else if(sym=="COPPER")              {aValue=66;      cValue=155;}
   else if(sym=="PL")                  {aValue=2.5;     cValue=100;}
   else if(sym=="HG")                  {aValue=0.0066;  cValue=0.0155;}
   else if(sym=="XAGUSD")              {aValue=0.02;    cValue=0.03;}
   else if(sym=="HQ")                  {aValue=35;      cValue=135;}
   else if(sym=="NG")                  {aValue=0.0050;  cValue=0.0050;}
   else if(sym=="USCRUDE" || sym=="WT" || sym=="CL" || sym=="BRN") {aValue=0.08; cValue=0.13;}
   else if(sym=="COCOA")               {aValue=10;      cValue=15;}
   else if(sym=="SUGAR")               {aValue=0.1;     cValue=0.06;}
   else if(sym=="COFFEE")              {aValue=0.2;     cValue=0.3;}
   else if(sym=="SOYBEAN")             {aValue=2;       cValue=5;}
   else if(sym=="CORN")                {aValue=1.6;     cValue=1.2;}
   else if(sym=="WHEAT")               {aValue=2.4;     cValue=1.2;}
   else {aValue=3; cValue=8;} // 国内期货等默认值
  }
//+------------------------------------------------------------------+
//| 设置开盘时间（根据品种）                                          |
//+------------------------------------------------------------------+
void SetOpenRangeTimes()
  {
   if(使用外部开盘时间输入) return;

   string sym=_Symbol;

   if(sym=="NZDUSD")                              {OpenRangeStart="00:00"; OpenRangeEnd="00:30";}
   else if(sym=="AUDUSD")                         {OpenRangeStart="01:00"; OpenRangeEnd="01:30";}
   else if(sym=="USDJPY"||sym=="AUDJPY"||sym=="EURJPY"||sym=="GBPJPY")
                                                   {OpenRangeStart="02:20"; OpenRangeEnd="02:50";}
   else if(sym=="NIK225")                         {OpenRangeStart="01:30"; OpenRangeEnd="01:50";}
   else if(sym=="NKD")                            {OpenRangeStart="01:30"; OpenRangeEnd="01:50";}
   else if(sym=="HSI.p")                          {OpenRangeStart="03:15"; OpenRangeEnd="03:35";}
   else if(sym=="HSI")                            {OpenRangeStart="03:15"; OpenRangeEnd="03:30";}
   else if(sym=="CHINA300"||sym=="CHINA300.p")    {OpenRangeStart="03:30"; OpenRangeEnd="03:45";}
   else if(sym=="CHINA-A50")                      {OpenRangeStart="03:00"; OpenRangeEnd="03:20";}
   else if(sym=="XU")                             {OpenRangeStart="04:01"; OpenRangeEnd="04:20";}
   else if(sym=="TCTZ")                           {OpenRangeStart="04:31"; OpenRangeEnd="05:00";}
   else if(sym=="LNVG")                           {OpenRangeStart="04:20"; OpenRangeEnd="04:45";}
   else if(sym=="IDCB")                           {OpenRangeStart="04:10"; OpenRangeEnd="04:30";}
   else if(sym=="EURUSD"||sym=="USDCHF"||sym=="EURGBP")
                                                   {OpenRangeStart="09:30"; OpenRangeEnd="09:45";}
   else if(sym=="GBPUSD")                         {OpenRangeStart="09:30"; OpenRangeEnd="09:45";}
   else if(sym=="FDAX"||sym=="DAX.p")             {OpenRangeStart="10:01"; OpenRangeEnd="10:15";}
   else if(sym=="FCE"||sym=="FESX"||sym=="FTI")   {OpenRangeStart="10:01"; OpenRangeEnd="10:15";}
   else if(sym=="Z"||sym=="IBX"||sym=="MIB")      {OpenRangeStart="10:01"; OpenRangeEnd="10:15";}
   else if(sym=="Russia50")                       {OpenRangeStart="10:01"; OpenRangeEnd="10:15";}
   else if(sym=="DBK"||sym=="BMW"||sym=="ADS"||sym=="DAI"||sym=="VOW"||sym=="BAYN"||sym=="ENI")
                                                   {OpenRangeStart="11:01"; OpenRangeEnd="11:15";}
   else if(sym=="XAUUSD"||sym=="XAGUSD"||sym=="COPPER"||sym=="HG"||sym=="PA"||sym=="PL")
                                                   {OpenRangeStart="15:00"; OpenRangeEnd="15:15";}
   else if(sym=="USDX")                           {OpenRangeStart="15:05"; OpenRangeEnd="15:20";}
   else if(sym=="USDCAD")                         {OpenRangeStart="15:20"; OpenRangeEnd="15:35";}
   else if(sym=="USCRUDE"||sym=="CL"||sym=="WT"||sym=="NG"||sym=="HO")
                                                   {OpenRangeStart="15:30"; OpenRangeEnd="15:45";}
   else if(sym=="NQ100"||sym=="SPX500"||sym=="DJI30"||sym=="NAS100.p"||sym=="SPX500.p"||sym=="DOW.p")
                                                   {OpenRangeStart="16:30"; OpenRangeEnd="16:45";}
   else if(sym=="NQ"||sym=="ES"||sym=="YM")       {OpenRangeStart="16:30"; OpenRangeEnd="16:45";}
   else if(sym=="SOYBEAN"||sym=="CORN"||sym=="WHEAT")
                                                   {OpenRangeStart="17:30"; OpenRangeEnd="17:30";}
   else if(sym=="SUGAR"||sym=="COFFEE"||sym=="COCOA")
                                                   {OpenRangeStart="15:30"; OpenRangeEnd="15:30";}
   else if(sym=="BIDU"||sym=="AMZN"||sym=="BABA"||sym=="GS"||sym=="NVDA"||sym=="WFC")
                                                   {OpenRangeStart="16:31"; OpenRangeEnd="16:45";}
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
//---- 设置开盘区间时间
   SetOpenRangeTimes();

   string barTime="",lastBarTime="";
   string barDay="",lastBarDay="";
   int openBar=0;
   int calc_bars=MathMin(barsjs,rates_total);

//---- 初始化缓冲区
   if(prev_calculated==0)
     {
      for(int i=0; i<rates_total; i++)
        {
         Buffer1[i]=EMPTY_VALUE;
         Buffer2[i]=EMPTY_VALUE;
         Buffer3[i]=EMPTY_VALUE;
         Buffer4[i]=EMPTY_VALUE;
         Buffer5[i]=EMPTY_VALUE;
         Buffer6[i]=EMPTY_VALUE;
        }
     }

//---- 从旧到新扫描查找开盘区间
   for(int i=calc_bars-1; i>=0; i--)
     {
      barTime=TimeToString(time[i],TIME_MINUTES);
      lastBarTime=TimeToString(time[i+1],TIME_MINUTES);
      barDay=TimeToString(time[i],TIME_DATE);
      lastBarDay=TimeToString(time[i+1],TIME_DATE);

      // 检测开盘区间结束
      if((OpenRangeEnd=="00:00" && barTime>=OpenRangeEnd && barDay>lastBarDay) ||
         (barTime>=OpenRangeEnd && lastBarTime<OpenRangeEnd))
        {
         if(openBar>0)
           {
            CalculateOpenRange(openBar,i+1,high,low,close);
            aUp=openRangeHigh+aValue;
            aDown=openRangeLow-aValue;
            cUp=openRangeHigh+cValue;
            cDown=openRangeLow-cValue;
           }
        }

      // 检测开盘区间开始
      if((OpenRangeStart=="00:00" && barTime>=OpenRangeStart && barDay>lastBarDay) ||
         (barTime>=OpenRangeStart && lastBarTime<OpenRangeStart))
        {
         openBar=i;
        }

      // 在开盘区间开始之后绘制指标
      if(openBar>0 && i<=openBar)
        {
         DrawIndicators(i);
        }
     }

   return(rates_total);
  }
//+------------------------------------------------------------------+
//| 计算开盘区间高低点                                                 |
//+------------------------------------------------------------------+
void CalculateOpenRange(int openBar,int closeBar,const double &high[],const double &low[],const double &close[])
  {
   openRangeHigh=0;
   openRangeLow=999999;

   for(int i=openBar; i>=closeBar && i>=0; i--)
     {
      if(high[i]>openRangeHigh) openRangeHigh=high[i];
      if(low[i]<openRangeLow)   openRangeLow=low[i];
     }
  }
//+------------------------------------------------------------------+
//| 绘制指标值                                                        |
//+------------------------------------------------------------------+
void DrawIndicators(int curBar)
  {
   if(openRangeHigh<=0) return;

   if(DisplayOpeningRange)
     {
      Buffer1[curBar]=openRangeHigh;
      Buffer2[curBar]=openRangeLow;
     }

   if(DisplayAs)
     {
      Buffer3[curBar]=aUp;
      Buffer4[curBar]=aDown;
     }

   if(DisplayCs)
     {
      Buffer5[curBar]=cUp;
      Buffer6[curBar]=cDown;
     }
  }
//+------------------------------------------------------------------+
