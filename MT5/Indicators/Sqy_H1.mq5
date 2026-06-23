//+------------------------------------------------------------------+
//|                                                          Sqy_H1.mq5 |
//|                                    改编自 MT4 版本 Sqy_H1.mq4 |
//|                            原作者: CompanyName 2018 |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//|                            功能: 多周期数字多态SR感知指标 |
//|                            依赖: SqSr_mtf_eli_2 指标(需先编译) |
//|                            ⚠ 原版依赖行无行头文件(数字多态感知) |
//|                              已用简化多周期SR信号逻辑替代 |
//+------------------------------------------------------------------+
#property copyright "Copyright 2018, CompanyName"
#property link      "http://www.companyname.net"
#property version   "2.00"
#property indicator_separate_window
#property indicator_buffers 2
#property indicator_plots   2
//---- 绘制属性
#property indicator_type1   DRAW_LINE
#property indicator_color1  Coral
#property indicator_label1  "D1H4 SR"
#property indicator_type2   DRAW_LINE
#property indicator_color2  Aqua
#property indicator_label2  "H1M30 SR"

//---- 水平线
#property indicator_level1 6
#property indicator_levelcolor White
#property indicator_levelstyle STYLE_DOT

//---- 输入参数
input int    SRPeriod=55;                     // SR周期
input int    SRShift=8900;                    // 计算偏移量
input ENUM_TIMEFRAMES 周期选择=PERIOD_CURRENT; // 使用周期
input bool   可以因为MN1数不全忽略WN1数据=true; // WN1数据不全时继续

//---- 指标缓冲区
double D1H4SRBuffer[];
double H1M30SRBuffer[];

//---- 全局变量
bool   ExtParameters=false;
int    sr_handle=INVALID_HANDLE;

//+------------------------------------------------------------------+
//| 初始化                                                            |
//+------------------------------------------------------------------+
int OnInit()
  {
//---- 设置缓冲区
   SetIndexBuffer(0,D1H4SRBuffer,INDICATOR_DATA);
   SetIndexBuffer(1,H1M30SRBuffer,INDICATOR_DATA);

//---- 设置绘制属性
   PlotIndexSetInteger(0,PLOT_LINE_STYLE,STYLE_DASHDOT);
   PlotIndexSetInteger(0,PLOT_LINE_WIDTH,4);
   PlotIndexSetInteger(1,PLOT_LINE_STYLE,STYLE_DASHDOT);
   PlotIndexSetInteger(1,PLOT_LINE_WIDTH,2);

   PlotIndexSetInteger(0,PLOT_DRAW_BEGIN,SRPeriod);
   PlotIndexSetInteger(1,PLOT_DRAW_BEGIN,SRPeriod);

//---- 创建SqSr_mtf_eli_2指标句柄
//    buf0/1=W1上/下轨, buf2/3=D1上/下轨, buf4/5=H4上/下轨, buf6/7=H1上/下轨
   sr_handle=iCustom(_Symbol,周期选择,"SqSr_mtf_eli_2");
   if(sr_handle==INVALID_HANDLE)
     {
      Alert("提醒:"+_Symbol+" "+EnumToString(周期选择)+": 无法加载SqSr_mtf_eli_2指标，请先编译并安装该指标");
      return(INIT_FAILED);
     }

//---- 验证初始化参数
   double buf0[],buf1[];
   ArraySetAsSeries(buf0,true);
   ArraySetAsSeries(buf1,true);
   if(CopyBuffer(sr_handle,0,0,2,buf0)>=2 && CopyBuffer(sr_handle,1,0,2,buf1)>=2)
     {
      if(buf0[1]>0 && buf1[1]>0) ExtParameters=true;
      else if(可以因为MN1数不全忽略WN1数据) ExtParameters=true;
      else
        {
         Alert("提醒:"+_Symbol+" "+EnumToString(周期选择)+": 无法正确产生原始数据");
         return(INIT_FAILED);
        }
     }
   else ExtParameters=true;

   IndicatorSetString(INDICATOR_SHORTNAME,"Sqy_H1 SR Perception");
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| 析构                                                              |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(sr_handle!=INVALID_HANDLE) IndicatorRelease(sr_handle);
  }
//+------------------------------------------------------------------+
//| 计算                                                              |
//|   SqSr_mtf_eli_2 缓冲区映射:                                     |
//|   buf0/1=W1, buf2/3=D1, buf4/5=H4, buf6/7=H1                   |
//|   原版数字多态感知()来自行无行头文件(上万余行)，此处简化替代        |
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
   if(rates_total<=SRPeriod || !ExtParameters)
      return(0);

//---- 确定计算范围
   int limit=rates_total-prev_calculated;
   if(prev_calculated>0) limit++;
   limit=MathMin(SRShift,limit);

