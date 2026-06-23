//+------------------------------------------------------------------+
//|                                                       ACD_枢轴.mq5 |
//|                                    改编自 MT4 版本 TSR_Ranges.mq4 |
//|                            原作者: Ogeima / cja |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//|                            功能: 多周期枢轴计算+交易辅助面板 |
//+------------------------------------------------------------------+
#property copyright "Copyright 2006, Ogeima"
#property link      "ph_bresson@yahoo.com"
#property version   "1.00"
#property indicator_separate_window

//---- 输入参数
input double  Risk_to_Reward_ratio=3.0;  // 风险回报比
input string  交易趋势方向="做多";        // 交易趋势方向
input string  w1="ACD_枢轴";             // 指标简称
input string  shuzhouhe="3+6+1";         // 枢轴组合方式: 3+6+1,3+6,3+1,6+1
input int     Open_Hour=3;               // 开盘小时
input int     Open_Minute=15;            // 开盘分钟
input int     Openlong=20;               // 开盘时长(分钟)
input int     a=28;                      // A值
input int     c=100;                     // C值
input int     计算起始日=0;               // 计算起始日偏移
input int     调整横位0=180;              // 横坐标调整
input int     扩大显示空间基础单元=50;     // 显示空间单元
input int     前三行显示字体大小=10;       // 字体大小
input int     扩大Y轴空间基础单元=15;      // Y轴空间单元
input bool    显示距离止损位最小开仓损失金额计算=true; // 显示止损计算
input bool    EmailAlert=true;           // 邮件报警
input bool    pmAlert=false;             // 弹窗报警
input bool    报警已经处理=false;         // 报警已处理标志
input int     alert_6s=3;               // 6日收缩报警阈值
input int     alert_3s=2;               // 3日收缩报警阈值
input int     alert_1s=1;               // 1日收缩报警阈值
input int     alert_hs=8;               // 综合收缩报警阈值

//---- 全局变量
int    nDigits;
double Point_Value;
double A_Point;
double C_Point;
double UnitMINSizing;
double Symblo_SPREAD;
bool   OK_Volue=true;
double dianchasguzhi=1;
double 计价货币转换值=1;
datetime jiaocha=0;
string  short_name;

//+------------------------------------------------------------------+
//| 自定义指标初始化函数                                              |
//+------------------------------------------------------------------+
int OnInit()
  {
   short_name=w1;
   IndicatorSetString(INDICATOR_SHORTNAME,short_name);

   if(显示距离止损位最小开仓损失金额计算)
      CalculateTradeMetrics();

   nDigits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| 计算交易度量参数（点值、最小手数、点差等）                         |
//+------------------------------------------------------------------+
void CalculateTradeMetrics()
  {
//---- 计价货币转换值（简化处理，MT5不再支持AccountCompany）
   计价货币转换值=1;

//---- 点差估值
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   switch(digits)
     {
      case 0:  dianchasguzhi=1;       break;
      case 1:  dianchasguzhi=0.1;     break;
      case 2:  dianchasguzhi=0.01;    break;
      case 3:  dianchasguzhi=0.001;   break;
      case 4:  dianchasguzhi=0.0001;  break;
      case 5:  dianchasguzhi=0.00001; break;
     }

   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double spread_pts=(double)SymbolInfoInteger(_Symbol,SYMBOL_SPREAD);
   double jisuanjiage=ask+spread_pts*dianchasguzhi;

   Point_Value=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE)/SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE)*计价货币转换值;
   UnitMINSizing=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   Symblo_SPREAD=spread_pts*dianchasguzhi;
   OK_Volue=true;
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
   int R1=0,R5=0,R10=0,R20=0,RAvg=0;

//---- 获取日线数据
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   int copied=CopyRates(_Symbol,PERIOD_D1,0,101,rates);
   if(copied<100) return(0);

