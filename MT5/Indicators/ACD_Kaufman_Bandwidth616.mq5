//+------------------------------------------------------------------+
//|                                          ACD_Kaufman_Bandwidth616.mq5 |
//|                                    改编自 MT4 版本 Bandswidth.mq4 |
//|                            原作者: Linuxser for Forex TSD |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//|                            依赖: Kaufman_Bands 指标 (需先编译) |
//+------------------------------------------------------------------+
#property copyright "Copyright 2004, MetaQuotes Software Corp."
#property link      "http://www.metaquotes.net/"
#property version   "1.00"
#property indicator_separate_window
#property indicator_buffers 8
#property indicator_plots   8
//---- 绘制属性
#property indicator_type1   DRAW_LINE
#property indicator_color1  Yellow
#property indicator_label1  "Kaufman20 Bandwidth"
#property indicator_type2   DRAW_LINE
#property indicator_color2  Aqua
#property indicator_label2  "BB20 Bandwidth"
#property indicator_type3   DRAW_LINE
#property indicator_color3  Red
#property indicator_label3  "BB50 Bandwidth"
#property indicator_type4   DRAW_LINE
#property indicator_color4  LimeGreen
#property indicator_label4  "Kaufman50 Bandwidth"
#property indicator_type5   DRAW_LINE
#property indicator_color5  Blue
#property indicator_label5  "BB20 Up (aux)"
#property indicator_type6   DRAW_LINE
#property indicator_color6  LightCoral
#property indicator_label6  "BB20 Down (aux)"
#property indicator_type7   DRAW_LINE
#property indicator_color7  Pink
#property indicator_label7  "BB50 Narrow (aux)"
//---- 第8个缓冲区（不绘制）
// property indicator_type8   DRAW_LINE
// property indicator_color8  Black

//---- 水平线（斐波那契衍生）
#property indicator_level1 0.0008
#property indicator_level2 0.0012
#property indicator_level3 0.0021
#property indicator_level4 0.0034
#property indicator_level5 0.0055
#property indicator_level6 0.0089
#property indicator_level7 0.0144
#property indicator_level8 0.0233
#property indicator_levelcolor White
#property indicator_levelstyle STYLE_DOT

//---- 输入参数
input int    BBPeriod=20;          // 布林带周期(20)
input int    StdDeviation=2;       // 标准差倍数
input int    BBPeriod1=20;         // 布林带周期1
input int    StdDeviation1=2;      // 标准差倍数1
input int    BBPeriod2=50;         // 布林带周期2
input int    StdDeviation2=2;      // 标准差倍数2
input int    BBPeriod3=50;         // 卡夫曼布林带周期3
input int    StdDeviation3=2;      // 卡夫曼标准差倍数3
input bool   EmailAlert=false;     // 邮件报警
input bool   pmAlert=false;        // 弹窗报警
input bool   M1_Email_Alert=false; // M1周期邮件报警
input bool   M5_Email_Alert=false; // M5周期邮件报警
input bool   M15_Email_Alert=false;// M15周期邮件报警
input bool   M30_Email_Alert=false;// M30周期邮件报警

//---- 指标缓冲区
double BLGBuffer[];   // 卡夫曼20带宽
double BLGBuffer1[];  // 布林20带宽
double BLGBuffer2[];  // 布林50带宽
double BLGBuffer3[];  // 卡夫曼50带宽
double BLGBuffer4[];  // 布林20多头辅助
double BLGBuffer5[];  // 布林20空头辅助
double BLGBuffer6[];  // 布林50收窄辅助
double BLGBuffer7[];  // 信号值(不绘制)

//---- 句柄和状态
int    kf_handle_def=INVALID_HANDLE;
int    kf_handle_custom=INVALID_HANDLE;
datetime jiaocha=0;
datetime jiaocha1=0;
datetime jiaocha2=0;