//---- 获取各周期SR数据
   double w1_up[],w1_down[];    // buf0/buf1
   double d1_up[],d1_down[];    // buf2/buf3
   double h4_up[],h4_down[];    // buf4/buf5
   double h1_up[],h1_down[];    // buf6/buf7

   ArraySetAsSeries(w1_up,true);  ArraySetAsSeries(w1_down,true);
   ArraySetAsSeries(d1_up,true);  ArraySetAsSeries(d1_down,true);
   ArraySetAsSeries(h4_up,true);  ArraySetAsSeries(h4_down,true);
   ArraySetAsSeries(h1_up,true);  ArraySetAsSeries(h1_down,true);

   bool ok=true;
   if(CopyBuffer(sr_handle,0,0,rates_total,w1_up)<=0) ok=false;
   if(CopyBuffer(sr_handle,1,0,rates_total,w1_down)<=0) ok=false;
   if(CopyBuffer(sr_handle,2,0,rates_total,d1_up)<=0) ok=false;
   if(CopyBuffer(sr_handle,3,0,rates_total,d1_down)<=0) ok=false;
   if(CopyBuffer(sr_handle,4,0,rates_total,h4_up)<=0) ok=false;
   if(CopyBuffer(sr_handle,5,0,rates_total,h4_down)<=0) ok=false;
   if(CopyBuffer(sr_handle,6,0,rates_total,h1_up)<=0) ok=false;
   if(CopyBuffer(sr_handle,7,0,rates_total,h1_down)<=0) ok=false;
   if(!ok) return(0);

//---- 逐根计算数字多态SR感知(简化版)
//   原版数字多态感知()是一个整合了波动性/趋势性/关键位/ATR止损
//   等多个维度的综合状态评分系统，此处用SR位置+趋势连续性替代
   for(int i=limit-1; i>=0 && !IsStopped(); i--)
     {
      if(i+1>=rates_total)
        {
         D1H4SRBuffer[i]=0;
         H1M30SRBuffer[i]=0;
         continue;
        }

      // D1H4综合感知: 大周期(W1/D1/H4)SR位置评分
      double d1h4_score=0;
      double h1m30_score=0;

      // W1级别 (最高权重)
      if(w1_up[i+1]>0 && close[i+1]>w1_up[i+1])          d1h4_score+=8;
      else if(w1_down[i+1]>0 && close[i+1]<w1_down[i+1]) d1h4_score-=8;

      // D1级别
      if(d1_up[i+1]>0 && close[i+1]>d1_up[i+1])          d1h4_score+=4;
      else if(d1_down[i+1]>0 && close[i+1]<d1_down[i+1]) d1h4_score-=4;

      // H4级别
      if(h4_up[i+1]>0 && close[i+1]>h4_up[i+1])          d1h4_score+=2;
      else if(h4_down[i+1]>0 && close[i+1]<h4_down[i+1]) d1h4_score-=2;

      // H1级别 — H1M30感知
      if(h1_up[i+1]>0 && close[i+1]>h1_up[i+1])          h1m30_score+=2;
      else if(h1_down[i+1]>0 && close[i+1]<h1_down[i+1]) h1m30_score-=2;

      // 趋势连续性加成
      if(i+2<rates_total)
        {
         if(d1_up[i+1]>0 && d1_up[i+2]>0 && close[i+1]>d1_up[i+1] && close[i+2]>d1_up[i+2]) d1h4_score+=2;
         if(d1_down[i+1]>0 && d1_down[i+2]>0 && close[i+1]<d1_down[i+1] && close[i+2]<d1_down[i+2]) d1h4_score-=2;
        }

      if(i+3<rates_total)
        {
         if(d1_up[i+1]>0 && d1_up[i+2]>0 && d1_up[i+3]>0 &&
            close[i+1]>d1_up[i+1] && close[i+2]>d1_up[i+2] && close[i+3]>d1_up[i+3]) d1h4_score+=3;
         if(d1_down[i+1]>0 && d1_down[i+2]>0 && d1_down[i+3]>0 &&
            close[i+1]<d1_down[i+1] && close[i+2]<d1_down[i+2] && close[i+3]<d1_down[i+3]) d1h4_score-=3;
        }

      D1H4SRBuffer[i]=d1h4_score;
      H1M30SRBuffer[i]=h1m30_score;
     }

   return(rates_total);
  }
//+------------------------------------------------------------------+
//|  注意:                                                           |
//|  原始MT4版本依赖:                                                |
//|    #include <行无行090.mqh>                                     |
//|    #include <行无行0011.mqh>                                    |
//|    #include <行无行001.mqh>                                     |
//|  核心函数 数字多态感知() 整合了波动性/趋势性/关键位/ATR止损/布林  |
//|  等多个维度的综合状态评分系统，涉及上万余行代码                   |
//|  本版本使用多周期SR位置+趋势连续性评分替代                       |
//|  如需完整功能，需要将上述3个include文件一并改编为MQL5            |
//+------------------------------------------------------------------+
