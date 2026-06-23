//+------------------------------------------------------------------+
//|                                              EA_GoldenFishTrader.mq5 |
//|                                    改编自 MT4 版本 金羊鱼操盘神器.mq4 |
//|                            原作者: Copyright 2017 |
//|                            改编为 MQL5 (MetaEditor 5) 语言 |
//|                            功能: 手动交易面板EA (买卖/挂单/平仓) |
//+------------------------------------------------------------------+
#property copyright "Copyright 2017, MetaQuotes Software Corp."
#property link      "https://www.mql5.com"
#property version   "1.00"

//---- 输入参数
input string 请输入验证码="";               // 验证码
input color   bgColorWB=clrWhite;          // 背景颜色
input double 本金=2000;                     // 本金
input double ztmb=3;                        // 最大资金回撤
input bool   本次专属不使用默认用本次输入值=false; // 使用手动输入值
input string StartTime="08:50";             // 开始交易时间
input string StopTime="22:45";              // 停止交易时间
input double dianzhi=18.8;                  // 点值
input double UnitMAXSizing=0.8;             // 最大手数
input double UnitMINSizing=0.01;            // 最小手数
input int    accountNum=5542002;             // 允许的实盘账号

//---- 全局变量
bool   isRight=false;                       // 面板在右边
bool   isMT4Show=false;                     // MT4信息显示
bool   isGAISHI1Show=false;                 // 概势1显示
bool   isGAISHI2Show=false;                 // 概势2显示
int    magic=112358;
double chicangliang=0.1;
string checkNum="123";                      // 验证码
datetime expireDemoTime=D'2029.11.07 00:00'; // 模拟盘到期日期
datetime expireLiveTime=D'2029.11.07 00:00'; // 实盘到期日期

