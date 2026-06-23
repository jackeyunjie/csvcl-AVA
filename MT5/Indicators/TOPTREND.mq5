//+------------------------------------------------------------------+
//|                                                        TOPTREND.mq5 |
//|                                    改编自 MT4 版本 BBands_Stop_v1.mq4 |
//|                            原作者: TrendLaboratory Ltd. |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//+------------------------------------------------------------------+
#property copyright "Copyright 2006, TrendLaboratory Ltd."
#property link      "http://finance.groups.yahoo.com/group/TrendLaboratory"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 6
#property indicator_plots   6
//---- 绘制属性
#property indicator_type1   DRAW_ARROW
#property indicator_color1  RoyalBlue
#property indicator_label1  "UpTrend Stop"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  Red
#property indicator_label2  "DownTrend Stop"
#property indicator_type3   DRAW_ARROW
#property indicator_color3  RoyalBlue
#property indicator_label3  "UpTrend Signal"
#property indicator_type4   DRAW_ARROW
#property indicator_color4  Red
#property indicator_label4  "DownTrend Signal"
#property indicator_type5   DRAW_LINE
#property indicator_color5  RoyalBlue
#property indicator_label5  "UpTrend Line"
#property indicator_type6   DRAW_LINE
#property indicator_color6  Red
#property indicator_label6  "DownTrend Line"

//---- 输入参数
input int    Length=20;       // 布林带周期
input int    Deviation=2;     // 标准差倍数
input double MoneyRisk=1.00;  // 偏移系数
input int    Signal=1;        // 信号显示模式: 1-信号+止损; 0-仅止损; 2-仅信号
input int    Line=1;          // 线条显示模式: 0-不显示; 1-显示
input int    Nbars=1000;      // 计算k线数量
input bool   SoundON=true;    // 声音报警开关

//---- 指标缓冲区
double UpTrendBuffer[];
double DownTrendBuffer[];
double UpTrendSignal[];
double DownTrendSignal[];
double UpTrendLine[];
double DownTrendLine[];

//---- 全局变量
bool TurnedUp=false;
bool TurnedDown=false;

