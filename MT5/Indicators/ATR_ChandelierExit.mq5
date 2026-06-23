//+------------------------------------------------------------------+
//|                                              ATR_ChandelierExit.mq5 |
//|                                    改编自 MT4 版本 ChandelierExit.mq4 |
//|                            原作者: MQLService |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//+------------------------------------------------------------------+
#property copyright "MQLService"
#property link      "scripts@mqlservice.com"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 4
#property indicator_plots   4
//---- 绘制属性
#property indicator_type1   DRAW_LINE
#property indicator_color1  Aqua
#property indicator_label1  "Chandelier Long"
#property indicator_type2   DRAW_LINE
#property indicator_color2  Magenta
#property indicator_label2  "Chandelier Short"
#property indicator_type3   DRAW_LINE
#property indicator_color3  Aqua
#property indicator_label3  "Chandelier Long (aux)"
#property indicator_type4   DRAW_LINE
#property indicator_color4  Magenta
#property indicator_label4  "Chandelier Short (aux)"

//---- 输入参数
input int    Range=7;         // 最高/最低价回溯周期
input int    Shift=0;         // 偏移
input int    ATRPeriod=9;     // ATR周期
input double ATRMultipl=2.5;  // ATR倍数
input bool   EmailAlert=false;// 邮件报警
input bool   pmAlert=false;   // 弹窗报警

//---- 指标缓冲区
double ExtMapBuffer3[];
double ExtMapBuffer4[];
double ExtMapBuffer1[];
double ExtMapBuffer2[];
double direction[];

//---- 全局变量
datetime jiaocha=0;
int      atr_handle=INVALID_HANDLE;

//+------------------------------------------------------------------+
//| 自定义指标初始化函数                                              |
//+------------------------------------------------------------------+
int OnInit()
  {
//---- 创建ATR指标句柄
   atr_handle=iATR(_Symbol,_Period,ATRPeriod);
   if(atr_handle==INVALID_HANDLE)
     {
      Print("无法创建 iATR 指标句柄");
      return(INIT_FAILED);
     }

//---- 设置指标缓冲区
   SetIndexBuffer(0,ExtMapBuffer3,INDICATOR_DATA);
   SetIndexBuffer(1,ExtMapBuffer4,INDICATOR_DATA);
   SetIndexBuffer(2,ExtMapBuffer1,INDICATOR_DATA);
   SetIndexBuffer(3,ExtMapBuffer2,INDICATOR_DATA);

//---- 设置辅助缓冲区(不用于绘制)
   IndicatorBuffers(5);
   SetIndexBuffer(4,direction,INDICATOR_CALCULATIONS);

//---- 设置空值
   PlotIndexSetDouble(2,PLOT_EMPTY_VALUE,0.0);
   PlotIndexSetDouble(3,PLOT_EMPTY_VALUE,0.0);

//---- 设置指标简称
   string shortnme="Chandelier("+IntegerToString(Range)+",ATR("+IntegerToString(ATRPeriod)+","+DoubleToString(ATRMultipl,2)+"))";
   IndicatorSetString(INDICATOR_SHORTNAME,shortnme);

   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| 自定义指标析构函数                                                |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
//---- 释放ATR指标句柄
   if(atr_handle!=INVALID_HANDLE)
      IndicatorRelease(atr_handle);
  }
//+------------------------------------------------------------------+
//| 自定义指标计算函数                                                |
//|   吊灯止损指标：基于ATR的最高价/最低价动态止损                      |
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

//---- 确定计算起始位置
   if(prev_calculated==0)
     {
      limit=rates_total-1;
      // 初始化方向缓冲区
      for(int i=0; i<rates_total; i++)
         direction[i]=0;
     }
   else
     {
      limit=rates_total-prev_calculated+1;
      if(limit<0) limit=0;
     }

//---- 获取ATR数据
   double atr_buffer[];
   ArraySetAsSeries(atr_buffer,true);
   if(CopyBuffer(atr_handle,0,0,rates_total,atr_buffer)<=0)
      return(0);

//---- 从旧到新逐根计算
   for(int i=limit; i>=0 && !IsStopped(); i--)
     {
      ExtMapBuffer1[i]=EMPTY_VALUE;
      ExtMapBuffer2[i]=EMPTY_VALUE;

      // 计算ATR值
      double ATRvalue=atr_buffer[i+Shift]*ATRMultipl;

      // 计算最高价区间的ATR下线 和 最低价区间的ATR上线
      double period_high=0,period_low=999999;
      for(int j=0; j<Range && (i+Shift+j)<rates_total; j++)
        {
         if(high[i+Shift+j]>period_high) period_high=high[i+Shift+j];
         if(low[i+Shift+j]<period_low)   period_low=low[i+Shift+j];
        }

      ExtMapBuffer1[i]=period_high-ATRvalue;
      ExtMapBuffer2[i]=period_low+ATRvalue;

      ExtMapBuffer3[i]=EMPTY_VALUE;
      ExtMapBuffer4[i]=EMPTY_VALUE;

      // 趋势方向判断
      direction[i]=direction[i+1];

      if(close[i]>ExtMapBuffer2[i+1]) direction[i]=1;
      if(close[i]<ExtMapBuffer1[i+1]) direction[i]=-1;

      // 根据方向收紧止损
      if(direction[i]>0)
        {
         if(ExtMapBuffer1[i]<ExtMapBuffer1[i+1])
            ExtMapBuffer1[i]=ExtMapBuffer1[i+1];
         ExtMapBuffer3[i]=ExtMapBuffer1[i];
         ExtMapBuffer4[i]=EMPTY_VALUE;
        }

      if(direction[i]<0)
        {
         if(ExtMapBuffer2[i]>ExtMapBuffer2[i+1])
            ExtMapBuffer2[i]=ExtMapBuffer2[i+1];
         ExtMapBuffer4[i]=ExtMapBuffer2[i];
         ExtMapBuffer3[i]=EMPTY_VALUE;
        }

      // 报警逻辑：多头信号
      if((ExtMapBuffer3[i+1]!=EMPTY_VALUE) && (ExtMapBuffer3[i+2]==EMPTY_VALUE))
        {
         if(i==0)
           {
            if(jiaocha!=time[0])
              {
               if(pmAlert)
                  Alert("ATR吊灯 做多 ",_Symbol," ",_Period," 分钟周期:  价格在 ",DoubleToString(SymbolInfoDouble(_Symbol,SYMBOL_BID),_Digits));
               if(EmailAlert)
                  SendMail("ATR在"+_Symbol+" "+EnumToString(_Period)+": 做多","在 "+DoubleToString(SymbolInfoDouble(_Symbol,SYMBOL_BID),_Digits));
               jiaocha=time[0];
              }
           }
        }

      // 报警逻辑：空头信号
      if((ExtMapBuffer4[i+1]!=EMPTY_VALUE) && (ExtMapBuffer4[i+2]==EMPTY_VALUE))
        {
         if(i==0)
           {
            if(jiaocha!=time[0])
              {
               if(pmAlert)
                  Alert("ATR吊灯 在"+_Symbol+" "+EnumToString(_Period)+" 分钟周期: 发出做空信号","     价格在 "+DoubleToString(SymbolInfoDouble(_Symbol,SYMBOL_BID),_Digits));
               if(EmailAlert)
                  SendMail("ATR在"+_Symbol+" "+EnumToString(_Period)+": 做空","在 "+DoubleToString(SymbolInfoDouble(_Symbol,SYMBOL_BID),_Digits));
               jiaocha=time[0];
              }
           }
        }
     }

   return(rates_total);
  }
//+------------------------------------------------------------------+