//+------------------------------------------------------------------+
//| 初始化函数                                                        |
//+------------------------------------------------------------------+
int OnInit()
  {
//---- 根据品种智能设置参数
   if(!本次专属不使用默认用本次输入值)
      SetSmartDefaults();

   if(!IsDemoAccount() && AccountInfoInteger(ACCOUNT_LOGIN)!=accountNum)
     {
      Alert("实盘账号不匹配，请联系QQ 824878544");
      return(INIT_FAILED);
     }

   if(TimeLocal()>=expireLiveTime)
     {
      Alert("EA已过期，请联系QQ 824878544");
      return(INIT_FAILED);
     }

   drawRightPanel();
   Alert("欢迎使用金羊鱼操盘神器, 实盘请联系QQ 824878544");
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| 智能设置默认参数                                                   |
//+------------------------------------------------------------------+
void SetSmartDefaults()
  {
   magic=MathRand();

   string sym=_Symbol;

   if(sym=="HSI43")               {UnitMAXSizing=10; UnitMINSizing=1;}
   else if(sym=="NIK225")         {UnitMAXSizing=5000; UnitMINSizing=10;}
   else if(sym=="DJI30")          {UnitMAXSizing=0.5; UnitMINSizing=0.1;}
   else if(sym=="XAGUSD")         {UnitMAXSizing=10; UnitMINSizing=0.01;}

   if(sym=="AUDUSD")             {dianzhi=100000; StartTime="02:00"; StopTime="23:15";}
   else if(sym=="USDJPY")        {dianzhi=900;  StartTime="02:30"; StopTime="23:15";}
   else if(sym=="AUDJPY")        {dianzhi=684;  StartTime="02:30"; StopTime="23:15";}
   else if(sym=="EURJPY")        {dianzhi=1053; StartTime="02:30"; StopTime="23:15";}
   else if(sym=="CADJPY")        {dianzhi=1170; StartTime="02:30"; StopTime="23:15";}
   else if(sym=="GBPJPY")        {dianzhi=1160; StartTime="02:30"; StopTime="23:15";}
   else if(sym=="EURUSD"||sym=="GBPUSD") {dianzhi=100000; StartTime="08:15"; StopTime="22:15";}
   else if(sym=="USDCHF")        {dianzhi=102469; StartTime="08:15"; StopTime="22:15";}
   else if(sym=="CHINA300")      {dianzhi=43.62; StartTime="03:40"; StopTime="09:00";}
   else if(sym=="HSI43")         {dianzhi=0.128; StartTime="03:30"; StopTime="10:15";}
   else if(sym=="NIK225")        {dianzhi=0.009; StartTime="01:30"; StopTime="10:15";}
   else if(sym=="NKD")           {dianzhi=5; StartTime="01:30"; StopTime="10:15";}
   else if(sym=="XU")            {dianzhi=1; StartTime="03:00"; StopTime="15:15";}
   else if(sym=="HSI")           {dianzhi=0.65; StartTime="03:30"; StopTime="10:15";}
   else if(sym=="FCE")           {dianzhi=14; StartTime="09:20"; StopTime="22:45";}
   else if(sym=="FDAX")          {dianzhi=14; StartTime="10:20"; StopTime="22:45";}
   else if(sym=="Z")             {dianzhi=14; StartTime="10:20"; StopTime="22:45";}
   else if(sym=="FESX")          {dianzhi=24.67; StartTime="10:20"; StopTime="22:45";}
   else if(sym=="MIB")           {dianzhi=1.4; StartTime="10:20"; StopTime="22:45";}
   else if(sym=="DJI30")         {dianzhi=1; StartTime="16:50"; StopTime="22:00";}
   else if(sym=="ES")            {dianzhi=50; StartTime="16:50"; StopTime="22:00";}
   else if(sym=="YM")            {dianzhi=10; StartTime="16:50"; StopTime="22:00";}
   else if(sym=="NQ")            {dianzhi=20; StartTime="16:50"; StopTime="22:00";}
   else if(sym=="USDX")          {dianzhi=100; StartTime="15:20"; StopTime="22:15";}
   else if(sym=="XAUUSD")        {dianzhi=100; StartTime="15:40"; StopTime="22:15";}
   else if(sym=="XAGUSD")        {dianzhi=5000; StartTime="15:40"; StopTime="22:15";}
   else if(sym=="USDCAD")        {dianzhi=80000; StartTime="15:50"; StopTime="22:15";}
   else if(sym=="WT")            {dianzhi=1000; StartTime="15:50"; StopTime="22:15";}
   else if(sym=="DAI"||sym=="DBK"||sym=="BMW"||sym=="VOW"||sym=="BAYN"||sym=="ADS"||sym=="ENI")
                                  {dianzhi=120; StartTime="10:20"; StopTime="18:15";}
  }
//+------------------------------------------------------------------+
//| 析构函数                                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) { ObjectsDeleteAll(0,0,-1); }
//+------------------------------------------------------------------+
//| 每个Tick                                                          |
//+------------------------------------------------------------------+
void OnTick()
  {
   double moveStopPoint=StringToDouble(ObjectGetString(0,"move_stop_num",OBJPROP_TEXT));
   if(moveStopPoint>0)
      moveStop();
  }
//+------------------------------------------------------------------+
//| 图表事件处理（按钮点击）                                            |
//+------------------------------------------------------------------+
void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam)
  {
   if(id!=CHARTEVENT_OBJECT_CLICK) return;

   if("left_up"==sparam)           { if(isRight) drawLeftPanel(); }
   else if("right_up"==sparam)     { if(!isRight) drawRightPanel(); }
   else if("hide_button"==sparam)  { ObjectsDeleteAll(0,0,-1); drawButton("show_button","显示",clrDeepSkyBlue,isRight?57:15,15,42); }
   else if("show_button"==sparam)  { if(isRight) drawRightPanel(); else drawLeftPanel(); }
   else if("mt4_info"==sparam)     { isMT4Show=!isMT4Show; if(isMT4Show) showMT4Info(); else hideMT4Info(); }
   else if("mt4_bg"==sparam)       { hideMT4Info(); }
   else if("gaishi1_info"==sparam) { isGAISHI1Show=!isGAISHI1Show; if(isGAISHI1Show) showGAISHI1Info(); else hideGAISHI1Info(); }
   else if("gaishi1_bg"==sparam)   { hideGAISHI1Info(); }
   else if("gaishi2_info"==sparam) { isGAISHI2Show=!isGAISHI2Show; if(isGAISHI2Show) showGAISHI2Info(); else hideGAISHI2Info(); }
   else if("gaishi2_bg"==sparam)   { hideGAISHI2Info(); }
   else if("buy_act"==sparam)
     {
      double lots=StringToDouble(ObjectGetString(0,"lots_num",OBJPROP_TEXT));
      int sun=(int)StringToInteger(ObjectGetString(0,"stop_num",OBJPROP_TEXT));
      int ying=(int)StringToInteger(ObjectGetString(0,"profit_num",OBJPROP_TEXT));
      int hua=(int)StringToInteger(ObjectGetString(0,"move_point_num",OBJPROP_TEXT));
      orderBuy(lots,sun,ying,hua,_Symbol+"BUY");
     }
   else if("sell_act"==sparam)
     {
      double lots=StringToDouble(ObjectGetString(0,"lots_num",OBJPROP_TEXT));
      int sun=(int)StringToInteger(ObjectGetString(0,"stop_num",OBJPROP_TEXT));
      int ying=(int)StringToInteger(ObjectGetString(0,"profit_num",OBJPROP_TEXT));
      int hua=(int)StringToInteger(ObjectGetString(0,"move_point_num",OBJPROP_TEXT));
      orderSell(lots,sun,ying,hua,_Symbol+"SELL");
     }
   else if("pend_buy_name"==sparam)
     {
      double lots=StringToDouble(ObjectGetString(0,"lots_num",OBJPROP_TEXT));
      int sun=(int)StringToInteger(ObjectGetString(0,"stop_num",OBJPROP_TEXT));
      int ying=(int)StringToInteger(ObjectGetString(0,"profit_num",OBJPROP_TEXT));
      int hua=(int)StringToInteger(ObjectGetString(0,"move_point_num",OBJPROP_TEXT));
      double orderPrice=StringToDouble(ObjectGetString(0,"pend_buy_num",OBJPROP_TEXT));
      guaBuy(lots,orderPrice,sun,ying,hua,_Symbol+"BUY");
     }
   else if("pend_sell_name"==sparam)
     {
      double lots=StringToDouble(ObjectGetString(0,"lots_num",OBJPROP_TEXT));
      int sun=(int)StringToInteger(ObjectGetString(0,"stop_num",OBJPROP_TEXT));
      int ying=(int)StringToInteger(ObjectGetString(0,"profit_num",OBJPROP_TEXT));
      int hua=(int)StringToInteger(ObjectGetString(0,"move_point_num",OBJPROP_TEXT));
      double orderPrice=StringToDouble(ObjectGetString(0,"pend_sell_num",OBJPROP_TEXT));
      guaSell(lots,orderPrice,sun,ying,hua,_Symbol+"SELL");
     }
   else if("del_pend_order"==sparam) { deleteGua(); }
   else if("close_all"==sparam)
     { int hua=(int)StringToInteger(ObjectGetString(0,"move_point_num",OBJPROP_TEXT)); closeAll(hua); }
   else if("close_p_buy"==sparam)
     { int hua=(int)StringToInteger(ObjectGetString(0,"move_point_num",OBJPROP_TEXT)); closeBuyProfit(hua); }
   else if("close_p_sell"==sparam)
     { int hua=(int)StringToInteger(ObjectGetString(0,"move_point_num",OBJPROP_TEXT)); closeSellProfit(hua); }
   else if("close_buy"==sparam)
     { int hua=(int)StringToInteger(ObjectGetString(0,"move_point_num",OBJPROP_TEXT)); closeAllBuy(hua); }
   else if("close_sell"==sparam)
     { int hua=(int)StringToInteger(ObjectGetString(0,"move_point_num",OBJPROP_TEXT)); closeAllSell(hua); }
   else if("clock_order"==sparam) { clockOrder(); }
   else if("revers_order"==sparam) { reversOrder(); }
  }
