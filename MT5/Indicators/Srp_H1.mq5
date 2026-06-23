//+------------------------------------------------------------------+
//|                                                          Srp_H1.mq5 |
//|                                    改编自 MT4 版本 Srp_H1.mq4 |
//|                            原作者: CompanyName 2018 |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//|                            功能: 多周期SR得分指标(W1/D1/H4/H1) |
//|                            依赖: SqSr_mtf_eli_2 指标(需先编译) |
//+------------------------------------------------------------------+
#property copyright "Copyright 2018, CompanyName"
#property link      "http://www.companyname.net"
#property version   "2.00"
#property indicator_separate_window
#property indicator_buffers 5
#property indicator_plots   5
//---- 绘制属性
#property indicator_type1   DRAW_LINE
#property indicator_color1  Coral
#property indicator_label1  "W1 SR Score"
#property indicator_type2   DRAW_LINE
#property indicator_color2  Aqua
#property indicator_label2  "D1 SR Score"
#property indicator_type3   DRAW_ARROW
#property indicator_color3  Magenta
#property indicator_label3  "H4 SR Score"
#property indicator_type4   DRAW_LINE
#property indicator_color4  Red
#property indicator_label4  "H1 SR Score"
#property indicator_type5   DRAW_LINE
#property indicator_color5  Yellow
#property indicator_label5  "Composite SR Score"

//---- 水平线
#property indicator_level1 3
#property indicator_level2 -3
#property indicator_level3 0
#property indicator_levelcolor Yellow
#property indicator_levelstyle STYLE_DOT

//---- 输入参数
input int    SRPeriod=55;                     // SR周期
input int    SRShift=189;                     // 计算偏移量
input bool   可以因为MN1数不全忽略WN1数据=true; // WN1数据不全时继续

//---- 指标缓冲区
double W1SRBuffer[];
double D1SRBuffer[];
double H4SRBuffer[];
double H1SRBuffer[];
double ZSRBuffer[];

//---- 全局变量
bool   ExtParameters=false;
int    sr_handle=INVALID_HANDLE;

