//+------------------------------------------------------------------+
//|                                              EA_PositionGuardian.mq5 |
//|                                    改编自 MT4 版本 持仓保姆ldeyi.mq4 |
//|                            原作者: Greatshore |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//|                            功能: 持仓管理EA (止损/获利跟踪退出) |
//|                            依赖: ATR_ChandelierExit 指标 |
//+------------------------------------------------------------------+
#property copyright "Greatshore"
#property link      "greatshore@live.cn"
#property version   "2.00"

#define TP_PRICE_LINE "OG TP Price Line"
#define SL_PRICE_LINE "OG SL Price Line"

//---- 输入参数
input string  Orders="*";                    // 管理哪些订单(*=全部)
input int     TP_Method=3;                   // 获利方式: 1-Envelopes包络线+均线, 2-趋势线
input int     SL_Method=5;                   // 止损方式: 1-Envelopes, 2-趋势线, 3-SAR, 4-顾比倒数, 5-ATR
input double  ATRMultipl=2.5;               // ATR倍数
input bool    isATR周期开仓一致=true;         // ATR周期与开仓周期一致
input int     ATR周期开仓=30;                 // ATR开仓周期(分钟值)
input bool    ShowLines=true;                // 是否显示获利止损线
input color   TP_LineColor=clrAqua;          // 获利价格线颜色
input int     TP_TimeFrame=0;                // 获利价计算时间周期(0=当前)
input int     TP_MA_Period=34;               // 获利均线周期
input ENUM_MA_METHOD TP_MA_Method=MODE_EMA;  // 获利均线方法
input ENUM_APPLIED_PRICE TP_MA_Price=PRICE_CLOSE; // 获利均线计算价格
input double  TP_Env_Dev=0.2;               // 获利Envelopes偏移百分比
input int     TP_Shift=0;                    // 获利计算shift
input color   SL_LineColor=clrMagenta;       // 止损价格线颜色
input int     SL_TimeFrame=0;                // 止损价时间周期(0=当前)
input int     SL_MA_Period=20;               // 止损均线周期
input ENUM_MA_METHOD SL_MA_Method=MODE_EMA;  // 止损均线方法
input ENUM_APPLIED_PRICE SL_MA_Price=PRICE_CLOSE; // 止损均线计算价格
input double  SL_Env_Dev=0;                 // 止损Envelopes偏移
input double  SL_SARStep=0.02;              // SAR止损步长
input double  SL_SARMax=0.5;                // SAR止损最大值
input int     SL_Shift=0;                    // 止损计算shift
input int     G_H=20;                        // 顾比nH
input int     G_L=20;                        // 顾比nL

//---- 全局变量
string   TPObjName,SLObjName;
ulong    OrdersID[];
int      OrdersCount,OpType;
int      atr_handle=INVALID_HANDLE;

//+------------------------------------------------------------------+
//| EA初始化                                                          |
//+------------------------------------------------------------------+
int OnInit()
  {
   if((SL_Method==3 || SL_Method==5) && (SL_Shift<1))
      SL_Shift=1;

//---- 创建ATR吊灯止损指标句柄(SL_Method=5时使用)
   if(SL_Method==5)
     {
      atr_handle=iCustom(_Symbol,_Period,"ATR_ChandelierExit",7,0,9,ATRMultipl,false,false);
      if(atr_handle==INVALID_HANDLE)
         Print("警告: 无法加载 ATR_ChandelierExit 指标, SL_Method=5 可能无法工作。请先编译该指标。");
     }

   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| EA析构                                                            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   ObjectDelete(0,TP_PRICE_LINE);
   ObjectDelete(0,SL_PRICE_LINE);
   Comment("");

   if(atr_handle!=INVALID_HANDLE)
      IndicatorRelease(atr_handle);
  }