//+------------------------------------------------------------------+
//| 画左边面板                                                        |
//+------------------------------------------------------------------+
void drawLeftPanel()
  {
   isRight=false;
   ObjectsDeleteAll(0,0,-1);

   drawButton("left_up","左上",clrDeepSkyBlue,15,15,42);
   drawButton("right_up","右上",clrDeepSkyBlue,62,15,42);
   drawButton("hide_button","隐藏",clrDeepSkyBlue,109,15,42);
   drawButton("mt4_info","MT4信息",clrDeepSkyBlue,15,42,135);
   drawButton("gaishi1_info","概势1",clrDeepSkyBlue,15,69,135);
   drawButton("gaishi2_info","概势2",clrDeepSkyBlue,15,96,135);

   drawButton("profit_name","止赢点数",clrDarkGray,15,123,65);
   drawEditText("profit_num","0",clrDarkGray,85,123);
   drawButton("move_point","最大滑点",clrDarkGray,15,150,65);
   drawEditText("move_point_num","100",clrDarkGray,85,150);

   drawButton("buy_act","买入/Buy",clrRed,15,177,65);
   drawButton("sell_act","卖出/Sell",clrLime,85,177,65);

   drawButton("pend_buy_name","挂单买入",clrRed,15,204,65);
   drawEditText("pend_buy_num","0",clrDarkGray,85,204);
   drawButton("pend_sell_name","挂单卖出",clrLime,15,231,65);
   drawEditText("pend_sell_num","0",clrDarkGray,85,231);

   drawButton("move_stop","移动止损",clrDarkGray,15,258,65);
   drawEditText("move_stop_num","0",clrDarkGray,85,258);

   drawButton("del_pend_order","删除挂单",clrDeepSkyBlue,15,285,135);
   drawButton("close_all","全部平仓",clrDeepSkyBlue,15,312,135);
   drawButton("close_p_buy","平多赢利",clrRed,15,339,65);
   drawButton("close_p_sell","平空赢利",clrLime,85,339,65);
   drawButton("close_buy","全平Buy",clrDeepSkyBlue,15,366,65);
   drawButton("close_sell","全平Sell",clrDeepSkyBlue,85,366,65);
   drawButton("clock_order","一键锁仓",clrCornflowerBlue,15,393,65);
   drawButton("revers_order","一键反向",clrCornflowerBlue,85,393,65);

   drawButton("lots_name","手 数",clrDarkGray,15,420,65);
   drawEditText("lots_num","0.1",clrDarkGray,85,420);
   drawButton("stop_name","止损点数",clrDarkGray,15,447,65);
   drawEditText("stop_num","0",clrDarkGray,85,447);
  }
