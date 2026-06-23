//+------------------------------------------------------------------+
//|                                   SQ_IndicatorValuesExportEA.mq4 |
//|                                                                  |
//|                    EA to export indicator values from MetaTrader |
//|                Output to: /{Data folder}/tester/files/******.csv |
//+------------------------------------------------------------------+

#property copyright "Copyright © 2018 StrategyQuant"
#property link      "http://www.StrategyQuant.com"
//#include <行无行090.mqh>
extern int 几根K线看=1;
#define N_minutes 1
#define M_hours 1
//extern  bool 使用外部输入单品 =true;//不使用组品，使用外部输入单品

enum 客观周期
  {
   客观周期MN1=43200,
   客观周期W1=10080,
   客观周期D1=1440,
   客观周期H4=240,
   客观周期H1=60,
   客观周期M30=30,
   客观周期M15=15,
   客观周期M5=5,
   客观周期M1=1,
   使用当前周期=0,
  };

enum 应用周期
  {
   应用到月线周线日线=0,
   应用到月线周线=1,
   应用到日线H4线=2,
   应用到H1线M30线=3,
   应用到月线周线日线H4线H1线M30线=4,
  };
应用周期 应用周期的选择=0;
enum 应用品种组
  {
   应用到d品=-1,
   应用到0=0,
   应用到1=1,
   应用到2=2,
   应用到3=3,
   应用到4=4,
   应用到5=5,
   应用到6=6,
  };

enum 应用指标
  {
   应用到SR_BK=0,
   应用到RSI_ADX=1,
   应用到ACD_ATR=2,
  };
应用指标 应用指标的选择=0;
enum 应用四气
  {
   应用到春夏生长=1,
   应用到秋收=2,
   应用到冬藏=0,
  };
应用四气 应用四气的选择=0;
enum 应用时间方法
  {
   应用到输入始终时间值=1,
   应用到输入结束时间值=2,
   应用到输入开始时间值=3,
   应用到输入结束K线值=0,
  };
enum 应用此产品
  {
   应用到AUDUSD值=1,
   应用到GBPUSD值=2,
   应用到NZDUSD值=3,
   应用到USDCAD值=4,
   应用到USDJPY值=5,
   应用到EURUSD值=6,
   应用到EURJPY值=7,
   应用到GBPJPY值=8,
   XXX=333,
   应用到XAUUSD值=9,
   应用到XAGUSD值=10,
   应用到WT值=11,
   ZZZ=555,
   应用到HSI值=12,
   应用到XU值=13,
   应用到FDAX值=14,
   应用到NQ值=15,
   应用到YM值=16,
   应用到ES值=17,
   应用到NKD值=18,
   应用到FCE值=30,
   应用到Russia50值=31,
   yyy=888,
   应用到HG值=19,
   应用到PA值=20,
   应用到PL值=21,
   应用到HO值=22,
   应用到NG值=23,
   eee=999,
   应用到SOYBEAN值=24,
   应用到CORN值=25,
   应用到COCOA值=26,
   应用到SUGAR值=27,
   应用到WHEAT值=28,
   应用到COFFEE值=29,

   应用到本图表=133,
   应用到外部手动输入品种=136,



  };
enum 应用测试K数
  {
   应用测试K数1=1,//应用测试K数1
   应用测试K数3=3,//应用测试K数3
   应用测试K数6=6,
   应用测试K数12=12,
   应用测试K数36=36,
   应用测试K数60=60,
   应用测试K数80=80,
   应用测试K数130=130,
   应用测试K数210=210,
   应用测试K数340=340,
   应用测试K数500=500,
   应用测试K数800=800,
   应用测试K数1198=1198,
   应用测试K数2100=2100,
   应用测试K数3400=3400,
   应用测试K数4500=4500,
   应用测试K数5500=5500,
  };
extern  bool 单独测试true多品种同测false =true;
extern 客观周期  period_客观角度=客观周期D1;
extern int  period_时分点=1;
extern 应用品种组 应用品种组的选择=5;
extern 应用此产品 单独测试产品=应用到本图表;//
应用时间方法  使用应用时间方法=0;
extern 应用测试K数 测试K数=应用测试K数1198;
datetime  开始时刻=D'2021.03.03 12:00';
datetime  结束时刻=D'2021.04.16 16:00';

int 回溯K数=0;
//int 测试K数=3;
bool 闭藏邮件报警=false;
bool 邮件报警=false;
bool 突破邮件报警=false;
bool 突破声音报警=false;
bool 加油邮件报警=false;
bool 可以加载=true;
double gaodi_bfb=0.1;
int  period_ok=PERIOD_H1;

extern string synbol_ok="WTI";

string  symbols_zs="KVBL";
string currentTime = "";
string lastTime = "";
double Point_Value;
double A_Point;
double C_Point;
double UnitMINSizing;
double Symblo_SPREAD;

datetime jiaocha_D1_kbw=0;
datetime jiaocha_H4_kbw=0;
datetime jiaocha_W1_kbw=0;
string   symbols[14] =
  {
   "#BABA","#GOOG","#AMZN","#BA","#AMD","#APPL","#MMM","#CLX","#KO","#DIS","#EBAY","#META","#GS","#FDX"
  };

string symbols_1[] =
  {
    "#INTEL","#JPM","#MAR","#MA","#MCD","#MRK","#NFLX","#NKE","#PEP","#QCOM","#SBUX","#TSLA","#VZ","#ZM" };
string   symbols_2[] =
  {
  "#IBM","#MSFT","#XOM","#LMT","#AVGO","#NVDA","#CAT","#JNJ","#PFE","#ADS","#AIR","#ALV","#BAYN","#BMW"
   };
string   symbols_3[] =
  {
 "#MBG","#MOH","#VOW3","#LOR" 
  };
string   symbols_4[] =
  {
   "PTR","PVH","ENI","RL","RNO","RACE","SBUX","SAVE","RCL","RYAAY","ORCL","SQM","SPY","SNAP","Sberbank","SVMK","SIE","SAP","REP","SK","Spotify"
  };
string   symbols_5[] =
  {
   "HSI","SPX500","NAS100","DAX","NIKKEI","CHINA300","USDJPY","GBPUSD","DOW","XAUUSD.v","XAGUSD.v","ChinaA50","USOIL.v","FTSE100"
 , "#BABA","#GOOG","#AMZN","#BA","#AMD","#AAPL","#MMM","#CLX","#KO","#DIS","#EBAY","#META","#GS","#FDX"
 , "#INTEL","#JPM","#MAR","#MA","#MCD","#MRK","#NFLX","#NKE","#PEP","#QCOM","#SBUX","#TSLA","#VZ","#ZM"
 , "#IBM","#MSFT","#XOM","#LMT","#AVGO","#NVDA","#CAT","#JNJ","#PFE","#ADS","#AIR","#ALV","#BAYN","#BMW"
  ,"#VOW3","#MOH","#LOR","#MBG","#SBUX","BTCUSD"
  
  
  };
string   symbols_6[] =
  {
   "HG","PA","PL","HO","NG","SOYBEAN","CORN","COFFEE","COCOA","SUGAR","WHEAT","CL","BRN","BTCUSD","BRN"
  };
string   symbols_8[] =
  {
// ,30个产品（FX玫红色）比特币
   "#USSPX500","BTCUSD","ETHUSD","LTCUSD","BCHUSD","XRPUSD","BATUSD","BTGUSD","DOGUSD","DOTUSD","DSHUSD","EOSUSD","ETCUSD","IOTUSD","LNKUSD","NEOUSD","NEOUSD"
   "XLMUSD","XMRUSD","ZECUSD","AAVEUSD","FILUSD","LUNAUSD","SOLUSD","UNIUSD","ADAUSD","MATICUSD","SUSHIUSD","THETAUSD","XTZUSD","TRXUSD","VETUSD"
  };
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
int      symbols_count(int jizu)
  {
   int countes=0;
   if(jizu==-1)
     {
      countes=1;
      return(countes);
     }
   if(jizu==0)
     {
      countes=ArraySize(symbols);
      return(countes);
     }
   if(jizu==1)
     {
      countes=ArraySize(symbols_1);
      return(countes);
     }

   if(jizu==2)
     {
      countes=ArraySize(symbols_2);
      return(countes);
     }
   if(jizu==3)
     {
      countes=ArraySize(symbols_3);
      return(countes);
     }
   if(jizu==4)
     {
      countes=ArraySize(symbols_4);
      return(countes);
     }
   if(jizu==5)
     {
      countes=ArraySize(symbols_5);
      return(countes);
     }
   if(jizu==6)
     {
      countes=ArraySize(symbols_6);
      return(countes);
     }
   return(countes);
  }
//+------------------------------------------------------------------+
//| string SymbolByNumber                                   |
//+------------------------------------------------------------------+
string GetSymbolString(int jizu,int Number)
  {
//----
   string res="";

   if(jizu==-1)
     {

      if(单独测试true多品种同测false==true)
        {

         res=String单品(单独测试产品);
         return(res);
        }

      //  return(res);
     }
   if(jizu==0)
     {
      res=symbols[Number];
      return(res);
     }
   if(jizu==1)
     {
      res=symbols_1[Number];
      return(res);
     }
//----
   if(jizu==2)
     {
      res=symbols_2[Number];
      return(res);
     }
   if(jizu==3)
     {
      res=symbols_3[Number];
      return(res);
     }
   if(jizu==4)
     {
      res=symbols_4[Number];
      return(res);
     }
   if(jizu==5)
     {
      res=symbols_5[Number];
      return(res);
     }
   if(jizu==6)
     {
      res=symbols_6[Number];
      return(res);
     }
   return(res);
  }
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
void OnInit()
  {
   EventSetTimer(1*N_minutes);//参数是秒，还有毫秒的函数bool  EventSetMillisecondTimer(int  milliseconds      // number of milliseconds  );
  }


