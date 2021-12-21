import time
import pyupbit
import datetime
import telepot   # telepot 모듈 import 
import j_key

token = j_key.get_tele_token()
mc = j_key.get_tele_mc()
bot = telepot.Bot(token) # bot.sendMessage(mc, "test") # 할말 적어서 메시지 보내기 
access = j_key.get_upbit_access()
secret = j_key.get_upbit_secret()
signal_buy = 0
phase_buy = 0
krw=0
ticker_b=0
ticker_avg_buy=0
ticker = "EOS"
trailing_target=0
trailing_start=0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

def get_balance(ticker):
    global krw, ticker_b, ticker_avg_buy
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == "KRW":
            krw = float(b['balance'])
        if b['currency'] == ticker:
            if b['balance'] is not None:
                ticker_b = float(b['balance'])
            else:
                ticker_b = 0
            if b['avg_buy_price'] is not None:
                ticker_avg_buy = float(b['avg_buy_price'])
            else:
                ticker_avg_buy = 0 
    return krw, ticker_b, ticker_avg_buy   

# 로그인
upbit = pyupbit.Upbit(access, secret)

ticker = "EOS"
get_balance(ticker) 
msg_balance = "Upbit Auto-Trade START"+"\nKRW잔고: "+str(int(krw))+"원\n"+ticker+"잔고: "+str(int(ticker_b))+"\n매수평단가: "+ str(int(ticker_avg_buy))+"원"
bot.sendMessage(mc, msg_balance)
print(msg_balance)
# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()
        ticker = "EOS"
        df = pyupbit.get_ohlcv("KRW-"+ticker, interval="minute5", count=50)
        close = df['close']
        df_30m = pyupbit.get_ohlcv("KRW-"+ticker, interval="minute30", count=50)
        close_30m = df_30m['close']

        # 이동평균계산 --------------------------------------------------------------------------------------------------------------#
        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        ma120 = close.rolling(120).mean()

        # MACD 
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1-exp2
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_osc = macd - macd_signal

        exp1_30m = close_30m.ewm(span=12, adjust=False).mean()
        exp2_30m = close_30m.ewm(span=26, adjust=False).mean()
        macd_30m = exp1_30m-exp2_30m
        macd_signal_30m = macd_30m.ewm(span=9, adjust=False).mean()
        macd_osc_30m = macd_30m - macd_signal_30m

        # Scochastic Slow --------------------------------------------------------------------------------------------------------------#
        Period = 30
        SlowK_period = 3
        SlowD_period = 3
        fast_k = (close - df['low'].rolling(Period).min()) / (df['high'].rolling(Period).max() - df['low'].rolling(Period).min())*100
        slow_k = fast_k.rolling(window=SlowK_period).mean()
        slow_d = slow_k.rolling(window=SlowD_period).mean()
        
        fast_k_30m = (close_30m - df_30m['low'].rolling(Period).min()) / (df_30m['high'].rolling(Period).max() - df_30m['low'].rolling(Period).min())*100
        slow_k_30m = fast_k_30m.rolling(window=SlowK_period).mean()
        slow_d_30m = slow_k_30m.rolling(window=SlowD_period).mean()

        #잔고조회
        get_balance(ticker)
        if ticker_b == 0 :
            signal_buy = 0
            phase_buy = 0
        else:
            signal_buy = 1


        current_price = get_current_price("KRW-"+ticker)
        
        #-----SELL--------------------------------------------------------------------------------------------------------------------------------------#
         
            #if (macd[-2] >= exp3[-2] and macd[-1] < exp3[-1]) or (current_price > ticker_avg_buy*1.05) or (current_price < ticker_avg_buy*0.97)  :
            #if (slow_k[-2] >= 80 and slow_k[-1] < slow_d[-1]) or (current_price > ticker_avg_buy*1.05) or (current_price < ticker_avg_buy*0.97)  :
        if (slow_k[-2] >= 80 and slow_k[-2] >= slow_d[-2] and slow_k[-1] < slow_d[-1]) or (current_price > ticker_avg_buy*1.05) or (current_price < ticker_avg_buy*0.98)  :
            if signal_buy == 1 and phase_buy != 0 :  
                upbit.sell_market_order("KRW-"+ticker, ticker_b)  
                signal_buy = 0
                phase_buy = 0
                msg_sell = ticker+" 전량매도\n매도가: "+ str(int(current_price)) +"\n매도수량: "+str(int(ticker_b))+"\n예상수익률: "+str(int((current_price/ticker_avg_buy-1)*100)) +"%"
                #bot.sendMessage(mc, msg_sell)
                get_balance(ticker)              
                msg_balance = "\nKRW잔고: "+str(int(krw))+"원"
                bot.sendMessage(mc, msg_sell+msg_balance)

        if signal_buy == 1 and phase_buy != 0 :
            if current_price >= ticker_avg_buy*1.015 :
                trailing_start =1               
        if trailing_start == 1 :
            if current_price > trailing_target :
                trailing_target = current_price
            if current_price <= trailing_target*0.995 :
                upbit.sell_market_order("KRW-"+ticker, ticker_b)
                signal_buy = 0
                phase_buy = 0
                trailing_start=0
                msg_sell = ticker+" 전량매도(Trailing)\n매도가: "+ str(int(current_price)) +"\n매도수량: "+str(int(ticker_b))+"\n예상수익률: "+str(int((current_price/ticker_avg_buy-1)*100)) +"%"
                #bot.sendMessage(mc, msg_sell)
                get_balance(ticker)              
                msg_balance = "\nKRW잔고: "+str(int(krw))+"원"
                bot.sendMessage(mc, msg_sell+msg_balance)
        #-----------------------------------------------------------------------------------------------------------------------------------------------#        

        #-----BUY-----------------------------------------------------------------------------------------------------------------------------------#
        #if (target_price < current_price) and (macd[-1] > macd_signal[-1]) and (krw > 5000):
        #if (slow_k[-2] <= 80) and (macd[-2] < macd_signal[-2]) and (macd[-1] >= macd_signal[-1]) and (slow_k[-1] >= slow_d[-1]) and (krw > 5000):
        #if (slow_k[-2] <= 20) and (slow_k[-2] < slow_d[-2]) and (slow_k[-1] >= slow_d[-1]) and (macd_osc[-3] < macd_osc[-2]) and (macd_osc[-2] < macd_osc[-1]) and (macd_osc_30m[-2] < macd_osc_30m[-1]) and (krw > 5000):
        if (slow_k[-2] <= 80) and (slow_k[-2] < slow_d[-2]) and (slow_k[-1] >= slow_d[-1]) and (slow_k_30m[-1] >= slow_d_30m[-1]) and (krw > 5000):
        
            if (phase_buy == 2) and (ticker_avg_buy*0.995 > current_price) :
                upbit.buy_market_order("KRW-"+ticker, (krw*0.9995))
                msg_buy = ticker+" 매수(3차)\n매수가:"+ str(int(current_price))+"원" +"\n매수금:"+str(int((krw*0.9995)))+"원"
                #bot.sendMessage(mc, msg_buy)
                phase_buy = 3
                get_balance(ticker)               
                msg_balance = "\nKRW잔고: "+str(int(krw))+"원\n"+ticker+"잔고: "+str(int(ticker_b))+"\n매수평단가: "+ str(int(ticker_avg_buy))+"원"
                bot.sendMessage(mc, msg_buy+msg_balance)
                
                    
            elif (phase_buy == 1) and (ticker_avg_buy*0.995 > current_price) :
                upbit.buy_market_order("KRW-"+ticker, (krw*0.9995)*0.5)
                msg_buy = ticker+" 매수(2차)\n매수가:"+ str(int(current_price))+"원" +"\n매수금:"+str(int((krw*0.9995)*0.5))+"원"
                #bot.sendMessage(mc, msg_buy)
                phase_buy = 2
                get_balance(ticker)                
                msg_balance = "\nKRW잔고: "+str(int(krw))+"원\n"+ticker+"잔고: "+str(int(ticker_b))+"\n매수평단가: "+ str(int(ticker_avg_buy))+"원"
                bot.sendMessage(mc, msg_buy+msg_balance)
                

            elif (phase_buy == 0)  :
                upbit.buy_market_order("KRW-"+ticker, (krw*0.9995)*0.3)
                msg_buy = ticker+" 매수(1차)\n매수가:"+ str(int(current_price))+"원" +"\n매수금:"+str(int((krw*0.9995)*0.3))+"원"
                #bot.sendMessage(mc, msg_buy)
                phase_buy = 1
                signal_buy = 1
                get_balance(ticker)         
                msg_balance = "\nKRW잔고: "+str(int(krw))+"원\n"+ticker+"잔고: "+str(int(ticker_b))+"\n매수평단가: "+ str(int(ticker_avg_buy))+"원"
                bot.sendMessage(mc, msg_buy+msg_balance)
        #------------------------------------------------------------------------------------------------------------------------------------------#        


        
        time.sleep(1)
    except Exception as e:
        print(e)
        bot.sendMessage(mc, str(e))
        time.sleep(1)