//+------------------------------------------------------------------+
//| 画右边面板                                                        |
//+------------------------------------------------------------------+
void drawRightPanel()
  {
   isRight=true;
   ObjectsDeleteAll(0,0,-1);

   drawButton("left_up","左上",clrDeepSkyBlue,150,15,42);
   drawButton("right_up","右上",clrDeepSkyBlue,103,15,42);
   drawButton("hide_button","隐藏",clrDeepSkyBlue,56,15,42);
   drawButton("mt4_info","MT4信息",clrDeepSkyBlue,150,42,135);
   drawButton("gaishi1_info","概势1",clrDeepSkyBlue,150,69,135);
   drawButton("gaishi2_info","概势2",clrDeepSkyBlue,150,96,135);

   drawButton("profit_name","止赢点数",clrDarkGray,150,123,65);
   drawEditText("profit_num","0",clrDarkGray,80,123);
   drawButton("move_point","最大滑点",clrDarkGray,150,150,65);
   drawEditText("move_point_num","100",clrDarkGray,80,150);

   drawButton("buy_act","买入/Buy",clrRed,150,177,65);
   drawButton("sell_act","卖出/Sell",clrLime,80,177,65);

   drawButton("pend_buy_name","挂单买入",clrRed,150,204,65);
   drawEditText("pend_buy_num","0",clrDarkGray,80,204);
   drawButton("pend_sell_name","挂单卖出",clrLime,150,231,65);
   drawEditText("pend_sell_num","0",clrDarkGray,80,231);

   drawButton("move_stop","移动止损",clrDarkGray,150,258,65);
   drawEditText("move_stop_num","0",clrDarkGray,80,258);

   drawButton("del_pend_order","删除挂单",clrDeepSkyBlue,150,285,135);
   drawButton("close_all","全部平仓",clrDeepSkyBlue,150,312,135);
   drawButton("close_p_buy","平多赢利",clrRed,150,339,65);
   drawButton("close_p_sell","平空赢利",clrLime,80,339,65);
   drawButton("close_buy","全平Buy",clrDeepSkyBlue,150,366,65);
   drawButton("close_sell","全平Sell",clrDeepSkyBlue,80,366,65);
   drawButton("clock_order","一键锁仓",clrCornflowerBlue,150,393,65);
   drawButton("revers_order","一键反向",clrCornflowerBlue,80,393,65);

   drawButton("lots_name","手 数",clrDarkGray,150,420,65);
   drawEditText("lots_num","0.1",clrDarkGray,80,420);
   drawButton("stop_name","止损点数",clrDarkGray,150,447,65);
   drawEditText("stop_num","0",clrDarkGray,80,447);
  }
