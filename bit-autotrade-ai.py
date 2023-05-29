import pyupbit
import time
import datetime
import schedule
import requests
from prophet import Prophet

def send_message(msg):
    """디스코드 메세지 전송"""
    now = datetime.datetime.now()
    message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}
    requests.post(DISCORD_WEBHOOK_URL, data=message)
    print(message)
    
def cal_target(ticker):
    df = pyupbit.get_ohlcv(ticker, "day")
    yesterday = df.iloc[-2]
    today = df.iloc[-1]
    yesterday_range = yesterday['high'] - yesterday['low']
    target = today['open'] + yesterday_range * 0.3
    return target

# Prophet으로 당일 종가 가격 예측
predicted_close_price = 0
def predict_price(ticker):
    global predicted_close_price
    df = pyupbit.get_ohlcv(ticker, "minute60")
    
    df = df.reset_index()
    df['ds'] = df['index']
    df['y'] = df['close']
    data = df[['ds','y']]
    
    model = Prophet()
    model.fit(data)
    
    future = model.make_future_dataframe(periods=24, freq='H')
    forecast = model.predict(future)
    
    closeDf = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
    if len(closeDf) == 0:
        closeDf = forecast[forecast['ds'] == data.iloc[-1]['ds'].replace(hour=9)]
    closeValue = closeDf['yhat'].values[0]
    predicted_close_price = closeValue
predict_price("KRW-BTC")
schedule.every().hour.do(lambda: predict_price("KRW-BTC"))

# 객체 생성
f = open("upbit.txt")
lines = f.readlines()
access = lines[0].strip()   #access key
secret = lines[1].strip()   #secret key
DISCORD_WEBHOOK_URL = lines[2].strip()  #디스코드 웹훅 key
f.close()
upbit = pyupbit.Upbit(access, secret) # class instance, object

# 변수 설정
target = cal_target("KRW-BTC")
op_mode = False
hold = False

send_message("코인 자동매매 프로그램을 시작합니다")
                  
while True:
    now = datetime.datetime.now()
    
    # 매도 시도
    if now.hour == 8 and now.minute == 59 and 50 <= now.second <= 59:
        if op_mode is True and hold is True:
            btc_balance = upbit.get_balance("KRW-BTC")
            upbit.sell_market_order("KRW-BTC", btc_balance)
            send_message("코인을 전량 매도 하였습니다")
            hold = False
            
        op_mode = False
        time.sleep(10)
    
    
    # 09:00:00 목표가 갱신
    if now.hour == 9 and now.minute == 0 and 20 <= now.second <= 30:
        target = cal_target("KRW-BTC")
        op_mode = True
    
    price = pyupbit.get_current_price("KRW-BTC")
    
    # 매초마다 조건을 확인한 후 매수 시도
    if op_mode is True and hold is False and price > target and price < predicted_close_price :
        # 매수
        krw_balance = upbit.get_balance("KRW")
        upbit.buy_market_order("KRW-BTC", krw_balance)
        #upbit.buy_market_order("KRW-BTC", krw_balance * 0.5) # 보유금액에 50% 만 구매
        send_message("코인을 전량 매수 하였습니다")
        hold = True
        
    print(f"현재시간: {now} 현재가: {price} 목표가: {target} 종가예측: {predicted_close_price} 보유상태: {hold} 동작상태: {op_mode}")
    time.sleep(1)