//+------------------------------------------------------------------+
//| 自定义指标初始化函数                                              |
//+------------------------------------------------------------------+
int OnInit()
  {
//---- 设置指标缓冲区
   SetIndexBuffer(0,UpTrendBuffer,INDICATOR_DATA);
   SetIndexBuffer(1,DownTrendBuffer,INDICATOR_DATA);
   SetIndexBuffer(2,UpTrendSignal,INDICATOR_DATA);
   SetIndexBuffer(3,DownTrendSignal,INDICATOR_DATA);
   SetIndexBuffer(4,UpTrendLine,INDICATOR_DATA);
   SetIndexBuffer(5,DownTrendLine,INDICATOR_DATA);

//---- 设置箭头编码
   PlotIndexSetInteger(0,PLOT_ARROW,159);
   PlotIndexSetInteger(1,PLOT_ARROW,159);
   PlotIndexSetInteger(2,PLOT_ARROW,108);
   PlotIndexSetInteger(3,PLOT_ARROW,108);

//---- 设置小数位数
   IndicatorSetInteger(INDICATOR_DIGITS,_Digits);

//---- 设置指标简称
   IndicatorSetString(INDICATOR_SHORTNAME,"BBands Stop("+IntegerToString(Length)+","+IntegerToString(Deviation)+")");

   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| 自定义指标计算函数                                                |
//|   布林带止损指标：基于布林带上下轨的趋势跟踪止损                    |
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
   int    i,shift,trend;
   int    calc_bars=MathMin(Nbars,rates_total);

//---- 确定计算起始位置
   int start_pos;
   if(prev_calculated==0)
     {
      // 首次加载，初始化所有缓冲区
      start_pos=calc_bars-Length-1;
      if(start_pos<0) start_pos=0;
      for(shift=calc_bars-1; shift>=0; shift--)
        {
         UpTrendBuffer[shift]=0;
         DownTrendBuffer[shift]=0;
         UpTrendSignal[shift]=0;
         DownTrendSignal[shift]=0;
         UpTrendLine[shift]=EMPTY_VALUE;
         DownTrendLine[shift]=EMPTY_VALUE;
        }
     }
   else
     {
      // 增量更新，从需要更新的k线开始
      start_pos=rates_total-prev_calculated+1;
      if(start_pos<0) start_pos=0;
      if(start_pos>=calc_bars)
         start_pos=calc_bars-1;
     }

//---- 预计算布林带上下轨
   double smax[],smin[];
   ArrayResize(smax,calc_bars);
   ArrayResize(smin,calc_bars);

   for(shift=0; shift<calc_bars; shift++)
     {
      smax[shift]=iBands(_Symbol,_Period,Length,Deviation,0,PRICE_CLOSE,MODE_UPPER,shift);
      smin[shift]=iBands(_Symbol,_Period,Length,Deviation,0,PRICE_CLOSE,MODE_LOWER,shift);
     }

//---- 从旧到新逐根计算
   double bsmax[],bsmin[];
   ArrayResize(bsmax,calc_bars);
   ArrayResize(bsmin,calc_bars);

   for(shift=start_pos; shift>=0; shift--)
     {
      // 趋势判断
      if(close[shift]>smax[shift+1])
         trend=1;
      else if(close[shift]<smin[shift+1])
         trend=-1;
      else
        {
         // 保持前一根的趋势（将Trend从上一根继承）
         // 但在这里无法直接获取上一根趋势，因此在实际代码中应使用缓冲区记录
         // 此处简化处理：根据上一根的缓冲区值判断
         if(UpTrendBuffer[shift+1]!=0 && UpTrendBuffer[shift+1]!=-1.0)
            trend=1;
         else if(DownTrendBuffer[shift+1]!=0 && DownTrendBuffer[shift+1]!=-1.0)
            trend=-1;
         else
            trend=0;
        }

      // 收紧止损：趋势方向下，止损只能往有利方向移动
      if(trend>0 && smin[shift]<smin[shift+1])
         smin[shift]=smin[shift+1];
      if(trend<0 && smax[shift]>smax[shift+1])
         smax[shift]=smax[shift+1];

      // 计算偏移后的布林带止损
      bsmax[shift]=smax[shift]+0.5*(MoneyRisk-1)*(smax[shift]-smin[shift]);
      bsmin[shift]=smin[shift]-0.5*(MoneyRisk-1)*(smax[shift]-smin[shift]);

      // 偏移后的止损也保持收紧特性
      if(trend>0 && bsmin[shift]<bsmin[shift+1])
         bsmin[shift]=bsmin[shift+1];
      if(trend<0 && bsmax[shift]>bsmax[shift+1])
         bsmax[shift]=bsmax[shift+1];

      // 根据趋势方向填充缓冲区
      if(trend>0)
        {
         if(Signal>0 && UpTrendBuffer[shift+1]==-1.0)
           {
            UpTrendSignal[shift]=bsmin[shift];
            UpTrendBuffer[shift]=bsmin[shift];
            if(Line>0) UpTrendLine[shift]=bsmin[shift];
            if(SoundON && shift==0 && !TurnedUp)
              {
               Alert("BBands going Up on ",_Symbol,"-",EnumToString(_Period));
               TurnedUp=true;
               TurnedDown=false;
              }
           }
         else
           {
            UpTrendBuffer[shift]=bsmin[shift];
            if(Line>0) UpTrendLine[shift]=bsmin[shift];
            UpTrendSignal[shift]=-1;
           }
         if(Signal==2) UpTrendBuffer[shift]=0;
         DownTrendSignal[shift]=-1;
         DownTrendBuffer[shift]=-1.0;
         DownTrendLine[shift]=EMPTY_VALUE;
        }
      else if(trend<0)
        {
         if(Signal>0 && DownTrendBuffer[shift+1]==-1.0)
           {
            DownTrendSignal[shift]=bsmax[shift];
            DownTrendBuffer[shift]=bsmax[shift];
            if(Line>0) DownTrendLine[shift]=bsmax[shift];
            if(SoundON && shift==0 && !TurnedDown)
              {
               Alert("BBands going Down on ",_Symbol,"-",EnumToString(_Period));
               TurnedDown=true;
               TurnedUp=false;
              }
           }
         else
           {
            DownTrendBuffer[shift]=bsmax[shift];
            if(Line>0) DownTrendLine[shift]=bsmax[shift];
            DownTrendSignal[shift]=-1;
           }
         if(Signal==2) DownTrendBuffer[shift]=0;
         UpTrendSignal[shift]=-1;
         UpTrendBuffer[shift]=-1.0;
         UpTrendLine[shift]=EMPTY_VALUE;
        }
     }

   return(rates_total);
  }
//+------------------------------------------------------------------+