//+------------------------------------------------------------------+
//| 画按钮                                                            |
//+------------------------------------------------------------------+
void drawButton(string name,string text,color clr,int x,int y,int w)
  {
   if(ObjectFind(0,name)<0)
      ObjectCreate(0,name,OBJ_BUTTON,0,0,0);
   ObjectSetString(0,name,OBJPROP_TEXT,text);
   ObjectSetInteger(0,name,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,name,OBJPROP_BGCOLOR,clr);
   ObjectSetInteger(0,name,OBJPROP_XSIZE,w);
   ObjectSetInteger(0,name,OBJPROP_YSIZE,22);
   ObjectSetInteger(0,name,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,name,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,name,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,9);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
  }
//+------------------------------------------------------------------+
//| 画输入框                                                          |
//+------------------------------------------------------------------+
void drawEditText(string name,string text,color clr,int x,int y)
  {
   if(ObjectFind(0,name)<0)
      ObjectCreate(0,name,OBJ_EDIT,0,0,0);
   ObjectSetString(0,name,OBJPROP_TEXT,text);
   ObjectSetInteger(0,name,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,name,OBJPROP_BGCOLOR,clrWhite);
   ObjectSetInteger(0,name,OBJPROP_XSIZE,55);
   ObjectSetInteger(0,name,OBJPROP_YSIZE,22);
   ObjectSetInteger(0,name,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,name,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,name,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,9);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,true);
  }
//+------------------------------------------------------------------+
//| 移动止损                                                          |
//+------------------------------------------------------------------+
void moveStop()
  {
   int ying=(int)StringToInteger(ObjectGetString(0,"profit_num",OBJPROP_TEXT));
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol)
        {
         double sl=PositionGetDouble(POSITION_SL);
         double tp=PositionGetDouble(POSITION_TP);
         if(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY && tp>0)
            SendModify(ticket,sl,PositionGetDouble(POSITION_PRICE_OPEN)+ying*_Point);
         else if(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_SELL && tp>0)
            SendModify(ticket,sl,PositionGetDouble(POSITION_PRICE_OPEN)-ying*_Point);
        }
     }
  }
