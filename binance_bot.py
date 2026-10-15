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


# --- 2. إعدادات تليجرام ---
TOKEN = "8979107331:AAHMrQci5lt-FdDj-8SQr6GDYTxob1nmX1o"
CHAT_ID = "7841120409"

def send_telegram_message(text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

def parse_float_input(text):
    cleaned = text.replace("%", "").replace("−", "-").strip()
    return float(cleaned)

def get_market_data(symbol):
    # جلب السعر الحالي ونسبة التغير خلال 24 ساعة تماماً مثل التطبيق
    urls = [
        f"https://api1.binance.com/api/v3/ticker/24hr?symbol={symbol}",
        f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}",
        f"https://data-api.binance.vision/api/v3/ticker/24hr?symbol={symbol}"
    ]
    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=3)
            if res.status_code == 200:
                data = res.json()
                price = float(data.get('lastPrice', 0))
                price_change_percent = float(data.get('priceChangePercent', 0))
                if price > 0:
                    return price, price_change_percent
        except Exception:
            continue
    return 0.0, 0.0


# --- 3. بيانات العملات ونظام التنبيهات التدريجية ---
tracked_symbols = {
    "BTCUSDT": {"buy_drop": 5.0, "sell_rise": 10.0},
    "ETHUSDT": {"buy_drop": 6.0, "sell_rise": 10.0}
}

# تتبع المراحل التي تم التنبيه بها لكي لا تتكرر
notified_stages = {
    "BTCUSDT": {"3": False, "6": False, "10": False},
    "ETHUSDT": {"3": False, "6": False, "10": False}
}

user_states = {}
temp_coin_data = {}
base_prices = {}
current_prices = {}


# --- 4. دالة بناء أزرار العملات ---
def get_coins_management_keyboard(action_type):
    keyboard = {"inline_keyboard": []}
    for symbol in tracked_symbols.keys():
        keyboard["inline_keyboard"].append([
            {"text": f"🪙 {symbol}", "callback_data": f"{action_type}_{symbol}"}
        ])
    keyboard["inline_keyboard"].append([{"text": "🔙 القائمة الرئيسية", "callback_data": "main_menu"}])
    return keyboard