//+------------------------------------------------------------------+
//| 自定义指标初始化函数                                              |
//+------------------------------------------------------------------+
int OnInit()
  {
//---- 设置指标缓冲区
   SetIndexBuffer(0,BLGBuffer,INDICATOR_DATA);
   SetIndexBuffer(1,BLGBuffer1,INDICATOR_DATA);
   SetIndexBuffer(2,BLGBuffer2,INDICATOR_DATA);
   SetIndexBuffer(3,BLGBuffer3,INDICATOR_DATA);
   SetIndexBuffer(4,BLGBuffer4,INDICATOR_DATA);
   SetIndexBuffer(5,BLGBuffer5,INDICATOR_DATA);
   SetIndexBuffer(6,BLGBuffer6,INDICATOR_DATA);
   SetIndexBuffer(7,BLGBuffer7,INDICATOR_CALCULATIONS);

//---- 设置指标简称
   string short_name="KafmanBandswidth("+IntegerToString(BBPeriod)+","+IntegerToString(BBPeriod1)+","+IntegerToString(BBPeriod2)+","+IntegerToString(StdDeviation)+")";
   IndicatorSetString(INDICATOR_SHORTNAME,short_name);

//---- 设置绘制起始偏移
   PlotIndexSetInteger(0,PLOT_DRAW_BEGIN,BBPeriod);

//---- 创建Kaufman_Bands指标句柄（默认参数）
   kf_handle_def=iCustom(_Symbol,_Period,"Kaufman_Bands");
   if(kf_handle_def==INVALID_HANDLE)
     {
      Print("错误：无法加载 Kaufman_Bands 指标（默认参数），请确保已编译该指标");
      return(INIT_FAILED);
     }

//---- 创建Kaufman_Bands指标句柄（自定义参数: periodAMA=9,nfast=2,nslow=30,G=2.0,dK=2.0,BBPeriod3,StdDeviation3）
   kf_handle_custom=iCustom(_Symbol,_Period,"Kaufman_Bands",9,2,30,2.0,2.0,BBPeriod3,StdDeviation3);
   if(kf_handle_custom==INVALID_HANDLE)
     {
      Print("警告：无法加载 Kaufman_Bands 指标（自定义参数），将使用默认句柄");
     }

   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| 自定义指标析构函数                                                |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(kf_handle_def!=INVALID_HANDLE)
      IndicatorRelease(kf_handle_def);
   if(kf_handle_custom!=INVALID_HANDLE)
      IndicatorRelease(kf_handle_custom);
  }
//+------------------------------------------------------------------+
//| 自定义指标计算函数                                                |
//|   计算Kaufman Bands和Bollinger Bands的带宽比率                    |
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
   int i;

//---- 检查数据是否足够
   if(rates_total<=BBPeriod2)
      return(0);

//---- 确定计算起始位置
   int start_pos;
   if(prev_calculated==0)
     {
      start_pos=rates_total-BBPeriod2-1;
      for(i=1; i<=BBPeriod2; i++)
         BLGBuffer[rates_total-i]=0.0;
     }
   else
     {
      start_pos=rates_total-prev_calculated+1;
      if(start_pos<0) start_pos=0;
     }

//---- 获取Kaufman_Bands数据（默认参数）
   double kf_up_def[],kf_down_def[],kf_ama_def[];
   ArraySetAsSeries(kf_up_def,true);
   ArraySetAsSeries(kf_down_def,true);
   ArraySetAsSeries(kf_ama_def,true);
   int copied=CopyBuffer(kf_handle_def,3,0,rates_total,kf_up_def);    // 缓冲区3=UpBand
   copied=CopyBuffer(kf_handle_def,4,0,rates_total,kf_down_def);     // 缓冲区4=DownBand
   copied=CopyBuffer(kf_handle_def,0,0,rates_total,kf_ama_def);      // 缓冲区0=kAMAbuffer

//---- 获取Kaufman_Bands数据（自定义参数）
   double kf_up_cust[],kf_down_cust[],kf_ama_cust[];
   ArraySetAsSeries(kf_up_cust,true);
   ArraySetAsSeries(kf_down_cust,true);
   ArraySetAsSeries(kf_ama_cust,true);
   if(kf_handle_custom!=INVALID_HANDLE)
     {
      CopyBuffer(kf_handle_custom,3,0,rates_total,kf_up_cust);
      CopyBuffer(kf_handle_custom,4,0,rates_total,kf_down_cust);
      CopyBuffer(kf_handle_custom,0,0,rates_total,kf_ama_cust);
     }

