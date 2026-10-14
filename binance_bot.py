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
        self.wfile.write(b"Binance Full Management Trading Bot is Live!")

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


# --- 3. بيانات العملات وقوائمها الديناميكية ---
tracked_symbols = {
    "BTCUSDT": {"buy_drop": 5.0, "sell_rise": 2.0},
    "ETHUSDT": {"buy_drop": 5.0, "sell_rise": 2.0}
}

# حالات المحادثة لإدارة العملات (إضافة أو تعديل)
user_states = {}
temp_coin_data = {}


# --- 4. دالة بناء أزرار قائمة العملات للتعديل أو الحذف ---
def get_coins_management_keyboard(action_type):
    keyboard = {"inline_keyboard": []}
    for symbol in tracked_symbols.keys():
        keyboard["inline_keyboard"].append([
            {"text": f"🪙 {symbol}", "callback_data": f"{action_type}_{symbol}"}
        ])
    keyboard["inline_keyboard"].append([{"text": "🔙 القائمة الرئيسية", "callback_data": "main_menu"}])
    return keyboard


# --- 5. معالج أوامر تليجرام والأزرار التفاعلية ---
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
                    
                    # 1. التعامل مع الرسائل النصية ومدخلات المستخدم
                    if "message" in update:
                        message = update["message"]
                        text = message.get("text", "").strip()
                        current_state = user_states.get(CHAT_ID)
                        
                        if text == "/start":
                            user_states[CHAT_ID] = None
                            send_main_menu()
                        
                        # --- حالات إضافة عملة جديدة ---
                        elif current_state == "waiting_for_symbol":
                            symbol = text.upper()
                            if not symbol.endswith("USDT"):
                                symbol += "USDT"
                            temp_coin_data["symbol"] = symbol
                            user_states[CHAT_ID] = "waiting_for_buy_drop"
                            send_telegram_message(f"✅ تم استقبال العملة: `{symbol}`\n\nالرجاء إدخال **نسبة هبوط الشراء** الجديدة (مثلاً: `5` أو `7`):")
                        
                        elif current_state == "waiting_for_buy_drop":
                            try:
                                buy_val = float(text)
                                temp_coin_data["buy_drop"] = buy_val
                                user_states[CHAT_ID] = "waiting_for_sell_rise"
                                send_telegram_message(f"✅ نسبة الهبوط للشراء: `{buy_val}%`.\n\nالآن أُكتبي **نسبة صعود البيع/جني الأرباح** (مثلاً: `2` أو `3`):")
                            except ValueError:
                                send_telegram_message("❌ الرجاء إدخال رقم صحيح بالنسبة المئوية (مثل 5 أو 2):")
                        
                        elif current_state == "waiting_for_sell_rise":
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
                                    f"• تنبيه البيع عند صعود: `+{sell_val}%`"
                                )
                                send_main_menu()
                            except ValueError:
                                send_telegram_message("❌ الرجاء إدخال رقم صحيح بالنسبة المئوية:")

                        # --- حالات تعديل نسب عملة موجودة ---
                        elif current_state == "waiting_for_edit_buy":
                            try:
                                buy_val = float(text)
                                temp_coin_data["buy_drop"] = buy_val
                                user_states[CHAT_ID] = "waiting_for_edit_sell"
                                symbol = temp_coin_data["symbol"]
                                send_telegram_message(f"✅ تم تحديث هبوط الشراء لـ `{symbol}` إلى `{buy_val}%`.\n\nالآن أُكتبي **نسبة صعود البيع** الجديدة:")
                            except ValueError:
                                send_telegram_message("❌ الرجاء إدخال رقم صحيح:")

                        elif current_state == "waiting_for_edit_sell":
                            try:
                                sell_val = float(text)
                                symbol = temp_coin_data["symbol"]
                                buy_val = temp_coin_data["buy_drop"]
                                
                                tracked_symbols[symbol] = {"buy_drop": buy_val, "sell_rise": sell_val}
                                user_states[CHAT_ID] = None
                                
                                send_telegram_message(
                                    f"🔄 **تم تعديل نسب العملة بنجاح!**\n\n"
                                    f"• العملة: `{symbol}`\n"
                                    f"• هبوط الشراء الجديد: `-{buy_val}%`\n"
                                    f"• صعود البيع الجديد: `+{sell_val}%`"
                                )
                                send_main_menu()
                            except ValueError:
                                send_telegram_message("❌ الرجاء إدخال رقم صحيح:")

                    # 2. التعامل مع ضغطات الأزرار التفاعلية (Inline Keyboards)
                    elif "callback_query" in update:
                        callback = update["callback_query"]
                        data = callback.get("data", "")
                        
                        if data == "main_menu":
                            user_states[CHAT_ID] = None
                            send_main_menu()
                        
                        elif data == "add_coin":
                            user_states[CHAT_ID] = "waiting_for_symbol"
                            send_telegram_message("➕ **إضافة عملة جديدة**\n\nأُكتبي رمز العملة (مثلاً: `SOL` أو `BNB`):")
                        
                        elif data == "list_coins":
                            msg = "📋 **العملات التي يتم مراقبتها حالياً:**\n\n"
                            for s, conf in tracked_symbols.items():
                                msg += f"• `{s}` ⬅️ هبوط شراء: `-{conf['buy_drop']}%` | صعود بيع: `+{conf['sell_rise']}%`\n"
                            
                            keyboard = {"inline_keyboard": [[{"text": "🔙 القائمة الرئيسية", "callback_data": "main_menu"}]]}
                            send_telegram_message(msg, reply_markup=keyboard)
                        
                        elif data == "edit_coin_menu":
                            if not tracked_symbols:
                                send_telegram_message("⚠️ لا توجد عملات مضافة حالياً للتعديل.")
                            else:
                                kb = get_coins_management_keyboard("edit")
                                send_telegram_message("⚙️ **اختر العملة التي تريدين تعديل نسبها:**", reply_markup=kb)
                        
                        elif data == "delete_coin_menu":
                            if not tracked_symbols:
                                send_telegram_message("⚠️ لا توجد عملات مضافة حالياً للحذف.")
                            else:
                                kb = get_coins_management_keyboard("delete")
                                send_telegram_message("🗑️ **اختر العملة التي تريدين حذفها من المراقبة:**", reply_markup=kb)
                        
                        # معالجة اختيار عملة للتعديل
                        elif data.startswith("edit_"):
                            symbol = data.replace("edit_", "")
                            if symbol in tracked_symbols:
                                temp_coin_data["symbol"] = symbol
                                user_states[CHAT_ID] = "waiting_for_edit_buy"
                                send_telegram_message(f"✏️ تعديل نسب العملة: `{symbol}`\n\nالنسبة الحالية للشراء هي `-{tracked_symbols[symbol]['buy_drop']}%`.\nالرجاء إدخال **نسبة هبوط الشراء الجديدة**:")
                        
                        # معالجة اختيار عملة للحذف
                        elif data.startswith("delete_"):
                            symbol = data.replace("delete_", "")
                            if symbol in tracked_symbols:
                                del tracked_symbols[symbol]
                                send_telegram_message(f"🗑️ تم حذف العملة `{symbol}` بنجاح من قائمة المراقبة.")
                                send_main_menu()

        except Exception as e:
            print(f"Update error: {e}")
        time.sleep(2)

