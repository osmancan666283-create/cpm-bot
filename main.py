import telebot
import sqlite3
import random
import time
import string
import requests

BOT_TOKEN = "8860966276:AAGoD1jxA8vY-nTBttAuWgQOkUvMFWtQVsg"
ADMIN_ID = 8520025523

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
GITHUB_STOCK_URL = "https://raw.githubusercontent.com/KULLANICI_ADI/REPO_ADI/main/stok.txt"

user_states = {}
user_temp_data = {}  
MAINTENANCE_MODE = False

def generate_random_code():
    return "CPMRK-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def db_init():
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        cw_rk_balance INTEGER DEFAULT 0,
        is_vip BOOLEAN DEFAULT 0,
        vip_expire_time INTEGER DEFAULT 0,
        daily_spins INTEGER DEFAULT 1,
        ticket_rights INTEGER DEFAULT 0,
        referred_by INTEGER,
        last_spin_day TEXT DEFAULT '',
        last_daily_bonus TEXT DEFAULT '',
        task_count INTEGER DEFAULT 0
    )""")
    
    migrations = [
        "ALTER TABLE users ADD COLUMN vip_expire_time INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN daily_spins INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN ticket_rights INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN referred_by INTEGER",
        "ALTER TABLE users ADD COLUMN last_spin_day TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN last_daily_bonus TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN task_count INTEGER DEFAULT 0"
    ]
    for mig in migrations:
        try:
            cursor.execute(mig)
        except sqlite3.OperationalError:
            pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dynamic_promo_codes (
        code TEXT PRIMARY KEY,
        reward_type TEXT,
        reward_value INTEGER DEFAULT 0,
        is_used INTEGER DEFAULT 0
    )""")
    
    try:
        cursor.execute("ALTER TABLE dynamic_promo_codes ADD COLUMN is_used INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

def check_vip_status(user_id):
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_vip, vip_expire_time FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] == 1:
        if int(time.time()) >= row[1]:
            cursor.execute("UPDATE users SET is_vip = 0, vip_expire_time = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            return False
        conn.close()
        return True
    conn.close()
    return False

def get_account_from_github_stock():
    try:
        response = requests.get(GITHUB_STOCK_URL, timeout=5)
        if response.status_code == 200:
            lines = [line.strip() for line in response.text.splitlines() if line.strip()]
            if lines:
                return random.choice(lines)
    except Exception:
        pass
    return None

def get_main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(telebot.types.KeyboardButton("🛒 VIP Hesap Mağazası"))
    markup.add(telebot.types.KeyboardButton("⚡ Volt Coin Al"))
    markup.add(telebot.types.KeyboardButton("🎁 Günlük Bonus (+20 Volt)"))
    markup.add(telebot.types.KeyboardButton("🎯 Görev Yap & Kazan"))
    markup.add(telebot.types.KeyboardButton("👑 VIP Üyelik Al"))
    markup.add(telebot.types.KeyboardButton("🎡 Şans Çarkı"))
    markup.add(telebot.types.KeyboardButton("🎟️ Sürpriz Promo Kod Al (8 Yıldız)"))
    markup.add(telebot.types.KeyboardButton("🎟️ Promo Kod Kullan"))
    markup.add(telebot.types.KeyboardButton("🎫 Biletlerim & Kullan"))
    markup.add(telebot.types.KeyboardButton("🎮 CPM1 İşlemleri"))
    markup.add(telebot.types.KeyboardButton("🎮 CPM2 İşlemleri"))
    markup.add(telebot.types.KeyboardButton("👥 Arkadaşını Davet Et"))
    markup.add(telebot.types.KeyboardButton("👤 Profilim"))
    return markup

def send_star_invoice(chat_id, title, description, payload, amount_in_stars):
    prices = [telebot.types.LabeledPrice(label=title, amount=amount_in_stars)]
    bot.send_invoice(
        chat_id=chat_id, title=title, description=description,
        invoice_payload=payload, provider_token="", currency="XTR", prices=prices, start_parameter="buy_stars"
    )

@bot.message_handler(commands=['bakim'])
def toggle_maintenance(message):
    global MAINTENANCE_MODE
    if message.from_user.id != ADMIN_ID:
        return
    MAINTENANCE_MODE = not MAINTENANCE_MODE
    bot.send_message(message.chat.id, "⚙️ Bakım Durumu: " + ("ACILDI" if MAINTENANCE_MODE else "KAPATILDI"))

@bot.message_handler(commands=['toplukod'])
def admin_create_bulk_codes(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        bot.send_message(message.chat.id, "Kullanim: /toplukod <adet>")
        return
    
    count = int(args[1])
    if count > 200:
        bot.send_message(message.chat.id, "⚠️ Tek seferde en fazla 200 kod üretebilirsin.")
        return

    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    generated_list = []
    for _ in range(count):
        code = generate_random_code()
        reward_val = random.randint(1500, 8000)
        cursor.execute("INSERT OR REPLACE INTO dynamic_promo_codes (code, reward_type, reward_value, is_used) VALUES (?, ?, ?, 0)", (code, "volt", reward_val))
        generated_list.append(f"`{code}` ({reward_val} Volt)")

    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, f"✅ Başarıyla {count} adet kod üretildi!")
    chunk_size = 30
    for i in range(0, len(generated_list), chunk_size):
        text_chunk = "\n".join(generated_list[i:i + chunk_size])
        bot.send_message(message.chat.id, f"📋 **Kod Listesi:**\n\n" + text_chunk)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    global MAINTENANCE_MODE
    if MAINTENANCE_MODE and chat_id != ADMIN_ID:
        bot.send_message(chat_id, "🛠️ Bot şu an bakımda.")
        return

    args = message.text.split()
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (chat_id,))
    if not cursor.fetchone():
        ref_by = None
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
            if ref_id != chat_id:
                ref_by = ref_id
                cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + 50 WHERE user_id = ?", (ref_id,))
                try:
                    bot.send_message(ref_id, "🎉 Arkadaşın katıldı! +50 Volt Coin kazandın.")
                except Exception:
                    pass
        cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (chat_id, ref_by))
        conn.commit()
    conn.close()
    bot.send_message(chat_id, "👋 Hoş Geldin NEYOM! Menüden seçim yapabilirsin:", reply_markup=get_main_keyboard())