//+------------------------------------------------------------------+
//| 每个Tick执行                                                      |
//+------------------------------------------------------------------+
void OnTick()
  {
   double TPPrice,SLPrice;
   bool   SetTPObj=false,SetSLObj=false;
   string MesgText;

   GetOrdersID();
   if(OpType<0)
      return;

//---- 趋势线模式下需搜索图表上的趋势线对象
   if(TP_Method==2)
      SetTPObj=(ObjectFind(0,TPObjName)<0);
   if(SL_Method==2)
      SetSLObj=(ObjectFind(0,SLObjName)<0);
   if(SetTPObj || SetSLObj)
      SearchObjName(OpType,SetTPObj,SetSLObj);

//---- 计算当前获利价和止损价
   CalcPrice(TPPrice,SLPrice);

//---- 显示信息
   MesgText="S/L @ ";
   MesgText+=(SLPrice<0)?" __ ":DoubleToString(SLPrice,_Digits);
   MesgText+="   T/P @ ";
   MesgText+=(TPPrice<0)?" __ ":DoubleToString(TPPrice,_Digits);
   Comment(MesgText);

//---- 显示水平线
   if(ShowLines)
      ShowTPSLLines(TPPrice,SLPrice);

//---- 检查每个持仓是否需要止盈止损
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);

   for(int i=0; i<OrdersCount; i++)
     {
      long type=PositionGetInteger(POSITION_TYPE);

      // 空单检查: 价格>=止损价→止损, 价格<=获利价→止盈
      if(type==POSITION_TYPE_SELL)
        {
         if(SLPrice>0 && ask>=SLPrice)   ClosePosition(OrdersID[i],0);
         if(TPPrice>0 && ask<=TPPrice)   ClosePosition(OrdersID[i],1);
        }
      // 多单检查: 价格<=止损价→止损, 价格>=获利价→止盈
      else if(type==POSITION_TYPE_BUY)
        {
         if(SLPrice>0 && bid<=SLPrice)   ClosePosition(OrdersID[i],0);
         if(TPPrice>0 && bid>=TPPrice)   ClosePosition(OrdersID[i],1);
        }
     }
  }
//+------------------------------------------------------------------+
//| 获取需要管理的持仓列表                                             |
//+------------------------------------------------------------------+
void GetOrdersID()
  {
   int n=PositionsTotal();
   ArrayResize(OrdersID,n);
   bool all=(StringFind(Orders,"*")>=0);

   OpType=-1;
   OrdersCount=0;

   for(int i=n-1; i>=0; i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket))
         continue;
      if(_Symbol!=PositionGetString(POSITION_SYMBOL))
         continue;

      // 匹配规则: * = 全部, 或按订单号/注释前缀(3位/2位/2位)匹配
      string c=PositionGetString(POSITION_COMMENT);
      string c_123=StringSubstr(c,0,2);
      string c_abts=StringSubstr(c,2,2);
      string c_frtime=StringSubstr(c,5,2);

      if(!all &&
         StringFind(Orders,IntegerToString(ticket),0)<0 &&
         StringFind(Orders,c_123,0)<0 &&
         StringFind(Orders,c_abts,0)<0 &&
         StringFind(Orders,c_frtime,0)<0)
         continue;

      long o=PositionGetInteger(POSITION_TYPE);
      if(o>=2) continue; // 跳过挂单

      // 确保所有持仓方向一致
      if(OpType>=0 && o!=OpType)
        {OpType=-1; break;}
      OpType=(int)o;
      OrdersID[OrdersCount]=ticket;
      OrdersCount++;
     }

//---- 无持仓则清除水平线
   if(OrdersCount==0)
     {
      ObjectDelete(0,TP_PRICE_LINE);
      ObjectDelete(0,SL_PRICE_LINE);
     }
  }
