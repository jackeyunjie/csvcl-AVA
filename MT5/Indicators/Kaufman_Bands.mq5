//+------------------------------------------------------------------+
//|                                                     Kaufman_Bands.mq5 |
//|                                    改编自 MT4 版本 Kaufman.mq4 |
//|                            原作者: konKop & wellx |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//+------------------------------------------------------------------+
#property copyright "Copyright 2003-2004, by konKop, for MT GOODMAN,af,Mstera ,wellx"
#property link      "http://www.metaquotes.net"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 5
#property indicator_plots   5
//---- 绘制属性
#property indicator_type1   DRAW_LINE
#property indicator_color1  Sienna
#property indicator_label1  "Kaufman AMA"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  DeepSkyBlue
#property indicator_label2  "AMA Up Signal"
#property indicator_type3   DRAW_ARROW
#property indicator_color3  Gold
#property indicator_label3  "AMA Down Signal"
#property indicator_type4   DRAW_LINE
#property indicator_color4  White
#property indicator_label4  "Upper Band"
#property indicator_type5   DRAW_LINE
#property indicator_color5  White
#property indicator_label5  "Lower Band"

//---- 输入参数
input int       periodAMA=9;        // AMA周期
input int       nfast=2;            // 快EMA周期
input int       nslow=30;           // 慢EMA周期
input double    G=2.0;              // AMA平滑指数
input double    dK=2.0;             // 信号触发阈值(点数)
input int       BollingerPeriod=20; // 布林带周期
input double    K_Bollinger=2.0;    // 布林带标准差倍数

//---- 指标缓冲区
double kAMAbuffer[];
double kAMAupsig[];
double kAMAdownsig[];
double UpBand[];
double DownBand[];

//---- 全局变量
int    prevbars=0;
double slowSC,fastSC;

//+------------------------------------------------------------------+
//| 自定义指标初始化函数                                              |
//+------------------------------------------------------------------+
int OnInit()
  {
//---- 设置指标缓冲区 (INDICATOR_DATA 表示用于绘制的数据)
   SetIndexBuffer(0,kAMAbuffer,INDICATOR_DATA);
   SetIndexBuffer(1,kAMAupsig,INDICATOR_DATA);
   SetIndexBuffer(2,kAMAdownsig,INDICATOR_DATA);
   SetIndexBuffer(3,UpBand,INDICATOR_DATA);
   SetIndexBuffer(4,DownBand,INDICATOR_DATA);

//---- 设置箭头编码
   PlotIndexSetInteger(1,PLOT_ARROW,159);
   PlotIndexSetInteger(2,PLOT_ARROW,159);

//---- 设置空值(不显示的位置)
   PlotIndexSetDouble(1,PLOT_EMPTY_VALUE,0.0);
   PlotIndexSetDouble(2,PLOT_EMPTY_VALUE,0.0);

//---- 设置小数位数
   IndicatorSetInteger(INDICATOR_DIGITS,_Digits);

//---- 设置指标简称
   IndicatorSetString(INDICATOR_SHORTNAME,"Kaufman_Bands("+IntegerToString(periodAMA)+","+IntegerToString(BollingerPeriod)+")");

   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| 自定义指标计算函数                                                |
//|   Kaufman自适应均线(AMA) + 布林带 + 箭头信号                      |
//|   关键：AMA是序列依赖的，必须从旧到新逐根计算                       |
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
   int    i,start_pos;
   double noise,signal,ER;
   double dSC,ERSC,SSC;
   double AMA,AMA0;
   double deviation,counter_Boll;
   double ddK;

//---- 检查数据是否足够
   if(rates_total<=(periodAMA+2))
      return(0);

//---- 计算快慢平滑系数（只需计算一次）
   slowSC=(2.0/(nslow+1));
   fastSC=(2.0/(nfast+1));

//---- 确定计算起始位置
   if(prev_calculated==0)
     {
      // 首次加载，需要从最旧的k线开始计算
      start_pos=rates_total-periodAMA-2;
      // 初始化信号缓冲区
      for(i=0; i<rates_total; i++)
        {
         kAMAupsig[i]=0.0;
         kAMAdownsig[i]=0.0;
        }
     }
   else
     {
      // 增量计算，只需重新计算最新的几根k线
      start_pos=rates_total-prev_calculated+1;
      if(start_pos<periodAMA+2)
         start_pos=periodAMA+2;
     }

//---- 确定初始AMA值 (从start_pos+1位置的收盘价开始)
   if(start_pos<rates_total-1)
      AMA0=close[start_pos+1];
   else
      AMA0=close[rates_total-1];

//---- 从旧到新逐根计算（Kaufman AMA 是序列依赖的）
   for(int pos=start_pos; pos>=0; pos--)
     {
      // 计算市场效率系数 ER
      signal=MathAbs(close[pos]-close[pos+periodAMA]);
      noise=0.000000001;
      for(i=0; i<periodAMA; i++)
         noise=noise+MathAbs(close[pos+i]-close[pos+i+1]);

      ER=signal/noise;

      // 计算平滑系数 SSC
      dSC=(fastSC-slowSC);
      ERSC=ER*dSC;
      SSC=ERSC+slowSC;
      SSC=SSC*SSC; // ERSC+slowSC 再做平方 (等效于 MathPow(SSC, G) 当 G=2.0)

      // 计算AMA
      AMA=AMA0+(SSC*(close[pos]-AMA0));
      kAMAbuffer[pos]=AMA;

      // 计算布林带偏差
      deviation=0;
      for(counter_Boll=0; counter_Boll<BollingerPeriod && (pos+counter_Boll)<rates_total; counter_Boll++)
         deviation=deviation+MathPow(close[pos+counter_Boll]-kAMAbuffer[pos+counter_Boll],2);
      deviation=MathSqrt(deviation/BollingerPeriod);

      // 计算上下布林带
      UpBand[pos]=AMA+deviation*K_Bollinger;
      DownBand[pos]=AMA-deviation*K_Bollinger;

      // 生成箭头信号
      ddK=(AMA-AMA0);
      if((MathAbs(ddK)>(dK*_Point)) && (ddK>0))
         kAMAupsig[pos]=AMA;
      if((MathAbs(ddK)>(dK*_Point)) && (ddK<0))
         kAMAdownsig[pos]=AMA;

      // 将当前AMA作为下一次迭代的AMA0
      AMA0=AMA;
     }

   prevbars=rates_total;
   return(rates_total);
  }
//+------------------------------------------------------------------+
