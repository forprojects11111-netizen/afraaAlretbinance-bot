import time
import traceback
import requests

TELEGRAM_BOT_TOKEN = "8979107331:AAEu-Wj3yT9k098z7T6w7z4..."  # توكن البوت الخاص بك
CHAT_ID = "7841120409"  # معرف الشات الخاص بك

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"خطأ في إرسال التنبيه: {e}")

def run_bot():
    print("🚀 جاري تشغيل بوت مراقبة بايننس بنجاح...")
    send_telegram_message("🤖 **مرحباً مهندسة!** تم تشغيل بوت مراقبة بايننس بنجاح على السيرفر السحابي وتفعيل الإشعارات الدائمة.")
    
    while True:
        # هنا يتم وضع فحص الأسواق والتنبيهات المستمرة
        time.sleep(60)

if __name__ == "__main__":
    while True:
        try:
            run_bot()
        except Exception as e:
            print(f"⚠️ حدث خطأ: {e}")
            traceback.print_exc()
            print("🔄 جاري إعادة تشغيل النظام تلقائياً...")
            time.sleep(10)