//---- 数组定义
   double rates_dpvr[101][40];  // 每日多周期枢轴数据
   double ra1[101],ra2[101],ra3[101],ra4[101];
   int    day[101],month[101];
   double rates_dpr[3][101][9];  // 1日/3日/6日枢轴价格
   datetime dt[101];

   int    zihao1[101],zihao2[101],zihao3[101],zihao4[101];
   color  zise1[101],zise2[101],zise3[101],zise4[101];

//---- 初始化
   ArrayInitialize(ra1,0);
   ArrayInitialize(ra2,0);
   ArrayInitialize(ra3,0);
   ArrayInitialize(ra4,0);

//---- 第一步：计算各周期枢轴数据
   for(int d=99; d>=0; d--)
     {
      if(d>=copied) continue;

      // 1日数据
      rates_dpr[0][d][0]=rates[d].low;   // 低点
      rates_dpr[0][d][1]=rates[d].high;  // 高点
      rates_dpr[0][d][2]=rates[d].close; // 收盘价
      rates_dpr[0][d][3]=rates_dpr[0][d][0]-rates_dpr[0][d][1]; // 价幅

      dt[d]=rates[d].time;
      day[d]=TimeDay(dt[d]);
      month[d]=TimeMonth(dt[d]);

      // 1日枢轴
      rates_dpvr[d][1]=rates[d].high;       // 最高价
      rates_dpvr[d][2]=rates[d].low;        // 最低价
      rates_dpvr[d][4]=rates[d].close;      // 收盘价
      rates_dpvr[d][0]=(rates_dpvr[d][1]+rates_dpvr[d][2]+rates_dpvr[d][4])/3; // 枢轴价格
      rates_dpvr[d][3]=2*MathAbs(rates_dpvr[d][0]-(rates_dpvr[d][1]+rates_dpvr[d][2])/2); // 枢轴价副
      rates_dpvr[d][5]=rates_dpvr[d][0]+rates_dpvr[d][3]/2; // 枢轴高点
      rates_dpvr[d][6]=rates_dpvr[d][0]-rates_dpvr[d][3]/2; // 枢轴低点
      rates_dpvr[d][7]=rates_dpvr[d][1]-rates_dpvr[d][2];   // 价格波幅
      ra1[d]=rates_dpvr[d][3];

      // 3日枢轴
      if(d+1<copied && d+2<copied)
        {
         rates_dpvr[d][11]=MathMax(MathMax(rates[d+1].high,rates[d].high),rates[d+2].high);
         rates_dpvr[d][12]=MathMin(MathMin(rates[d+1].low,rates[d].low),rates[d+2].low);
        }
      else
        {
         rates_dpvr[d][11]=rates[d].high;
         rates_dpvr[d][12]=rates[d].low;
        }
      rates_dpvr[d][14]=rates[d].close;
      rates_dpvr[d][10]=(rates_dpvr[d][11]+rates_dpvr[d][12]+rates_dpvr[d][14])/3;
      rates_dpvr[d][13]=2*MathAbs(rates_dpvr[d][10]-(rates_dpvr[d][11]+rates_dpvr[d][12])/2);
      rates_dpvr[d][15]=rates_dpvr[d][10]+rates_dpvr[d][13]/2;
      rates_dpvr[d][16]=rates_dpvr[d][10]-rates_dpvr[d][13]/2;
      rates_dpvr[d][17]=rates_dpvr[d][11]-rates_dpvr[d][12];
      ra2[d]=rates_dpvr[d][13];

      // 6日枢轴
      if(d+3<copied && d+4<copied && d+5<copied)
        {
         rates_dpvr[d][21]=MathMax(MathMax(MathMax(rates[d+3].high,rates[d+4].high),rates[d+5].high),rates_dpvr[d][11]);
         rates_dpvr[d][22]=MathMin(MathMin(MathMin(rates[d+3].low,rates[d+4].low),rates[d+5].low),rates_dpvr[d][12]);
        }
      else
        {
         rates_dpvr[d][21]=rates_dpvr[d][11];
         rates_dpvr[d][22]=rates_dpvr[d][12];
        }
      rates_dpvr[d][24]=rates[d].close;
      rates_dpvr[d][20]=(rates_dpvr[d][21]+rates_dpvr[d][22]+rates_dpvr[d][24])/3;
      rates_dpvr[d][23]=2*MathAbs(rates_dpvr[d][20]-(rates_dpvr[d][21]+rates_dpvr[d][22])/2);
      rates_dpvr[d][25]=rates_dpvr[d][20]+rates_dpvr[d][23]/2;
      rates_dpvr[d][26]=rates_dpvr[d][20]-rates_dpvr[d][23]/2;
      rates_dpvr[d][27]=rates_dpvr[d][21]-rates_dpvr[d][22];
      ra3[d]=rates_dpvr[d][23];

      // 综合枢轴计算（根据shuzhouhe参数）
      if(shuzhouhe=="6+1")
        {
         rates_dpvr[d][33]=rates_dpvr[d][23]+rates_dpvr[d][3];
         rates_dpvr[d][35]=MathMax(rates_dpvr[d][25],rates_dpvr[d][5]);
         rates_dpvr[d][36]=MathMin(rates_dpvr[d][26],rates_dpvr[d][6]);
         ra4[d]=rates_dpvr[d][33];
        }
      else if(shuzhouhe=="3+1")
        {
         rates_dpvr[d][33]=rates_dpvr[d][13]+rates_dpvr[d][3];
         rates_dpvr[d][35]=MathMax(rates_dpvr[d][15],rates_dpvr[d][5]);
         rates_dpvr[d][36]=MathMin(rates_dpvr[d][16],rates_dpvr[d][6]);
         ra4[d]=rates_dpvr[d][33];
        }
      else if(shuzhouhe=="3+6")
        {
         rates_dpvr[d][33]=rates_dpvr[d][23]+rates_dpvr[d][13];
         rates_dpvr[d][35]=MathMax(rates_dpvr[d][15],rates_dpvr[d][25]);
         rates_dpvr[d][36]=MathMin(rates_dpvr[d][16],rates_dpvr[d][26]);
         ra4[d]=rates_dpvr[d][33];
        }
      else // 3+6+1
        {
         rates_dpvr[d][33]=rates_dpvr[d][23]+rates_dpvr[d][13]+rates_dpvr[d][3];
         rates_dpvr[d][35]=MathMax(MathMax(rates_dpvr[d][15],rates_dpvr[d][25]),rates_dpvr[d][5]);
         rates_dpvr[d][36]=MathMin(MathMin(rates_dpvr[d][16],rates_dpvr[d][26]),rates_dpvr[d][6]);
         ra4[d]=rates_dpvr[d][33];
        }
     }