//+------------------------------------------------------------------+
//| 一键反向(平仓→反向开仓)                                            |
//+------------------------------------------------------------------+
void reversOrder()
  {
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol)
        {
         int sun=(int)StringToInteger(ObjectGetString(0,"stop_num",OBJPROP_TEXT));
         int ying=(int)StringToInteger(ObjectGetString(0,"profit_num",OBJPROP_TEXT));
         int hua=(int)StringToInteger(ObjectGetString(0,"move_point_num",OBJPROP_TEXT));
         double lots=PositionGetDouble(POSITION_VOLUME);
         bool isBuy=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);

         if(PositionClose(ticket))
           {
            if(isBuy) orderSell(lots,sun,ying,hua,_Symbol+"SELL");
            else      orderBuy(lots,sun,ying,hua,_Symbol+"BUY");
           }
         else Alert("反向失败: ",GetLastError());
        }
     }
  }
//+------------------------------------------------------------------+
//| 一键锁仓(不平仓，反向开仓)                                          |
//+------------------------------------------------------------------+
void clockOrder()
  {
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol)
        {
         int sun=(int)StringToInteger(ObjectGetString(0,"stop_num",OBJPROP_TEXT));
         int ying=(int)StringToInteger(ObjectGetString(0,"profit_num",OBJPROP_TEXT));
         int hua=(int)StringToInteger(ObjectGetString(0,"move_point_num",OBJPROP_TEXT));
         if(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)
            orderSell(PositionGetDouble(POSITION_VOLUME),sun,ying,hua,_Symbol+"SELL");
         else
            orderBuy(PositionGetDouble(POSITION_VOLUME),sun,ying,hua,_Symbol+"BUY");
        }
     }
  }
//+------------------------------------------------------------------+
//| 平全部空单                                                        |
//+------------------------------------------------------------------+
void closeAllSell(int movePoint)
  {
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_SELL)
        { if(!PositionClose(ticket)) Alert("平空单失败: ",GetLastError()); }
     }
  }
//+------------------------------------------------------------------+
//| 平全部多单                                                        |
//+------------------------------------------------------------------+
void closeAllBuy(int movePoint)
  {
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)
        { if(!PositionClose(ticket)) Alert("平多单失败: ",GetLastError()); }
     }
  }
//+------------------------------------------------------------------+
//| 平盈利空单                                                        |
//+------------------------------------------------------------------+
void closeSellProfit(int movePoint)
  {
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_SELL && PositionGetDouble(POSITION_PROFIT)>0)
        { if(!PositionClose(ticket)) Alert("平空单失败: ",GetLastError()); }
     }
  }
//+------------------------------------------------------------------+
//| 平盈利多单                                                        |
//+------------------------------------------------------------------+
void closeBuyProfit(int movePoint)
  {
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY && PositionGetDouble(POSITION_PROFIT)>0)
        { if(!PositionClose(ticket)) Alert("平多单失败: ",GetLastError()); }
     }
  }
//+------------------------------------------------------------------+
//| 全部平仓                                                          |
//+------------------------------------------------------------------+
void closeAll(int movePoint)
  {
   for(int i=PositionsTotal()-1; i>=0; i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol)
        { if(!PositionClose(ticket)) Alert("平仓失败: ",GetLastError()); }
     }
  }
//+------------------------------------------------------------------+
//| 删除所有挂单                                                      |
//+------------------------------------------------------------------+
void deleteGua()
  {
   for(int i=OrdersTotal()-1; i>=0; i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(OrderSelect(ticket) && OrderGetString(ORDER_SYMBOL)==_Symbol)
        {
         if(!OrderDelete(ticket)) Alert("删除挂单失败: ",GetLastError());
        }
     }
  }
