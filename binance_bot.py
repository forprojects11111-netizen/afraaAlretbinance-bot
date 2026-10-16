if text == "/start":
    user_states[CHAT_ID] = None
    # 1. إرسال القائمة الرئيسية النظيفة
    send_main_menu()
    
    # 2. حذف الرسالة السابقة المزعجة تلقائياً لو أرسلها المشروع القديم
    message_id = message.get("message_id")
    if message_id:
        try:
            # حذف الرسالة التي تحتوي على رابط القناة (الرسالة التالية للـ start)
            delete_url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
            requests.post(delete_url, json={"chat_id": CHAT_ID, "message_id": message_id + 1})
        except Exception:
            pass