//---- 获取当前价格（M15收盘价）
   double 使用价格=0;
   double m15_close[];
   ArraySetAsSeries(m15_close,true);
   if(CopyClose(_Symbol,PERIOD_M15,0,2,m15_close)>=2)
      使用价格=m15_close[1];
   else
      使用价格=SymbolInfoDouble(_Symbol,SYMBOL_BID);

   double ZB63_10=使用价格;

//---- 枢轴位置分析变量
   color zise15=clrGray,zise16=clrGray,zise25=clrGray,zise26=clrGray;
   color zise35=clrGray,zise36=clrGray,zise45=clrGray,zise46=clrGray;
   double SZ1JIAGE=0,SZ1JULI=0,SZ1R=0,SZ1YANSE=clrGray;
   double SZ3JIAGE=0,SZ3JULI=0,SZ3R=0,SZ3YANSE=clrGray;
   double SZ6JIAGE=0,SZ6JULI=0,SZ6R=0,SZ6YANSE=clrGray;

//---- 6日枢轴位置判断
   if(ZB63_10>=rates_dpvr[1][25])
     {
      zise35=clrGreen; zise36=clrGreen;
      SZ6YANSE=clrGreen;
      if(交易趋势方向=="做多")
        {
         SZ6JIAGE=rates_dpvr[1][26];
         SZ6R=Point_Value*UnitMINSizing*(MathAbs(使用价格-SZ6JIAGE)+Symblo_SPREAD);
         SZ6JULI=MathAbs(使用价格-SZ6JIAGE)+Symblo_SPREAD;
        }
     }
   else if(ZB63_10<=rates_dpvr[1][26])
     {
      zise35=clrRed; zise36=clrRed;
      SZ6YANSE=clrRed;
      if(交易趋势方向=="做空")
        {
         SZ6JIAGE=rates_dpvr[1][25];
         SZ6JULI=MathAbs(使用价格-SZ6JIAGE)+Symblo_SPREAD;
         SZ6R=Point_Value*UnitMINSizing*(MathAbs(使用价格-SZ6JIAGE)+Symblo_SPREAD);
        }
     }
   else
     {
      zise35=clrGray; zise36=clrGray; SZ6YANSE=clrGray;
      if(交易趋势方向=="做多")
        {
         SZ6JIAGE=rates_dpvr[1][26];
         SZ6JULI=MathAbs(使用价格-SZ6JIAGE)+Symblo_SPREAD;
         SZ6R=Point_Value*UnitMINSizing*(MathAbs(使用价格-SZ6JIAGE)+Symblo_SPREAD);
        }
      else if(交易趋势方向=="做空")
        {
         SZ6JIAGE=rates_dpvr[1][25];
         SZ6R=Point_Value*UnitMINSizing*(MathAbs(使用价格-SZ6JIAGE)+Symblo_SPREAD);
         SZ6JULI=MathAbs(使用价格-SZ6JIAGE)+Symblo_SPREAD;
        }
     }