//+------------------------------------------------------------------+
//| 挂空单                                                            |
//+------------------------------------------------------------------+
int guaSell(double Lots,double price,double sun,double ying,int movePoint,string comment)
  {
   MqlTradeRequest req={0};
   MqlTradeResult  res={0};
   req.action=TRADE_ACTION_PENDING;
   req.symbol=_Symbol;
   req.type=ORDER_TYPE_SELL_STOP;
   req.volume=Lots;
   req.price=price;
   req.deviation=movePoint;
   req.sl=sun>0?price+sun*_Point:0;
   req.tp=ying>0?price-ying*_Point:0;
   req.comment=comment;
   req.magic=magic;
   if(!OrderSend(req,res))
      Alert("挂空单失败: ",res.retcode);
   return((int)res.order);
  }
//+------------------------------------------------------------------+
//| 挂多单                                                            |
//+------------------------------------------------------------------+
int guaBuy(double Lots,double price,int sun,int ying,int movePoint,string comment)
  {
   MqlTradeRequest req={0};
   MqlTradeResult  res={0};
   req.action=TRADE_ACTION_PENDING;
   req.symbol=_Symbol;
   req.type=ORDER_TYPE_BUY_STOP;
   req.volume=Lots;
   req.price=price;
   req.deviation=movePoint;
   req.sl=sun>0?price-sun*_Point:0;
   req.tp=ying>0?price+ying*_Point:0;
   req.comment=comment;
   req.magic=magic;
   if(!OrderSend(req,res))
      Alert("挂多单失败: ",res.retcode);
   return((int)res.order);
  }
//+------------------------------------------------------------------+
//| 开空单                                                            |
//+------------------------------------------------------------------+
int orderSell(double Lots,int sun,int ying,int movePoint,string comment)
  {
   MqlTradeRequest req={0};
   MqlTradeResult  res={0};
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);

   req.action=TRADE_ACTION_DEAL;
   req.symbol=_Symbol;
   req.type=ORDER_TYPE_SELL;
   req.volume=Lots;
   req.price=bid;
   req.deviation=movePoint;
   req.sl=sun>0?bid+sun*_Point:0;
   req.tp=ying>0?bid-ying*_Point:0;
   req.comment=comment;
   req.magic=magic;

   if(!OrderSend(req,res))
     { Alert("下空单失败: ",res.retcode); return(-1); }
   return((int)res.order);
  }
//+------------------------------------------------------------------+
//| 开多单                                                            |
//+------------------------------------------------------------------+
int orderBuy(double Lots,int sun,int ying,int movePoint,string comment)
  {
   MqlTradeRequest req={0};
   MqlTradeResult  res={0};
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);

   req.action=TRADE_ACTION_DEAL;
   req.symbol=_Symbol;
   req.type=ORDER_TYPE_BUY;
   req.volume=Lots;
   req.price=ask;
   req.deviation=movePoint;
   req.sl=sun>0?ask-sun*_Point:0;
   req.tp=ying>0?ask+ying*_Point:0;
   req.comment=comment;
   req.magic=magic;

   if(!OrderSend(req,res))
     { Alert("下多单失败: ",res.retcode); return(-1); }
   return((int)res.order);
  }
//+------------------------------------------------------------------+
//| 修改持仓止损止盈                                                   |
//+------------------------------------------------------------------+
void SendModify(ulong ticket,double sl,double tp)
  {
   MqlTradeRequest req={0};
   MqlTradeResult  res={0};
   req.action=TRADE_ACTION_SLTP;
   req.position=ticket;
   req.symbol=_Symbol;
   req.sl=sl;
   req.tp=tp;
   if(!OrderSend(req,res))
      Print("修改SLTP失败: ",res.retcode);
  }