//+------------------------------------------------------------------+
//| 在图表对象中寻找趋势线(作为获利/止损参考)                           |
//+------------------------------------------------------------------+
void SearchObjName(int Type,bool GetTPObj=true,bool GetSLObj=true)
  {
   int    iAbove=-1,iBelow=-1,iTP,iSL;
   double MinAbove=999999,MaxBelow=0,y1,y2;
   string ObjName;
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);

   for(int i=ObjectsTotal(0)-1; i>=0; i--)
     {
      ObjName=ObjectName(0,i);
      long ObjType=ObjectGetInteger(0,ObjName,OBJPROP_TYPE);
      switch(ObjType)
        {
         case OBJ_TREND:
         case OBJ_TRENDBYANGLE:
            y1=CalcLineValue(ObjName,0,1,(int)ObjType);
            y2=y1;
            break;
         case OBJ_CHANNEL:
            y1=CalcLineValue(ObjName,0,MODE_UPPER,(int)ObjType);
            y2=CalcLineValue(ObjName,0,MODE_LOWER,(int)ObjType);
            break;
         default: y1=-1; y2=-1;
        }

      if(y1>0 && y1<bid && y1>MaxBelow)       {MaxBelow=y1; iBelow=i;}
      else if(y2>bid && y2<MinAbove)           {MinAbove=y2; iAbove=i;}
      else
        {
         if(y1>0 && y1<MinAbove)               {MinAbove=y1; iAbove=i;}
         if(y2>MaxBelow)                       {MaxBelow=y2; iBelow=i;}
        }
     }

//---- 根据持仓方向分配TP/SL对象
   switch(Type)
     {
      case POSITION_TYPE_BUY:  iTP=iAbove; iSL=iBelow; break;
      case POSITION_TYPE_SELL: iTP=iBelow; iSL=iAbove; break;
      default:                 iTP=-1;     iSL=-1;
     }
   if(GetTPObj && iTP>=0) TPObjName=ObjectName(0,iTP);
   if(GetSLObj && iSL>=0) SLObjName=ObjectName(0,iSL);
  }
//+------------------------------------------------------------------+
//| 计算获利价和止损价 (根据Method选择)                                |
//+------------------------------------------------------------------+
void CalcPrice(double &TPPrice,double &SLPrice)
  {
   ENUM_TIMEFRAMES tf=(TP_TimeFrame==0)?PERIOD_CURRENT:IntToTimeframe(TP_TimeFrame);
   ENUM_TIMEFRAMES sl_tf=(SL_TimeFrame==0)?PERIOD_CURRENT:IntToTimeframe(SL_TimeFrame);

//========== 获利价 ==========
   TPPrice=-1;
   switch(TP_Method)
     {
      case 1: // Envelopes = MA * (1 + Dev%)
        {
         int ma_h=iMA(_Symbol,tf,TP_MA_Period,0,TP_MA_Method,TP_MA_Price);
         if(ma_h!=INVALID_HANDLE)
           {
            double ma[];
            ArraySetAsSeries(ma,true);
            if(CopyBuffer(ma_h,0,0,TP_Shift+1,ma)>=TP_Shift+1)
               TPPrice=(1+TP_Env_Dev*0.01)*ma[TP_Shift];
            IndicatorRelease(ma_h);
           }
        }
        break;
      case 2: // 趋势线
         TPPrice=CalcLineValue(TPObjName,TP_Shift,1+OpType);
         break;
     }

//========== 止损价 ==========
   SLPrice=-1;
   switch(SL_Method)
     {
      case 1: // Envelopes
        {
         int ma_h=iMA(_Symbol,sl_tf,SL_MA_Period,0,SL_MA_Method,SL_MA_Price);
         if(ma_h!=INVALID_HANDLE)
           {
            double ma[];
            ArraySetAsSeries(ma,true);
            if(CopyBuffer(ma_h,0,0,SL_Shift+1,ma)>=SL_Shift+1)
               SLPrice=(1+SL_Env_Dev*0.01)*ma[SL_Shift];
            IndicatorRelease(ma_h);
           }
        }
        break;
      case 2: // 趋势线
         SLPrice=CalcLineValue(SLObjName,SL_Shift,2-OpType);
         break;
      case 3: // SAR
        {
         int sar_h=iSAR(_Symbol,sl_tf,SL_SARStep,SL_SARMax);
         if(sar_h!=INVALID_HANDLE)
           {
            double sar[];
            ArraySetAsSeries(sar,true);
            if(CopyBuffer(sar_h,0,0,SL_Shift+1,sar)>=SL_Shift+1)
               SLPrice=sar[SL_Shift];
            IndicatorRelease(sar_h);
           }
        }
        break;
      case 4: // 顾比倒数
        {
         int gb_h=iCustom(_Symbol,sl_tf,"g顾比倒数",G_H,G_L);
         if(gb_h==INVALID_HANDLE)
           {SLPrice=-1; Print("无法加载 g顾比倒数 指标，请先编译安装");}
         else
           {
            double gb[];
            ArraySetAsSeries(gb,true);
            if(CopyBuffer(gb_h,2,0,SL_Shift+1,gb)>=SL_Shift+1)
               SLPrice=gb[SL_Shift];
            IndicatorRelease(gb_h);
           }
        }
        break;
      case 5: // ATR吊灯止损
        {
         bool period_match=!isATR周期开仓一致 ||
                          (isATR周期开仓一致 && PeriodSeconds(_Period)/60==ATR周期开仓);
         if(!period_match)
           {Alert("ATR跟踪离场与开仓周期不一致，请认真核实"); break;}

         if(atr_handle!=INVALID_HANDLE)
           {
            double atr_buf0[],atr_buf1[];
            ArraySetAsSeries(atr_buf0,true);
            ArraySetAsSeries(atr_buf1,true);
            if(CopyBuffer(atr_handle,0,0,3,atr_buf0)>=3 &&
               CopyBuffer(atr_handle,1,0,3,atr_buf1)>=3)
              {
               if(atr_buf0[1]!=EMPTY_VALUE && atr_buf1[1]==EMPTY_VALUE)
                  SLPrice=atr_buf0[1];   // 多头排列 → 多单止损
               else if(atr_buf1[1]!=EMPTY_VALUE && atr_buf0[1]==EMPTY_VALUE)
                  SLPrice=atr_buf1[1];   // 空头排列 → 空单止损
              }
           }
        }
        break;
     }
  }
