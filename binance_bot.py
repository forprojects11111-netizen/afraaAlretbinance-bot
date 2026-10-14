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
        self.wfile.write(b"Binance Interactive Trading Bot is Live!")

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()


# --- 2. إعدادات تليجرام الخاصة بكِ ---
TOKEN = "8979107331:AAHMrQci5lt-FdDj-8SQr6GDYTxob1nmX1o"
CHAT_ID = "7841120409"

def send_telegram_message(text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")


# --- 3. بيانات العملات وقوائمها (قابلة للتحديث ديناميكياً) ---
# القاموس يحمل كل عملة ونسبها: { "BTCUSDT": {"buy_drop": 5.0, "sell_rise": 2.0} }
tracked_symbols = {
    "BTCUSDT": {"buy_drop": 5.0, "sell_rise": 2.0},
    "ETHUSDT": {"buy_drop": 5.0, "sell_rise": 2.0}
}

# حالات المحادثة لإضافة عملة جديدة عبر البوت
user_states = {}
temp_coin_data = {}


# --- 4. معالج أوامر تليجرام والأزرار التفاعلية ---
def check_telegram_updates():
    global tracked_symbols, user_states, temp_coin_data
    last_update_id = 0
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
            res = requests.get(url).json()
            if res.get("result"):
                for update in res["result"]:
                    last_update_id = update["update_id"]
                    
                    # 1. التعامل مع الرسائل النصية
                    if "message" in update:
                        message = update["message"]
                        text = message.get("text", "").strip()
                        
                        if text == "/start":
                            user_states[CHAT_ID] = None
                            keyboard = {
                                "inline_keyboard": [
                                    [{"text": "➕ إضافة عملة جديدة", "callback_data": "add_coin"}],
                                    [{"text": "📋 العملات المراقبَة", "callback_data": "list_coins"}]
                                ]
                            }
                            send_telegram_message(
                                "🤖 **أهلاً بكِ يا مهندسة عفراء!**\n\n"
                                "بوت التداول الذكي جاهز ومستعد.\n"
                                "• الشراء عند الهبوط (5% - 10%+)\n"
                                "• البيع عند الصعود (2% - 5%+)\n\n"
                                "اخترِ من القناة أو الأزرار أدناه:",
                                reply_markup=keyboard
                            )
                        
                        # متابعة خطوات إضافة العملة إذا كان المستخدم في حالة ادخال
                        elif user_states.get(CHAT_ID) == "waiting_for_symbol":
                            symbol = text.upper()
                            if not symbol.endswith("USDT"):
                                symbol += "USDT"
                            temp_coin_data["symbol"] = symbol
                            user_states[CHAT_ID] = "waiting_for_buy_drop"
                            send_telegram_message(f"✅ تم استقبال العملة: `{symbol}`\n\nالرجاء إدخال **نسبة هبوط الشراء** المطلوبة (مثلاً أكتب: `5` أو `7`):")
                        
                        elif user_states.get(CHAT_ID) == "waiting_for_buy_drop":
                            try:
                                buy_val = float(text)
                                temp_coin_data["buy_drop"] = buy_val
                                user_states[CHAT_ID] = "waiting_for_sell_rise"
                                send_telegram_message(f"✅ تم تحديد هبوط الشراء بنسبة `{buy_val}%`.\n\nالآن أُكتبي **نسبة صعود البيع/جني الأرباح** (مثلاً أكتب: `2` أو `3`):")
                            except ValueError:
                                send_telegram_message("❌ الرجاء إدخال رقم صحيح بالنسبة المئوية (مثل 5 أو 2):")
                        
                        elif user_states.get(CHAT_ID) == "waiting_for_sell_rise":
                            try:
                                sell_val = float(text)
                                symbol = temp_coin_data["symbol"]
                                buy_val = temp_coin_data["buy_drop"]
                                
                                tracked_symbols[symbol] = {"buy_drop": buy_val, "sell_rise": sell_val}
                                user_states[CHAT_ID] = None
                                
                                send_telegram_message(
                                    f"🎉 **تمت إضافة العملة بنجاح!**\n\n"
                                    f"• العملة: `{symbol}`\n"
                                    f"• تنبيه الشراء عند هبوط: `-{buy_val}%`\n"
                                    f"• تنبيه البيع عند صعود: `+{sell_val}%`\n\n"
                                    f"🚀 البوت بدأ بمراقبتها فوراً 24/7!"
                                )
                            except ValueError:
                                send_telegram_message("❌ الرجاء إدخال رقم صحيح بالنسبة المئوية:")

                    # 2. التعامل مع ضغطات الأزرار (Inline Keyboards)
                    elif "callback_query" in update:
                        callback = update["callback_query"]
                        data = callback.get("data", "")
                        
                        if data == "add_coin":
                            user_states[CHAT_ID] = "waiting_for_symbol"
                            send_telegram_message("➕ **إضافة عملة جديدة**\n\nالرجاء كتابة رمز العملة التي تريدين مراقبتها (مثلاً: `SOL` أو `DOGE`):")
                        
                        elif data == "list_coins":
                            msg = "📋 **العملات التي يتم مراقبتها حالياً:**\n\n"
                            for s, conf in tracked_symbols.items():
                                msg += f"• `{s}` ⬅️ شراء: `-{conf['buy_drop']}%` | بيع: `+{conf['sell_rise']}%`\n"
                            send_telegram_message(msg)

        except Exception as e:
            print(f"Update error: {e}")
        time.sleep(2)

threading.Thread(target=check_telegram_updates, daemon=True).start()


# --- 5. منطق المراقبة المستمرة لكل العملات المضافة ---
def monitor_binance_trading():
    print("Binance dynamic strategy monitor started...")
    base_prices = {}
    
    while True:
        # نأخذ نسخة من المفاتيح لكي لا يحدث خطأ إذا تغيرت القائمة أثناء الدوران
        current_symbols = list(tracked_symbols.keys())
        
        for symbol in current_symbols:
            try:
                api_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                res = requests.get(api_url).json()
                current_price = float(res.get('price', 0))
                
                if current_price == 0:
                    continue
                
                # تعيين سعر الأساس إذا كانت المرة الأولى للعملة
                if symbol not in base_prices or base_prices[symbol] is None:
                    base_prices[symbol] = current_price
                    continue
                
                base_price = base_prices[symbol]
                config = tracked_symbols.get(symbol, {"buy_drop": 5.0, "sell_rise": 2.0})
                
                buy_drop_limit = config["buy_drop"]
                sell_rise_limit = config["sell_rise"]
                
                # حساب نسبة التغير اللحظية من سعر الأساس
                price_change_percent = ((current_price - base_price) / base_price) * 100
                
                # 1. حالة الهبوط (تنبيه شراء)
                if price_change_percent <= -buy_drop_limit:
                    msg = (
                        f"🚨 **تنبيه شراء (فرصة دخول)**\n\n"
                        f"• العملة: `{symbol}`\n"
                        f"• السعر السابق: `{base_price}`\n"
                        f"• السعر الحالي: `{current_price}`\n"
                        f"• نسبة الهبوط: `{price_change_percent:.2f}%` 🔻\n\n"
                        f"💡 دخلت في النطاق المستهدف للشراء برأس مال 20$!"
                    )
                    send_telegram_message(msg)
                    base_prices[symbol] = current_price
                
                # 2. حالة الصعود (تنبيه بيع جني الأرباح)
                elif price_change_percent >= sell_rise_limit:
                    msg = (
                        f"💰 **تنبيه بيع / جني أرباح**\n\n"
                        f"• العملة: `{symbol}`\n"
                        f"• سعر الشراء: `{base_price}`\n"
                        f"• السعر الحالي: `{current_price}`\n"
                        f"• نسبة الصعود: `+{price_change_percent:.2f}%` 🚀\n\n"
                        f"💡 تحققت نسبة الربح المستهدفة للوصول لهدفك!"
                    )
                    send_telegram_message(msg)
                    base_prices[symbol] = current_price
                    
            except Exception as e:
                print(f"Error checking {symbol}: {e}")
                
        # الفحص كل دقيقة
        time.sleep(60)

if __name__ == "__main__":
    monitor_binance_trading()