//+------------------------------------------------------------------+
//| 显示MT4信息(占位)                                                  |
//+------------------------------------------------------------------+
void showMT4Info()
  {
   ObjectDelete(0,"mt4_bg");
   ObjectCreate(0,"mt4_bg",OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,"mt4_bg",OBJPROP_XSIZE,300);
   ObjectSetInteger(0,"mt4_bg",OBJPROP_YSIZE,200);
   ObjectSetInteger(0,"mt4_bg",OBJPROP_BGCOLOR,clrWhite);
   ObjectSetInteger(0,"mt4_bg",OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,"mt4_bg",OBJPROP_XDISTANCE,isRight?150:165);
   ObjectSetInteger(0,"mt4_bg",OBJPROP_YDISTANCE,42);
   ObjectSetInteger(0,"mt4_bg",OBJPROP_SELECTABLE,true);

   double bal=AccountInfoDouble(ACCOUNT_BALANCE);
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   string info="账号: "+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"\n"+
               "余额: "+DoubleToString(bal,2)+"\n"+
               "净值: "+DoubleToString(eq,2)+"\n"+
               "品种: "+_Symbol;
   ObjectCreate(0,"mt4_label",OBJ_LABEL,0,0,0);
   ObjectSetString(0,"mt4_label",OBJPROP_TEXT,info);
   ObjectSetInteger(0,"mt4_label",OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,"mt4_label",OBJPROP_XDISTANCE,isRight?155:170);
   ObjectSetInteger(0,"mt4_label",OBJPROP_YDISTANCE,47);
   ObjectSetInteger(0,"mt4_label",OBJPROP_FONTSIZE,10);
   ObjectSetInteger(0,"mt4_label",OBJPROP_COLOR,clrBlack);
  }
//+------------------------------------------------------------------+
void hideMT4Info()
  {
   ObjectDelete(0,"mt4_bg");
   ObjectDelete(0,"mt4_label");
  }
//+------------------------------------------------------------------+
void showGAISHI1Info()
  {
   ObjectDelete(0,"gaishi1_bg");
   ObjectCreate(0,"gaishi1_bg",OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,"gaishi1_bg",OBJPROP_XSIZE,300);
   ObjectSetInteger(0,"gaishi1_bg",OBJPROP_YSIZE,150);
   ObjectSetInteger(0,"gaishi1_bg",OBJPROP_BGCOLOR,clrWhite);
   ObjectSetInteger(0,"gaishi1_bg",OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,"gaishi1_bg",OBJPROP_XDISTANCE,isRight?150:165);
   ObjectSetInteger(0,"gaishi1_bg",OBJPROP_YDISTANCE,69);
   ObjectSetInteger(0,"gaishi1_bg",OBJPROP_SELECTABLE,true);
  }
//+------------------------------------------------------------------+
void hideGAISHI1Info()
  {
   ObjectDelete(0,"gaishi1_bg");
  }
//+------------------------------------------------------------------+
void showGAISHI2Info()
  {
   ObjectDelete(0,"gaishi2_bg");
   ObjectCreate(0,"gaishi2_bg",OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,"gaishi2_bg",OBJPROP_XSIZE,300);
   ObjectSetInteger(0,"gaishi2_bg",OBJPROP_YSIZE,150);
   ObjectSetInteger(0,"gaishi2_bg",OBJPROP_BGCOLOR,clrWhite);
   ObjectSetInteger(0,"gaishi2_bg",OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,"gaishi2_bg",OBJPROP_XDISTANCE,isRight?150:165);
   ObjectSetInteger(0,"gaishi2_bg",OBJPROP_YDISTANCE,96);
   ObjectSetInteger(0,"gaishi2_bg",OBJPROP_SELECTABLE,true);
  }
//+------------------------------------------------------------------+
void hideGAISHI2Info()
  {
   ObjectDelete(0,"gaishi2_bg");
  }
//+------------------------------------------------------------------+
//| 判断是否模拟账户(MQL5替代MT4的IsDemo())                            |
//+------------------------------------------------------------------+
bool IsDemoAccount()
  {
   return(AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_DEMO);
  }
//+------------------------------------------------------------------+