//---- 3日枢轴位置判断
   if(ZB63_10>=rates_dpvr[1][15])
     {
      zise25=clrGreen; zise26=clrGreen; SZ3YANSE=clrGreen;
      if(交易趋势方向=="做多")
        {SZ3JIAGE=rates_dpvr[1][16]; SZ3R=Point_Value*UnitMINSizing*(MathAbs(使用价格-SZ3JIAGE)+Symblo_SPREAD); SZ3JULI=MathAbs(使用价格-SZ3JIAGE)+Symblo_SPREAD;}
     }
   else if(ZB63_10<=rates_dpvr[1][16])
     {
      zise25=clrRed; zise26=clrRed; SZ3YANSE=clrRed;
      if(交易趋势方向=="做空")
        {SZ3JIAGE=rates_dpvr[1][15]; SZ3JULI=MathAbs(使用价格-SZ3JIAGE)+Symblo_SPREAD; SZ3R=Point_Value*UnitMINSizing*(MathAbs(使用价格-SZ3JIAGE)+Symblo_SPREAD);}
     }
   else
     {
      zise25=clrGray; zise26=clrGray; SZ3YANSE=clrGray;
      if(交易趋势方向=="做多")
        {SZ3JIAGE=rates_dpvr[1][16]; SZ3R=Point_Value*UnitMINSizing*(MathAbs(使用价格-SZ3JIAGE)+Symblo_SPREAD); SZ3JULI=MathAbs(使用价格-SZ3JIAGE)+Symblo_SPREAD;}
      else if(交易趋势方向=="做空")
        {SZ3JIAGE=rates_dpvr[1][15]; SZ3JULI=MathAbs(使用价格-SZ3JIAGE)+Symblo_SPREAD; SZ3R=Point_Value*UnitMINSizing*(MathAbs(使用价格-SZ3JIAGE)+Symblo_SPREAD);}
     }

