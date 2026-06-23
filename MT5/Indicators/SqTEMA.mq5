//+------------------------------------------------------------------+
//|                                                         SqTEMA.mq5 |
//|                                    改编自 MT4 版本 SqTEMA.mq4 |
//|                            原作者: Mark Fric / Patrick Mulloy |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//|                            公式: TEMA = 3*EMA - 3*EMA(EMA) + EMA(EMA(EMA)) |
//+------------------------------------------------------------------+
#property copyright "Copyright 2012, Mark Fric"
#property link      "http://www.geneticbuilder.com/"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 1
#property indicator_plots   1
//---- 绘制属性
#property indicator_type1   DRAW_LINE
#property indicator_color1  Red
#property indicator_label1  "TEMA"

//---- 输入参数
input int                EMA_Period=14;          // EMA周期
input ENUM_APPLIED_PRICE Price_type=PRICE_OPEN;  // 价格类型

//---- 指标缓冲区
double Tema[];
double Ema[];
double EmaOfEma[];
double EmaOfEmaOfEma[];

//+------------------------------------------------------------------+
//| 初始化                                                            |
//+------------------------------------------------------------------+
int OnInit()
  {
//---- 4个缓冲区(1绘制 + 3计算)
   IndicatorBuffers(4);

   SetIndexBuffer(0,Tema,INDICATOR_DATA);
   SetIndexBuffer(1,Ema,INDICATOR_CALCULATIONS);
   SetIndexBuffer(2,EmaOfEma,INDICATOR_CALCULATIONS);
   SetIndexBuffer(3,EmaOfEmaOfEma,INDICATOR_CALCULATIONS);

   IndicatorSetInteger(INDICATOR_DIGITS,_Digits+2);
   IndicatorSetString(INDICATOR_SHORTNAME,"TEMA("+IntegerToString(EMA_Period)+")");

   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| 计算                                                              |
//|   TEMA = 3*EMA - 3*EMA(EMA) + EMA(EMA(EMA))                     |
//|   MT5不支持iMAOnArray，手动实现EMA数组计算                       |
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
   int limit;

   if(prev_calculated==0)
      limit=rates_total-EMA_Period;
   else
     {
      limit=rates_total-prev_calculated+EMA_Period;
      if(limit<0) limit=0;
     }

//---- 第一步：获取源价格数组
   for(int i=0; i<rates_total; i++)
      Ema[i]=GetAppliedPrice(i,open,high,low,close);

//---- 第二步：计算源价格的EMA
   CalculateEMA(Ema,rates_total,EMA_Period,limit);

//---- 第三步：将EMA结果拷贝到EmaOfEma，计算EMA的EMA
   for(int i=0; i<rates_total; i++)
      EmaOfEma[i]=Ema[i];
   CalculateEMA(EmaOfEma,rates_total,EMA_Period,limit);

//---- 第四步：计算EMA(EMA(EMA))
   for(int i=0; i<rates_total; i++)
      EmaOfEmaOfEma[i]=EmaOfEma[i];
   CalculateEMA(EmaOfEmaOfEma,rates_total,EMA_Period,limit);

//---- 第五步：TEMA = 3*EMA - 3*EMA(EMA) + EMA(EMA(EMA))
   for(int i=MathMax(0,rates_total-limit-1); i<rates_total && !IsStopped(); i++)
      Tema[i]=3*Ema[i]-3*EmaOfEma[i]+EmaOfEmaOfEma[i];

   return(rates_total);
  }
//+------------------------------------------------------------------+
//| 获取应用价格                                                      |
//+------------------------------------------------------------------+
double GetAppliedPrice(int i,const double &open[],const double &high[],
                       const double &low[],const double &close[])
  {
   switch(Price_type)
     {
      case PRICE_CLOSE:    return(close[i]);
      case PRICE_OPEN:     return(open[i]);
      case PRICE_HIGH:     return(high[i]);
      case PRICE_LOW:      return(low[i]);
      case PRICE_MEDIAN:   return((high[i]+low[i])/2.0);
      case PRICE_TYPICAL:  return((high[i]+low[i]+close[i])/3.0);
      case PRICE_WEIGHTED: return((high[i]+low[i]+close[i]+close[i])/4.0);
      default:             return(close[i]);
     }
  }
//+------------------------------------------------------------------+
//| 手动计算EMA（原地修改数组）                                        |
//|   将src[]的前limit个元素替换为它们的EMA值                         |
//+------------------------------------------------------------------+
void CalculateEMA(double &src[],int total,int period,int limit)
  {
   if(total<=period) return;

   double pr=2.0/(period+1);

//---- 计算第一个EMA值(简单平均作为初始值)
   double sum=0;
   for(int j=0; j<period; j++)
      sum+=src[total-1-j];
   src[total-1-period]=sum/period;

//---- 递推计算后续EMA值
   int start=total-2-period;
   if(start>total-limit) start=total-limit;
   for(int i=start; i>=0 && !IsStopped(); i--)
      src[i]=src[i+1]+pr*(src[i]-src[i+1]);
  }
//+------------------------------------------------------------------+
