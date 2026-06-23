//+------------------------------------------------------------------+
//|                                                SqSr_mtf_eli_2.mq5 |
//|                                    改编自 MT4 版本 SqSr_mtf_eli_2.mq4 |
//|                            原作者: Copyright 2006, Eli hayun |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//|                            功能: 多周期支撑阻力MTF指标 |
//|                            依赖: SqFractal 指标(需先编译) |
//+------------------------------------------------------------------+
#property copyright "Copyright 2006, Eli hayun"
#property link      "http://www.elihayun.com"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 8
#property indicator_plots   8
//---- 绘制属性
#property indicator_type1   DRAW_ARROW
#property indicator_color1  SteelBlue
#property indicator_label1  "Period_1 Up"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  Red
#property indicator_label2  "Period_1 Down"
#property indicator_type3   DRAW_ARROW
#property indicator_color3  Aqua
#property indicator_label3  "Period_2 Up"
#property indicator_type4   DRAW_ARROW
#property indicator_color4  Magenta
#property indicator_label4  "Period_2 Down"
#property indicator_type5   DRAW_ARROW
#property indicator_color5  CornflowerBlue
#property indicator_label5  "Period_3 Up"
#property indicator_type6   DRAW_ARROW
#property indicator_color6  DarkOrange
#property indicator_label6  "Period_3 Down"
#property indicator_type7   DRAW_LINE
#property indicator_color7  SkyBlue
#property indicator_label7  "Period_4 Up"
#property indicator_type8   DRAW_LINE
#property indicator_color8  Yellow
#property indicator_label8  "Period_4 Down"

//---- 输入参数
input bool 软件自动判断周期=true;          // 软件自动判断周期
input ENUM_TIMEFRAMES Period_1=PERIOD_W1;  // 周期1
input ENUM_TIMEFRAMES Period_2=PERIOD_D1;  // 周期2
input ENUM_TIMEFRAMES Period_3=PERIOD_H4;  // 周期3
input ENUM_TIMEFRAMES Period_4=PERIOD_H1;  // 周期4
input bool display_Period_1=true;          // 显示周期1
input bool display_Period_2=true;          // 显示周期2
input bool display_Period_3=true;          // 显示周期3
input bool display_Period_4=true;          // 显示周期4
input bool Play_Sound=false;               // 播放声音
input int  Fractal=5;                       // 分形参数(左右K线数)

//---- 指标缓冲区
double buf_up1D[];
double buf_down1D[];
double buf_up4H[];
double buf_down4H[];
double buf_up1H[];
double buf_down1H[];
double buf_up30M[];
double buf_down30M[];

//---- 分形指标句柄
int    fractal_handle1=INVALID_HANDLE;
int    fractal_handle2=INVALID_HANDLE;
int    fractal_handle3=INVALID_HANDLE;
int    fractal_handle4=INVALID_HANDLE;