//---- 1日枢轴位置判断
   if(ZB63_10>=rates_dpvr[1][5])
     {
      zise15=clrGreen; zise16=clrGreen; SZ1YANSE=clrGreen;
      if(交易趋势方向=="做多")
        {SZ1JIAGE=rates_dpvr[1][6]; SZ1R=Point_Value*UnitMINSizing*(MathAbs(使用价格-SZ1JIAGE)+Symblo_SPREAD); SZ1JULI=MathAbs(使用价格-SZ1JIAGE)+Symblo_SPREAD;}
     }
   else if(ZB63_10<=rates_dpvr[1][6])
     {
      zise15=clrRed; zise16=clrRed; SZ1YANSE=clrRed;
      if(交易趋势方向=="做空")
        {SZ1JIAGE=rates_dpvr[1][5]; SZ1JULI=MathAbs(使用价格-SZ1JIAGE)+Symblo_SPREAD; SZ1R=Point_Value*UnitMINSizing*(MathAbs(使用价格-SZ1JIAGE)+Symblo_SPREAD);}
     }
   else
     {
      zise15=clrGray; zise16=clrGray; SZ1YANSE=clrGray;
      if(交易趋势方向=="做多")
        {SZ1JIAGE=rates_dpvr[1][6]; SZ1R=Point_Value*UnitMINSizing*(MathAbs(使用价格-SZ1JIAGE)+Symblo_SPREAD); SZ1JULI=MathAbs(使用价格-SZ1JIAGE)+Symblo_SPREAD;}
      else if(交易趋势方向=="做空")
        {SZ1JIAGE=rates_dpvr[1][5]; SZ1JULI=MathAbs(使用价格-SZ1JIAGE)+Symblo_SPREAD; SZ1R=Point_Value*UnitMINSizing*(MathAbs(使用价格-SZ1JIAGE)+Symblo_SPREAD);}
     }

//---- 计算收缩判别
   int geshu1=0,geshu2=0,geshu3=0;
   for(int r=2; r<33 && r<copied; r++)
     {if(ra1[r]<ra1[1]) geshu1++;}
   for(int t=2; t<33 && t<copied; t++)
     {if(ra2[t]<ra2[1]) geshu2++;}
   for(int u=2; u<33 && u<copied; u++)
     {if(ra3[u]<ra3[1]) geshu3++;}

//---- 枢轴价副趋势分析
   for(int Z=0; Z<33 && Z+3<copied; Z++)
     {
      int ZZ=Z+计算起始日;
      zihao1[ZZ]=10; zise1[ZZ]=clrWhite;
      if(ra1[ZZ+1]>ra1[ZZ] && ra1[ZZ+2]>ra1[ZZ] && ra1[ZZ+3]>ra1[ZZ])
        {zihao1[ZZ]=12; zise1[ZZ]=clrOrange;}
      if(ra1[ZZ+1]>ra1[ZZ] && ra1[ZZ+2]>ra1[ZZ+1] && ra1[ZZ+3]>ra1[ZZ+2])
        {zihao1[ZZ]=14; zise1[ZZ]=clrRed;}

      zihao2[ZZ]=10; zise2[ZZ]=clrWhite;
      if(rates_dpvr[ZZ+1][13]>rates_dpvr[ZZ][13] && rates_dpvr[ZZ+2][13]>rates_dpvr[ZZ][13] && rates_dpvr[ZZ+3][13]>rates_dpvr[ZZ][13])
        {zihao2[ZZ]=11; zise2[ZZ]=clrOrange;}
      if(rates_dpvr[ZZ+1][13]>rates_dpvr[ZZ][13] && rates_dpvr[ZZ+2][13]>rates_dpvr[ZZ+1][13] && rates_dpvr[ZZ+3][13]>rates_dpvr[ZZ+2][13])
        {zihao2[ZZ]=12; zise2[ZZ]=clrRed;}

      zihao3[ZZ]=10; zise3[ZZ]=clrWhite;
      if(rates_dpvr[ZZ+1][23]>rates_dpvr[ZZ][23] && rates_dpvr[ZZ+2][23]>rates_dpvr[ZZ][23] && rates_dpvr[ZZ+3][23]>rates_dpvr[ZZ][23])
        {zihao3[ZZ]=11; zise3[ZZ]=clrOrange;}
      if(rates_dpvr[ZZ+1][23]>rates_dpvr[ZZ][23] && rates_dpvr[ZZ+2][23]>rates_dpvr[ZZ+1][23] && rates_dpvr[ZZ+3][23]>rates_dpvr[ZZ+2][23])
        {zihao3[ZZ]=12; zise3[ZZ]=clrRed;}

      zihao4[ZZ]=10; zise4[ZZ]=clrWhite;
      if(rates_dpvr[ZZ+1][33]>rates_dpvr[ZZ][33] && rates_dpvr[ZZ+2][33]>rates_dpvr[ZZ][33] && rates_dpvr[ZZ+3][33]>rates_dpvr[ZZ][33])
        {zihao4[ZZ]=11; zise4[ZZ]=clrOrange;}
      if(rates_dpvr[ZZ+1][33]>rates_dpvr[ZZ][33] && rates_dpvr[ZZ+2][33]>rates_dpvr[ZZ+1][33] && rates_dpvr[ZZ+3][33]>rates_dpvr[ZZ+2][33])
        {zihao4[ZZ]=12; zise4[ZZ]=clrRed;}
     }