@bot.message_handler(commands=['ekle'])
def admin_add_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
        bot.send_message(message.chat.id, "Kullanim: /ekle <user_id> <miktar>")
        return
    target_id, amount = int(args[1]), int(args[2])
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, cw_rk_balance) VALUES (?, ?)", (target_id, amount))
    else:
        cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + ? WHERE user_id = ?", (amount, target_id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ {target_id} ID'li kullanıcıya +{amount} Volt eklendi.")

@bot.message_handler(commands=['sifirla'])
def admin_reset_db(message):
    if message.from_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS dynamic_promo_codes")
    conn.commit()
    conn.close()
    db_init()
    bot.send_message(message.chat.id, "🗑️ Veritabanı sıfırlandı!")

@bot.message_handler(func=lambda message: True)
def handle_menu_clicks(message):
    chat_id = message.chat.id
    text = message.text
    global MAINTENANCE_MODE
    if MAINTENANCE_MODE and chat_id != ADMIN_ID:
        bot.send_message(chat_id, "🛠️ Bot bakımda.")
        return

    is_user_vip = check_vip_status(chat_id)
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT cw_rk_balance, is_vip, daily_spins, ticket_rights, last_spin_day, last_daily_bonus, task_count FROM users WHERE user_id = ?", (chat_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (chat_id,))
        conn.commit()
        row = (0, 0, 1, 0, '', '', 0)
    
    cwrk, is_vip, spins, tickets, last_day, last_bonus, task_count = row
    today = time.strftime("%Y-%m-%d")

    current_state = user_states.get(chat_id)

    # --- CPM1 & CPM2 DOĞRULAMA VE İŞLEM KONTROLLERİ ---
    
    if current_state == "cpm1_email_1":
        val = text.strip()
        if "@" not in val or "cpm2" in val.lower():
            user_states[chat_id] = None
            user_temp_data.pop(chat_id, None)
            bot.send_message(chat_id, "❌ **Geçersiz bilgi!** Bu bilgiler CPM1 ile uyuşmuyor. İşlem iptal edildi.", reply_markup=get_main_keyboard())
            conn.close()
            return
        user_temp_data[chat_id] = val
        user_states[chat_id] = "cpm1_email_2"
        bot.send_message(chat_id, "📧 CPM1 Yeni E-Postanızı **tekrar girin** (Doğrulama):")
        conn.close()
        return

    elif current_state == "cpm1_email_2":
        val2 = text.strip()
        first_val = user_temp_data.get(chat_id)
        user_states[chat_id] = None
        user_temp_data.pop(chat_id, None)

        if val2 != first_val:
            bot.send_message(chat_id, "❌ **Geçersiz bilgi!** E-postalar eşleşmiyor. İşlem iptal edildi.", reply_markup=get_main_keyboard())
            conn.close()
            return

        if cwrk >= 1:
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance - 1 WHERE user_id = ?", (chat_id,))
            conn.commit()
            bot.send_message(chat_id, f"✅ **CPM1 İşlem Başarılı!**\n📧 Yeni E-Posta: `{val2}`\n⚡ Harcanan: 1 Volt | Kalan: {cwrk - 1}", reply_markup=get_main_keyboard())
        else:
            bot.send_message(chat_id, f"❌ Yetersiz bakiye! 1 Volt gerekiyor. Mevcut: {cwrk}", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif current_state == "cpm1_pass_1":
        val = text.strip()
        if len(val) < 4:
            user_states[chat_id] = None
            user_temp_data.pop(chat_id, None)
            bot.send_message(chat_id, "❌ **Geçersiz bilgi!** CPM1 şifre kurallarına uymuyor. İşlem iptal edildi.", reply_markup=get_main_keyboard())
            conn.close()
            return
        user_temp_data[chat_id] = val
        user_states[chat_id] = "cpm1_pass_2"
        bot.send_message(chat_id, "🔑 CPM1 Yeni Şifrenizi **tekrar girin** (Doğrulama):")
        conn.close()
        return

    elif current_state == "cpm1_pass_2":
        val2 = text.strip()
        first_val = user_temp_data.get(chat_id)
        user_states[chat_id] = None
        user_temp_data.pop(chat_id, None)

        if val2 != first_val:
            bot.send_message(chat_id, "❌ **Geçersiz bilgi!** Şifreler eşleşmiyor. İşlem iptal edildi.", reply_markup=get_main_keyboard())
            conn.close()
            return

        if cwrk >= 1:
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance - 1 WHERE user_id = ?", (chat_id,))
            conn.commit()
            bot.send_message(chat_id, f"✅ **CPM1 İşlem Başarılı!**\n🔑 Yeni Şifre: `{val2}`\n⚡ Harcanan: 1 Volt | Kalan: {cwrk - 1}", reply_markup=get_main_keyboard())
        else:
            bot.send_message(chat_id, f"❌ Yetersiz bakiye! 1 Volt gerekiyor. Mevcut: {cwrk}", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif current_state == "cpm2_email_1":
        val = text.strip()
        if "@" not in val or "cpm1" in val.lower():
            user_states[chat_id] = None
            user_temp_data.pop(chat_id, None)
            bot.send_message(chat_id, "❌ **Geçersiz bilgi!** Bu bilgiler CPM2 ile uyuşmuyor. İşlem iptal edildi.", reply_markup=get_main_keyboard())
            conn.close()
            return
        user_temp_data[chat_id] = val
        user_states[chat_id] = "cpm2_email_2"
        bot.send_message(chat_id, "📧 CPM2 Yeni E-Postanızı **tekrar girin** (Doğrulama):")
        conn.close()
        return

    elif current_state == "cpm2_email_2":
        val2 = text.strip()
        first_val = user_temp_data.get(chat_id)
        user_states[chat_id] = None
        user_temp_data.pop(chat_id, None)

        if val2 != first_val:
            bot.send_message(chat_id, "❌ **Geçersiz bilgi!** E-postalar eşleşmiyor. İşlem iptal edildi.", reply_markup=get_main_keyboard())
            conn.close()
            return

        if cwrk >= 1:
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance - 1 WHERE user_id = ?", (chat_id,))
            conn.commit()
            bot.send_message(chat_id, f"✅ **CPM2 İşlem Başarılı!**\n📧 Yeni E-Posta: `{val2}`\n⚡ Harcanan: 1 Volt | Kalan: {cwrk - 1}", reply_markup=get_main_keyboard())
        else:
            bot.send_message(chat_id, f"❌ Yetersiz bakiye! 1 Volt gerekiyor. Mevcut: {cwrk}", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif current_state == "cpm2_pass_1":
        val = text.strip()
        if len(val) < 6:
            user_states[chat_id] = None
            user_temp_data.pop(chat_id, None)
            bot.send_message(chat_id, "❌ **Geçersiz bilgi!** CPM2 şifre en az 6 karakter olmalıdır. İşlem iptal edildi.", reply_markup=get_main_keyboard())
            conn.close()
            return
        user_temp_data[chat_id] = val
        user_states[chat_id] = "cpm2_pass_2"
        bot.send_message(chat_id, "🔑 CPM2 Yeni Şifrenizi **tekrar girin** (Doğrulama):")
        conn.close()
        return

    elif current_state == "cpm2_pass_2":
        val2 = text.strip()
        first_val = user_temp_data.get(chat_id)
        user_states[chat_id] = None
        user_temp_data.pop(chat_id, None)

        if val2 != first_val:
            bot.send_message(chat_id, "❌ **Geçersiz bilgi!** Şifreler eşleşmiyor. İşlem iptal edildi.", reply_markup=get_main_keyboard())
            conn.close()
            return

        if cwrk >= 1:
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance - 1 WHERE user_id = ?", (chat_id,))
            conn.commit()
            bot.send_message(chat_id, f"✅ **CPM2 İşlem Başarılı!**\n🔑 Yeni Şifre: `{val2}`\n⚡ Harcanan: 1 Volt | Kalan: {cwrk - 1}", reply_markup=get_main_keyboard())
        else:
            bot.send_message(chat_id, f"❌ Yetersiz bakiye! 1 Volt gerekiyor. Mevcut: {cwrk}", reply_markup=get_main_keyboard())
        conn.close()
        return

    # --- NORMAL MENÜ İŞLEMLERİ ---
    if text == "⬅️ Ana Menü":
        user_states[chat_id] = None
        user_temp_data.pop(chat_id, None)
        bot.send_message(chat_id, "✅ Ana Menüdesin.", reply_markup=get_main_keyboard())

    elif text == "🎮 CPM1 İşlemleri":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(telebot.types.KeyboardButton("🔒 CPM1 Mail Değiş (1 Volt)"))
        markup.add(telebot.types.KeyboardButton("🔑 CPM1 Şifre Değiş (1 Volt)"))
        markup.add(telebot.types.KeyboardButton("⬅️ Ana Menü"))
        bot.send_message(chat_id, "🎮 **CPM1 İşlem Menüsü:**", reply_markup=markup)

    elif text == "🎮 CPM2 İşlemleri":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(telebot.types.KeyboardButton("🔒 CPM2 Mail Değiş (1 Volt)"))
        markup.add(telebot.types.KeyboardButton("🔑 CPM2 Şifre Değiş (1 Volt)"))
        markup.add(telebot.types.KeyboardButton("⬅️ Ana Menü"))
        bot.send_message(chat_id, "🎮 **CPM2 İşlem Menüsü:**", reply_markup=markup)

    elif text == "🔒 CPM1 Mail Değiş (1 Volt)":
        if cwrk >= 1:
            user_states[chat_id] = "cpm1_email_1"
            bot.send_message(chat_id, "📧 **CPM1 Yeni E-Posta Adresini Girin:**")
        else:
            bot.send_message(chat_id, f"❌ Yetersiz bakiye! Mevcut: {cwrk}", reply_markup=get_main_keyboard())

    elif text == "🔑 CPM1 Şifre Değiş (1 Volt)":
        if cwrk >= 1:
            user_states[chat_id] = "cpm1_pass_1"
            bot.send_message(chat_id, "🔑 **CPM1 Yeni Şifrenizi Girin:**")
        else:
            bot.send_message(chat_id, f"❌ Yetersiz bakiye! Mevcut: {cwrk}", reply_markup=get_main_keyboard())

    elif text == "🔒 CPM2 Mail Değiş (1 Volt)":
        if cwrk >= 1:
            user_states[chat_id] = "cpm2_email_1"
            bot.send_message(chat_id, "📧 **CPM2 Yeni E-Posta Adresini Girin:**")
        else:
            bot.send_message(chat_id, f"❌ Yetersiz bakiye! Mevcut: {cwrk}", reply_markup=get_main_keyboard())

    elif text == "🔑 CPM2 Şifre Değiş (1 Volt)":
        if cwrk >= 1:
            user_states[chat_id] = "cpm2_pass_1"
            bot.send_message(chat_id, "🔑 **CPM2 Yeni Şifrenizi Girin:**")
        else:
            bot.send_message(chat_id, f"❌ Yetersiz bakiye! Mevcut: {cwrk}", reply_markup=get_main_keyboard())

    elif text == "🎯 Görev Yap & Kazan":
        task_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        task_markup.add(telebot.types.KeyboardButton("📢 Kanal Paylaşım Görevi Ekle"))
        task_markup.add(telebot.types.KeyboardButton("🔍 Kanal Kontrol Et"))
        task_markup.add(telebot.types.KeyboardButton("⬅️ Ana Menü"))
        bot.send_message(chat_id, f"🎯 Görev Merkezi\n\n📊 İlerleme: {task_count} / 15", reply_markup=task_markup)

    elif text == "🔍 Kanal Kontrol Et":
        bot.send_message(chat_id, f"📊 Toplam Paylaşım: {task_count} / 15", reply_markup=get_main_keyboard())

    elif text == "📢 Kanal Paylaşım Görevi Ekle":
        if task_count >= 15:
            bot.send_message(chat_id, "✅ Zaten 15 görevi tamamladın!", reply_markup=get_main_keyboard())
        else:
            user_states[chat_id] = "waiting_channel_link"
            bot.send_message(chat_id, "📢 Paylaşım yaptığın kanalın linkini gönder:")

    elif user_states.get(chat_id) == "waiting_channel_link":
        user_states[chat_id] = None
        task_count += 1
        if task_count >= 15:
            won_reward = random.choice([250, 500, 750, 1000])
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + ?, task_count = 15 WHERE user_id = ?", (won_reward, chat_id))
            conn.commit()
            bot.send_message(chat_id, f"🎉 15 Görev Tamamlandı! +{won_reward} Volt Coin Eklendi!", reply_markup=get_main_keyboard())
        else:
            cursor.execute("UPDATE users SET task_count = ? WHERE user_id = ?", (task_count, chat_id))
            conn.commit()
            bot.send_message(chat_id, f"✅ Kaydedildi! İlerleme: {task_count} / 15", reply_markup=get_main_keyboard())

    elif text == "⚡ Volt Coin Al":
        volt_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        volt_markup.add(telebot.types.KeyboardButton("🔹 100 Volt (50 ⭐)"))
        volt_markup.add(telebot.types.KeyboardButton("🔹 250 Volt (110 ⭐)"))
        volt_markup.add(telebot.types.KeyboardButton("🔹 500 Volt (200 ⭐)"))
        volt_markup.a