# --- 5. معالج أوامر تليجرام والأزرار ---
def check_telegram_updates():
    global tracked_symbols, user_states, temp_coin_data, base_prices, current_prices, notified_stages
    last_update_id = 0
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
            res = requests.get(url, timeout=35).json()
            if res.get("result"):
                for update in res["result"]:
                    last_update_id = update["update_id"]
                    
                    if "message" in update:
                        message = update["message"]
                        text = message.get("text", "").strip()
                        current_state = user_states.get(CHAT_ID)
                        
                        if text == "/start":
                            user_states[CHAT_ID] = None
                            send_main_menu()
                        
                        elif current_state == "waiting_for_symbol":
                            symbol = text.upper()
                            if not symbol.endswith("USDT"):
                                symbol += "USDT"
                            temp_coin_data["symbol"] = symbol
                            user_states[CHAT_ID] = "waiting_for_buy_drop"
                            send_telegram_message(f"✅ تم استقبال العملة: `{symbol}`\n\nالرجاء إدخال **نسبة هبوط الشراء** (مثل: `5`):")
                        
                        elif current_state == "waiting_for_buy_drop":
                            try:
                                buy_val = abs(parse_float_input(text))
                                temp_coin_data["buy_drop"] = buy_val
                                user_states[CHAT_ID] = "waiting_for_sell_rise"
                                send_telegram_message(f"✅ نسبة الهبوط للشراء: `{buy_val}%`.\n\nالآن أُكتبي **نسبة صعود البيع المستهدفة** (مثل: `10` لهدف الـ 22$):")
                            except ValueError:
                                send_telegram_message("❌ الرجاء إدخال رقم صحيح:")
                        
                        elif current_state == "waiting_for_sell_rise":
                            try:
                                sell_val = abs(parse_float_input(text))
                                symbol = temp_coin_data["symbol"]
                                buy_val = temp_coin_data["buy_drop"]
                                
                                tracked_symbols[symbol] = {"buy_drop": buy_val, "sell_rise": sell_val}
                                notified_stages[symbol] = {"3": False, "6": False, "10": False}
                                p, _ = get_market_data(symbol)
                                base_prices[symbol] = p
                                current_prices[symbol] = p
                                user_states[CHAT_ID] = None
                                
                                send_telegram_message(
                                    f"🎉 **تمت إضافة العملة بنجاح!**\n\n"
                                    f"• العملة: `{symbol}`\n"
                                    f"• تنبيه الشراء عند هبوط: `-{buy_val}%`\n"
                                    f"• تنبيهات الصعود التدريجية: (+3%، +6%、، والهدف النهائي +{sell_val}%)"
                                )
                                send_main_menu()
                            except ValueError:
                                send_telegram_message("❌ الرجاء إدخال رقم صحيح:")

                        elif current_state == "waiting_for_edit_buy":
                            try:
                                buy_val = abs(parse_float_input(text))
                                temp_coin_data["buy_drop"] = buy_val
                                user_states[CHAT_ID] = "waiting_for_edit_sell"
                                symbol = temp_coin_data["symbol"]
                                send_telegram_message(f"✅ تم تحديث هبوط الشراء لـ `{symbol}` إلى `{buy_val}%`.\n\nالآن أُكتبي **نسبة صعود البيع** الجديدة:")
                            except ValueError:
                                send_telegram_message("❌ الرجاء إدخال رقم صحيح:")

                        elif current_state == "waiting_for_edit_sell":
                            try:
                                sell_val = abs(parse_float_input(text))
                                symbol = temp_coin_data["symbol"]
                                buy_val = temp_coin_data["buy_drop"]
                                
                                tracked_symbols[symbol] = {"buy_drop": buy_val, "sell_rise": sell_val}
                                notified_stages[symbol] = {"3": False, "6": False, "10": False}
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

                    elif "callback_query" in update:
                        callback = update["callback_query"]
                        data = callback.get("data", "")
                        
                        if data == "main_menu":
                            user_states[CHAT_ID] = None
                            send_main_menu()
                        
                        elif data == "add_coin":
                            user_states[CHAT_ID] = "waiting_for_symbol"
                            send_telegram_message("➕ **إضافة عملة جديدة**\n\nأُكتبي رمز العملة (مثلاً: `SOL` أو `DOGE`):")
                        
                        elif data == "price_check_menu":
                            kb = get_coins_management_keyboard("checkprice")
                            send_telegram_message("📈 **اختر العملة لمعرفة سعرها اللحظي ونسبتها الآن:**", reply_markup=kb)
                        
                        elif data.startswith("checkprice_"):
                            symbol = data.replace("checkprice_", "")
                            if symbol in tracked_symbols:
                                cur_p, official_change = get_market_data(symbol)
                                if cur_p > 0:
                                    current_prices[symbol] = cur_p
                                else:
                                    cur_p = current_prices.get(symbol, 0.0)
                                
                                if symbol not in base_prices or base_prices[symbol] == 0.0:
                                    base_prices[symbol] = cur_p
                                
                                base_p = base_prices[symbol]
                                conf = tracked_symbols[symbol]
                                
                                sign = "+" if official_change >= 0 else ""
                                change_str = f"`{sign}{official_change:.2f}%`"
                                
                                msg = (
                                    f"🪙 **تقرير العملة اللحظي: `{symbol}`**\n\n"
                                    f"• السعر الحالي: `{cur_p}` USDT\n"
                                    f"• سعر الأساس: `{base_p}` USDT\n"
                                    f"• نسبة التغير (24 ساعة): {change_str}\n\n"
                                    f"🎯 **النسب المحددة للمراقبة:**\n"
                                    f"• تنبيه الشراء: `-{conf['buy_drop']}%`\n"
                                    f"• تنبيه البيع المستهدف: `+{conf['sell_rise']}%` (تدريجي: 3%، 6%، 10% أرباح الـ 22$)"
                                )
                                
                                keyboard = {"inline_keyboard": [[{"text": "🔙 اختر عملة أخرى", "callback_data": "price_check_menu"}, {"text": "🏠 الرئيسية", "callback_data": "main_menu"}]]}
                                send_telegram_message(msg, reply_markup=keyboard)
                        
                        elif data == "list_coins":
                            msg = "📋 **العملات التي يتم مراقبتها حالياً:**\n\n"
                            for s, conf in tracked_symbols.items():
                                msg += f"• `{s}` ⬅️ هبوط شراء: `-{conf['buy_drop']}%` | صعود بيع: `+{conf['sell_rise']}%`\n"
                            
                            keyboard = {"inline_keyboard": [[{"text": "🔙 القائمة الرئيسية", "callback_data": "main_menu"}]]}
                            send_telegram_message(msg, reply_markup=keyboard)
                        
                        elif data == "edit_coin_menu":
                            kb = get_coins_management_keyboard("edit")
                            send_telegram_message("⚙️ **اختر العملة التي تريدين تعديل نسبها:**", reply_markup=kb)
                        
                        elif data == "delete_coin_menu":
                            kb = get_coins_management_keyboard("delete")
                            send_telegram_message("🗑️ **اختر العملة التي تريدين حذفها:**", reply_markup=kb)
                        
                        elif data.startswith("edit_"):
                            symbol = data.replace("edit_", "")
                            if symbol in tracked_symbols:
                                temp_coin_data["symbol"] = symbol
                                user_states[CHAT_ID] = "waiting_for_edit_buy"
                                send_telegram_message(f"✏️ تعديل نسب العملة: `{symbol}`\n\nالرجاء إدخال **نسبة هبوط الشراء الجديدة** (مثل 6):")
                        
                        elif data.startswith("delete_"):
                            symbol = data.replace("delete_", "")
                            if symbol in tracked_symbols:
                                del tracked_symbols[symbol]
                                if symbol in base_prices:
                                    del base_prices[symbol]
                                if symbol in current_prices:
                                    del current_prices[symbol]
                                if symbol in notified_stages:
                                    del notified_stages[symbol]
                                send_telegram_message(f"🗑️ تم حذف العملة `{symbol}` بنجاح.")
                                send_main_menu()

        except Exception as e:
            print(f"Update error: {e}")
        time.sleep(2)