//---- 收缩报警
   int geshu4=geshu1+geshu2+geshu3;
   if(geshu1<=alert_1s || geshu2<=alert_3s || geshu3<=alert_6s || geshu4<=alert_hs)
     {
      if(!报警已经处理)
        {
         if(jiaocha!=time[0])
           {
            if(pmAlert)
               Alert("枢轴指标 在"+_Symbol+" 发出收缩信号","     价格在 "+DoubleToString(SymbolInfoDouble(_Symbol,SYMBOL_BID),_Digits));
            if(EmailAlert)
               SendMail("枢轴指标 在"+_Symbol+" 发出收缩信号","在 "+DoubleToString(SymbolInfoDouble(_Symbol,SYMBOL_BID),_Digits));
            jiaocha=time[0];
           }
        }
     }

//---- 计算日波幅
   double day_high[],day_low[];
   ArraySetAsSeries(day_high,true);
   ArraySetAsSeries(day_low,true);
   CopyHigh(_Symbol,PERIOD_D1,0,21,day_high);
   CopyLow(_Symbol,PERIOD_D1,0,21,day_low);

   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   if(day_high[0]>0 && day_low[0]>0)
      R1=(int)((day_high[1]-day_low[1])/_Point);

   for(int i=1; i<=5; i++)
      R5+=(int)((day_high[i]-day_low[i])/_Point);
   for(int i=1; i<=10; i++)
      R10+=(int)((day_high[i]-day_low[i])/_Point);
   for(int i=1; i<=20; i++)
      R20+=(int)((day_high[i]-day_low[i])/_Point);

   R5=R5/5;
   R10=R10/10;
   R20=R20/20;
   RAvg=(R1+R5+R10+R20)/4;

   int RoomUp=0,RoomDown=0,StopLoss_Long=0,StopLoss_Short=0;
   double SL_Long=0,SL_Short=0;

   if(day_low[0]>0 && day_high[0]>0)
     {
      RoomUp=RAvg-(int)((bid-day_low[0])/_Point);
      RoomDown=RAvg-(int)((day_high[0]-bid)/_Point);
     }

   if(Risk_to_Reward_ratio>0)
     {
      StopLoss_Long=(int)(RoomUp/Risk_to_Reward_ratio);
      SL_Long=bid-StopLoss_Long*_Point;
      StopLoss_Short=(int)(RoomDown/Risk_to_Reward_ratio);
      SL_Short=bid+StopLoss_Short*_Point;
     }

//---- 绘制文本标签面板
   DrawTextPanel(RAvg,R1,R5,R10,R20,RoomUp,RoomDown,StopLoss_Long,StopLoss_Short,SL_Long,SL_Short);

   return(rates_total);
  }
