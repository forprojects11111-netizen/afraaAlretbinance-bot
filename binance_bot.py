import os
import time
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- 1. خادم الويب الوهمي لضمان عمل البوت 24/7 على Render ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Binance Trading Bot is Live!")

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()


# --- 2. إعدادات تليجرام الخاصة بكِ ---
TOKEN = "8979107331:AAHMrQci5lt-FdDj-8SQr6GDYTxob1nmX1o"
CHAT_ID = "7841120409"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")


# --- 3. معالج أوامر تليجرام (لاستجابة /start) ---
def check_telegram_updates():
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
            res = requests.get(url).json()
            if res.get("result"):
                for update in res["result"]:
                    last_update_id = update["update_id"]
                    message = update.get("message", {})
                    text = message.get("text", "")
                    
                    if text == "/start":
                        send_telegram_message("🤖 أهلاً بكِ يا مهندسة عفراء! بوت التداول (شراء عند الهبوط 5%-10% وبيع عند الصعود 2%-5%) يعمل الآن بكفاءة 24/7 🚀")
        except Exception as e:
            print(f"Update error: {e}")
        time.sleep(2)

threading.Thread(target=check_telegram_updates, daemon=True).start()


# --- 4. منطق المراقبة بالشروط المخصصة للشراء والبيع ---
SYMBOLS = ["BTCUSDT", "ETHUSDT"]

# النسب المحددة:
BUY_DROP_MIN = 5.0    # تنبيه شراء عندما يهبط بنسبة تتراوح بين 5% إلى 10% فما فوق
SELL_RISE_MIN = 2.0   # تنبيه بيع جني أرباح عندما يصعد بنسبة تتراوح بين 2% إلى 5% فما فوق

def monitor_binance_trading():
    print("Binance custom strategy monitor started...")
    base_prices = {}
    
    while True:
        for symbol in SYMBOLS:
            try:
                api_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                res = requests.get(api_url).json()
                current_price = float(res.get('price', 0))
                
                # تعيين سعر الأساس إذا كانت المرة الأولى
                if symbol not in base_prices or base_prices[symbol] is None:
                    base_prices[symbol] = current_price
                    continue
                
                base_price = base_prices[symbol]
                
                # حساب نسبة التغير اللحظية من سعر الأساس
                price_change_percent = ((current_price - base_price) / base_price) * 100
                
                # 1. حالة الهبوط (تنبيه شراء من 5% إلى 10%+)
                if price_change_percent <= -BUY_DROP_MIN:
                    msg = (
                        f"🚨 **تنبيه شراء (هبوط بنسبة {abs(price_change_percent):.2f}%)**\n\n"
                        f"• العملة: `{symbol}`\n"
                        f"• السعر السابق: `{base_price}`\n"
                        f"• السعر الحالي: `{current_price}`\n\n"
                        f"💡 النسبة دخلت في نطاق الهبوط المستهدف (من 5% إلى 10%+)، فرصة للشراء برأس مال 20$!"
                    )
                    send_telegram_message(msg)
                    base_prices[symbol] = current_price
                
                # 2. حالة الصعود (تنبيه بيع جني الأرباح من 2% إلى 5%+)
                elif price_change_percent >= SELL_RISE_MIN:
                    msg = (
                        f"💰 **تنبيه بيع / جني أرباح (صعود بنسبة +{price_change_percent:.2f}%)**\n\n"
                        f"• العملة: `{symbol}`\n"
                        f"• سعر الشراء: `{base_price}`\n"
                        f"• السعر الحالي: `{current_price}`\n\n"
                        f"💡 النسبة دخلت في نطاق الصعود المستهدف (من 2% إلى 5%+)، فرصة للبيع وتحقيق الأرباح!"
                    )
                    send_telegram_message(msg)
                    base_prices[symbol] = current_price
                    
            except Exception as e:
                print(f"Error checking {symbol}: {e}")
                
        # الفحص كل دقيقة
        time.sleep(60)

if __name__ == "__main__":
    monitor_binance_trading()