//+------------------------------------------------------------------+
//| 计算图表对象(趋势线/通道)在某K线的对应价格                         |
//+------------------------------------------------------------------+
double CalcLineValue(string ObjName,int Shift,int ValueIndex=1,int ObjType=-1)
  {
   double y1,y2,delta,ret;

   if(ObjType<0 && StringLen(ObjName)>0)
      ObjType=(int)ObjectGetInteger(0,ObjName,OBJPROP_TYPE);

   switch(ObjType)
     {
      case OBJ_TREND:
      case OBJ_TRENDBYANGLE:
         ret=LineGetValueByShift(ObjName,Shift);
         break;
      case OBJ_CHANNEL:
        {
         // OBJPROP_TIME索引: 0=时间1, 1=时间2, 2=时间3
         datetime t3=(datetime)ObjectGetInteger(0,ObjName,OBJPROP_TIME,0,2);
         int i=GetBarShift(_Symbol,PERIOD_CURRENT,t3);
         delta=ObjectGetDouble(0,ObjName,OBJPROP_PRICE,0,2)-LineGetValueByShift(ObjName,i);
         y1=LineGetValueByShift(ObjName,Shift);
         y2=y1+delta;
         ret=(ValueIndex==MODE_UPPER)?MathMax(y1,y2):MathMin(y1,y2);
        }
        break;
      default: ret=-1;
     }
   return(ret);
  }
//+------------------------------------------------------------------+
//| 显示获利/止损水平线于图表                                          |
//+------------------------------------------------------------------+
void ShowTPSLLines(double TPPrice,double SLPrice)
  {
   datetime now=TimeCurrent();

   if(TPPrice<0) ObjectDelete(0,TP_PRICE_LINE);
   else
     {
      if(ObjectFind(0,TP_PRICE_LINE)<0)
        {
         ObjectCreate(0,TP_PRICE_LINE,OBJ_HLINE,0,0,TPPrice);
         ObjectSetInteger(0,TP_PRICE_LINE,OBJPROP_COLOR,TP_LineColor);
         ObjectSetInteger(0,TP_PRICE_LINE,OBJPROP_STYLE,STYLE_DASHDOTDOT);
         ObjectSetInteger(0,TP_PRICE_LINE,OBJPROP_WIDTH,1);
        }
      ObjectMove(0,TP_PRICE_LINE,0,now,TPPrice);
     }

   if(SLPrice<0) ObjectDelete(0,SL_PRICE_LINE);
   else
     {
      if(ObjectFind(0,SL_PRICE_LINE)<0)
        {
         ObjectCreate(0,SL_PRICE_LINE,OBJ_HLINE,0,0,SLPrice);
         ObjectSetInteger(0,SL_PRICE_LINE,OBJPROP_COLOR,SL_LineColor);
         ObjectSetInteger(0,SL_PRICE_LINE,OBJPROP_STYLE,STYLE_DASHDOTDOT);
         ObjectSetInteger(0,SL_PRICE_LINE,OBJPROP_WIDTH,1);
        }
      ObjectMove(0,SL_PRICE_LINE,0,now,SLPrice);
     }
  }