def send_main_menu():
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔍 فحص سعر عملة الآن", "callback_data": "price_check_menu"}],
            [{"text": "➕ إضافة عملة جديدة", "callback_data": "add_coin"}],
            [{"text": "📋 استعراض جميع العملات", "callback_data": "list_coins"}],
            [{"text": "⚙️ تعديل نسب عملة", "callback_data": "edit_coin_menu"}],
            [{"text": "🗑️ حذف عملة", "callback_data": "delete_coin_menu"}]
        ]
    }
    send_telegram_message(
        "🤖 **لوحة تحكم بوت التداول - مهندسة عفراء**\n\n"
        "اخترِ الإجراء المطلوب من الأزرار أدناه:",
        reply_markup=keyboard
    )

threading.Thread(target=check_telegram_updates, daemon=True).start()


# --- 6. منطق المراقبة المستمرة والتنبيهات التدريجية ---
def monitor_binance_trading():
    global base_prices, current_prices, notified_stages
    print("Binance full-management strategy monitor started with official 24h metrics & progressive alerts...")
    
    while True:
        current_symbols = list(tracked_symbols.keys())
        
        for symbol in current_symbols:
            try:
                current_price, price_change_percent = get_market_data(symbol)
                
                if current_price == 0:
                    continue
                
                current_prices[symbol] = current_price
                
                if symbol not in base_prices or base_prices[symbol] is None or base_prices[symbol] == 0:
                    base_prices[symbol] = current_price
                    continue
                
                base_price = base_prices[symbol]
                config = tracked_symbols.get(symbol, {"buy_drop": 5.0, "sell_rise": 10.0})
                
                buy_drop_limit = config["buy_drop"]
                
                # حساب النسبة الداخلية بناءً على سعر الأساس للصفقة الحالية
                internal_change_percent = ((current_price - base_price) / base_price) * 100
                
                # 1. تنبيه الشراء
                if internal_change_percent <= -buy_drop_limit:
                    msg = (
                        f"🚨 **تنبيه شراء (فرصة دخول)**\n\n"
                        f"• العملة: `{symbol}`\n"
                        f"• سعر الأساس: `{base_price}`\n"
                        f"• السعر الحالي: `{current_price}`\n"
                        f"• نسبة الهبوط: `{internal_change_percent:.2f}%` 🔻\n\n"
                        f"💡 وصلت للحد المستهدَف للشراء برأس مال 20$!"
                    )
                    send_telegram_message(msg)
                    base_prices[symbol] = current_price
                    notified_stages[symbol] = {"3": False, "6": False, "10": False}
                
                # 2. التنبيهات التدريجية المرحلية للصعود نحو الـ 22$ (هدف الـ 10%)
                stages = [
                    (3.0, "🌱 **تنبيه مرحلي (1/3): اقتراب الموجة!**\n\n• العملة: `{symbol}`\n• صعدت بنسبة: `+3%`\n• رأس مالك الحالي يقترب من `20.60$` 🚀"),
                    (6.0, "📈 **تنبيه مرحلي (2/3): منتصف الطريق!**\n\n• العملة: `{symbol}`\n• صعدت بنسبة: `+6%`\n• رأس مالك الحالي يقترب من `21.20$` ✨"),
                    (10.0, "💰 **تنبيه هدف البيع النهائي (3/3): حققنا الـ 22$!**\n\n• العملة: `{symbol}`\n• سعر الشراء: `{base_price}`\n• السعر الحالي: `{current_price}`\n• نسبة الصعود: `+{internal_change_percent:.2f}%` 🎉\n\n💡 **مبروك يا مهندسة! رأس مالك وصل الآن إلى 22 دولاراً، يمكنكِ البيع الآن لجني الأرباح!**")
                ]
                
                for threshold, stage_text in stages:
                    stage_key = str(int(threshold))
                    if internal_change_percent >= threshold and not notified_stages[symbol][stage_key]:
                        msg = stage_text.format(symbol=symbol, base_price=base_price, current_price=current_price, internal_change_percent=internal_change_percent)
                        send_telegram_message(msg)
                        notified_stages[symbol][stage_key] = True
                        
                        # إذا وصل للهدف النهائي (10%)، إعادة ضبط السعر الأساسي لبدء دورة جديدة
                        if threshold == 10.0:
                            base_prices[symbol] = current_price
                    
            except Exception as e:
                print(f"Error checking {symbol}: {e}")
                
        time.sleep(60)

if __name__ == "__main__":
    monitor_binance_trading()