def send_main_menu():
    keyboard = {
        "inline_keyboard": [
            [{"text": "➕ إضافة عملة جديدة", "callback_data": "add_coin"}],
            [{"text": "📋 استعراض العملات والنسب", "callback_data": "list_coins"}],
            [{"text": "⚙️ تعديل نسب عملة", "callback_data": "edit_coin_menu"}],
            [{"text": "🗑️ حذف عملة", "callback_data": "delete_coin_menu"}]
        ]
    }
    send_telegram_message(
        "🤖 **لوحة تحكم بوت التداول - مهندسة عفراء**\n\n"
        "اخترِ الإجراء المطلوب من الأزرار أدناه لإدارة العملات ونسب التداول بكل سهولة:",
        reply_markup=keyboard
    )

threading.Thread(target=check_telegram_updates, daemon=True).start()


# --- 6. منطق المراقبة المستمرة لكل العملات والنسب المحدثة ---
def monitor_binance_trading():
    print("Binance full-management strategy monitor started...")
    base_prices = {}
    
    while True:
        current_symbols = list(tracked_symbols.keys())
        
        for symbol in current_symbols:
            try:
                api_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                res = requests.get(api_url).json()
                current_price = float(res.get('price', 0))
                
                if current_price == 0:
                    continue
                
                if symbol not in base_prices or base_prices[symbol] is None:
                    base_prices[symbol] = current_price
                    continue
                
                base_price = base_prices[symbol]
                config = tracked_symbols.get(symbol, {"buy_drop": 5.0, "sell_rise": 2.0})
                
                buy_drop_limit = config["buy_drop"]
                sell_rise_limit = config["sell_rise"]
                
                price_change_percent = ((current_price - base_price) / base_price) * 100
                
                # 1. حالة الهبوط (تنبيه شراء)
                if price_change_percent <= -buy_drop_limit:
                    msg = (
                        f"🚨 **تنبيه شراء (فرصة دخول)**\n\n"
                        f"• العملة: `{symbol}`\n"
                        f"• السعر السابق: `{base_price}`\n"
                        f"• السعر الحالي: `{current_price}`\n"
                        f"• نسبة الهبوط: `{price_change_percent:.2f}%` 🔻\n\n"
                        f"💡 وصلت للحد المستهدَف للشراء برأس مال 20$!"
                    )
                    send_telegram_message(msg)
                    base_prices[symbol] = current_price
                
                # 2. حالة الصعود (تنبيه بيع جني الأرباح)
                elif price_change_percent >= sell_rise_limit:
                    msg = (
                        f"💰 **تنبيه بيع / جني الأرباح**\n\n"
                        f"• العملة: `{symbol}`\n"
                        f"• سعر الشراء: `{base_price}`\n"
                        f"• السعر الحالي: `{current_price}`\n"
                        f"• نسبة الصعود: `+{price_change_percent:.2f}%` 🚀\n\n"
                        f"💡 تحققت نسبة الربح المستهدفة للوصول لهدف الـ 2$!"
                    )
                    send_telegram_message(msg)
                    base_prices[symbol] = current_price
                    
            except Exception as e:
                print(f"Error checking {symbol}: {e}")
                
        time.sleep(60)

if __name__ == "__main__":
    monitor_binance_trading()