//+------------------------------------------------------------------+
//| 初始化                                                            |
//+------------------------------------------------------------------+
int OnInit()
  {
//---- 自动判断周期
   if(软件自动判断周期)
     {
      switch(_Period)
        {
         case PERIOD_W1:  Period_1=PERIOD_MN1; Period_2=PERIOD_W1; Period_3=PERIOD_W1; Period_4=PERIOD_W1; break;
         case PERIOD_D1:  Period_1=PERIOD_MN1; Period_2=PERIOD_W1; Period_3=PERIOD_D1; Period_4=PERIOD_D1; break;
         case PERIOD_H4:  Period_1=PERIOD_MN1; Period_2=PERIOD_W1; Period_3=PERIOD_D1; Period_4=PERIOD_H4; break;
         case PERIOD_H1:  Period_1=PERIOD_W1;  Period_2=PERIOD_D1; Period_3=PERIOD_H4; Period_4=PERIOD_H1; break;
         case PERIOD_M30: Period_1=PERIOD_D1;  Period_2=PERIOD_H4; Period_3=PERIOD_H1; Period_4=PERIOD_M30; break;
         case PERIOD_M15: Period_1=PERIOD_H4;  Period_2=PERIOD_H1; Period_3=PERIOD_M30;Period_4=PERIOD_M15;break;
         case PERIOD_M5:  Period_1=PERIOD_H1;  Period_2=PERIOD_M30;Period_3=PERIOD_M15;Period_4=PERIOD_M5; break;
         case PERIOD_M1:  Period_1=PERIOD_M30; Period_2=PERIOD_M15;Period_3=PERIOD_M5; Period_4=PERIOD_M1; break;
        }
     }

//---- 周期不能小于当前周期
   if(Period_1<_Period) Period_1=_Period;
   if(Period_2<_Period) Period_2=_Period;
   if(Period_3<_Period) Period_3=_Period;
   if(Period_4<_Period) Period_4=_Period;

//---- 设置指针箭头
   PlotIndexSetInteger(0,PLOT_ARROW,159);
   PlotIndexSetInteger(1,PLOT_ARROW,159);
   PlotIndexSetInteger(2,PLOT_ARROW,159);
   PlotIndexSetInteger(3,PLOT_ARROW,159);
   PlotIndexSetInteger(4,PLOT_ARROW,159);
   PlotIndexSetInteger(5,PLOT_ARROW,159);
   PlotIndexSetInteger(6,PLOT_ARROW,159);
   PlotIndexSetInteger(7,PLOT_ARROW,159);

//---- 设置线宽
   PlotIndexSetInteger(0,PLOT_LINE_WIDTH,3);
   PlotIndexSetInteger(1,PLOT_LINE_WIDTH,3);
   PlotIndexSetInteger(2,PLOT_LINE_WIDTH,2);
   PlotIndexSetInteger(3,PLOT_LINE_WIDTH,2);

//---- 设置不显示的周期
   if(!display_Period_1 || Period_1<_Period) { PlotIndexSetInteger(0,PLOT_DRAW_TYPE,DRAW_NONE); PlotIndexSetInteger(1,PLOT_DRAW_TYPE,DRAW_NONE); }
   if(!display_Period_2 || Period_2<_Period) { PlotIndexSetInteger(2,PLOT_DRAW_TYPE,DRAW_NONE); PlotIndexSetInteger(3,PLOT_DRAW_TYPE,DRAW_NONE); }
   if(!display_Period_3 || Period_3<_Period) { PlotIndexSetInteger(4,PLOT_DRAW_TYPE,DRAW_NONE); PlotIndexSetInteger(5,PLOT_DRAW_TYPE,DRAW_NONE); }
   if(!display_Period_4 || Period_4<_Period) { PlotIndexSetInteger(6,PLOT_DRAW_TYPE,DRAW_NONE); PlotIndexSetInteger(7,PLOT_DRAW_TYPE,DRAW_NONE); }

//---- 设置缓冲区
   SetIndexBuffer(0,buf_up1D,INDICATOR_DATA);
   SetIndexBuffer(1,buf_down1D,INDICATOR_DATA);
   SetIndexBuffer(2,buf_up4H,INDICATOR_DATA);
   SetIndexBuffer(3,buf_down4H,INDICATOR_DATA);
   SetIndexBuffer(4,buf_up1H,INDICATOR_DATA);
   SetIndexBuffer(5,buf_down1H,INDICATOR_DATA);
   SetIndexBuffer(6,buf_up30M,INDICATOR_DATA);
   SetIndexBuffer(7,buf_down30M,INDICATOR_DATA);

//---- 设置标签
   PlotIndexSetString(0,PLOT_LABEL,tf2txt(Period_1)+" Up");
   PlotIndexSetString(1,PLOT_LABEL,tf2txt(Period_1)+" Down");
   PlotIndexSetString(2,PLOT_LABEL,tf2txt(Period_2)+" Up");
   PlotIndexSetString(3,PLOT_LABEL,tf2txt(Period_2)+" Down");
   PlotIndexSetString(4,PLOT_LABEL,tf2txt(Period_3)+" Up");
   PlotIndexSetString(5,PLOT_LABEL,tf2txt(Period_3)+" Down");
   PlotIndexSetString(6,PLOT_LABEL,tf2txt(Period_4)+" Up");
   PlotIndexSetString(7,PLOT_LABEL,tf2txt(Period_4)+" Down");

//---- 创建SqFractal指标句柄(4个周期)
   fractal_handle1=iCustom(_Symbol,Period_1,"SqFractal",Fractal);
   fractal_handle2=iCustom(_Symbol,Period_2,"SqFractal",Fractal);
   fractal_handle3=iCustom(_Symbol,Period_3,"SqFractal",Fractal);
   fractal_handle4=iCustom(_Symbol,Period_4,"SqFractal",Fractal);

   if(fractal_handle1==INVALID_HANDLE || fractal_handle2==INVALID_HANDLE ||
      fractal_handle3==INVALID_HANDLE || fractal_handle4==INVALID_HANDLE)
     {
      Print("无法创建SqFractal指标句柄，请先编译SqFractal.mq5");
      return(INIT_FAILED);
     }

   IndicatorSetString(INDICATOR_SHORTNAME,"SqSr_MTF "+tf2txt(Period_1)+"/"+tf2txt(Period_2)+"/"+tf2txt(Period_3)+"/"+tf2txt(Period_4));
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| 析构                                                              |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(fractal_handle1!=INVALID_HANDLE) IndicatorRelease(fractal_handle1);
   if(fractal_handle2!=INVALID_HANDLE) IndicatorRelease(fractal_handle2);
   if(fractal_handle3!=INVALID_HANDLE) IndicatorRelease(fractal_handle3);
   if(fractal_handle4!=INVALID_HANDLE) IndicatorRelease(fractal_handle4);
  }
//+------------------------------------------------------------------+
//| 计算                                                              |
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
   int limit=rates_total-prev_calculated+Period_4/PeriodSeconds(_Period);
   if(limit<0) limit=0;