//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void  OnTimer()
  {
    if(
      (TimeMinute(TimeLocal())!=period_时分点)&&
     ( (TimeHour(TimeLocal())!=8)||(TimeHour(TimeLocal())!=13)||(TimeHour(TimeLocal())!=20))
   )
     {
      return;
     }
   else
      if(
         (TimeMinute(TimeLocal())==period_时分点)
         &&
         ( (TimeHour(TimeLocal())==8)||(TimeHour(TimeLocal())==13)||(TimeHour(TimeLocal())==20))
      )
        {
           {
            if(AccountInfoInteger(ACCOUNT_TRADE_ALLOWED)!=true)
              {
               lastTime = currentTime;
               return;
              }
            else
               if(AccountInfoInteger(ACCOUNT_TRADE_ALLOWED)==true)
                 {

                  string fileName ="-";

                  if(单独测试true多品种同测false==true)
                    {



                     symbols_zs=String单品(单独测试产品);



                    }
                  测试K数=测试K数;
                  period_客观角度=周期规范含当前周期(period_客观角度);
                  if(使用应用时间方法==0)
                    {
                     fileName =symbols_zs+"_@_"+StringTF(period_客观角度)+"_#"+测试K数+"_"+TimeToStr(TimeLocal(), TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点"+IntegerToString(TimeMinute(TimeLocal()))+".csv";
                    }
                  else
                     if(使用应用时间方法==1)
                       {
                        fileName ="时间指标单品_方法"+ "_周期_"+StringTF(period_客观角度)+ "_开始_"+TimeToStr(开始时刻, TIME_DATE)+ "_结束_"+TimeToStr(结束时刻, TIME_DATE)+ "_产品：_"+"_"+symbols[0]+"_"+symbols[1]+"_"+symbols[2]+".csv";
                       }
                     else
                        if(使用应用时间方法==2)
                          {
                           fileName ="时间指标单品_方法"+使用应用时间方法+ "_周期_"+StringTF(period_客观角度)+ "_测试_"+测试K数+ "_结束_"+TimeToStr(结束时刻, TIME_DATE)+ "_产品：_"+"_"+symbols[0]+"_"+symbols[1]+"_"+symbols[2]+".csv";
                          }

                        else
                           if(使用应用时间方法==3)
                             {
                              fileName ="时间指标单品_方法"+使用应用时间方法+ "_周期_"+StringTF(period_客观角度)+ "_测试_"+测试K数+ "_开始_"+TimeToStr(开始时刻, TIME_DATE)+ "_产品：_"+"_"+symbols[0]+"_"+symbols[1]+"_"+symbols[2]+".csv";
                             }
                           else
                             {
                              fileName ="时间指标单品_方法"+使用应用时间方法+ "_周期_"+StringTF(period_客观角度)+ "_错误选择了时间输入模式_"+"_"+symbols[0]+"_"+symbols[1]+"_"+symbols[2]+".csv";
                             }
                  int TF4=多周期切换(period_客观角度,4);
                  int TF3=多周期切换(period_客观角度,3);
                  int TF2=多周期切换(period_客观角度,2);
                  int TF1=多周期切换(period_客观角度,1);
                  int TF0=多周期切换(period_客观角度,0);
                  int TF_1=多周期切换(period_客观角度,-1);
                  int TF_2=多周期切换(period_客观角度,-2);
                  int TF_3=多周期切换(period_客观角度,-3);
                  int TF_4=多周期切换(period_客观角度,-4);
                  int handle = FileOpen(fileName,FILE_READ|FILE_WRITE|FILE_CSV,',');// FILE_READ | FILE_WRITE|FILE_CSV,',');
                  if(handle>0)
                    {
                     string Symbol_0;


               /*      if(period_客观角度==1)
                       {
                        FileWrite(handle,"SymbolName,天时计算,H1M30M15M5M1,测试K数,收缩_H1,趋势_H1,突破SR_H1,反转_H1,关位_H1  ,幅动_H1,Time_H1,Price_H1,收缩_M30,趋势_M30,突破SR_M30,反转_M30,关位_M30 ,幅动_M30,Time_M30,Price_M30,收缩_M15,趋势_M15,突破SR_M15,反转_M15,关位_M15 ,幅动_M15,Time_M15,Price_M15 ,收缩_M5,趋势_M5,突破SR_M5,反转_M5,关位_M5 ,幅动_M5,Time_M5,Price_M5 ,收缩_M1,趋势_M1,突破SR_M1,反转_M1,关位_M1   ,幅动_M5M1,Time_M1,Price_M1");//
                       }
                     else
                        if(period_客观角度==5)
                          {
                           FileWrite(handle,"SymbolName,天时计算,H4H1M30M15M5,测试K数,收缩_H4,趋势_H4,突破SR_H4,反转_H4,关位_H4  ,幅动_H4,Time_H4,Price_H4 ,收缩_H1,趋势_H1,突破SR_H1,反转_H1,关位_H1  ,幅动_H1,Time_H1,Price_H1,收缩_M30,趋势_M30,突破SR_M30,反转_M30,关位_M30 ,幅动_M30,Time_M30,Price_M30,收缩_M15,趋势_M15,突破SR_M15,反转_M15,关位_M15 ,幅动_M15,Time_M15,Price_M15 ,收缩_M5,趋势_M5,突破SR_M5,反转_M5,关位_M5 ,幅动_M5,Time_M5,Price_M5 ");//
                          }
                        else
                           if(period_客观角度==15)
                             {
                              FileWrite(handle,"SymbolName,TIME,Period,PRICE,MN1,W1,D1,H4,H1,M30,M15,M5,M1");
                             }
                           else
                              if(period_客观角度==30)
                                {
                                 FileWrite(handle,"SymbolName,天时计算,W1D1H4H1M30,测试K数,收缩_W1,趋势_W1,突破SR,反转_W1,关位_W1   ,幅动_W1,Time_W1,Price_W1,收缩_D1,趋势_D1,突破SR_D1,反转_D1,关位_D1  ,幅动_D1,Time_D1,Price_D1,收缩_H4,趋势_H4,突破SR_H4,反转_H4,关位_H4  ,幅动_H4,Time_H4,Price_H4 ,收缩_H1,趋势_H1,突破SR_H1,反转_H1,关位_H1  ,幅动_H1,Time_H1,Price_H1,收缩_M30,趋势_M30,突破SR_M30,反转_M30,关位_M30 ,幅动_M30,Time_M30,Price_M30  ");//

                                }
                              else
                                 if(period_客观角度==60)
                                   {
                           FileWrite(handle,"SymbolName,TIME,Period,PRICE,MN1,W1,D1,H4,H1,M30,M15,M5,M1");                     }
                                 else
                                    if(period_客观角度==240)
                                      {

                                       FileWrite(handle,"SymbolName,天时计算,MN1W1D1H4,测试K数,收缩_MN1,趋势_MN1,突破SR,反转_MN1,关位_MN1 ,幅动_MN1, Time_MN1,Price_MN1,收缩_W1,趋势_W1,突破SR,反转_W1,关位_W1   ,幅动_W1,Time_W1,Price_W1,收缩_D1,趋势_D1,突破SR_D1,反转_D1,关位_D1  ,幅动_D1,Time_D1,Price_D1,收缩_H4,趋势_H4,突破SR_H4,反转_H4,关位_H4  ,幅动_H4,Time_H4,Price_H4  ");//

                                      }
                                    else*/
                                       if(period_客观角度==1440)
                                         {

                                         FileWrite(handle,"SymbolName,TIME,weekday,Period,openPRICE,highPRICE,lowPRICE,closePRICE,MN1,W1,D1");                }
                                       else
                                          if((period_客观角度==10080)||(period_客观角度==43200))
                                            {

                                             FileWrite(handle,"SymbolName,天时计算,MN1_W1_D1,测试K数,收缩_MN1,趋势_MN1,突破SR,反转_MN1,关位_MN1 ,幅动_MN1, Time_MN1,Price_MN1,收缩_W1,趋势_W1,突破SR,反转_W1,关位_W1   ,幅动_W1,Time_W1,Price_W1");//

                                            }
                     if(单独测试true多品种同测false==true)
                       {

                        应用品种组的选择=-1;

                       }
                     for(int SymbolCounter=0; SymbolCounter<symbols_count(应用品种组的选择); SymbolCounter++)
                       {
                        Symbol_0=GetSymbolString(应用品种组的选择,SymbolCounter);
                        int 开始shift=iBarShift(Symbol_0,period_客观角度,开始时刻);
                        int 结束shift=iBarShift(Symbol_0,period_客观角度,结束时刻);

                        if(使用应用时间方法==0)
                          {

                          }

                        else
                           if(使用应用时间方法==1)
                             {

                              测试K数= 开始shift-结束shift+1;
                              回溯K数= 结束shift;
                             }
                           else
                              if(使用应用时间方法==2)
                                {

                                 回溯K数= 结束shift;
                                }
                              else
                                 if(使用应用时间方法==3)
                                   {
                                    回溯K数= 开始shift-测试K数+1;
                                    if(回溯K数<0)
                                      {
                                       回溯K数=0;
                                       测试K数=开始shift;
                                      }
                                   }

                        //--------W1------



                        //-----------------------------

                        for(int g=0; g<测试K数; g++)
                          {
                           //--------------------------------

                           RefreshRates();





                           string                            BK_M15="-",BK_M5="-",BK_D1="-",BK_H4="-",BK_H1="-",BK_M30="-",BK_W1="-",BK_MN1="-",BK_M1="-"
                                 ,SR_M15="-",SR_M5="-",SR_D1="-",SR_H4="-",SR_H1="-",SR_M30="-",SR_W1="-",SR_MN1="-",SR_M1="-"
                                 ,ATR_M15="-",ATR_M5="-",ATR_D1="-",ATR_H4="-",ATR_H1="-",ATR_M30="-",ATR_W1="-",ATR_MN1="-",ATR_M1="-"
                                 ,ADX_M15="-",ADX_M5="-",ADX_D1="-",ADX_H4="-",ADX_H1="-",ADX_M30="-",ADX_W1="-",ADX_MN1="-",ADX_M1="-"
                                 ,RSI_M15="-",RSI_M5="-",RSI_D1="-",RSI_H4="-",RSI_H1="-",RSI_M30="-",RSI_W1="-",RSI_MN1="-",RSI_M1="-"
                                 ,ATRSTOP_M15="-",ATRSTOP_M5="-",ATRSTOP_D1="-",ATRSTOP_H4="-",ATRSTOP_H1="-",ATRSTOP_M30="-",ATRSTOP_W1="-",ATRSTOP_MN1="-",ATRSTOP_M1="-"
                                 ,LMT_M15="-",LMT_M5="-",LMT_D1="-",LMT_H4="-",LMT_H1="-",LMT_M30="-",LMT_W1="-",LMT_MN1="-",LMT_M1="-"
                                 ,TBD_M15="-",TBD_M5="-",TBD_D1="-",TBD_H4="-",TBD_H1="-",TBD_M30="-",TBD_W1="-",TBD_MN1="-",TBD_M1="-"
                                 ,BLP_M15="-",BLP_M5="-",BLP_D1="-",BLP_H4="-",BLP_H1="-",BLP_M30="-",BLP_W1="-",BLP_MN1="-",BLP_M1="-"



                                 ;
                           int  shift_OK_W1_D1_H4_H1_M30_M15_M5_M1=   回溯K数+g ;


                           RefreshRates();

                           string lg_MN1="无";
                           string lg_W1="无";
                           string qz_MN1="无";
                           string qz_W1="无";
                           string tp_MN1="无";
                           string tp_W1="无";
                           string bd_MN1="无";
                           string bd_W1="无";
                           string fz_MN1="无";
                           string fz_W1="无";
                           string gw_MN1="无";
                           string gw_W1="无";

                           int  shift_MN1=iBarShift(Symbol_0,PERIOD_MN1, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int  shift_W1=iBarShift(Symbol_0,PERIOD_W1, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int  shift_D1=iBarShift(Symbol_0,PERIOD_D1, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int  shift_H4=iBarShift(Symbol_0,PERIOD_H4, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int  shift_H1=iBarShift(Symbol_0,PERIOD_H1, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int  shift_M30=iBarShift(Symbol_0,PERIOD_M30, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int  shift_M15=iBarShift(Symbol_0,PERIOD_M15, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int  shift_M5=iBarShift(Symbol_0,PERIOD_M5, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int  shift_M1=iBarShift(Symbol_0,PERIOD_M1, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));

                           string close_M1=DoubleToStr(iClose(Symbol_0,PERIOD_M1,shift_M1),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                           string close_M5=DoubleToStr(iClose(Symbol_0,PERIOD_M5,shift_M5),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                           string close_M15=DoubleToStr(iClose(Symbol_0,PERIOD_M15,shift_M15),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                           string close_M30=DoubleToStr(iClose(Symbol_0,PERIOD_M30,shift_M30),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                           string close_H1=DoubleToStr(iClose(Symbol_0,PERIOD_H1,shift_H1),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                           string close_H4=DoubleToStr(iClose(Symbol_0,PERIOD_H4,shift_H4),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                           string close_D1=DoubleToStr(iClose(Symbol_0,PERIOD_D1,shift_D1),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                           string close_W1=DoubleToStr(iClose(Symbol_0,PERIOD_W1,shift_W1),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                           string close_MN1=DoubleToStr(iClose(Symbol_0,PERIOD_MN1,shift_MN1),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                           
                                string open_D1=DoubleToStr(iOpen(Symbol_0,PERIOD_D1,shift_D1),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                                string high_D1=DoubleToStr(iHigh(Symbol_0,PERIOD_D1,shift_D1),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                                string low_D1=DoubleToStr(iLow(Symbol_0,PERIOD_D1,shift_D1),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                           if(g==0)
                             {
                              close_M5=DoubleToStr(iClose(Symbol_0,PERIOD_M1,2),(int)MarketInfo(Symbol_0,MODE_DIGITS));
                              close_M30=close_M5;
                              close_H4=close_M5;
                              close_M1=close_M5;
                              close_W1=close_M5;
                             }
                           SR_MN1=guanjianwei_hdnj(Symbol_0,PERIOD_MN1,shift_MN1);
                           SR_W1=guanjianwei_hdnj(Symbol_0,PERIOD_W1,shift_W1);
                           SR_D1=guanjianwei_hdnj(Symbol_0,PERIOD_D1,shift_D1);
                           SR_H4=guanjianwei_hdnj(Symbol_0,PERIOD_H4,shift_H4);
                           SR_H1=guanjianwei_hdnj(Symbol_0,PERIOD_H1,shift_H1);
                           SR_M30=guanjianwei_hdnj(Symbol_0,PERIOD_M30,shift_M30);
                           SR_M15=guanjianwei_hdnj(Symbol_0,PERIOD_M15,shift_M15);
                           SR_M5=guanjianwei_hdnj(Symbol_0,PERIOD_M5,shift_M5);
                           SR_M1=guanjianwei_hdnj(Symbol_0,PERIOD_M1,shift_M1);

                           ADX_MN1=qushixing_hdnj(Symbol_0,PERIOD_MN1,shift_MN1);
                           ADX_W1=qushixing_hdnj(Symbol_0,PERIOD_W1,shift_W1);
                           ADX_D1=qushixing_hdnj(Symbol_0,PERIOD_D1,shift_D1);
                           ADX_H4=qushixing_hdnj(Symbol_0,PERIOD_H4,shift_H4);
                           ADX_H1=qushixing_hdnj(Symbol_0,PERIOD_H1,shift_H1);
                           ADX_M30=qushixing_hdnj(Symbol_0,PERIOD_M30,shift_M30);
                           ADX_M15=qushixing_hdnj(Symbol_0,PERIOD_M15,shift_M15);
                           ADX_M5=qushixing_hdnj(Symbol_0,PERIOD_M5,shift_M5);
                           ADX_M1=qushixing_hdnj(Symbol_0,PERIOD_M1,shift_M1);

                           BK_MN1=bodongxing_hdnj(Symbol_0,PERIOD_MN1,shift_MN1);
                           BK_W1=bodongxing_hdnj(Symbol_0,PERIOD_W1,shift_W1);
                           BK_D1=bodongxing_hdnj(Symbol_0,PERIOD_D1,shift_D1);
                           BK_H4=bodongxing_hdnj(Symbol_0,PERIOD_H4,shift_H4);
                           BK_H1=bodongxing_hdnj(Symbol_0,PERIOD_H1,shift_H1);
                           BK_M30=bodongxing_hdnj(Symbol_0,PERIOD_M30,shift_M30);
                           BK_M15=bodongxing_hdnj(Symbol_0,PERIOD_M15,shift_M15);
                           BK_M5=bodongxing_hdnj(Symbol_0,PERIOD_M5,shift_M5);
                           BK_M1=bodongxing_hdnj(Symbol_0,PERIOD_M1,shift_M1);

                           RSI_MN1=rsi_hdnj(Symbol_0,PERIOD_MN1,shift_MN1);
                           RSI_W1=rsi_hdnj(Symbol_0,PERIOD_W1,shift_W1);
                           RSI_D1=rsi_hdnj(Symbol_0,PERIOD_D1,shift_D1);
                           RSI_H4=rsi_hdnj(Symbol_0,PERIOD_H4,shift_H4);
                           RSI_H1=rsi_hdnj(Symbol_0,PERIOD_H1,shift_H1);
                           RSI_M30=rsi_hdnj(Symbol_0,PERIOD_M30,shift_M30);
                           RSI_M15=rsi_hdnj(Symbol_0,PERIOD_M15,shift_M15);
                           RSI_M5=rsi_hdnj(Symbol_0,PERIOD_M5,shift_M5);
                           RSI_M1=rsi_hdnj(Symbol_0,PERIOD_M1,shift_M1);

                           ATRSTOP_MN1=atrstop_hdnj(Symbol_0,PERIOD_MN1,shift_MN1);
                           ATRSTOP_W1=atrstop_hdnj(Symbol_0,PERIOD_W1,shift_W1);
                           ATRSTOP_D1=atrstop_hdnj(Symbol_0,PERIOD_D1,shift_D1);
                           ATRSTOP_H4=atrstop_hdnj(Symbol_0,PERIOD_H4,shift_H4);
                           ATRSTOP_H1=atrstop_hdnj(Symbol_0,PERIOD_H1,shift_H1);
                           ATRSTOP_M30=atrstop_hdnj(Symbol_0,PERIOD_M30,shift_M30);
                           ATRSTOP_M15=atrstop_hdnj(Symbol_0,PERIOD_M15,shift_M15);
                           ATRSTOP_M5=atrstop_hdnj(Symbol_0,PERIOD_M5,shift_M5);
                           ATRSTOP_M1=atrstop_hdnj(Symbol_0,PERIOD_M1,shift_M1);

                           string TOP_MN1=top_hdnj(Symbol_0,PERIOD_MN1,shift_MN1);
                           string TOP_W1=top_hdnj(Symbol_0,PERIOD_W1,shift_W1);
                           string TOP_D1=top_hdnj(Symbol_0,PERIOD_D1,shift_D1);
                           string TOP_H4=top_hdnj(Symbol_0,PERIOD_H4,shift_H4);
                           string TOP_H1=top_hdnj(Symbol_0,PERIOD_H1,shift_H1);
                           string TOP_M30=top_hdnj(Symbol_0,PERIOD_M30,shift_M30);
                           string TOP_M15=top_hdnj(Symbol_0,PERIOD_M15,shift_M15);
                           string TOP_M5=top_hdnj(Symbol_0,PERIOD_M5,shift_M5);
                           string TOP_M1=top_hdnj(Symbol_0,PERIOD_M1,shift_M1);

                           LMT_MN1=lmt_hdnj(Symbol_0,PERIOD_MN1,shift_MN1);
                           LMT_W1=lmt_hdnj(Symbol_0,PERIOD_W1,shift_W1);
                           LMT_D1=lmt_hdnj(Symbol_0,PERIOD_D1,shift_D1);
                           LMT_H4=lmt_hdnj(Symbol_0,PERIOD_H4,shift_H4);
                           LMT_H1=lmt_hdnj(Symbol_0,PERIOD_H1,shift_H1);
                           LMT_M30=lmt_hdnj(Symbol_0,PERIOD_M30,shift_M30);
                           LMT_M15=lmt_hdnj(Symbol_0,PERIOD_M15,shift_M15);
                           LMT_M5=lmt_hdnj(Symbol_0,PERIOD_M5,shift_M5);
                           LMT_M1=lmt_hdnj(Symbol_0,PERIOD_M1,shift_M1);

                           TBD_MN1=tbd_hdnj(Symbol_0,PERIOD_MN1,shift_MN1);
                           TBD_W1=tbd_hdnj(Symbol_0,PERIOD_W1,shift_W1);
                           TBD_D1=tbd_hdnj(Symbol_0,PERIOD_D1,shift_D1);
                           TBD_H4=tbd_hdnj(Symbol_0,PERIOD_H4,shift_H4);
                           TBD_H1=tbd_hdnj(Symbol_0,PERIOD_H1,shift_H1);
                           TBD_M30=tbd_hdnj(Symbol_0,PERIOD_M30,shift_M30);
                           TBD_M15=tbd_hdnj(Symbol_0,PERIOD_M15,shift_M15);
                           TBD_M5=tbd_hdnj(Symbol_0,PERIOD_M5,shift_M5);
                           TBD_M1=tbd_hdnj(Symbol_0,PERIOD_M1,shift_M1);


                           BLP_MN1=blp_hdnj(Symbol_0,PERIOD_MN1,shift_MN1);
                           BLP_W1=blp_hdnj(Symbol_0,PERIOD_W1,shift_W1);
                           BLP_D1=blp_hdnj(Symbol_0,PERIOD_D1,shift_D1);
                           BLP_H4=blp_hdnj(Symbol_0,PERIOD_H4,shift_H4);
                           BLP_H1=blp_hdnj(Symbol_0,PERIOD_H1,shift_H1);
                           BLP_M30=blp_hdnj(Symbol_0,PERIOD_M30,shift_M30);
                           BLP_M15=blp_hdnj(Symbol_0,PERIOD_M15,shift_M15);
                           BLP_M5=blp_hdnj(Symbol_0,PERIOD_M5,shift_M5);
                           BLP_M1=blp_hdnj(Symbol_0,PERIOD_M1,shift_M1);

                           if((period_客观角度!=1))
                             {
                              //--------------lg---MN1`------------

                              if(
                                 (BK_MN1=="闭藏")||(ADX_MN1=="闭藏")
                              )
                                {
                                 lg_MN1="MN1";
                                }
                              //--------------------------qz-----MN1----
                              //  if(
                              //      ((BK_MN1=="发陈")||(BK_MN1=="蕃秀")||(ADX_MN1=="空发")||(ADX_MN1=="空藏")||(ADX_MN1=="空趋")||(ADX_MN1=="多发")||(ADX_MN1=="多藏")||(ADX_MN1=="多趋"))

                              //   )
                              //     {
                              //      qz_MN1="MN长";
                              //     }
                              if(
                                 ((ADX_MN1=="空发")||(ADX_MN1=="空藏")||(ADX_MN1=="空趋"))

                              )
                                {
                                 qz_MN1="MN空";
                                }
                              if(
                                 ((ADX_MN1=="多发")||(ADX_MN1=="多藏")||(ADX_MN1=="多趋"))

                              )
                                {
                                 qz_MN1="MN多";


                                }
                              //---------------------------tp------MN1-----------
                              if(

                                 ((SR_MN1=="天")||(SR_MN1=="上")||(SR_MN1=="天外天")||(BLP_MN1=="天天"))
                              )
                                {
                                 tp_MN1="MN天";
                                }
                              if(
                                 ((SR_MN1=="地")||(SR_MN1=="下")||(SR_MN1=="地外地")||(BLP_MN1=="地地"))
                              )
                                {
                                 tp_MN1="MN地";
                                }
                              //---------------------bd--------MN1---------------
                              if(
                                 (TBD_MN1=="发陈")||(TBD_MN1=="藏发")||(TBD_MN1=="蕃秀")
                              )
                                {
                                 bd_MN1="MN1";
                                }
                              //------------FZ----MN1-----------------
                              if(
                                 (TOP_MN1=="多上")
                              )
                                {
                                 fz_MN1="MNT上";
                                }

                              if(
                                 (ATRSTOP_MN1=="多上")
                              )
                                {
                                 fz_MN1="MNA上";
                                }

                              if(
                                 (RSI_MN1=="低上")
                              )
                                {
                                 fz_MN1="MNR上";
                                }
                              if(
                                 (LMT_MN1=="上")
                              )
                                {
                                 fz_MN1="MNL上";
                                }
                              if(
                                 (TOP_MN1=="空下")
                              )
                                {
                                 fz_MN1="MNT下";
                                }

                              if(
                                 (ATRSTOP_MN1=="空下")
                              )
                                {
                                 fz_MN1="MNT下";
                                }

                              if(
                                 (RSI_MN1=="高下")
                              )
                                {
                                 fz_MN1="MNR下";
                                }
                              if(
                                 (LMT_MN1=="下")
                              )
                                {
                                 fz_MN1="MNL下";
                                }


                              //----------------GW--MN1-
                              if(

                                 ((SR_MN1=="高")||(SR_MN1=="上")||(BLP_MN1=="高高")||(LMT_MN1=="高"))

                              )
                                {
                                 gw_MN1="MN高";
                                }
                              if(
                                 ((SR_MN1=="低")||(SR_MN1=="下")||(BLP_MN1=="低低")||(LMT_MN1=="低"))
                              )
                                {
                                 gw_MN1="MN低";
                                }
                             }
                           if((period_客观角度!=5)&&(period_客观角度!=1))
                              //--------------lg---W1`------------
                             {
                              if(
                                 (BK_W1=="闭藏")||(ADX_W1=="闭藏")
                              )
                                {

                                 lg_W1="W1";

                                }
                              //--------------------------qz-----W1----

                              //    if(
                              //       ((BK_W1=="发陈")||(BK_W1=="蕃秀"))
                              //    )
                              //      {

                              //  qz_W1="W长";
                              //

                              //  }
                              if(
                                 ((ADX_W1=="多发")||(ADX_W1=="多藏")||(ADX_W1=="多趋"))
                              )
                                {
                                 if(qz_W1=="无")
                                   {
                                    qz_W1="W多";
                                   }
                                 else
                                    if(qz_W1!="无")
                                      {qz_W1=qz_W1+"W多";}
                                }

                              if(
                                 ((ADX_W1=="空发")||(ADX_W1=="空藏")||(ADX_W1=="空趋"))
                              )
                                {
                                 if(qz_W1=="无")
                                   {
                                    qz_W1="W空";
                                   }
                                 else
                                    if(qz_W1!="无")
                                      {qz_W1=qz_W1+"W空";}
                                }
                              //---------------------------tp------W1-----------

                              if(
                                 ((SR_W1=="天")||(SR_W1=="上")||(SR_W1=="天外天")||(BLP_W1=="天天"))
                              )
                                {
                                 if(tp_W1=="无")
                                   {
                                    tp_W1="W天";
                                   }
                                 else
                                   {tp_W1=tp_W1+"W天";}
                                }
                              if(
                                 ((SR_W1=="地")||(SR_W1=="下")||(SR_W1=="地外地")||(BLP_W1=="地地"))
                              )
                                {
                                 if(tp_W1=="无")
                                   {
                                    tp_W1="W地";
                                   }
                                 else
                                   {tp_W1=tp_W1+"W地";}
                                }
                             }
                           //---------------------bd-----W1------------------

                           if(
                              (TBD_W1=="发陈")||(TBD_W1=="藏发")||(TBD_W1=="蕃秀")
                           )
                             {
                              if(bd_W1=="无")
                                {
                                 bd_W1="W1";
                                }
                              else
                                {bd_W1=bd_W1+"W1";}
                             }

                           //------------FZ--------W1-------------

                           if(
                              (TOP_W1=="多上")
                           )
                             {

                              if(fz_W1=="无")
                                {
                                 fz_W1="WT上";
                                }
                              else
                                {fz_W1=fz_W1+"WT上";}
                             }

                           if(
                              (ATRSTOP_W1=="多上")
                           )
                             {

                              if(fz_W1=="无")
                                {
                                 fz_W1="WA上";
                                }
                              else
                                {fz_W1=fz_W1+"WA上";}
                             }


                           if(
                              (RSI_W1=="低上")
                           )
                             {

                              if(fz_W1=="无")
                                {
                                 fz_W1="WR上";
                                }
                              else
                                {fz_W1=fz_W1+"WR上";}
                             }

                           if(
                              (LMT_W1=="上")
                           )
                             {

                              if(fz_W1=="无")
                                {
                                 fz_W1="WL上";
                                }
                              else
                                {fz_W1=fz_W1+"WL上";}
                             }

                           if(
                              (TOP_W1=="空下")
                           )
                             {
                              if(fz_W1=="无")
                                {
                                 fz_W1="WT下";
                                }
                              else
                                {fz_W1=fz_W1+"WT下";};
                             }

                           if(
                              (ATRSTOP_W1=="空下")
                           )
                             {
                              if(fz_W1=="无")
                                {
                                 fz_W1="WA下";
                                }
                              else
                                {fz_W1=fz_W1+"WA下";};
                             }


                           if(
                              (RSI_W1=="高下")
                           )
                             {
                              if(fz_W1=="无")
                                {
                                 fz_W1="WR下";
                                }
                              else
                                {fz_W1=fz_W1+"WR下";};
                             }
                           if(
                              (LMT_W1=="下")
                           )
                             {
                              if(fz_W1=="无")
                                {
                                 fz_W1="WL下";
                                }
                              else
                                {fz_W1=fz_W1+"WL下";};
                             }

                           //----------------GW-W1--

                           if(

                              ((SR_W1=="高")||(SR_W1=="上")||(BLP_W1=="高高")||(LMT_W1=="高"))

                           )
                             {
                              if(gw_W1=="无")
                                {
                                 gw_W1="W高";
                                }
                              else

                                {gw_W1=gw_W1+"W高";}
                             }
                           if(
                              ((SR_W1=="低")||(SR_W1=="下")||(BLP_W1=="低低")||(LMT_W1=="低"))
                           )
                             {
                              if(gw_W1=="无")
                                {
                                 gw_W1="W低";
                                }
                              else

                                {gw_W1=gw_W1+"W低";}
                             }


                           //--------------------------------



                           //第一组
                           string lg_D1="无";
                           string qz_D1="无";
                           string tp_D1="无";
                           string bd_D1="无";
                           string fz_D1="无";
                           string gw_D1="无";
                           //第一组
                           string lg_H4="无";
                           string qz_H4="无";
                           string tp_H4="无";
                           string bd_H4="无";
                           string fz_H4="无";
                           string gw_H4="无";


                           if((period_客观角度!=43200)&&(period_客观角度!=5)&&(period_客观角度!=1))
                             {
                              //------------FZ----D1-----------------
                              if(
                                 (TOP_D1=="多上")
                              )
                                {
                                 if(fz_D1=="无")
                                   {
                                    fz_D1="DT上";
                                   }
                                 else
                                   {fz_D1=fz_D1+"DT上";}
                                }
                              if(
                                 (ATRSTOP_D1=="多上")
                              )
                                {
                                 if(fz_D1=="无")
                                   {
                                    fz_D1="DA上";
                                   }
                                 else
                                   {fz_D1=fz_D1+"DA上";}
                                }
                              if(
                                 (RSI_D1=="低上")
                              )
                                {
                                 if(fz_D1=="无")
                                   {
                                    fz_D1="DR上";
                                   }
                                 else
                                   {fz_D1=fz_D1+"DR上";}
                                }
                              if(
                                 (LMT_D1=="上")
                              )
                                {
                                 if(fz_D1=="无")
                                   {
                                    fz_D1="DL上";
                                   }
                                 else
                                   {fz_D1=fz_D1+"DL上";}
                                }
                              if(
                                 (TOP_D1=="空下")
                              )
                                {
                                 if(fz_D1=="无")
                                   {
                                    fz_D1="DT下";
                                   }
                                 else
                                   {fz_D1=fz_D1+"DT下";}
                                }
                              if(
                                 (ATRSTOP_D1=="空下")
                              )
                                {
                                 if(fz_D1=="无")
                                   {
                                    fz_D1="DA下";
                                   }
                                 else
                                   {fz_D1=fz_D1+"DA下";}
                                }
                              if(
                                 (RSI_D1=="高下")
                              )
                                {
                                 if(fz_D1=="无")
                                   {
                                    fz_D1="DR下";
                                   }
                                 else
                                   {fz_D1=fz_D1+"DR下";}
                                }
                              if(
                                 (LMT_D1=="下")
                              )
                                {
                                 if(fz_D1=="无")
                                   {
                                    fz_D1="DL下";
                                   }
                                 else
                                   {fz_D1=fz_D1+"DL下";}
                                }
                              //-------------LG------H4-----
                              if(
                                 ((BK_D1=="闭藏")||(ADX_D1=="闭藏"))
                              )
                                {
                                 if(lg_D1=="无")
                                   {
                                    lg_D1="D1";
                                   }
                                 else
                                   {lg_D1=lg_D1+"D1";}
                                }
                              if(

                                 ((SR_D1=="天")||(SR_D1=="上")||(SR_D1=="天外天")||(BLP_D1=="天天"))

                              )
                                {
                                 if(tp_D1=="无")
                                   {
                                    tp_D1="D天";
                                   }
                                 else
                                   {tp_D1=tp_D1+"D天";}
                                }
                              if(
                                 ((SR_D1=="地")||(SR_D1=="下")||(SR_D1=="地外地")||(BLP_D1=="地地"))
                              )
                                {
                                 if(tp_D1=="无")
                                   {
                                    tp_D1="D地";
                                   }
                                 else
                                   {tp_D1=tp_D1+"D地";}
                                }
                              //------------------GW------D1-------


                              if(

                                 ((SR_D1=="高")||(SR_D1=="上")||(BLP_D1=="高高")||(LMT_D1=="高"))

                              )
                                {
                                 if(gw_D1=="无")
                                   {
                                    gw_D1="D高";
                                   }
                                 else

                                   {gw_D1=gw_D1+"D高";}
                                }
                              if(
                                 ((SR_D1=="低")||(SR_D1=="下")||(BLP_D1=="低低")||(LMT_D1=="低"))

                              )
                                {
                                 if(gw_D1=="无")
                                   {
                                    gw_D1="D低";
                                   }
                                 else

                                   {gw_D1=gw_D1+"D低";}
                                }
                              //----------------------------QZ--------------------------------


                              //    if(
                              //     ((BK_D1=="发陈")||(BK_D1=="蕃秀"))



                              // )
                              //   {
                              //    qz_D1="D1长";
                              //   }
                              if(
                                 ((ADX_D1=="空发")||(ADX_D1=="空藏")||(ADX_D1=="空趋"))
                              )
                                {
                                 qz_D1="D1空";
                                }
                              if(
                                 ((ADX_D1=="多发")||(ADX_D1=="多藏")||(ADX_D1=="多趋"))
                              )
                                {
                                 qz_D1="D1多";
                                }

                              //-----------------------------------------ATRBD--------------------------
                              if(
                                 ((TBD_D1=="发陈")||(TBD_D1=="藏发")||(TBD_D1=="蕃秀"))
                              )
                                {
                                 if(bd_D1=="无")
                                   {
                                    bd_D1="D1";
                                   }
                                 else
                                   {bd_D1=bd_D1+"D1";}
                                }

                             }

                      /*     if((period_客观角度!=43200)&&(period_客观角度!=1440))
                             {
                              if(
                                 (TOP_H4=="多上")
                              )
                                {
                                 if(fz_H4=="无")
                                   {
                                    fz_H4="H4T上";
                                   }
                                 else
                                   {fz_H4=fz_H4+"H4T上";}
                                }
                              if(
                                 (ATRSTOP_H4=="多上")
                              )
                                {
                                 if(fz_H4=="无")
                                   {
                                    fz_H4="H4A上";
                                   }
                                 else
                                   {fz_H4=fz_H4+"H4A上";}
                                }
                              if(
                                 (RSI_H4=="低上")
                              )
                                {
                                 if(fz_H4=="无")
                                   {
                                    fz_H4="H4R上";
                                   }
                                 else
                                   {fz_H4=fz_H4+"H4R上";}
                                }
                              if(
                                 (LMT_H4=="上")
                              )
                                {
                                 if(fz_H4=="无")
                                   {
                                    fz_H4="H4L上";
                                   }
                                 else
                                   {fz_H4=fz_H4+"H4L上";}
                                }
                              if(
                                 (TOP_H4=="空下")
                              )
                                {
                                 if(fz_H4=="无")
                                   {
                                    fz_H4="H4T下";
                                   }
                                 else
                                   {fz_H4=fz_H4+"H4T下";}
                                }


                              if(
                                 (ATRSTOP_H4=="空下")
                              )
                                {
                                 if(fz_H4=="无")
                                   {
                                    fz_H4="H4A下";
                                   }
                                 else
                                   {fz_H4=fz_H4+"H4A下";}
                                }

                              if(
                                 (RSI_H4=="高下")
                              )
                                {
                                 if(fz_H4=="无")
                                   {
                                    fz_H4="H4R下";
                                   }
                                 else
                                   {fz_H4=fz_H4+"H4R下";}
                                }
                              if(
                                 (LMT_H4=="下")
                              )
                                {
                                 if(fz_H4=="无")
                                   {
                                    fz_H4="H4L下";
                                   }
                                 else
                                   {fz_H4=fz_H4+"H4L下";}
                                }

                              if(
                                 ((BK_H4=="闭藏")||(ADX_H4=="闭藏"))
                              )
                                {
                                 if(lg_H4=="无")
                                   {
                                    lg_H4="H4";
                                   }
                                 else
                                   {lg_H4=lg_H4+"H4";}
                                }
                              //------------------TP----H4---------
                              if(

                                 (((SR_H4=="天")||(SR_H4=="上")||(SR_H4=="天外天")||(BLP_H4=="天天")))

                              )
                                {
                                 if(tp_H4=="无")
                                   {
                                    tp_H4="H4天";
                                   }
                                 else
                                   {tp_H4=tp_H4+"H4天";}
                                }
                              if(
                                 ((SR_H4=="地")||(SR_H4=="下")||(SR_H4=="地外地")||(BLP_H4=="地地"))


                              )
                                {
                                 if(tp_H4=="无")
                                   {
                                    tp_H4="H4地";
                                   }
                                 else
                                   {tp_H4=tp_H4+"H4地";}
                                }
                              //------------------GW------H4-------
                              if(

                                 ((SR_H4=="高")||(SR_H4=="上")||(BLP_H4=="高高")||(LMT_H4=="高"))


                              )
                                {
                                 if(gw_H4=="无")
                                   {
                                    gw_H4="H4高";
                                   }
                                 else

                                   {gw_H4=gw_H4+"H4高";}
                                }
                              if(
                                 ((SR_H4=="低")||(SR_H4=="下")||(BLP_H4=="低低")||(LMT_H4=="低"))

                              )
                                {
                                 if(gw_H4=="无")
                                   {
                                    gw_H4="H4低";
                                   }
                                 else

                                   {gw_H4=gw_H4+"H4低";}
                                }
                              // if(

                              //   ((BK_H4=="发陈")||(BK_H4=="蕃秀"))

                              //  )
                              //   {
                              //   if(qz_H4=="无")
                              //     {
                              //      qz_H4="H4长";
                              //     }
                              //    else
                              //      {qz_H4=qz_H4+"H4长";}
                              //   }
                              if(



                                 ((ADX_H4=="空发")||(ADX_H4=="空藏")||(ADX_H4=="空趋"))

                              )
                                {
                                 if(qz_H4=="无")
                                   {
                                    qz_H4="H4空";
                                   }
                                 else
                                   {qz_H4=qz_H4+"H4空";}
                                }
                              if(



                                 ((ADX_H4=="多发")||(ADX_H4=="多藏")||(ADX_H4=="多趋"))

                              )
                                {
                                 if(qz_H4=="无")
                                   {
                                    qz_H4="H4多";
                                   }
                                 else
                                   {qz_H4=qz_H4+"H4多";}
                                }
                              //-------------------------------------

                              if(
                                 ((TBD_H4=="发陈")||(TBD_H4=="藏发")||(TBD_H4=="蕃秀"))
                              )
                                {
                                 if(bd_H4=="无")
                                   {
                                    bd_H4="H4";
                                   }
                                 else
                                   {bd_H4=bd_H4+"H4";}
                                }
                             }







                           if((period_客观角度!=43200)&&(period_客观角度!=10080)&&(period_客观角度!=1440))
                             {
                              //-----------------H1---------------------

                              string lg_H1="无";
                              string qz_H1="无";
                              string tp_H1="无";
                              string bd_H1="无";
                              string fz_H1="无";
                              string gw_H1="无";
                              if(
                                 ((BK_H1=="闭藏")||(ADX_H1=="闭藏"))
                              )
                                {
                                 if(lg_H1=="无")
                                   {
                                    lg_H1="H1";
                                   }
                                 else
                                   {lg_H1=lg_H1+"H1";}
                                }
                              if(

                                 ((SR_H1=="天")||(SR_H1=="上")||(SR_H1=="天外天")||(BLP_H1=="天天"))

                              )
                                {
                                 if(tp_H1=="无")
                                   {
                                    tp_H1="H1天";
                                   }
                                 else
                                   {tp_H1=tp_H1+"H1天";}
                                }
                              if(
                                 ((SR_H1=="地")||(SR_H1=="下")||(SR_H1=="地外地")||(BLP_H1=="地地"))

                              )
                                {
                                 if(tp_H1=="无")
                                   {
                                    tp_H1="H1地";
                                   }
                                 else
                                   {tp_H1=tp_H1+"H1地";}
                                }




                              //    if(
                              //      ((BK_H1=="发陈")||(BK_H1=="蕃秀"))



                              //   )
                              //     {
                              //      if(qz_H1=="无")
                              //       {
                              //        qz_H1="H1长";
                              //       }
                              //     else
                              //       {qz_H1=qz_H1+"H1长";}
                              //    }
                              if((ADX_H1=="空发")||(ADX_H1=="空藏")||(ADX_H1=="空趋"))
                                {
                                 if(qz_H1=="无")
                                   {
                                    qz_H1="H1空";
                                   }
                                 else
                                   {qz_H1=qz_H1+"H1空";}
                                }
                              if((ADX_H1=="多发")||(ADX_H1=="多藏")||(ADX_H1=="多趋"))

                                {
                                 if(qz_H1=="无")
                                   {
                                    qz_H1="H1多";
                                   }
                                 else
                                   {qz_H1=qz_H1+"H1多";}
                                }

                              if(
                                 (TOP_H1=="多上")
                              )
                                {
                                 if(fz_H1=="无")
                                   {
                                    fz_H1="H1T上";
                                   }
                                 else
                                   {fz_H1=fz_H1+"H1T上";}
                                }



                              if(
                                 (ATRSTOP_H1=="多上")
                              )
                                {
                                 if(fz_H1=="无")
                                   {
                                    fz_H1="H1A上";
                                   }
                                 else
                                   {fz_H1=fz_H1+"H1A上";}
                                }
                              if(
                                 (RSI_H1=="低上")
                              )
                                {
                                 if(fz_H1=="无")
                                   {
                                    fz_H1="H1R上";
                                   }
                                 else
                                   {fz_H1=fz_H1+"H1R上";}
                                }
                              if(
                                 (LMT_H1=="上")
                              )
                                {
                                 if(fz_H1=="无")
                                   {
                                    fz_H1="H1L上";
                                   }
                                 else
                                   {fz_H1=fz_H1+"H1L上";}
                                }

                              if(
                                 (TOP_H1=="空下")
                              )
                                {
                                 if(fz_H1=="无")
                                   {
                                    fz_H1="H1T下";
                                   }
                                 else
                                   {fz_H1=fz_H1+"H1T下";}
                                }

                              if(
                                 (ATRSTOP_H1=="空下")
                              )
                                {
                                 if(fz_H1=="无")
                                   {
                                    fz_H1="H1A下";
                                   }
                                 else
                                   {fz_H1=fz_H1+"H1A下";}
                                }
                              if(
                                 (RSI_H1=="高下")
                              )
                                {
                                 if(fz_H1=="无")
                                   {
                                    fz_H1="H1R下";
                                   }
                                 else
                                   {fz_H1=fz_H1+"H1R下";}
                                }
                              if(
                                 (LMT_H1=="下")
                              )
                                {
                                 if(fz_H1=="无")
                                   {
                                    fz_H1="H1L下";
                                   }
                                 else
                                   {fz_H1=fz_H1+"H1L下";}
                                }

                              if(

                                 ((SR_H1=="高")||(SR_H1=="上")||(BLP_H1=="高高")||(LMT_H1=="高"))

                              )
                                {
                                 if(gw_H1=="无")
                                   {
                                    gw_H1="H1高";
                                   }
                                 else

                                   {gw_H1=gw_H1+"H1高";}
                                }
                              if(
                                 ((SR_H1=="低")||(SR_H1=="下")||(BLP_H1=="低低")||(LMT_H1=="低"))

                              )
                                {
                                 if(gw_H1=="无")
                                   {
                                    gw_H1="H1低";
                                   }
                                 else

                                   {gw_H1=gw_H1+"H1低";}
                                }
                              if(
                                 ((TBD_H1=="发陈")||(TBD_H1=="藏发"))
                              )
                                {
                                 if(bd_H1=="无")
                                   {
                                    bd_H1="H1";
                                   }
                                 else
                                   {bd_H1=bd_H1+"H1";}
                                }
                             }
                           // //------------------M30---------------------
                           if((period_客观角度==15)||(period_客观角度==5)||(period_客观角度==1)||(period_客观角度==30))
                             {
                              string lg_M30="无";
                              string qz_M30="无";
                              string tp_M30="无";
                              string bd_M30="无";
                              string fz_M30="无";
                              string gw_M30="无";
                              if(
                                 ((BK_M30=="闭藏")||(ADX_M30=="闭藏"))
                              )
                                {
                                 if(lg_M30=="无")
                                   {
                                    lg_M30="M30";
                                   }
                                 else
                                   {lg_M30=lg_M30+"M30";}
                                }
                              // if(

                              //   ((BK_M30=="发陈")||(BK_M30=="蕃秀"))

                              // )
                              //  {
                              //  if(qz_M30=="无")
                              //    {
                              //    qz_M30="M30长";
                              //    }
                              //  else
                              //     {qz_M30=qz_M30+"M30长";}
                              //  }
                              if(

                                 ((ADX_M30=="空发")||(ADX_M30=="空藏")||(ADX_M30=="空趋"))

                              )
                                {
                                 if(qz_M30=="无")
                                   {
                                    qz_M30="M30空";
                                   }
                                 else
                                   {qz_M30=qz_M30+"M30空";}
                                }
                              if(

                                 ((ADX_M30=="多发")||(ADX_M30=="多藏")||(ADX_M30=="多趋"))

                              )
                                {
                                 if(qz_M30=="无")
                                   {
                                    qz_M30="M30多";
                                   }
                                 else
                                   {qz_M30=qz_M30+"M30多";}
                                }

                              if(
                                 ((TBD_M30=="发陈")||(TBD_M30=="藏发")||(TBD_M30=="蕃秀"))
                              )
                                {
                                 if(bd_M30=="无")
                                   {
                                    bd_M30="M30";
                                   }
                                 else
                                   {bd_M30=bd_M30+"M30";}
                                }
                              if(

                                 ((SR_M30=="天")||(SR_M30=="上")||(SR_M30=="天外天")||(BLP_M30=="天天"))

                              )
                                {
                                 if(tp_M30=="无")
                                   {
                                    tp_M30="M30天";
                                   }
                                 else
                                   {tp_M30=tp_M30+"M30天";}
                                }
                              if(
                                 ((SR_M30=="地")||(SR_M30=="下")||(SR_M30=="地外地")||(BLP_M30=="地地"))

                              )
                                {
                                 if(tp_M30=="无")
                                   {
                                    tp_M30="M30地";
                                   }
                                 else
                                   {tp_M30=tp_M30+"M30地";}
                                }

                              if(
                                 (TOP_M30=="多上")
                              )
                                {
                                 if(fz_M30=="无")
                                   {
                                    fz_M30="M30T上";
                                   }
                                 else
                                   {fz_M30=fz_M30+"M30T上";}
                                }

                              if(
                                 (ATRSTOP_M30=="多上")
                              )
                                {
                                 if(fz_M30=="无")
                                   {
                                    fz_M30="M30A上";
                                   }
                                 else
                                   {fz_M30=fz_M30+"M30A上";}
                                }
                              if(
                                 (RSI_M30=="低上")
                              )
                                {
                                 if(fz_M30=="无")
                                   {
                                    fz_M30="M30R上";
                                   }
                                 else
                                   {fz_M30=fz_M30+"M30R上";}
                                }
                              if(
                                 (LMT_M30=="上")
                              )
                                {
                                 if(fz_M30=="无")
                                   {
                                    fz_M30="M30L上";
                                   }
                                 else
                                   {fz_M30=fz_M30+"M30L上";}
                                }
                              if(
                                 (TOP_M30=="空下")
                              )
                                {
                                 if(fz_M30=="无")
                                   {
                                    fz_M30="M30T下";
                                   }
                                 else
                                   {fz_M30=fz_M30+"M30T下";}
                                }

                              if(
                                 (ATRSTOP_M30=="空下")
                              )
                                {
                                 if(fz_M30=="无")
                                   {
                                    fz_M30="M30A下";
                                   }
                                 else
                                   {fz_M30=fz_M30+"M30A下";}
                                }

                              if(
                                 (RSI_M30=="高下")
                              )
                                {
                                 if(fz_M30=="无")
                                   {
                                    fz_M30="M30R下";
                                   }
                                 else
                                   {fz_M30=fz_M30+"M30R下";}
                                }
                              if(
                                 (LMT_M30=="下")
                              )
                                {
                                 if(fz_M30=="无")
                                   {
                                    fz_M30="M30L下";
                                   }
                                 else
                                   {fz_M30=fz_M30+"M30L下";}
                                }

                              if(

                                 ((SR_M30=="高")||(SR_M30=="上")||(BLP_M30=="高高")||(LMT_M30=="高高"))

                              )
                                {
                                 if(gw_M30=="无")
                                   {
                                    gw_M30="M30高";
                                   }
                                 else

                                   {gw_M30=gw_M30+"M30高";}
                                }
                              if(
                                 ((SR_M30=="低")||(SR_M30=="下")||(BLP_M30=="低低")||(LMT_M30=="低"))

                              )
                                {
                                 if(gw_M30=="无")
                                   {
                                    gw_M30="M30低";
                                   }
                                 else

                                   {gw_M30=gw_M30+"M30低";}
                                }
                             }



                           if((period_客观角度==15)||(period_客观角度==5)||(period_客观角度==1))
                             {
                              //-----------------M15-----------------


                              string lg_M15="无";
                              string qz_M15="无";
                              string tp_M15="无";
                              string bd_M15="无";
                              string fz_M15="无";
                              string gw_M15="无";

                              //--------------------lg------------------------------
                              if(
                                 ((BK_M15=="闭藏")||(ADX_M15=="闭藏"))
                              )
                                {
                                 if(lg_M15=="无")
                                   {
                                    lg_M15="M15";
                                   }
                                 else
                                   {lg_M15=lg_M15+"M15";}
                                }

                              //---------------------qz----------------------------------
                              if(
                                 ((ADX_M15=="空发")||(ADX_M15=="空藏")||(ADX_M15=="空趋"))

                              )
                                {
                                 if(qz_M15=="无")
                                   {
                                    qz_M15="M15空";
                                   }
                                 else
                                   {qz_M15=qz_M15+"M15空";}
                                }
                              if(
                                 ((ADX_M15=="多发")||(ADX_M15=="多藏")||(ADX_M15=="多趋"))
                              )
                                {
                                 if(qz_M15=="无")
                                   {
                                    qz_M15="M15多";
                                   }
                                 else
                                   {qz_M15=qz_M15+"M15多";}
                                }
                              //-------------------fz---------
                              if(
                                 ((TBD_M15=="发陈")||(TBD_M15=="藏发")||(TBD_M15=="蕃秀"))
                              )
                                {
                                 if(bd_M15=="无")
                                   {
                                    bd_M15="M15";
                                   }
                                 else
                                   {bd_M15=bd_M15+"M15";}
                                }
                              if(

                                 ((SR_M15=="天")||(SR_M15=="上")||(SR_M15=="天外天")||(BLP_M15=="天天"))
                              )
                                {
                                 if(tp_M15=="无")
                                   {
                                    tp_M15="M15天";
                                   }
                                 else
                                   {tp_M15=tp_M15+"M15天";}
                                }
                              if(
                                 ((SR_M15=="地")||(SR_M15=="下")||(SR_M15=="地外地")||(BLP_M15=="地地"))
                              )
                                {
                                 if(tp_M15=="无")
                                   {
                                    tp_M15="M15地";
                                   }
                                 else
                                   {tp_M15=tp_M15+"M15地";}
                                }
                              if(
                                 (TOP_M15=="多上")
                              )
                                {
                                 if(fz_M15=="无")
                                   {
                                    fz_M15="M15T上";
                                   }
                                 else
                                   {fz_M15=fz_M15+"M15T上";}
                                }
                              if(
                                 (ATRSTOP_M15=="多上")
                              )
                                {
                                 if(fz_M15=="无")
                                   {
                                    fz_M15="M15A上";
                                   }
                                 else
                                   {fz_M15=fz_M15+"M15A上";}
                                }
                              if(
                                 (RSI_M15=="低上")
                              )
                                {
                                 if(fz_M15=="无")
                                   {
                                    fz_M15="M15R上";
                                   }
                                 else
                                   {fz_M15=fz_M15+"M15R上";}
                                }
                              if(
                                 (LMT_M15=="上")
                              )
                                {
                                 if(fz_M15=="无")
                                   {
                                    fz_M15="M15L上";
                                   }
                                 else
                                   {fz_M15=fz_M15+"M15L上";}
                                }
                              if(
                                 (TOP_M15=="空下")
                              )
                                {
                                 if(fz_M15=="无")
                                   {
                                    fz_M15="M15T下";
                                   }
                                 else
                                   {fz_M15=fz_M15+"M15T下";}
                                }
                              if(
                                 (ATRSTOP_M15=="空下")
                              )
                                {
                                 if(fz_M15=="无")
                                   {
                                    fz_M15="M15A下";
                                   }
                                 else
                                   {fz_M15=fz_M15+"M15A下";}
                                }
                              if(
                                 (RSI_M15=="高下")
                              )
                                {
                                 if(fz_M15=="无")
                                   {
                                    fz_M15="M15R下";
                                   }
                                 else
                                   {fz_M15=fz_M15+"M15R下";}
                                }
                              if(
                                 (LMT_M15=="下")
                              )
                                {
                                 if(fz_M15=="无")
                                   {
                                    fz_M15="M15L下";
                                   }
                                 else
                                   {fz_M15=fz_M15+"M15L下";}
                                }
                              if((SR_M15=="高")||(SR_M15=="上")||(BLP_M15=="高高")||(LMT_M15=="高"))
                                {
                                 if(gw_M15=="无")
                                   {
                                    gw_M15="M15高";
                                   }
                                 else

                                   {gw_M15=gw_M15+"M15高";}
                                }
                              if((SR_M15=="低")||(SR_M15=="下")||(BLP_M15=="低低")||(LMT_M15=="低"))
                                {
                                 if(gw_M15=="无")
                                   {
                                    gw_M15="M15低";
                                   }
                                 else

                                   {gw_M15=gw_M15+"M15低";}
                                }
                             }
                           if((period_客观角度==5)||(period_客观角度==15))
                             {
                              string lg_M5="无";
                              string qz_M5="无";
                              string tp_M5="无";
                              string bd_M5="无";
                              string fz_M5="无";
                              string gw_M5="无";
                              //------------lg-----

                              if(
                                 ((BK_M5=="闭藏")||(ADX_M5=="闭藏"))
                              )
                                {
                                 if(lg_M5=="无")
                                   {
                                    lg_M5="M5";
                                   }
                                 else
                                   {lg_M5=lg_M5+"M5";}
                                }
                              //-------------qz-------
                              if((ADX_M5=="空发")||(ADX_M5=="空藏")||(ADX_M5=="空趋"))
                                {
                                 if(qz_M5=="无")
                                   {
                                    qz_M5="M5空";
                                   }
                                 else
                                   {qz_M5=qz_M5+"M5空";}
                                }
                              if((ADX_M5=="多发")||(ADX_M5=="多藏")||(ADX_M5=="多趋"))
                                {
                                 if(qz_M5=="无")
                                   {
                                    qz_M5="M5多";
                                   }
                                 else
                                   {qz_M5=qz_M5+"M5多";}
                                }
                              //------------------fz--------------------

                              if(TOP_M5=="多上")
                                {
                                 if(fz_M5=="无")
                                   {
                                    fz_M5="M5T上";
                                   }
                                 else
                                   {
                                    fz_M5=fz_M5+"M5T上";
                                   }
                                }
                              if(
                                 (ATRSTOP_M5=="多上")
                              )
                                {
                                 if(fz_M5=="无")
                                   {
                                    fz_M5="M5A上";
                                   }
                                 else
                                   {fz_M5=fz_M5+"M5A上";}
                                }
                              if(RSI_M5=="低上")
                                {
                                 if(fz_M5=="无")
                                   {
                                    fz_M5="M5R上";
                                   }
                                 else
                                   {fz_M5=fz_M5+"M5R上";}
                                }
                              if(
                                 (LMT_M5=="上")
                              )
                                {
                                 if(fz_M5=="无")
                                   {
                                    fz_M5="M5L上";
                                   }
                                 else
                                   {fz_M5=fz_M5+"M5L上";}
                                }
                              if(
                                 (TOP_M5=="空下")
                              )
                                {
                                 if(fz_M5=="无")
                                   {
                                    fz_M5="M5T下";
                                   }
                                 else
                                   {fz_M5=fz_M5+"M5T下";}
                                }

                              if(
                                 (ATRSTOP_M5=="空下")
                              )
                                {
                                 if(fz_M5=="无")
                                   {
                                    fz_M5="M5A下";
                                   }
                                 else
                                   {fz_M5=fz_M5+"M5A下";}
                                }
                              if(
                                 (RSI_M5=="高下")
                              )
                                {
                                 if(fz_M5=="无")
                                   {
                                    fz_M5="M5R下";
                                   }
                                 else
                                   {fz_M5=fz_M5+"M5R下";}
                                }
                              if(
                                 (LMT_M5=="下")
                              )
                                {
                                 if(fz_M5=="无")
                                   {
                                    fz_M5="M5L下";
                                   }
                                 else
                                   {fz_M5=fz_M5+"M5L下";}
                                }

                              if((TBD_M5=="发陈")||(TBD_M5=="藏发")||(TBD_M5=="蕃秀"))
                                {
                                 if(bd_M5=="无")
                                   {
                                    bd_M5="M5";
                                   }
                                 else
                                   {bd_M5=bd_M5+"M5";}
                                }
                              if((SR_M5=="天")||(SR_M5=="上")||(SR_M5=="天外天")||(BLP_M5=="天天"))
                                {
                                 if(tp_M5=="无")
                                   {
                                    tp_M5="M5天";
                                   }
                                 else
                                   {tp_M5=tp_M5+"M5天";}
                                }

                              if(
                                 ((SR_M5=="地")||(SR_M5=="下")||(SR_M5=="地外地")||(BLP_M5=="地地"))

                              )
                                {
                                 if(tp_M5=="无")
                                   {
                                    tp_M5="M5地";
                                   }
                                 else
                                   {tp_M5=tp_M5+"M5地";}
                                }
                              //--------------------

                              if(

                                 (SR_M5=="高")||(SR_M5=="上")||(BLP_M5=="高高")||(LMT_M5=="高")

                              )
                                {
                                 if(gw_M5=="无")
                                   {
                                    gw_M5="M5高";
                                   }
                                 else

                                   {gw_M5=gw_M5+"M5高";}
                                }
                              if(
                                 (SR_M5=="低")||(SR_M5=="下")||(BLP_M5=="低低")||(LMT_M5=="低")
                              )
                                {
                                 if(gw_M5=="无")
                                   {
                                    gw_M5="M5低";
                                   }
                                 else
                                   {gw_M5=gw_M5+"M5低";}
                                }
                             }
                           if((period_客观角度==15))
                             {
                              string lg_M1="无";
                              string qz_M1="无";
                              string tp_M1="无";
                              string bd_M1="无";
                              string fz_M1="无";
                              string gw_M1="无";


                              //---------lg--------
                              if(
                                 ((BK_M1=="闭藏")||(ADX_M1=="闭藏"))
                              )
                                {
                                 if(lg_M1=="无")
                                   {
                                    lg_M1="M1";
                                   }
                                 else
                                   {lg_M5=lg_M5+"M1";}
                                }
                              //---------qz--------

                              if(

                                 ((ADX_M1=="空发")||(ADX_M1=="空藏")||(ADX_M1=="空趋"))

                              )
                                {
                                 if(qz_M1=="无")
                                   {
                                    qz_M1="M1空";
                                   }
                                 else
                                   {qz_M1=qz_M1+"M1空";}
                                }
                              if(

                                 ((ADX_M1=="多发")||(ADX_M1=="多藏")||(ADX_M1=="多趋"))

                              )
                                {
                                 if(qz_M1=="无")
                                   {
                                    qz_M1="M1多";
                                   }
                                 else
                                   {qz_M1=qz_M1+"M1多";}
                                }

                              //---------------------fzfz---------------------------------------------
                              if(TOP_M1=="多上")
                                {
                                 if(fz_M1=="无")
                                   {
                                    fz_M1="M1T上";
                                   }
                                 else
                                   {fz_M1=fz_M1+"M1T上";}
                                }
                              if(
                                 (ATRSTOP_M1=="多上")
                              )
                                {
                                 if(fz_M1=="无")
                                   {
                                    fz_M1="M1A上";
                                   }
                                 else
                                   {fz_M1=fz_M1+"M1A上";}
                                }
                              if(
                                 (RSI_M1=="低上")
                              )
                                {
                                 if(fz_M1=="无")
                                   {
                                    fz_M1="M1R上";
                                   }
                                 else
                                   {fz_M1=fz_M1+"M1R上";}
                                }
                              if(
                                 (LMT_M1=="上")
                              )
                                {
                                 if(fz_M1=="无")
                                   {
                                    fz_M1="M1L上";
                                   }
                                 else
                                   {fz_M1=fz_M1+"M1L上";}
                                }
                              if(
                                 (TOP_M1=="空下")
                              )
                                {
                                 if(fz_M1=="无")
                                   {
                                    fz_M1="M1T下";
                                   }
                                 else
                                   {fz_M1=fz_M1+"M1T下";}
                                }
                              if(
                                 (ATRSTOP_M1=="空下")
                              )
                                {
                                 if(fz_M1=="无")
                                   {
                                    fz_M1="M1A下";
                                   }
                                 else
                                   {fz_M1=fz_M1+"M1A下";}
                                }

                              if(
                                 (RSI_M1=="高下")
                              )
                                {
                                 if(fz_M1=="无")
                                   {
                                    fz_M1="M1R下";
                                   }
                                 else
                                   {fz_M1=fz_M1+"M1R下";}
                                }
                              if(
                                 (LMT_M1=="下")
                              )
                                {
                                 if(fz_M1=="无")
                                   {
                                    fz_M1="M1L下";
                                   }
                                 else
                                   {fz_M1=fz_M1+"M1L下";}
                                }


                              if(
                                 ((TBD_M1=="发陈")||(TBD_M1=="藏发")||(TBD_M1=="蕃秀"))
                              )
                                {
                                 if(bd_M1=="无")
                                   {
                                    bd_M1="M1";
                                   }
                                 else
                                   {bd_M1=bd_M1+"M1";}
                                }
                              if(

                                 ((SR_M1=="天")||(SR_M1=="上")||(SR_M1=="天外天")||(BLP_M1=="天天"))

                              )
                                {
                                 if(tp_M1=="无")
                                   {
                                    tp_M1="M1天";
                                   }
                                 else
                                   {tp_M1=tp_M1+"M1天";}
                                }
                              if(
                                 ((SR_M1=="地")||(SR_M1=="下")||(SR_M1=="地外地")||(BLP_M1=="地地"))

                              )
                                {
                                 if(tp_M1=="无")
                                   {
                                    tp_M1="M1地";
                                   }
                                 else
                                   {tp_M1=tp_M1+"M1地";}
                                }
                              if(

                                 (SR_M1=="高")||(SR_M1=="上")||(BLP_M1=="高高")||(LMT_M1=="高")

                              )
                                {
                                 if(gw_M1=="无")
                                   {
                                    gw_M1="M1高";
                                   }
                                 else

                                   {gw_M1=gw_M1+"M1高";}
                                }
                              if(
                                 (SR_M1=="低")||(SR_M1=="下")||(BLP_M1=="低低")||(LMT_M1=="低")
                              )
                                {
                                 if(gw_M1=="无")
                                   {
                                    gw_M1="M1低";
                                   }
                                 else

                                   {gw_M1=gw_M1+"M1低";}
                                }
                             }
                           //------------------------------------------------------------------

                           int kk4=iBarShift(Symbol_0,TF4, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int kk3=iBarShift(Symbol_0,TF3, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int kk2=iBarShift(Symbol_0,TF2, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int kk1=iBarShift(Symbol_0,TF1, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int kk0=iBarShift(Symbol_0,TF0, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int kk_1=iBarShift(Symbol_0,TF_1, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));
                           int kk_2=iBarShift(Symbol_0,TF_2, iTime(Symbol_0,period_客观角度,shift_OK_W1_D1_H4_H1_M30_M15_M5_M1));


                    /*       if(period_客观角度==1)
                             {
                              FileWrite(handle
                                        , Symbol_0,进制转换10T16(计算数字(lg_H1,qz_H1,tp_H1,bd_H1))+进制转换10T16(计算数字(lg_M30,qz_M30,tp_M30,bd_M30))+进制转换10T16(计算数字(lg_M15,qz_M15,tp_M15,bd_M15))+进制转换10T16(计算数字(lg_M5,qz_M5,tp_M5,bd_M5))+进制转换10T16(计算数字(lg_M1,qz_M1,tp_M1,bd_M1))+"__"

                                        ,"@"+period_客观角度
                                        ,g,lg_H1,qz_H1,tp_H1,fz_H1,gw_H1,bd_H1

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_H1,shift_H1), TIME_DATE|TIME_MINUTES)
                                        ,close_H1


                                        ,lg_M30,qz_M30,tp_M30,fz_M30,gw_M30,bd_M30
                                        ,TimeToStr(iTime(Symbol_0,PERIOD_M30,shift_M30), TIME_DATE|TIME_MINUTES)
                                        ,close_M30

                                        ,lg_M15,qz_M15,tp_M15,fz_M15,gw_M15,bd_M15
                                        ,TimeToStr(iTime(Symbol_0,PERIOD_M15,shift_M15), TIME_DATE|TIME_MINUTES)
                                        ,close_M15

                                        ,lg_M5,qz_M5,tp_M5,fz_M5,gw_M5,bd_M5
                                        ,TimeToStr(iTime(Symbol_0,PERIOD_M5,shift_M5), TIME_DATE|TIME_MINUTES)
                                        ,close_M5

                                        ,lg_M1,qz_M1,tp_M1,fz_M1,gw_M1,bd_M1
                                        ,TimeToStr(iTime(Symbol_0,PERIOD_M1,shift_M1), TIME_DATE|TIME_MINUTES)
                                        ,close_M1

                                       );//
                             }
                           if(period_客观角度==5)
                             {
                              FileWrite(handle
                                        , Symbol_0,进制转换10T16(计算数字(lg_H4,qz_H4,tp_H4,bd_H4))+进制转换10T16(计算数字(lg_H1,qz_H1,tp_H1,bd_H1))+进制转换10T16(计算数字(lg_M30,qz_M30,tp_M30,bd_M30))+进制转换10T16(计算数字(lg_M15,qz_M15,tp_M15,bd_M15))+进制转换10T16(计算数字(lg_M5,qz_M5,tp_M5,bd_M5))+"__"
                                        ,"@"+period_客观角度
                                        ,g,lg_H4,qz_H4,tp_H4,fz_H4,gw_H4,bd_H4

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_H4,shift_H4), TIME_DATE|TIME_MINUTES)
                                        ,close_H4


                                        ,lg_H1,qz_H1,tp_H1,fz_H1,gw_H1,bd_H1

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_H1,shift_H1), TIME_DATE|TIME_MINUTES)
                                        ,close_H1


                                        ,lg_M30,qz_M30,tp_M30,fz_M30,gw_M30,bd_M30
                                        ,TimeToStr(iTime(Symbol_0,PERIOD_M30,shift_M30), TIME_DATE|TIME_MINUTES)
                                        ,close_M30

                                        ,lg_M15,qz_M15,tp_M15,fz_M15,gw_M15,bd_M15
                                        ,TimeToStr(iTime(Symbol_0,PERIOD_M15,shift_M15), TIME_DATE|TIME_MINUTES)
                                        ,close_M15

                                        ,lg_M5,qz_M5,tp_M5,fz_M5,gw_M5,bd_M5
                                        ,TimeToStr(iTime(Symbol_0,PERIOD_M5,shift_M5), TIME_DATE|TIME_MINUTES)
                                        ,close_M5

                                       );//
                             }
                           if(period_客观角度==15)
                             {
                              FileWrite(handle
                                        ,Symbol_0,TimeToStr(iTime(Symbol_0,PERIOD_M15,shift_M15), TIME_DATE|TIME_MINUTES)
                                        ,"@"+period_客观角度,close_M15
                                        ,计算数字(lg_MN1,qz_MN1,tp_MN1,bd_MN1),计算数字(lg_W1,qz_W1,tp_W1,bd_W1),计算数字(lg_D1,qz_D1,tp_D1,bd_D1),计算数字(lg_H4,qz_H4,tp_H4,bd_H4),计算数字(lg_H1,qz_H1,tp_H1,bd_H1),计算数字(lg_M30,qz_M30,tp_M30,bd_M30),计算数字(lg_M15,qz_M15,tp_M15,bd_M15),计算数字(lg_M5,qz_M5,tp_M5,bd_M5),计算数字(lg_M1,qz_M1,tp_M1,bd_M1)
                                        /*
                                                    ,TimeToStr(iTime(Symbol_0,PERIOD_D1,shift_D1), TIME_DATE|TIME_MINUTES)
                                                    ,close_D1


                                                    ,lg_H4,qz_H4,tp_H4,fz_H4,gw_H4,bd_H4

                                                    ,TimeToStr(iTime(Symbol_0,PERIOD_H4,shift_H4), TIME_DATE|TIME_MINUTES)
                                                    ,close_H4


                                                    ,lg_H1,qz_H1,tp_H1,fz_H1,gw_H1,bd_H1

                                                    ,TimeToStr(iTime(Symbol_0,PERIOD_H1,shift_H1), TIME_DATE|TIME_MINUTES)
                                                    ,close_H1


                                                    ,lg_M30,qz_M30,tp_M30,fz_M30,gw_M30,bd_M30
                                                    ,TimeToStr(iTime(Symbol_0,PERIOD_M30,shift_M30), TIME_DATE|TIME_MINUTES)
                                                    ,close_M30

                                                    ,lg_M15,qz_M15,tp_M15,fz_M15,gw_M15,bd_M15
                                                    ,TimeToStr(iTime(Symbol_0,PERIOD_M15,shift_M15), TIME_DATE|TIME_MINUTES)
                                                    ,close_M15
                                       
                                       );//
                             }

                           if(period_客观角度==30)
                             {
                              FileWrite(handle
                                        , Symbol_0,进制转换10T16(计算数字(lg_W1,qz_W1,tp_W1,bd_W1))+进制转换10T16(计算数字(lg_D1,qz_D1,tp_D1,bd_D1))+进制转换10T16(计算数字(lg_H4,qz_H4,tp_H4,bd_H4))+进制转换10T16(计算数字(lg_H1,qz_H1,tp_H1,bd_H1))+进制转换10T16(计算数字(lg_M30,qz_M30,tp_M30,bd_M30))+"__"
                                        ,"@"+period_客观角度
                                        ,g,lg_W1,qz_W1,tp_W1,fz_W1,gw_W1,bd_W1

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_W1,shift_W1), TIME_DATE|TIME_MINUTES)
                                        ,close_W1


                                        ,lg_D1,qz_D1,tp_D1,fz_D1,gw_D1,bd_D1

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_D1,shift_D1), TIME_DATE|TIME_MINUTES)
                                        ,close_D1


                                        ,lg_H4,qz_H4,tp_H4,fz_H4,gw_H4,bd_H4

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_H4,shift_H4), TIME_DATE|TIME_MINUTES)
                                        ,close_H4


                                        ,lg_H1,qz_H1,tp_H1,fz_H1,gw_H1,bd_H1

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_H1,shift_H1), TIME_DATE|TIME_MINUTES)
                                        ,close_H1


                                        ,lg_M30,qz_M30,tp_M30,fz_M30,gw_M30,bd_M30
                                        ,TimeToStr(iTime(Symbol_0,PERIOD_M30,shift_M30), TIME_DATE|TIME_MINUTES)
                                        ,close_M30


                                       );//
                             }
                           if(period_客观角度==60)
                             {
                              FileWrite(handle
                                              ,Symbol_0,TimeToStr(iTime(Symbol_0,PERIOD_H1,shift_H1), TIME_DATE)
                                        ,"@"+period_客观角度,close_H1
                                        ,计算数字(lg_MN1,qz_MN1,tp_MN1,bd_MN1),计算数字(lg_W1,qz_W1,tp_W1,bd_W1),计算数字(lg_D1,qz_D1,tp_D1,bd_D1),计算数字(lg_H4,qz_H4,tp_H4,bd_H4),计算数字(lg_H1,qz_H1,tp_H1,bd_H1),计算数字(lg_M30,qz_M30,tp_M30,bd_M30),计算数字(lg_M15,qz_M15,tp_M15,bd_M15),计算数字(lg_M5,qz_M5,tp_M5,bd_M5),计算数字(lg_M1,qz_M1,tp_M1,bd_M1)
                                  ,g,lg_MN1,qz_MN1,tp_MN1,fz_MN1,gw_MN1,bd_MN1

                                                  ,TimeToStr(iTime(Symbol_0,PERIOD_MN1,shift_MN1), TIME_DATE|TIME_MINUTES)
                                                  ,close_MN1


                                                  ,lg_W1,qz_W1,tp_W1,fz_W1,gw_W1,bd_W1

                                                  ,TimeToStr(iTime(Symbol_0,PERIOD_W1,shift_W1), TIME_DATE|TIME_MINUTES)
                                                  ,close_W1


                                                  ,lg_D1,qz_D1,tp_D1,fz_D1,gw_D1,bd_D1

                                                  ,TimeToStr(iTime(Symbol_0,PERIOD_D1,shift_D1), TIME_DATE|TIME_MINUTES)
                                                  ,close_D1


                                                  ,lg_H4,qz_H4,tp_H4,fz_H4,gw_H4,bd_H4

                                                  ,TimeToStr(iTime(Symbol_0,PERIOD_H4,shift_H4), TIME_DATE|TIME_MINUTES)
                                                  ,close_H4


                                                  ,lg_H1,qz_H1,tp_H1,fz_H1,gw_H1,bd_H1

                                                  ,TimeToStr(iTime(Symbol_0,PERIOD_H1,shift_H1), TIME_DATE|TIME_MINUTES)
                                                  ,close_H1  

                                       );//
                             }

                           if(period_客观角度==240)
                             {
                              FileWrite(handle
                                        , Symbol_0,进制转换10T16(计算数字(lg_MN1,qz_MN1,tp_MN1,bd_MN1))+进制转换10T16(计算数字(lg_W1,qz_W1,tp_W1,bd_W1))+进制转换10T16(计算数字(lg_D1,qz_D1,tp_D1,bd_D1))+进制转换10T16(计算数字(lg_H4,qz_H4,tp_H4,bd_H4))+"__"
                                        ,"@"+period_客观角度
                                        ,g,lg_MN1,qz_MN1,tp_MN1,fz_MN1,gw_MN1,bd_MN1

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_MN1,shift_MN1), TIME_DATE|TIME_MINUTES)
                                        ,close_MN1


                                        ,lg_W1,qz_W1,tp_W1,fz_W1,gw_W1,bd_W1

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_W1,shift_W1), TIME_DATE|TIME_MINUTES)
                                        ,close_W1


                                        ,lg_D1,qz_D1,tp_D1,fz_D1,gw_D1,bd_D1

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_D1,shift_D1), TIME_DATE|TIME_MINUTES)
                                        ,close_D1


                                        ,lg_H4,qz_H4,tp_H4,fz_H4,gw_H4,bd_H4

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_H4,shift_H4), TIME_DATE|TIME_MINUTES)
                                        ,close_H4




                                       );//
                             }
                             */
                           if(period_客观角度==1440)
                             {
                              FileWrite(handle
                                       ,Symbol_0,TimeToStr(iTime(Symbol_0,PERIOD_D1,shift_D1), TIME_DATE|TIME_MINUTES),TimeDayOfWeek(iTime(Symbol_0,PERIOD_D1,shift_D1))
                                        ,"@"+period_客观角度
                                        ,open_D1,high_D1,low_D1,close_D1
                                        ,计算数字(lg_MN1,qz_MN1,tp_MN1,bd_MN1),计算数字(lg_W1,qz_W1,tp_W1,bd_W1),计算数字(lg_D1,qz_D1,tp_D1,bd_D1)
                              





                                       );//
                             }

                           if((period_客观角度==10080)||(period_客观角度==43200))
                             {
                              FileWrite(handle
                                        , Symbol_0,进制转换10T16(计算数字(lg_MN1,qz_MN1,tp_MN1,bd_MN1))+进制转换10T16(计算数字(lg_W1,qz_W1,tp_W1,bd_W1))+进制转换10T16(计算数字(lg_D1,qz_D1,tp_D1,bd_D1))+"__"
                                        ,"@"+period_客观角度
                                        ,g,lg_MN1,qz_MN1,tp_MN1,fz_MN1,gw_MN1,bd_MN1

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_MN1,shift_MN1), TIME_DATE|TIME_MINUTES)
                                        ,close_MN1


                                        ,lg_W1,qz_W1,tp_W1,fz_W1,gw_W1,bd_W1

                                        ,TimeToStr(iTime(Symbol_0,PERIOD_W1,shift_W1), TIME_DATE|TIME_MINUTES)
                                        ,close_W1
                                       );//
                             }
                           Sleep(2);
                          }
                       }
                    }
                 }
            FileClose(handle);
           }
         lastTime = currentTime;
         return;
        }
  }
  

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
//return(0);
//}
//+------------------------------------------------------------------+
//------------------------------
string CalcKBW(string Instr,int TF)
  {

   string kbw="他";
//Color_KBW=NeutralColor_KBW;
   double bbw0=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",0,0);//
   double bbw1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",1,0);//
   double bbw2=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",2,0);//
   double bbw3=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",3,0);//

   double bbw0_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",0,1);//
   double bbw1_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",1,1);//
   double bbw2_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",2,1);//
   double bbw3_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",3,1);//

   if(bbw2<=bbw3)

     {
      kbw="双靓";
     }
   else
      if((bbw2>bbw2_1) && (bbw1>bbw1_1) &&(bbw1>=bbw2)&& ((bbw1>=bbw3) || (bbw2>=bbw3)))
        {
         kbw="夏";

        }
      else
         if(((bbw0>bbw0_1)  && (bbw1>bbw1_1)) || ((bbw0>bbw0_1)  && (bbw3>bbw3_1))  || ((bbw0>bbw0_1)  && (bbw2>bbw2_1))|| ((bbw2>bbw2_1) && (bbw1>bbw1_1))|| ((bbw3>bbw3_1) && (bbw1>bbw1_1))|| ((bbw2>bbw2_1) && (bbw3>bbw3_1)))
           {

            if((bbw1>bbw2)&&(bbw1>=bbw3)&&(bbw2>=bbw3)&& (bbw1>=bbw1_1) && (bbw2>=bbw2_1))
              {
               kbw="夏";
              }

            else
               if(((bbw0>=bbw0_1) && (bbw2>=bbw2_1) && (bbw1>=bbw1_1))&& (bbw1<bbw3))

                 {
                  kbw="立春";

                 }
               else
                  if((bbw2>bbw2_1) && (bbw1>bbw1_1) &&(bbw1<bbw2)&& ((bbw1>=bbw3) || (bbw2>bbw3)))

                    {
                     kbw="春";
                    }

           }


         else
           {
            kbw="其他";
           }
   return (kbw);
  }
//----------------------------
string CalcLMT(string Instr,int TF)
  {
   string q;
   double lmt4=iCustom(Instr,TF,"流氓兔K神V3",4,0);//方向
//0.00001    -0.00001
   if(lmt4==0.00001)
     {
      q="多";

     }
   if(lmt4==-0.00001)
     {
      q="空";
     }
   return(q);
  }
//---------------
string CalcSR(string Instr,int TF)
  {

   double c0=iClose(Instr,TF,0);
   double c1=iClose(Instr,TF,1);
   double c2=iClose(Instr,TF,2);
   string sr="人";;
// Color_SR=NeutralColor_SR;

   double S0=iCustom(Instr,TF,"SR_MTF_Eli_2",TF,TF,TF,TF,0,0);//down
   double R0=iCustom(Instr,TF,"SR_MTF_Eli_2",TF,TF,TF,TF,1,0);//up

   if(c0>R0)
     {
      sr="天";
     }
   else
      if(c0<S0)
        {
         sr="地";
        }
   return (sr);
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
string CalcATR(string Instr,int TF)
  {
   string Direction="0";
   double ATRUP0=iCustom(Instr,TF,"ATR吊灯止损",0,0);
   double ATRUP1=iCustom(Instr,TF,"ATR吊灯止损",0,1);
   double ATRUP2=iCustom(Instr,TF,"ATR吊灯止损",0,2);
   double ATRDW0=iCustom(Instr,TF,"ATR吊灯止损",1,0);
   double ATRDW1=iCustom(Instr,TF,"ATR吊灯止损",1,1);
   double ATRDW2=iCustom(Instr,TF,"ATR吊灯止损",1,2);


   if(ATRUP0!=EMPTY_VALUE && ATRUP1!=EMPTY_VALUE)
     {
      Direction="多";

     }
   else
      if(ATRDW0!=EMPTY_VALUE && ATRDW1!=EMPTY_VALUE)
        {
         Direction="空";
        }
      else
         if(ATRUP1!=EMPTY_VALUE &&iClose(Instr,TF,1) <ATRUP1)
           {

            Direction="交";

           }
         else
            if(ATRDW1!=EMPTY_VALUE &&iClose(Instr,TF,1)>ATRDW1)
              {

               Direction="交";

              }
            else
               if(ATRDW1!=EMPTY_VALUE && ATRDW2!=EMPTY_VALUE && ATRDW0==EMPTY_VALUE && ATRUP0!=EMPTY_VALUE)
                 {

                  Direction="易多";

                 }
               else
                  if(ATRUP1!=EMPTY_VALUE && ATRUP2!=EMPTY_VALUE && ATRUP0==EMPTY_VALUE && ATRDW0!=EMPTY_VALUE)
                    {

                     Direction="易空";

                    }

   return (Direction);
  }


string GetEye(string Instr,int TF)

  {
   string eye="-";
   if(
      (CalcATR(Instr,TF)==1||CalcATR(Instr,TF)==2)&&
      (CalcSR(Instr,TF)=="天")&&
      (CalcKBW(Instr,TF)=="夏"||CalcKBW(Instr,TF)=="春"||CalcKBW(Instr,TF)=="立春")
   )
     {
      eye="多";
      if(CalcLMT(Instr,TF)=="1")
        {
         eye="多多";
        }
     }

   else
      if(
         (CalcATR(Instr,TF)==-1||CalcATR(Instr,TF)==-2)&&
         (CalcSR(Instr,TF)=="地")&&
         (CalcKBW(Instr,TF)=="夏"||CalcKBW(Instr,TF)=="春"||CalcKBW(Instr,TF)=="立春")
      )
        {
         eye="空";
         if(CalcLMT(Instr,TF)=="-1")
           {
            eye="空空";
           }
        }
      else
         if(CalcKBW(Instr,TF)=="靚")
           {
            eye="靚";
           }

   return(eye);


  }
//+------------------------------------------------------------------+
string CalcADX(string Instr,int TF)
  {
   string Qushi="无";
   double ADX_UP0=iCustom(Instr,TF,"SqADX",1,0);
   double ADX_UP1=iCustom(Instr,TF,"SqADX",1,1);
   double ADX_UP2=iCustom(Instr,TF,"SqADX",1,2);
   double ADX_DW0=iCustom(Instr,TF,"SqADX",2,0);
   double ADX_DW1=iCustom(Instr,TF,"SqADX",2,1);
   double ADX_DW2=iCustom(Instr,TF,"SqADX",2,1);

   double ADX_0=iCustom(Instr,TF,"SqADX",0,0);
   double ADX_1=iCustom(Instr,TF,"SqADX",0,1);
   double ADX_2=iCustom(Instr,TF,"SqADX",0,1);

   if(ADX_1>=ADX_0)
     {
      if(ADX_UP1>=ADX_DW1&& ADX_UP1>=ADX_DW0)
        {
         Qushi="多";
        }
      if(ADX_UP1<ADX_DW1&&ADX_UP0<ADX_DW0)
        {
         Qushi="空";
        }
      else
        {
         Qushi="无";
        }
     }
   else
     {
      Qushi="无";
     }
   return(Qushi);
  }
//+------------------------------------------------------------------+
string CalcB50(string Instr,int TF)
  {

   string kbw="他";
//Color_KBW=NeutralColor_KBW;
   double bbw0=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",0,0);//
   double bbw1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",1,0);//
   double bbw2=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",2,0);//
   double bbw3=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",3,0);//

   double bbw0_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",0,1);//
   double bbw1_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",1,1);//
   double bbw2_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",2,1);//
   double bbw3_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",3,1);//

   if(bbw2_1>=bbw2)
     {
      kbw="阳";
     }
   else
     {
      kbw="他";
     }
   return(kbw);
  }
//+------------------------------------------------------------------+
string CalcBbfb(string Instr,int TF)
  {

   string kbw="他";
//Color_KBW=NeutralColor_KBW;
   double bbw0=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",0,0);//
   double bbw1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",1,0);//
   double bbw2=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",2,0);//
   double bbw3=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",3,0);//

   double bbw0_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",0,1);//
   double bbw1_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",1,1);//
   double bbw2_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",2,1);//
   double bbw3_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",3,1);//

   if(bbw2_1>=bbw2)
     {
      kbw="阳";
     }
   else
     {
      kbw="他";
     }
   return(kbw);
  }
//------------------------------
string CalcB50_2(string Instr,int TF)
  {

   string kbw="他";
//Color_KBW=NeutralColor_KBW;
   double bbw0=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",0,0);//
   double bbw1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",1,0);//

   double bbw2=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",2,0);//

   double bbw3=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",3,0);//

   double bbw0_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",0,1);//
   double bbw1_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",1,1);//

   double bbw2_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",2,1);//

   double bbw3_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth505",3,1);//

   if((bbw2>=bbw2_1)&&(bbw2>=bbw3))

     {
      kbw="阳";
     }
   else
      if(bbw3_1<bbw2<bbw2_1)
        {
         kbw="秋";

        }
      else
         if(bbw2_1<bbw3_1)
           {
            kbw="冬";

           }
         else
           {
            kbw="他";
           }
   return (kbw);
  }
//----------------------------
//------------------------------
string CalcADX_2(string Instr,int TF)
  {
   string ADXQ="他";

   double ADX0=iCustom(Instr,TF,"SqADX",0,0);//
   double ADX1=iCustom(Instr,TF,"SqADX",1,0);//
   double ADX2=iCustom(Instr,TF,"SqADX",2,0);//

   double ADX0q=iCustom(Instr,TF,"SqADX",0,1);//
   double ADX1q=iCustom(Instr,TF,"SqADX",1,1);//
   double ADX2q=iCustom(Instr,TF,"SqADX",2,1);//

   if(ADX0q<=ADX0)
     {
      ADXQ="趋";
     }
   else
      if(ADX0q>ADX0)
        {
         ADXQ="无";
        }
   return(ADXQ);
  }
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
string guanjianwei_hdnj(string Instr,int TF,int hsk)//使用5种位置来表示，突破  天  ，上， 地，下，中间 人
  {
   double c0=iClose(Instr,TF,hsk+0);
   double c1=iClose(Instr,TF,hsk+1);
   double c2=iClose(Instr,TF,hsk+2);
   string sr="人";;
   double S0=iCustom(Instr,TF,"SR_MTF_Eli_2",TF,TF,TF,TF,0,hsk+0);//down
   double R0=iCustom(Instr,TF,"SR_MTF_Eli_2",TF,TF,TF,TF,1,hsk+0);//up
   double S1=iCustom(Instr,TF,"SR_MTF_Eli_2",TF,TF,TF,TF,0,hsk+1);//down
   double R1=iCustom(Instr,TF,"SR_MTF_Eli_2",TF,TF,TF,TF,1,hsk+1);//up
   double S2=iCustom(Instr,TF,"SR_MTF_Eli_2",TF,TF,TF,TF,0,hsk+2);//down
   double R2=iCustom(Instr,TF,"SR_MTF_Eli_2",TF,TF,TF,TF,1,hsk+2);//up
   if(R0==0||S0==0)
     {
      sr="无";
      return(sr);
     }
   else
      if((c0>R0)&&(c1>R1)&&(S0>R0))
        {
         sr="天外天";
         return(sr);
        }
      else
         if((c0>R0)&&(c1>R1)&&(R0>0))
           {
            sr="天";
            return(sr);
           }

         else
            if((c0>R0)&&((c1<=R1)||(c2<=R2)))
              {
               sr="上";
               if(突破邮件报警==true)
                 {
                  SendMail("上破_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+Instr+" 发生上破_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES)+"_"+AccountInfoInteger(ACCOUNT_LOGIN));
                 }
               return(sr);
              }
            else
               if((c0<S0)&&(c1<S1)&&(S0>R0))
                 {
                  sr="地外地";
                  return(sr);
                 }
               else
                  if((c0<S0)&&(c1<S1))
                    {
                     sr="地";
                     return(sr);
                    }
                  else
                     if((c0<S0)&&((c1>=S1)||(c2>=S2)))
                       {
                        sr="下";
                        if(突破邮件报警==true)
                          {
                           SendMail("下破_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+Instr+" 发生下破_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES)+"_"+AccountInfoInteger(ACCOUNT_LOGIN));
                          }
                        return(sr);
                       }
                     else//||   (       (c1<R1) && ( c1>= (R2- (R2-S2)*gaodi_bfb)   )     )       )
                        if((c0<R0) && (c0>= (R1-   MathAbs(R1-S1)*gaodi_bfb)))
                          {
                           sr= "高" ;
                           return(sr);
                          }
                        else//||   (       (c1<R1) && ( c1>= (R2- (R2-S2)*gaodi_bfb)   )     )       )
                           if((c1<R1)   && (c1>= (R2-  MathAbs(R2-S2)*gaodi_bfb)))
                             {
                              sr= "高" ;
                              return(sr);
                             }
                           else
                              if((c0>S0) && (c0<= (S1+  MathAbs(R1-S1)*gaodi_bfb)))
                                {
                                 sr= "低" ;
                                 return(sr);
                                }
                              else
                                 if((c1>S1) && (c1<= (S2+  MathAbs(R2-S2)*gaodi_bfb)))
                                   {
                                    sr= "低" ;
                                    return(sr);
                                   }



                                 else
                                   {
                                    sr="人";
                                    return(sr);
                                   }
   return (sr);
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
string bodongxing_hdnj(string Instr,int TF,int hsk)//波动性分为4中 ，阳，秋，冬，他
  {
   string kbw="他";
   double bbw0=iCustom(Instr,TF,"ACD Kaufman Bandwidth616",0,hsk+0);//
   double bbw1=iCustom(Instr,TF,"ACD Kaufman Bandwidth616",1,hsk+0);//
   double bbw2=iCustom(Instr,TF,"ACD Kaufman Bandwidth616",2,hsk+0);//
   double bbw3=iCustom(Instr,TF,"ACD Kaufman Bandwidth616",3,hsk+0);//

   double bbw0_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth616",0,hsk+1);//
   double bbw1_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth616",1,hsk+1);//
   double bbw2_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth616",2,hsk+1);//
   double bbw3_1=iCustom(Instr,TF,"ACD Kaufman Bandwidth616",3,hsk+1);//

   double bbw0_2=iCustom(Instr,TF,"ACD Kaufman Bandwidth616",0,hsk+2);//
   double bbw1_2=iCustom(Instr,TF,"ACD Kaufman Bandwidth616",1,hsk+2);//
   double bbw2_2=iCustom(Instr,TF,"ACD Kaufman Bandwidth616",2,hsk+2);//
   double bbw3_2=iCustom(Instr,TF,"ACD Kaufman Bandwidth616",3,hsk+2);//

   if(
      (bbw2_1<=bbw3_1)
      &&
      (iBars(Instr,TF)>(hsk+2+55))
   )
     {
      kbw="闭藏";
      if(邮件报警==true)
        {
         SendMail("双收_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+Instr+" 发生发陈波动性收缩_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES)+"_"+AccountInfoInteger(ACCOUNT_LOGIN));
        }
      return(kbw);
     }
   else
      if(((bbw2>=bbw2_1)&&(bbw1>=bbw1_1)&&(bbw1>=bbw2)&&((bbw1_1<=bbw2_1)||(bbw1_2<=bbw2_2)))&&(iBars(Instr,TF)>(hsk+2+55)))

        {
         kbw="发陈";
         if(邮件报警==true)
           {
            SendMail("发陈_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+Instr+" 发生发陈波动性变化_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES)+"_"+AccountInfoInteger(ACCOUNT_LOGIN));
           }
         return(kbw);
        }
      else
         if(((bbw2>=bbw2_1)&&(bbw1>=bbw1_1)&&(bbw1>=bbw2))&&(iBars(Instr,TF)>(hsk+2+55)))

           {
            kbw="蕃秀";
            return(kbw);
           }

         else
            if(((bbw2>=bbw2_1)&&(bbw2_1>=bbw3_1)&&(bbw2_2>=bbw3_2))&&(iBars(Instr,TF)>(hsk+2+55)))
              {
               kbw="阳";
               return(kbw);
              }
            else
               if(((bbw2<bbw2_1)&&(bbw2_2>bbw2_1))&&(iBars(Instr,TF)>(hsk+2+55)))
                 {
                  kbw="秋收";
                  return(kbw);
                 }
               else
                  if(((bbw2<=bbw2_1)&&(bbw2_2<=bbw2_1))&&(iBars(Instr,TF)>(hsk+2+55)))
                    {
                     kbw="容平";
                     return(kbw);
                    }
                  else
                    {
                     kbw="他";
                     return(kbw);
                    }
   return (kbw);
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
string qushixing_hdnj(string Instr,int TF,int hsk)//
  {
   double c0=iClose(Instr,TF,0);
   double c1=iClose(Instr,TF,1);
   double c2=iClose(Instr,TF,2);
   string sr="他";;
   double bbw0=iCustom(Instr,TF,"SqADX",0,hsk+0);//qushi
   double bbw1=iCustom(Instr,TF,"SqADX",1,hsk+0);//up
   double bbw2=iCustom(Instr,TF,"SqADX",2,hsk+0);//dwon


   double bbw0_1=iCustom(Instr,TF,"SqADX",0,hsk+1);//
   double bbw1_1=iCustom(Instr,TF,"SqADX",1,hsk+1);//
   double bbw2_1=iCustom(Instr,TF,"SqADX",2,hsk+1);//


   double bbw0_2=iCustom(Instr,TF,"SqADX",0,hsk+2);//
   double bbw1_2=iCustom(Instr,TF,"SqADX",1,hsk+2);//
   double bbw2_2=iCustom(Instr,TF,"SqADX",2,hsk+2);//

   if((bbw0<=20)  && (bbw0_1<= bbw0)&& (bbw1_1>= bbw1) && (bbw1<=20))                                     //(   (bbw0_1<= bbw1_1) && (bbw0> bbw1) )||    (  (bbw0_2<= bbw1_2) && (bbw0> bbw2)  )
     {
      sr="空藏";
      if(邮件报警==true)
        {
         SendMail("空藏_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+AccountInfoInteger(ACCOUNT_LOGIN)+"_"+Instr+" 发生ADX做空变化_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));
        }
      return(sr);

     }
   else
      if((bbw0<=20)&&(bbw0_1<= bbw0)&& (bbw2_1>= bbw2) && (bbw2<=20))                  //((bbw0_1<= bbw2_1) && (bbw0> bbw2))||((bbw0_2<= bbw2_2) && (bbw0> bbw2))
        {
         sr="多藏";
         if(邮件报警==true)
           {
            SendMail("多藏_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+AccountInfoInteger(ACCOUNT_LOGIN)+"_"+Instr+" 发生ADX做多变化_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));

           }
         return(sr);

        }
      else
         if((bbw0<=20)  && (bbw0_1> bbw0))
           {
            sr="闭藏";
            return(sr);
           }
         else
            if((bbw0<=20)&&(bbw0_1<bbw0))
              {
               sr="藏平";//观察是否有V反和双收双扩
               return(sr);
              }
            else
               if((bbw0>20)&&(bbw0_1<=20)&&(bbw1>bbw2))
                 {
                  sr="多发";
                  return(sr);
                 }
               else
                  if((bbw0>20)&&(bbw0_1<=20)&&(bbw2>bbw1))
                    {
                     sr="空发";
                     return(sr);
                    }
                  else
                     if((bbw1>bbw1_1)&&(bbw0> bbw0_1) &&(bbw0>=20) &&(bbw2< bbw2_1)&&(bbw2<=bbw1))
                       {
                        sr="多趋";
                        return(sr);
                       }
                     else
                        if((bbw0>=20)&&(bbw0>= bbw0_1)   &&(bbw1<bbw1_1)&&(bbw2> bbw2_1)&&(bbw2>= bbw1))
                          {
                           sr="空趋";
                           return(sr);
                          }
                        else
                           if((bbw0>20)&&(bbw0< bbw0_1)&&(bbw0_1<=bbw0_2))
                             {
                              sr="容平";
                              return(sr);
                             }
                           else
                             {
                              sr="他";
                              return(sr);
                             }
   return (sr);
  }
//+------------------------------------------------------------------+流氓兔K神V3
string lmt_hdnj(string Instr,int TF,int hsk)//
  {
   double c0=iClose(Instr,TF,hsk+0);
   double c1=iClose(Instr,TF,hsk+1);
   double c2=iClose(Instr,TF,hsk+2);
   string sr="他";;
   double bbw0=iCustom(Instr,TF,"流氓兔K神V2",4,hsk+0);//qushi
   double bbw1=iCustom(Instr,TF,"流氓兔K神V2",5,hsk+0);//up
   double bbw2=iCustom(Instr,TF,"流氓兔K神V2",10,hsk+0);//dwon


   double bbw0_1=iCustom(Instr,TF,"流氓兔K神V2",4,hsk+1);//
   double bbw1_1=iCustom(Instr,TF,"流氓兔K神V2",5,hsk+1);//
   double bbw2_1=iCustom(Instr,TF,"流氓兔K神V2",10,hsk+1);//


   double bbw0_2=iCustom(Instr,TF,"流氓兔K神V2",4,hsk+2);//
   double bbw1_2=iCustom(Instr,TF,"流氓兔K神V2",5,hsk+2);//
   double bbw2_2=iCustom(Instr,TF,"流氓兔K神V2",10,hsk+2);//

   if((bbw0==-1)&&(bbw0_1==-1)&&(bbw0_2==1))
     {
      sr="下";
      return(sr);
     }
   else
      if((bbw0==1)&&(bbw0_1==1)&&(bbw0_2==-1))
        {
         sr="上";
         return(sr);
        }
      else
         if((bbw0==1)&&(bbw0_1==1)&&(c0<=bbw1))
           {
            sr="低";
            return(sr);
           }
         else
            if((bbw0==1)&&(bbw0_1==1))
              {
               sr="偏多";
               return(sr);
              }
            else
               if((bbw0==-1)&&(bbw0_1==-1))
                 {
                  sr="偏空";
                  return(sr);
                 }
               else
                 {
                  sr="他";
                  return(sr);
                 }
   return (sr);
  }
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+流氓兔K神V3
string tbd_hdnj(string Instr,int TF,int hsk)//
  {
   double c0=iClose(Instr,TF,hsk+0);
   double c1=iClose(Instr,TF,hsk+1);
   double c2=iClose(Instr,TF,hsk+2);
   string sr1="他";;
   double bbw0=iCustom(Instr,TF,"Bollinger bands on ATR%",0,hsk+0);//qushi
   double bbw1=iCustom(Instr,TF,"Bollinger bands on ATR%",3,hsk+0);//up
   double bbw2=iCustom(Instr,TF,"Bollinger bands on ATR%",4,hsk+0);//dwon


   double bbw0_1=iCustom(Instr,TF,"Bollinger bands on ATR%",0,hsk+1);//
   double bbw1_1=iCustom(Instr,TF,"Bollinger bands on ATR%",3,hsk+1);//
   double bbw2_1=iCustom(Instr,TF,"Bollinger bands on ATR%",4,hsk+1);//


   double bbw0_2=iCustom(Instr,TF,"Bollinger bands on ATR%",0,hsk+2);//
   double bbw1_2=iCustom(Instr,TF,"Bollinger bands on ATR%",3,hsk+2);//
   double bbw2_2=iCustom(Instr,TF,"Bollinger bands on ATR%",4,hsk+2);//


   double BLMA50_UP=iCustom(Symbol(),TF,"GLI Bollinger Bands v2.0",50,0,2,false,5,0);
   double BLMA51_UP=iCustom(Symbol(),TF,"GLI Bollinger Bands v2.0",50,0,2,false,5,1);
   double BLMA52_UP=iCustom(Symbol(),TF,"GLI Bollinger Bands v2.0",50,0,2,false,5,2);

   double BLMA60_DW=iCustom(Symbol(),TF,"GLI Bollinger Bands v2.0",50,0,2,false,6,0);
   double BLMA61_DW=iCustom(Symbol(),TF,"GLI Bollinger Bands v2.0",50,0,2,false,6,1);
   double BLMA62_DW=iCustom(Symbol(),TF,"GLI Bollinger Bands v2.0",50,0,2,false,6,2);

   if((bbw0<=bbw1))
     {
      sr1="闭藏";
      return(sr1);
     }
   else
      if((bbw0>bbw1)&&(bbw0_1<=bbw0)&&(bbw0>bbw1)&&(bbw0_1<=bbw1_1)&&(bbw0<bbw2))
        {
         sr1="臧发";
         return(sr1);
        }
      else
         if((bbw0>bbw1)&&(bbw0_1<=bbw0)&&(bbw0>bbw1)&&(bbw0<bbw2))
           {
            sr1="发陈";
            return(sr1);
           }
         else
            if((bbw0>bbw1)&&(bbw0_1<=bbw0)&&(bbw0>=bbw2))
              {
               sr1="蕃秀";
               return(sr1);
              }


            else
               if((BLMA50_UP!=EMPTY_VALUE)||(BLMA60_DW!=EMPTY_VALUE)||(BLMA51_UP!=EMPTY_VALUE)||(BLMA61_DW!=EMPTY_VALUE))
                 {
                  sr1="蕃秀";
                  return(sr1);
                 }
               /*
                           else
                              if((bbw0>bbw1)&&(bbw0_1>bbw0)&&(bbw0_1<=bbw2_1))
                                {
                                 sr="中落";
                                 return(sr);
                                }
                              else
                                 if((bbw0>bbw2)&&(bbw0_1<=bbw2_1)&&(bbw0_1<=bbw0))
                                   {
                                    sr="上变";
                                    return(sr);
                                   }
                                 else
                                    if((bbw0>=bbw2)&&(bbw0_1>bbw0))
                                      {
                                       sr="上落";
                                       return(sr);
                                      }
                                    else
                                       if((bbw0>=bbw2)&&(bbw0_1<=bbw0))
                                         {
                                          sr="上升";
                                          return(sr);
                                         }
                                 */
               else
                 {
                  sr1="他";
                  return(sr1);
                 }
   return (sr1);
  }//+------------------------------------------------------------------+
string top_hdnj(string Instr,int TF,int hsk)//
  {
   double c0=iClose(Instr,TF,hsk+0);
   double c1=iClose(Instr,TF,hsk+1);
   double c2=iClose(Instr,TF,hsk+2);
   string sr="他";;
   double bbw0=iCustom(Instr,TF,"TOPTREND",50,4,hsk+0);//up
   double bbw1=iCustom(Instr,TF,"TOPTREND",50,5,hsk+0);//dwon


   double bbw0_1=iCustom(Instr,TF,"TOPTREND",50,4,hsk+1);//
   double bbw1_1=iCustom(Instr,TF,"TOPTREND",50,5,hsk+1);//



   double bbw0_2=iCustom(Instr,TF,"TOPTREND",50,4,hsk+2);//
   double bbw1_2=iCustom(Instr,TF,"TOPTREND",50,5,hsk+2);//


   if((bbw0!=EMPTY_VALUE)  &&(bbw0_1!=EMPTY_VALUE) &&(bbw0_2==EMPTY_VALUE))
     {
      sr="多上";
      return(sr);
     }
   else
      if((bbw1!=EMPTY_VALUE)  &&(bbw1_1!=EMPTY_VALUE) &&(bbw1_2==EMPTY_VALUE))
        {
         sr="空下";//观察是否有V反和双收双扩
         return(sr);
        }
      else

         if((bbw0!=EMPTY_VALUE)  &&(bbw0_1!=EMPTY_VALUE) &&(bbw0_2!=EMPTY_VALUE))
           {
            sr="中升";
            return(sr);
           }
         else
            if((bbw1!=EMPTY_VALUE)  &&(bbw1_1!=EMPTY_VALUE) &&(bbw1_2!=EMPTY_VALUE))
              {
               sr="中降";
               return(sr);
              }

            else
              {
               sr="他";
               return(sr);
              }
   return (sr);
  }
//+------------------------------------------------------------------+
string atrstop_hdnj(string Instr,int TF,int hsk)//
  {
   double c0=iClose(Instr,TF,hsk+0);
   double c1=iClose(Instr,TF,hsk+1);
   double c2=iClose(Instr,TF,hsk+2);
   string sr="他";;
   double bbw0=iCustom(Instr,TF,"ATR吊灯止损",0,hsk+0);//qushi
   double bbw1=iCustom(Instr,TF,"ATR吊灯止损",1,hsk+0);//up
//   double bbw2=iCustom(Instr,TF,"ATR吊灯止损",4,hsk+0);//dwon


   double bbw0_1=iCustom(Instr,TF,"ATR吊灯止损",0,hsk+1);//
   double bbw1_1=iCustom(Instr,TF,"ATR吊灯止损",1,hsk+1);//
// double bbw2_1=iCustom(Instr,TF,"ATR吊灯止损",4,hsk+1);//


   double bbw0_2=iCustom(Instr,TF,"ATR吊灯止损",0,hsk+2);//
   double bbw1_2=iCustom(Instr,TF,"ATR吊灯止损",1,hsk+2);//
//  double bbw2_2=iCustom(Instr,TF,"ATR吊灯止损",4,hsk+2);//

   if((bbw0!=EMPTY_VALUE)  &&(bbw0_1!=EMPTY_VALUE) &&(bbw0_2==EMPTY_VALUE))
     {
      sr="多上";
      return(sr);
     }
   else
      if((bbw1!=EMPTY_VALUE)  &&(bbw1_1!=EMPTY_VALUE) &&(bbw1_2==EMPTY_VALUE))
        {
         sr="空下";//观察是否有V反和双收双扩
         return(sr);
        }
      else

         if((bbw0!=EMPTY_VALUE)  &&(bbw0_1!=EMPTY_VALUE) &&(bbw0_2!=EMPTY_VALUE))
           {
            sr="中升";
            return(sr);
           }
         else
            if((bbw1!=EMPTY_VALUE)  &&(bbw1_1!=EMPTY_VALUE) &&(bbw1_2!=EMPTY_VALUE))
              {
               sr="中降";
               return(sr);
              }

            else
              {
               sr="他";
               return(sr);
              }
   return (sr);
  }
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
string rsi_hdnj(string Instr,int TF,int hsk)//
  {
   double c0=iClose(Instr,TF,hsk+0);
   double c1=iClose(Instr,TF,hsk+1);
   double c2=iClose(Instr,TF,hsk+2);
   string sr="他";;
   double bbw0=iCustom(Instr,TF,"RSIOMA_v2HHLSX",0,hsk+0);//qushi
   double bbw1=iCustom(Instr,TF,"RSIOMA_v2HHLSX",5,hsk+0);//up
   double bbw2=iCustom(Instr,TF,"RSIOMA_v2HHLSX",2,hsk+0);//dwon


   double bbw0_1=iCustom(Instr,TF,"RSIOMA_v2HHLSX",0,hsk+1);//
   double bbw1_1=iCustom(Instr,TF,"RSIOMA_v2HHLSX",5,hsk+1);//
   double bbw2_1=iCustom(Instr,TF,"RSIOMA_v2HHLSX",2,hsk+1);//


   double bbw0_2=iCustom(Instr,TF,"RSIOMA_v2HHLSX",0,hsk+2);//
   double bbw1_2=iCustom(Instr,TF,"RSIOMA_v2HHLSX",5,hsk+2);//
   double bbw2_2=iCustom(Instr,TF,"RSIOMA_v2HHLSX",2,hsk+2);//

   if((bbw0<=50)  && (bbw0_1<= bbw0)&& (bbw0>= bbw1) && (bbw0_1<=bbw1_1))                                     //(   (bbw0_1<= bbw1_1) && (bbw0> bbw1) )||    (  (bbw0_2<= bbw1_2) && (bbw0> bbw2)  )
     {
      sr="低上";
      if(加油邮件报警==true)
        {
         SendMail("低上_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+AccountInfoInteger(ACCOUNT_LOGIN)+"_"+Instr+" 发生RSI低上变化_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));
        }
      return(sr);

     }
   else
      if((bbw0>=50)&&(bbw0_1>= bbw0)&& (bbw0<= bbw1) && (bbw0_1>bbw1_1))                  //((bbw0_1<= bbw2_1) && (bbw0> bbw2))||((bbw0_2<= bbw2_2) && (bbw0> bbw2))
        {
         sr="高下";
         if(加油邮件报警==true)
           {
            SendMail("高下_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+AccountInfoInteger(ACCOUNT_LOGIN)+"_"+Instr+" 发生RSI高下变化_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));

           }
         return(sr);

        }
      else
         if((bbw0>50)  && (bbw0_1<= bbw0)&& (bbw0>= bbw1) && (bbw0_1<=bbw1_1))                                     //(   (bbw0_1<= bbw1_1) && (bbw0> bbw1) )||    (  (bbw0_2<= bbw1_2) && (bbw0> bbw2)  )
           {
            sr="高上";
            if(邮件报警==true)
              {
               SendMail("高上_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+AccountInfoInteger(ACCOUNT_LOGIN)+"_"+Instr+" 发生RSI高上变化_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));
              }
            return(sr);

           }
         else
            if((bbw0<50)&&(bbw0_1>= bbw0)&& (bbw0<= bbw1) && (bbw0_1>bbw1_1))                  //((bbw0_1<= bbw2_1) && (bbw0> bbw2))||((bbw0_2<= bbw2_2) && (bbw0> bbw2))
              {
               sr="低下";
               if(邮件报警==true)
                 {
                  SendMail("低下_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+AccountInfoInteger(ACCOUNT_LOGIN)+"_"+Instr+" 发生RSI低下变化_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));

                 }
               return(sr);

              }
            else
               if((bbw0>50)&&(bbw0_1<=bbw0)&&(bbw1_1<=bbw1))
                 {
                  sr="中升";
                  return(sr);
                 }
               else
                  if((bbw0<=50)&&(bbw0_1<=bbw0)&&(bbw1_1<=bbw1))
                    {
                     sr="初升";
                     return(sr);
                    }
                  else
                     if((bbw0>50)&&(bbw0_1>=bbw0)&&(bbw1_1>=bbw1))
                       {
                        sr="初降";
                        return(sr);
                       }
                     else
                        if((bbw0<50)&&(bbw0_1>=bbw0)&&(bbw1_1>=bbw1))
                          {
                           sr="中降";
                           return(sr);
                          }
                        else
                          {
                           sr="他";
                           return(sr);
                          }
   return (sr);
  }
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
string blp_hdnj(string Instr,int TF,int hsk)//
  {
   double c0=iClose(Instr,TF,hsk+0);
   double c1=iClose(Instr,TF,hsk+1);
   double c2=iClose(Instr,TF,hsk+2);
   string sr="他";;
   double bbw0=iCustom(Instr,TF,"Bollinger Bands %bea",0,hsk+0);//qushi
   double bbw1=iCustom(Instr,TF,"Bollinger Bands %bea",1,hsk+0);//up
// double bbw2=iCustom(Instr,TF,"Bollinger Bands %bea",2,hsk+0);//dwon


   double bbw0_1=iCustom(Instr,TF,"Bollinger Bands %bea",0,hsk+1);//
   double bbw1_1=iCustom(Instr,TF,"Bollinger Bands %bea",1,hsk+1);//
// double bbw2_1=iCustom(Instr,TF,"Bollinger Bands %bea",2,hsk+1);//


   double bbw0_2=iCustom(Instr,TF,"Bollinger Bands %bea",0,hsk+2);//
   double bbw1_2=iCustom(Instr,TF,"Bollinger Bands %bea",1,hsk+2);//
// double bbw2_2=iCustom(Instr,TF,"Bollinger Bands %bea",2,hsk+2);//
   if((bbw1_1<=0)  && (bbw0_1<= 0) &&
      (iBars(Instr,TF)>(hsk+55))
     )                                     //(   (bbw0_1<= bbw1_1) && (bbw0> bbw1) )||    (  (bbw0_2<= bbw1_2) && (bbw0> bbw2)  )
     {
      sr="地地";
      if(邮件报警==true)
        {
         SendMail("地地_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+AccountInfoInteger(ACCOUNT_LOGIN)+"_"+Instr+" 发生BLP地地_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));
        }
      return(sr);

     }

   else
      if((bbw1_1>1)&&(bbw0_1>1)&&
         (iBars(Instr,TF)>(hsk+55)))                  //((bbw0_1<= bbw2_1) && (bbw0> bbw2))||((bbw0_2<= bbw2_2) && (bbw0> bbw2))
        {
         sr="天天";
         if(邮件报警==true)
           {
            SendMail("天天_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+AccountInfoInteger(ACCOUNT_LOGIN)+"_"+Instr+" 发生BLIP天天变化_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));

           }
         return(sr);

        }

      else
         if((bbw0>0.85) && (bbw1>0.85) && (bbw1<1)&&
            (iBars(Instr,TF)>(hsk+55)))                                     //(   (bbw0_1<= bbw1_1) && (bbw0> bbw1) )||    (  (bbw0_2<= bbw1_2) && (bbw0> bbw2)  )
           {
            sr="高高";
            if(邮件报警==true)
              {
               SendMail("高高_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+AccountInfoInteger(ACCOUNT_LOGIN)+"_"+Instr+" 发生BLP高上变化_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));
              }
            return(sr);

           }
         else
            if((bbw0<0.15)&& (bbw1< 0.15) && (bbw1>=0)&&
               (iBars(Instr,TF)>(hsk+55)))                  //((bbw0_1<= bbw2_1) && (bbw0> bbw2))||((bbw0_2<= bbw2_2) && (bbw0> bbw2))
              {
               sr="低低";
               if(邮件报警==true)
                 {
                  SendMail("低低_"+StringTF(TF)+"_"+Instr+"_Date_"+TimeToStr(Time[0], TIME_DATE)+"_Time_"+IntegerToString(TimeHour(TimeLocal()))+"点",StringTF(TF)+"_"+AccountInfoInteger(ACCOUNT_LOGIN)+"_"+Instr+" 发生BLP低低变化_ "+TimeToString(TimeLocal(),TIME_DATE|TIME_MINUTES));

                 }
               return(sr);

              }
            else
              {
               sr="他";
               return(sr);
              }
   return (sr);
  }
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
string String单品(int 品种单测)
  {
   if(品种单测==1)
      return ("AUDUSD");
   if(品种单测==2)
      return ("GBPUSD");
   if(品种单测==3)
      return ("NZDUSD");
   if(品种单测==4)
      return ("USDCAD");

   if(品种单测==5)
      return ("USDJPY");
   if(品种单测==6)
      return ("EURUSD");
   if(品种单测==7)
      return ("EURJPY");
   if(品种单测==8)
      return ("GBPJPY");

   if(品种单测==9)
      return ("XAUUSD");
   if(品种单测==10)
      return ("XAGUSD");
   if(品种单测==11)
      return ("WT");
   if(品种单测==12)
      return ("HSI");


   if(品种单测==13)
      return ("XU");
   if(品种单测==14)
      return ("FDAX");
   if(品种单测==15)
      return ("NQ");
   if(品种单测==16)
      return ("YM");

   if(品种单测==17)
      return ("ES");
   if(品种单测==18)
      return ("NKD");


   if(品种单测==19)
      return ("HG");
   if(品种单测==20)
      return ("PA");
   if(品种单测==21)
      return ("PL");
   if(品种单测==22)
      return ("HO");


   if(品种单测==23)
      return ("NG");
   if(品种单测==24)
      return ("SOYBEAN");
   if(品种单测==25)
      return ("CORN");
   if(品种单测==26)
      return ("COCOA");

   if(品种单测==27)
      return ("SUGAR");
   if(品种单测==28)
      return ("WHEAT");

   if(品种单测==29)
      return ("COFFEE");

   if(品种单测==30)
      return ("FCE");

   if(品种单测==31)
      return ("Russia50");

   if(品种单测==32)
      return ("BIDU");
   else
      if(品种单测==133)
         return (_Symbol);
      else
         if(品种单测==136)
            return (synbol_ok);

   return ("");
  }
//+------------------------------------------------------------------+
int 计算数字(string lg1,string qz1,string tp1,string bd1)
  {
   int 计算结果=0;


   if(lg1=="无")
      计算结果=0*8;
   else
      if((StringFind(qz1,"多",1)!=-1)||(StringFind(tp1,"天",1)!=-1))
        {计算结果=计算结果+1*8;}
      else
         if((StringFind(qz1,"空",1)!=-1)||(StringFind(tp1,"地",1)!=-1))
           {计算结果=计算结果-1*8;}
         else
           {
            计算结果=计算结果+1*8;
           }
   if(qz1=="无")
      计算结果=计算结果+0*4;
   else
      if(StringFind(qz1,"多",1)!=-1)
        {计算结果=计算结果+1*4;}
      else
         if(StringFind(qz1,"空",1)!=-1)
           {计算结果=计算结果-1*4;}
   if(tp1=="无")
      计算结果=计算结果+0*2;
   else
      if(StringFind(tp1,"天",1)!=-1)
        {计算结果=计算结果+1*2;}
      else
         if(StringFind(tp1,"地",1)!=-1)
           {计算结果=计算结果-1*2;}
   if(bd1=="无")
      计算结果=计算结果+0*1;
   else
      if((StringFind(qz1,"多",1)!=-1)||(StringFind(tp1,"天",1)!=-1))
        {计算结果=计算结果+1*1;}
      else
         if((StringFind(qz1,"空",1)!=-1)||(StringFind(tp1,"地",1)!=-1))
           {计算结果=计算结果-1*1;}
         else
           {
            计算结果=计算结果+1*1;
           }
   return(计算结果);
  }
//+------------------------------------------------------------------+
string 进制转换10T16(int dd)
  {
   string r="";
   switch(dd)
     {
      case 0:
         r="0";
         break;
      case 1:
         r="1";
         break;
      case 2:
         r="2";
         break;
      case 3:
         r="3";
         break;
      case 4:
         r="4";
         break;
      case 5:
         r="5";
         break;
      case 6:
         r="6";
         break;
      case 7:
         r="7";
         break;
      case 8:
         r="8";
         break;
      case 9:
         r="9";
         break;
      case 10:
         r="A";
         break;
      case 11:
         r="B";
         break;
      case 12:
         r="C";
         break;
      case 13:
         r="D";
         break;
      case 14:
         r="E";
         break;
      case 15:
         r="F";
         break;
      case -1:
         r="-1";
         break;
      case -2:
         r="-2";
         break;
      case -3:
         r="-3";
         break;
      case -4:
         r="-4";
         break;
      case -5:
         r="-5";
         break;
      case -6:
         r="-6";
         break;
      case -7:
         r="-7";
         break;
      case -8:
         r="-8";
         break;
      case -9:
         r="-9";
         break;
      case -10:
         r="-A";
         break;
      case -11:
         r="-B";
         break;
      case -12:
         r="-C";
         break;
      case -13:
         r="-D";
         break;
      case -14:
         r="-E";
         break;
      case -15:
         r="-F";
         break;
     }
   return(r);
  }
//+------------------------------------------------------------------+
//|                                                                  |
int 进制转换16T10(string r)
  {
   int dd=0;
   if(r=="0")
      dd=0;
   else
      if(r=="1")
        {  dd=1;}
      else
         if(r=="2")
           { dd=2;}
         else
            if(r=="3")
              { dd=3;}
            else
               if(r=="4")
                 {dd=4;}
               else
                  if(r=="5")
                    { dd=5;}
                  else
                     if(r=="6")
                        dd=6;
                     else
                        if(r=="7")
                           dd=7;
                        else
                           if(r=="8")
                              dd=8;
                           else
                              if(r=="9")
                                 dd=9;
                              else
                                 if(r=="A")
                                    dd=10;
                                 else
                                    if(r=="B")
                                       dd=11;
                                    else
                                       if(r=="C")
                                          dd=12;
                                       else
                                          if(r=="D")
                                             dd=13;
                                          else
                                             if(r=="E")
                                                dd=14;
                                             else
                                                if(r=="F")
                                                   dd=15;
   return(dd);
  }

//+------------------------------------------------------------------+
string StringTF(int TF)
  {
   if(TF==1)
      return ("M1");
   if(TF==5)
      return ("M5");
   if(TF==15)
      return ("M15");
   if(TF==30)
      return ("M30");
   if(TF==60)
      return ("H1");
   if(TF==240)
      return ("H4");
   if(TF==1440)
      return ("D1");
   if(TF==10080)
      return ("W1");
   if(TF==43200)
      return ("MN");
   return ("");
  }
//+------------------------------------------------------------------+
int IntTF(string TF)
  {
   if(TF=="M1")
      return (1);
   if(TF=="M5")
      return (5);
   if(TF=="M15")
      return (15);
   if(TF=="M30")
      return (30);
   if(TF=="H1")
      return (60);
   if(TF=="H4")
      return (240);
   if(TF=="D1")
      return (1440);
   if(TF=="W1")
      return (10080);
   if(TF=="MN1")
      return (43200);
   return (0);
  }
//+------------------------------------------------------------------+
int 周期规范含当前周期(int f)
  {

   if(f!=0)
     {
      return(f);
     }
   else
      if(f==0)
        {
         if(Period()==1)
           {

            return(1);
           }
         else
            if(Period()==5)
              {
               return(5);
              }
            else
               if(Period()==15)
                 {
                  return(15);
                 }
               else
                  if(Period()==30)
                    {
                     return(30);
                    }
                  else
                     if(Period()==60)
                       {
                        return(60);
                       }
                     else
                        if(Period()==240)
                          {
                           return(240);
                          }
                        else
                           if(Period()==1440)
                             {
                              return(1440);
                             }
                           else
                              if(Period()==10080)
                                {
                                 return(10080);
                                }
                              else
                                 if(Period()==43200)
                                   {
                                    return(43200);
                                   }
                                 else
                                   {
                                    return(240);
                                   }

        }
      else
        {
         return(240);
        }
  }
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
int 多周期切换(int 初始周期,int 切换层数)
  {

   int jieguo=0;
   if(
      初始周期==PERIOD_M1
      ||
      ((初始周期==0)&&(Period()==PERIOD_M1))
   )
     {
      if(切换层数==1)
        {
         jieguo=5;

        }
      else
         if(切换层数==2)
           {
            jieguo=15;

           }
         else
            if(切换层数==3)
              {
               jieguo=30;

              }
            else
               if(切换层数==4)
                 {
                  jieguo=60;

                 }
               else
                  if(切换层数==-1)
                    {
                     jieguo=1;

                    }
                  else
                     if(切换层数==-2)
                       {
                        jieguo=1;

                       }
                     else
                        if(切换层数==-3)
                          {
                           jieguo=1;

                          }
                        else
                           if(切换层数==-4)
                             {
                              jieguo=1;

                             }
                           else
                             {
                              jieguo=1;
                             }
     }
   else
      if(初始周期==5||((初始周期==0)&&(Period()==PERIOD_M5)))
        {
         if(切换层数==1)
           {
            jieguo=15;

           }
         else
            if(切换层数==2)
              {
               jieguo=30;

              }
            else
               if(切换层数==3)
                 {
                  jieguo=60;

                 }
               else
                  if(切换层数==4)
                    {
                     jieguo=240;

                    }
                  else
                     if(切换层数==-1)
                       {
                        jieguo=1;

                       }
                     else
                        if(切换层数==-2)
                          {
                           jieguo=1;

                          }
                        else
                           if(切换层数==-3)
                             {
                              jieguo=1;

                             }
                           else
                              if(切换层数==-4)
                                {
                                 jieguo=1;

                                }
                              else
                                {
                                 jieguo=5;
                                }
        }
      else
         if(初始周期==15||((初始周期==0)&&(Period()==PERIOD_M15)))
           {
            if(切换层数==1)
              {
               jieguo=30;

              }
            else
               if(切换层数==2)
                 {
                  jieguo=60;

                 }
               else
                  if(切换层数==3)
                    {
                     jieguo=240;

                    }
                  else
                     if(切换层数==4)
                       {
                        jieguo=1440;

                       }
                     else
                        if(切换层数==-1)
                          {
                           jieguo=5;

                          }
                        else
                           if(切换层数==-2)
                             {
                              jieguo=1;

                             }
                           else
                              if(切换层数==-3)
                                {
                                 jieguo=1;

                                }
                              else
                                 if(切换层数==-4)
                                   {
                                    jieguo=1;

                                   }
                                 else
                                   {
                                    jieguo=15;
                                   }

           }
         else
            if(初始周期==30||((初始周期==0)&&(Period()==PERIOD_M30)))
              {
               if(切换层数==1)
                 {
                  jieguo=60;

                 }
               else
                  if(切换层数==2)
                    {
                     jieguo=240;

                    }
                  else
                     if(切换层数==3)
                       {
                        jieguo=1440;

                       }
                     else
                        if(切换层数==4)
                          {
                           jieguo=10080;

                          }
                        else
                           if(切换层数==-1)
                             {
                              jieguo=15;

                             }
                           else
                              if(切换层数==-2)
                                {
                                 jieguo=5;

                                }
                              else
                                 if(切换层数==-3)
                                   {
                                    jieguo=1;

                                   }
                                 else
                                    if(切换层数==-4)
                                      {
                                       jieguo=1;

                                      }
                                    else
                                      {
                                       jieguo=30;
                                      }
              }
            else
               if(初始周期==60||((初始周期==0)&&(Period()==PERIOD_H1)))
                 {
                  if(切换层数==1)
                    {
                     jieguo=240;

                    }
                  else
                     if(切换层数==2)
                       {
                        jieguo=1440;

                       }
                     else
                        if(切换层数==3)
                          {
                           jieguo=10080;

                          }
                        else
                           if(切换层数==4)
                             {
                              jieguo=43200;

                             }
                           else
                              if(切换层数==-1)
                                {
                                 jieguo=30;

                                }
                              else
                                 if(切换层数==-2)
                                   {
                                    jieguo=15;

                                   }
                                 else
                                    if(切换层数==-3)
                                      {
                                       jieguo=5;

                                      }
                                    else
                                       if(切换层数==-4)
                                         {
                                          jieguo=1;

                                         }
                                       else
                                         {
                                          jieguo=60;
                                         }

                 }
               else
                  if(初始周期==240|| ((初始周期==0)&&(Period()==PERIOD_H4)))
                    {
                     if(切换层数==1)
                       {
                        jieguo=1440;

                       }
                     else
                        if(切换层数==2)
                          {
                           jieguo=10080;

                          }
                        else
                           if(切换层数==3)
                             {
                              jieguo=43200;

                             }
                           else
                              if(切换层数==4)
                                {
                                 jieguo=43200;

                                }
                              else
                                 if(切换层数==-1)
                                   {
                                    jieguo=60;

                                   }
                                 else
                                    if(切换层数==-2)
                                      {
                                       jieguo=30;

                                      }
                                    else
                                       if(切换层数==-3)
                                         {
                                          jieguo=15;

                                         }
                                       else
                                          if(切换层数==-4)
                                            {
                                             jieguo=5;

                                            }
                                          else
                                            {
                                             jieguo=240;
                                            }
                    }
                  else
                     if(初始周期==1440||((初始周期==0)&&(Period()==PERIOD_D1)))
                       {
                        if(切换层数==1)
                          {
                           jieguo=10080;

                          }
                        else
                           if(切换层数==2)
                             {
                              jieguo=43200;

                             }
                           else
                              if(切换层数==3)
                                {
                                 jieguo=43200;

                                }
                              else
                                 if(切换层数==4)
                                   {
                                    jieguo=43200;

                                   }
                                 else
                                    if(切换层数==-1)
                                      {
                                       jieguo=240;

                                      }
                                    else
                                       if(切换层数==-2)
                                         {
                                          jieguo=60;

                                         }
                                       else
                                          if(切换层数==-3)
                                            {
                                             jieguo=30;

                                            }
                                          else
                                             if(切换层数==-4)
                                               {
                                                jieguo=15;

                                               }
                                             else
                                               {
                                                jieguo=1440;
                                               }

                       }
                     else
                       {
                        jieguo=43200;
                       }
   return(jieguo);
  }
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+


//+------------------------------------------------------------------+


//+------------------------------------------------------------------+

//+------------------------------------------------------------------+

//+------------------------------------------------------------------+

//+------------------------------------------------------------------+


//+------------------------------------------------------------------+

//+------------------------------------------------------------------+

//+------------------------------------------------------------------+

//+------------------------------------------------------------------+

//+------------------------------------------------------------------+


//+------------------------------------------------------------------+