//+------------------------------------------------------------------+
//| 初始化                                                            |
//+------------------------------------------------------------------+
int OnInit()
  {
//---- 设置缓冲区
   SetIndexBuffer(0,W1SRBuffer,INDICATOR_DATA);
   SetIndexBuffer(1,D1SRBuffer,INDICATOR_DATA);
   SetIndexBuffer(2,H4SRBuffer,INDICATOR_DATA);
   SetIndexBuffer(3,H1SRBuffer,INDICATOR_DATA);
   SetIndexBuffer(4,ZSRBuffer,INDICATOR_DATA);

//---- 设置绘制属性
   PlotIndexSetInteger(0,PLOT_LINE_STYLE,STYLE_DASHDOT);
   PlotIndexSetInteger(0,PLOT_LINE_WIDTH,2);
   PlotIndexSetInteger(1,PLOT_LINE_STYLE,STYLE_DASHDOT);
   PlotIndexSetInteger(1,PLOT_LINE_WIDTH,2);
   PlotIndexSetInteger(4,PLOT_LINE_STYLE,STYLE_DASHDOT);
   PlotIndexSetInteger(4,PLOT_LINE_WIDTH,2);

//---- 设置绘制起始
   PlotIndexSetInteger(0,PLOT_DRAW_BEGIN,SRPeriod);
   PlotIndexSetInteger(1,PLOT_DRAW_BEGIN,SRPeriod);
   PlotIndexSetInteger(2,PLOT_DRAW_BEGIN,SRPeriod);
   PlotIndexSetInteger(3,PLOT_DRAW_BEGIN,SRPeriod);
   PlotIndexSetInteger(4,PLOT_DRAW_BEGIN,SRPeriod);

//---- 创建SqSr_mtf_eli_2指标句柄(一个句柄含W1/D1/H4/H1四个周期)
   sr_handle=iCustom(_Symbol,_Period,"SqSr_mtf_eli_2");
   if(sr_handle==INVALID_HANDLE)
     {
      Alert("提醒:"+_Symbol+" "+EnumToString(_Period)+": 无法加载SqSr_mtf_eli_2指标，请先编译并安装该指标");
      return(INIT_FAILED);
     }

//---- 验证数据有效性
   double buf0[],buf1[];
   ArraySetAsSeries(buf0,true);
   ArraySetAsSeries(buf1,true);
   if(CopyBuffer(sr_handle,0,0,2,buf0)>=2 && CopyBuffer(sr_handle,1,0,2,buf1)>=2)
     {
      if(buf0[1]>0 && buf1[1]>0) ExtParameters=true;
      else if(可以因为MN1数不全忽略WN1数据) ExtParameters=true;
      else
        {
         Alert("提醒:"+_Symbol+" "+EnumToString(_Period)+": 无法正确产生WN1的原始数据");
         return(INIT_FAILED);
        }
     }
   else if(可以因为MN1数不全忽略WN1数据)
      ExtParameters=true;
   else
     {
      Alert("提醒:"+_Symbol+" "+EnumToString(_Period)+": 无法正确产生WN1和W1的原始数据");
      return(INIT_FAILED);
     }

   IndicatorSetString(INDICATOR_SHORTNAME,"Srp_H1 SR Score");
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
//|   buf0/1=W1 up/down, buf2/3=D1 up/down,                        |
//|   buf4/5=H4 up/down, buf6/7=H1 up/down                         |
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

//---- 获取SqSr_mtf_eli_2各周期SR数据
   double w1_up[],w1_down[];     // buf0=上轨, buf1=下轨
   double d1_up[],d1_down[];     // buf2=上轨, buf3=下轨
   double h4_up[],h4_down[];     // buf4=上轨, buf5=下轨
   double h1_up[],h1_down[];     // buf6=上轨, buf7=下轨

   ArraySetAsSeries(w1_up,true); ArraySetAsSeries(w1_down,true);
   ArraySetAsSeries(d1_up,true); ArraySetAsSeries(d1_down,true);
   ArraySetAsSeries(h4_up,true); ArraySetAsSeries(h4_down,true);
   ArraySetAsSeries(h1_up,true); ArraySetAsSeries(h1_down,true);

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

//---- 逐根计算多周期SR得分
   for(int i=limit-1; i>=0 && !IsStopped(); i--)
     {
      if(i+1>=rates_total) continue;

      // W1级别 (权重 8/-8) -> 使用 buf0(上轨)/buf1(下轨)
      if(w1_up[i+1]>0 && close[i+1]>w1_up[i+1])       W1SRBuffer[i]=8;
      else if(w1_down[i+1]>0 && close[i+1]<w1_down[i+1]) W1SRBuffer[i]=-8;
      else                                             W1SRBuffer[i]=0;

      // D1级别 (权重 4/-4) -> 使用 buf2(上轨)/buf3(下轨)
      if(d1_up[i+1]>0 && close[i+1]>d1_up[i+1])       D1SRBuffer[i]=4;
      else if(d1_down[i+1]>0 && close[i+1]<d1_down[i+1]) D1SRBuffer[i]=-4;
      else                                             D1SRBuffer[i]=0;

      // H4级别 (权重 2/-2) -> 使用 buf4(上轨)/buf5(下轨)
      if(h4_up[i+1]>0 && close[i+1]>h4_up[i+1])       H4SRBuffer[i]=2;
      else if(h4_down[i+1]>0 && close[i+1]<h4_down[i+1]) H4SRBuffer[i]=-2;
      else                                             H4SRBuffer[i]=0;

      // H1级别 (权重 1/-1) -> 使用 buf6(上轨)/buf7(下轨)
      if(h1_up[i+1]>0 && close[i+1]>h1_up[i+1])       H1SRBuffer[i]=1;
      else if(h1_down[i+1]>0 && close[i+1]<h1_down[i+1]) H1SRBuffer[i]=-1;
      else                                             H1SRBuffer[i]=0;

      // 综合得分 = W1*1 + D1*1 + H4*1 + H1*2
      ZSRBuffer[i]=W1SRBuffer[i]+D1SRBuffer[i]+H4SRBuffer[i]+H1SRBuffer[i]+H1SRBuffer[i];
     }

   return(rates_total);
  }
//+------------------------------------------------------------------+