//---- 获取各周期时间序列
   datetime TimeArray_1D[],TimeArray_4H[],TimeArray_1H[],TimeArray_30M[];
   ArraySetAsSeries(TimeArray_1D,true);
   ArraySetAsSeries(TimeArray_4H,true);
   ArraySetAsSeries(TimeArray_1H,true);
   ArraySetAsSeries(TimeArray_30M,true);

   CopyTime(_Symbol,Period_1,0,rates_total,TimeArray_1D);
   CopyTime(_Symbol,Period_2,0,rates_total,TimeArray_4H);
   CopyTime(_Symbol,Period_3,0,rates_total,TimeArray_1H);
   CopyTime(_Symbol,Period_4,0,rates_total,TimeArray_30M);

//---- 获取分形数据
   double frac1_up[],frac1_down[],frac2_up[],frac2_down[];
   double frac3_up[],frac3_down[],frac4_up[],frac4_down[];
   ArraySetAsSeries(frac1_up,true); ArraySetAsSeries(frac1_down,true);
   ArraySetAsSeries(frac2_up,true); ArraySetAsSeries(frac2_down,true);
   ArraySetAsSeries(frac3_up,true); ArraySetAsSeries(frac3_down,true);
   ArraySetAsSeries(frac4_up,true); ArraySetAsSeries(frac4_down,true);

   CopyBuffer(fractal_handle1,0,0,rates_total,frac1_up);   // UPPER fractal
   CopyBuffer(fractal_handle1,1,0,rates_total,frac1_down); // LOWER fractal
   CopyBuffer(fractal_handle2,0,0,rates_total,frac2_up);
   CopyBuffer(fractal_handle2,1,0,rates_total,frac2_down);
   CopyBuffer(fractal_handle3,0,0,rates_total,frac3_up);
   CopyBuffer(fractal_handle3,1,0,rates_total,frac3_down);
   CopyBuffer(fractal_handle4,0,0,rates_total,frac4_up);
   CopyBuffer(fractal_handle4,1,0,rates_total,frac4_down);

//---- 逐根对齐各周期时间并填充分形值
   int y1d=0,y4h=0,y1h=0,y30m=0;
   for(int i=limit; i>=0 && !IsStopped(); i--)
     {
      while(y1d<rates_total-1 && time[i]<TimeArray_1D[y1d]) y1d++;
      while(y4h<rates_total-1 && time[i]<TimeArray_4H[y4h]) y4h++;
      while(y1h<rates_total-1 && time[i]<TimeArray_1H[y1h]) y1h++;
      while(y30m<rates_total-1 && time[i]<TimeArray_30M[y30m]) y30m++;

      buf_up1D[i]   =frac1_up[y1d];
      buf_down1D[i] =frac1_down[y1d];
      buf_up4H[i]   =frac2_up[y4h];
      buf_down4H[i] =frac2_down[y4h];
      buf_up1H[i]   =frac3_up[y1h];
      buf_down1H[i] =frac3_down[y1h];
      buf_up30M[i]  =frac4_up[y30m];
      buf_down30M[i]=frac4_down[y30m];
     }

//---- 向前填充(当分形值为0时继承前一个有效值，使SR线连续)
   double pu_1=0,pd_1=0,pu_2=0,pd_2=0,pu_3=0,pd_3=0,pu_4=0,pd_4=0;
   for(int i=limit; i>=0 && !IsStopped(); i--)
     {
      if(buf_up1D[i]==0)   buf_up1D[i]=pu_1;   else pu_1=buf_up1D[i];
      if(buf_down1D[i]==0) buf_down1D[i]=pd_1; else pd_1=buf_down1D[i];
      if(buf_up4H[i]==0)   buf_up4H[i]=pu_2;   else pu_2=buf_up4H[i];
      if(buf_down4H[i]==0) buf_down4H[i]=pd_2; else pd_2=buf_down4H[i];
      if(buf_up1H[i]==0)   buf_up1H[i]=pu_3;   else pu_3=buf_up1H[i];
      if(buf_down1H[i]==0) buf_down1H[i]=pd_3; else pd_3=buf_down1H[i];
      if(buf_up30M[i]==0)  buf_up30M[i]=pu_4;  else pu_4=buf_up30M[i];
      if(buf_down30M[i]==0) buf_down30M[i]=pd_4;else pd_4=buf_down30M[i];
     }

   return(rates_total);
  }
//+------------------------------------------------------------------+
//| 时间周期转文本                                                    |
//+------------------------------------------------------------------+
string tf2txt(ENUM_TIMEFRAMES tf)
  {
   switch(tf)
     {
      case PERIOD_M1:  return("M1");
      case PERIOD_M5:  return("M5");
      case PERIOD_M15: return("M15");
      case PERIOD_M30: return("M30");
      case PERIOD_H1:  return("H1");
      case PERIOD_H4:  return("H4");
      case PERIOD_D1:  return("D1");
      case PERIOD_W1:  return("W1");
      case PERIOD_MN1: return("MN1");
     }
   return("??");
  }
//+------------------------------------------------------------------+