//---- 从旧到新逐根计算
   for(int pos=start_pos; pos>=0 && !IsStopped(); pos--)
     {
      // 卡夫曼20带宽 = (上轨-下轨)/中轨
      if(kf_ama_def[pos]!=0)
         BLGBuffer[pos]=(kf_up_def[pos]-kf_down_def[pos])/kf_ama_def[pos];

      // 布林20带宽 = (上轨-下轨)/均线
      double bb_up20=iBands(_Symbol,_Period,BBPeriod1,StdDeviation1,0,PRICE_CLOSE,MODE_UPPER,pos);
      double bb_down20=iBands(_Symbol,_Period,BBPeriod1,StdDeviation1,0,PRICE_CLOSE,MODE_LOWER,pos);
      double bb_ma20=iMA(_Symbol,_Period,BBPeriod1,0,MODE_SMA,PRICE_CLOSE,pos);
      if(bb_ma20!=0)
         BLGBuffer1[pos]=(bb_up20-bb_down20)/bb_ma20;

      // 布林50带宽
      double bb_up50=iBands(_Symbol,_Period,BBPeriod2,StdDeviation2,0,PRICE_CLOSE,MODE_UPPER,pos);
      double bb_down50=iBands(_Symbol,_Period,BBPeriod2,StdDeviation2,0,PRICE_CLOSE,MODE_LOWER,pos);
      double bb_ma50=iMA(_Symbol,_Period,BBPeriod2,0,MODE_SMA,PRICE_CLOSE,pos);
      if(bb_ma50!=0)
         BLGBuffer2[pos]=(bb_up50-bb_down50)/bb_ma50;

      // 卡夫曼50带宽（自定义参数）
      if(kf_handle_custom!=INVALID_HANDLE && kf_ama_cust[pos]!=0)
         BLGBuffer3[pos]=(kf_up_cust[pos]-kf_down_cust[pos])/kf_ama_cust[pos];

      // 辅助线初始化
      BLGBuffer4[pos]=BLGBuffer1[pos];
      BLGBuffer5[pos]=BLGBuffer1[pos];
      BLGBuffer6[pos]=BLGBuffer2[pos];

      // 信号逻辑：布林20 > 卡夫曼20 且 满足扩展条件
      if(BLGBuffer1[pos]>BLGBuffer[pos] &&
         (BLGBuffer1[pos]>BLGBuffer2[pos] || BLGBuffer2[pos]>BLGBuffer2[pos+1] || BLGBuffer2[pos]>BLGBuffer3[pos]) &&
         BLGBuffer1[pos]>BLGBuffer3[pos] &&
         BLGBuffer1[pos+1]<BLGBuffer1[pos])
        {
         BLGBuffer5[pos]=EMPTY_VALUE;
         BLGBuffer7[pos]=1;
        }
      else if(BLGBuffer1[pos]<BLGBuffer[pos] &&
              BLGBuffer1[pos]<BLGBuffer2[pos] &&
              BLGBuffer1[pos]<BLGBuffer3[pos])
        {
         BLGBuffer4[pos]=EMPTY_VALUE;
         BLGBuffer7[pos]=-1;
        }
      else
        {
         BLGBuffer4[pos]=EMPTY_VALUE;
         BLGBuffer5[pos]=EMPTY_VALUE;
         BLGBuffer7[pos]=0;
        }

      // 布林50收窄信号
      if(BLGBuffer2[pos]<=BLGBuffer3[pos])
         BLGBuffer6[pos]=EMPTY_VALUE;
     }

//---- 报警逻辑
   CheckAlerts(time,rates_total);

   return(rates_total);
  }
//+------------------------------------------------------------------+
//| 报警检查函数                                                      |
//+------------------------------------------------------------------+
void CheckAlerts(const datetime &time[],int rates_total)
  {
//---- 进入双收蓝海信号
   if((BLGBuffer6[1]!=EMPTY_VALUE) && (BLGBuffer6[0]==EMPTY_VALUE))
     {
      if(jiaocha!=time[0])
        {
         if(pmAlert)
            Alert("提醒:"+_Symbol+" "+EnumToString(_Period)+" 分钟周期: 进入道生之德绪之的双收蓝海","    时间在 "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));
         if(ShouldEmailAlert())
            SendMail("提醒:"+_Symbol+" "+EnumToString(_Period)+": 进入道生之德绪之的双收蓝海"," 时间在 "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));
         jiaocha=time[0];
        }
     }
//---- 持续双收蓝海信号
   else if((BLGBuffer6[1]==EMPTY_VALUE) && (BLGBuffer6[0]==EMPTY_VALUE))
     {
      if(jiaocha1!=time[0])
        {
         if(pmAlert)
            Alert("提醒:"+_Symbol+" "+EnumToString(_Period)+" 分钟周期: 持续道生之德绪之的双收蓝海","    时间在 "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));
         if(ShouldEmailAlert())
            SendMail("提醒:"+_Symbol+" "+EnumToString(_Period)+": 持续道生之德绪之的双收蓝海"," 时间在 "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));
         jiaocha1=time[0];
        }
     }
//---- 离开双收蓝海信号
   else if((BLGBuffer6[1]==EMPTY_VALUE) && (BLGBuffer6[0]!=EMPTY_VALUE))
     {
      if(jiaocha2!=time[0])
        {
         if(pmAlert)
            Alert("提醒:"+_Symbol+" "+EnumToString(_Period)+" 分钟周期: 长出双收蓝海","    时间在 "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));
         if(ShouldEmailAlert())
            SendMail("提醒:"+_Symbol+" "+EnumToString(_Period)+": 长出双收蓝海"," 时间在 "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));
         jiaocha2=time[0];
        }
     }
  }
//+------------------------------------------------------------------+
//| 判断是否应发送邮件报警                                            |
//+------------------------------------------------------------------+
bool ShouldEmailAlert()
  {
   if(!EmailAlert) return(false);

   ENUM_TIMEFRAMES tf=_Period;
   if(tf>PERIOD_M30) return(true);
   if(tf==PERIOD_M1 && M1_Email_Alert) return(true);
   if(tf==PERIOD_M5 && M5_Email_Alert) return(true);
   if(tf==PERIOD_M15 && M15_Email_Alert) return(true);
   if(tf==PERIOD_M30 && M30_Email_Alert) return(true);

   return(false);
  }
//+------------------------------------------------------------------+