//+------------------------------------------------------------------+
//| 平仓指定的持仓                                                    |
//+------------------------------------------------------------------+
void ClosePosition(ulong Ticket,int type)
  {
   static string reason[2]={"止损","止盈"};
   if(!PositionSelectByTicket(Ticket))
      return;

   MqlTradeRequest req={0};
   MqlTradeResult  res={0};
   req.action=TRADE_ACTION_DEAL;
   req.symbol=_Symbol;
   req.volume=PositionGetDouble(POSITION_VOLUME);
   req.deviation=100;
   req.position=Ticket;

   if(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)
     {req.type=ORDER_TYPE_SELL; req.price=SymbolInfoDouble(_Symbol,SYMBOL_BID);}
   else
     {req.type=ORDER_TYPE_BUY; req.price=SymbolInfoDouble(_Symbol,SYMBOL_ASK);}

   if(OrderSend(req,res))
      Print("持仓 #",Ticket," ",reason[type],"平仓 @" ,DoubleToString(res.price,_Digits));
   else
      Print("持仓 #",Ticket," 平仓失败, 错误码: ",res.retcode);
  }
//+------------------------------------------------------------------+
//| 计算直线上某偏移位置的价格(线性插值)                                |
//+------------------------------------------------------------------+
double LineGetValueByShift(string ObjName,int Shift)
  {
   // OBJPROP_TIME / OBJPROP_PRICE 索引方式: OBJPROP_TIME, 0=坐标1, 1=坐标2
   datetime t1=(datetime)ObjectGetInteger(0,ObjName,OBJPROP_TIME,0,0);
   datetime t2=(datetime)ObjectGetInteger(0,ObjName,OBJPROP_TIME,0,1);

   double i1=GetBarShift(_Symbol,PERIOD_CURRENT,t1);
   double i2=GetBarShift(_Symbol,PERIOD_CURRENT,t2);
   double y1=ObjectGetDouble(0,ObjName,OBJPROP_PRICE,0,0);
   double y2=ObjectGetDouble(0,ObjName,OBJPROP_PRICE,0,1);

   // 确保i1 >= i2 (i1是较新的bar=较小的shift)
   if(i1<i2) {double ti=i1;i1=i2;i2=ti;double ty=y1;y1=y2;y2=ty;}

   if(Shift>i1)
      return((y2-y1)/(i2-i1)*(Shift-i1)+y1);
   else
      return(ObjectGetValueByShift(0,ObjName,Shift));
  }
//+------------------------------------------------------------------+
//| 获取时间的K线偏移量                                               |
//+------------------------------------------------------------------+
int GetBarShift(string symbol,ENUM_TIMEFRAMES timeframe,datetime time)
  {
   datetime now=iTime(symbol,timeframe,0);
   if(time<now+PeriodSeconds(timeframe))
      return(iBarShift(symbol,timeframe,time));
   else
      return((int)((now-time)/PeriodSeconds(timeframe)));
  }
//+------------------------------------------------------------------+
//| 整型分钟值 → ENUM_TIMEFRAMES 枚举                                 |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES IntToTimeframe(int tf)
  {
   switch(tf)
     {
      case 0:     return(PERIOD_CURRENT);
      case 1:     return(PERIOD_M1);
      case 5:     return(PERIOD_M5);
      case 15:    return(PERIOD_M15);
      case 30:    return(PERIOD_M30);
      case 60:    return(PERIOD_H1);
      case 240:   return(PERIOD_H4);
      case 1440:  return(PERIOD_D1);
      case 10080: return(PERIOD_W1);
      case 43200: return(PERIOD_MN1);
     }
   return(PERIOD_CURRENT);
  }
//+------------------------------------------------------------------+