//+------------------------------------------------------------------+
//| 绘制文本标签面板                                                  |
//+------------------------------------------------------------------+
void DrawTextPanel(int RAvg,int R1,int R5,int R10,int R20,
                   int RoomUp,int RoomDown,int StopLoss_Long,int StopLoss_Short,
                   double SL_Long,double SL_Short)
  {
   int win_idx=ChartWindowFind(0,short_name);

   string P=EnumToString(_Period);
   string sym=StringSubstr(_Symbol,0,10);

//---- 第一行：品种+周期+平均波幅
   CreateLabel("TSR0",sym,前三行显示字体大小,"Arial Bold",clrCadetBlue,win_idx,25,2);
   CreateLabel("TSR1",P,前三行显示字体大小,"Arial Bold",clrCadetBlue,win_idx,110,2);
   CreateLabel("TSR2","平均波动幅度:",前三行显示字体大小,"Arial Bold",clrCadetBlue,win_idx,155,2);
   CreateLabel("TSR3",IntegerToString(RAvg),前三行显示字体大小,"Arial Bold",clrOrange,win_idx,260,2);

//---- 前01天
   CreateLabel("TSR4","前 01 天幅度:",前三行显示字体大小,"Arial",clrLightSteelBlue,win_idx,25,20);
   CreateLabel("TSR5",IntegerToString(R1),前三行显示字体大小,"Arial Bold",clrOrange,win_idx,135,20);
//---- 前05天
   CreateLabel("TSR6","前 05 天幅度:",前三行显示字体大小,"Arial",clrLightSteelBlue,win_idx,25,35);
   CreateLabel("TSR7",IntegerToString(R5),前三行显示字体大小,"Arial Bold",clrOrange,win_idx,135,35);
//---- 前10天
   CreateLabel("TSR8","前 10 天幅度:",前三行显示字体大小,"Arial",clrLightSteelBlue,win_idx,175,20);
   CreateLabel("TSR9",IntegerToString(R10),前三行显示字体大小,"Arial Bold",clrOrange,win_idx,265,20);
//---- 前20天
   CreateLabel("TSR10","前 20 天幅度:",10,"Arial",clrLightSteelBlue,win_idx,175,35);
   CreateLabel("TSR11",IntegerToString(R20),前三行显示字体大小,"Arial Bold",clrOrange,win_idx,265,35);
//---- 向上空间
   CreateLabel("TSR12","向上空间:",10,"Arial",clrLightSteelBlue,win_idx,330,20);
   CreateLabel("TSR13",IntegerToString(RoomUp),前三行显示字体大小,"Arial Bold",clrOrange,win_idx,400,20);
//---- 向下空间
   CreateLabel("TSR14","向下空间:",10,"Arial",clrLightSteelBlue,win_idx,330,35);
   CreateLabel("TSR15",IntegerToString(RoomDown),前三行显示字体大小,"Arial Bold",clrOrange,win_idx,400,35);
//---- 止损位
   CreateLabel("TSR16","多头止损: "+IntegerToString(StopLoss_Long)+"  @"+DoubleToString(SL_Long,_Digits),10,"Arial",clrLightSteelBlue,win_idx,25,55);
   CreateLabel("TSR17","空头止损: "+IntegerToString(StopLoss_Short)+"  @"+DoubleToString(SL_Short,_Digits),10,"Arial",clrLightSteelBlue,win_idx,175,55);

   ChartRedraw(0);
  }
//+------------------------------------------------------------------+
//| 创建文本标签                                                      |
//+------------------------------------------------------------------+
void CreateLabel(string name,string text,int font_size,string font,color clr,int win_idx,int x,int y)
  {
   if(ObjectFind(0,name)<0)
      ObjectCreate(0,name,OBJ_LABEL,win_idx,0,0);
   ObjectSetString(0,name,OBJPROP_TEXT,text);
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,font_size);
   ObjectSetString(0,name,OBJPROP_FONT,font);
   ObjectSetInteger(0,name,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,name,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,name,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,name,OBJPROP_YDISTANCE,y);
  }
//+------------------------------------------------------------------+
//| 清理标签对象                                                      |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   string names[]={"TSR0","TSR1","TSR2","TSR3","TSR4","TSR5","TSR6","TSR7",
                   "TSR8","TSR9","TSR10","TSR11","TSR12","TSR13","TSR14",
                   "TSR15","TSR16","TSR17"};
   for(int i=0; i<ArraySize(names); i++)
      ObjectDelete(0,names[i]);
  }
//+------------------------------------------------------------------+
