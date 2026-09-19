import telebot
import sqlite3
import random
import time
import requests

BOT_TOKEN = "8860966276:AAFkwmNEIuHYgvcioBpvEQj-WeGM4aBVnJk"
ADMIN_ID = 8520025523

print("Bot başlatılıyor...")
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
GITHUB_STOCK_URL = "https://raw.githubusercontent.com/osmancan666283-create/cpm-bot/main/stok.txt"

def db_init():
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        cw_rk_balance REAL DEFAULT 0,
        is_vip BOOLEAN DEFAULT 0,
        vip_expire_time INTEGER DEFAULT 0,
        daily_spins INTEGER DEFAULT 1,
        last_spin_day TEXT DEFAULT '',
        last_daily_bonus TEXT DEFAULT ''
    )""")
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
    except Exception as e:
        print("Stok Hatası:", e)
    return None

def get_main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        telebot.types.KeyboardButton("🛒 VIP Hesap Mağazası"),
        telebot.types.KeyboardButton("⚡ Volt Coin Al"),
        telebot.types.KeyboardButton("🎁 Günlük Bonus (+20 Volt)"),
        telebot.types.KeyboardButton("👑 VIP Üyelik Al"),
        telebot.types.KeyboardButton("🎡 Şans Çarkı"),
        telebot.types.KeyboardButton("👤 Profilim")
    )
    return markup

def send_star_invoice(chat_id, title, description, payload, amount_in_stars):
    prices = [telebot.types.LabeledPrice(label=title, amount=amount_in_stars)]
    bot.send_invoice(
        chat_id=chat_id, title=title, description=description,
        invoice_payload=payload, provider_token="", currency="XTR", prices=prices, start_parameter="buy_stars"
    )

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (chat_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (chat_id,))
        conn.commit()
    conn.close()
    bot.send_message(chat_id, "👋 Hoş Geldin! Menüden seçim yapabilirsin:", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_menu_clicks(message):
    chat_id = message.chat.id
    text = message.text

    is_user_vip = check_vip_status(chat_id)
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT cw_rk_balance, is_vip, vip_expire_time, daily_spins, last_spin_day, last_daily_bonus FROM users WHERE user_id = ?", (chat_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (chat_id,))
        conn.commit()
        row = (0, 0, 0, 1, '', '')
    
    cwrk, is_vip, vip_expire, spins, last_day, last_bonus = row
    today = time.strftime("%Y-%m-%d")

    if text == "⚡ Volt Coin Al":
        bot.send_message(chat_id, "⚡ Volt Paketleri Seçin (Pahalı ve Güçlü):", reply_markup=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(
            telebot.types.KeyboardButton("⚡ 1 Volt (1,500 ⭐)"),
            telebot.types.KeyboardButton("⚡ 5,000 Volt (65,000 ⭐)"),
            telebot.types.KeyboardButton("⚡ 25,000 Volt (290,000 ⭐)"),
            telebot.types.KeyboardButton("⚡ 93,250 Volt (999,999 ⭐)"),
            telebot.types.KeyboardButton("⬅️ Ana Menü")
        ))

    elif text == "⚡ 1 Volt (1,500 ⭐)":
        send_star_invoice(chat_id, "1 Volt", "Volt Yükleme", "buy_volt_1", 1500)
    elif text == "⚡ 5,000 Volt (65,000 ⭐)":
        send_star_invoice(chat_id, "5000 Volt", "Volt Yükleme", "buy_volt_5000", 65000)
    elif text == "⚡ 25,000 Volt (290,000 ⭐)":
        send_star_invoice(chat_id, "25000 Volt", "Volt Yükleme", "buy_volt_25000", 290000)
    elif text == "⚡ 93,250 Volt (999,999 ⭐)":
        send_star_invoice(chat_id, "93250 Volt", "Volt Yükleme", "buy_volt_93250", 999999)

    elif text == "👑 VIP Üyelik Al":
        bot.send_message(chat_id, "👑 VIP Süresini Seçin (1 Aydan 36 Aya - Fena Pahalı):", reply_markup=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(
            telebot.types.KeyboardButton("👑 1 Ay VIP (5,000 ⭐)"),
            telebot.types.KeyboardButton("👑 6 Ay VIP (27,500 ⭐)"),
            telebot.types.KeyboardButton("👑 12 Ay VIP (50,000 ⭐)"),
            telebot.types.KeyboardButton("👑 36 Ay VIP (135,000 ⭐)"),
            telebot.types.KeyboardButton("⬅️ Ana Menü")
        ))

    elif text == "👑 1 Ay VIP (5,000 ⭐)":
        send_star_invoice(chat_id, "1 Ay VIP", "VIP Üyelik", "buy_vip_1m", 5000)
    elif text == "👑 6 Ay VIP (27,500 ⭐)":
        send_star_invoice(chat_id, "6 Ay VIP", "VIP Üyelik", "buy_vip_6m", 27500)
    elif text == "👑 12 Ay VIP (50,000 ⭐)":
        send_star_invoice(chat_id, "12 Ay VIP", "VIP Üyelik", "buy_vip_12m", 50000)
    elif text == "👑 36 Ay VIP (135,000 ⭐)":
        send_star_invoice(chat_id, "36 Ay VIP", "VIP Üyelik", "buy_vip_36m", 135000)

    elif text == "🛒 VIP Hesap Mağazası":
        send_star_invoice(chat_id, "VIP Hesap", "Hesap Mağazası", "buy_vip_acc_star", 2500)

    elif text == "🎁 Günlük Bonus (+20 Volt)":
        if last_bonus == today:
            bot.send_message(chat_id, "❌ Bugün zaten aldın!", reply_markup=get_main_keyboard())
        else:
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + 20, last_daily_bonus = ? WHERE user_id = ?", (today, chat_id))
            conn.commit()
            bot.send_message(chat_id, "🎉 +20 Volt Eklendi!", reply_markup=get_main_keyboard())

    elif text == "🎡 Şans Çarkı":
        if last_day != today:
            spins = 3 if is_user_vip else 1
            cursor.execute("UPDATE users SET daily_spins = ?, last_spin_day = ? WHERE user_id = ?", (spins, today, chat_id))
            conn.commit()

        if spins <= 0:
            bot.send_message(chat_id, "❌ Günlük çevirme hakkın bitti!", reply_markup=get_main_keyboard())
        else:
            won = round(random.uniform(1.0, 7.0), 2) if is_user_vip else round(random.uniform(1.0, 1.5), 2)
            new_spins = spins - 1
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + ?, daily_spins = ? WHERE user_id = ?", (won, new_spins, chat_id))
            conn.commit()
            bot.send_message(chat_id, f"🎡 Çark döndü...\n\n🎉 {won} Volt Kazandın!\nKalan hak: {new_spins}", reply_markup=get_main_keyboard())

    elif text == "👤 Profilim":
        bot.send_message(chat_id, f"👤 Profil\n🆔 ID: `{chat_id}`\n⚡ Bakiye: {cwrk} Volt", reply_markup=get_main_keyboard())

    elif text == "⬅️ Ana Menü":
        bot.send_message(chat_id, "✅ Ana Menüdesin.", reply_markup=get_main_keyboard())

    else:
        bot.send_message(chat_id, "Geçerli bir seçim yapın.", reply_markup=get_main_keyboard())

    conn.close()

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout_query(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    payload = message.successful_payment.invoice_payload
    chat_id = message.chat.id
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()

    volt_amounts = {
        "buy_volt_1": 1,
        "buy_volt_5000": 5000,
        "buy_volt_25000": 25000,
        "buy_volt_93250": 93250
    }

    vip_months = {
        "buy_vip_1m": 1,
        "buy_vip_6m": 6,
        "buy_vip_12m": 12,
        "buy_vip_36m": 36
    }

    if payload in volt_amounts:
        amt = volt_amounts[payload]
        cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + ? WHERE user_id = ?", (amt, chat_id))
        bot.send_message(chat_id, f"🎉 +{amt} Volt Yüklendi!", reply_markup=get_main_keyboard())

    elif payload in vip_months:
        months = vip_months[payload]
        days = months * 30
        cursor.execute("SELECT vip_expire_time FROM users WHERE user_id = ?", (chat_id,))
        row = cursor.fetchone()
        current_time = int(time.time())
        base_time = row[0] if row and row[0] > current_time else current_time
        expire_timestamp = base_time + (days * 24 * 3600)
        
        cursor.execute("UPDATE users SET is_vip = 1, vip_expire_time = ?, daily_spins = 3 WHERE user_id = ?", (expire_timestamp, chat_id))
        bot.send_message(chat_id, f"🎉 {months} Aylık VIP Üyeliğin Tanımlandı!", reply_markup=get_main_keyboard())

    elif payload == "buy_vip_acc_star":
        account = get_account_from_github_stock()
        if account:
            bot.send_message(chat_id, f"🎉 Hesap:\n`{account}`", reply_markup=get_main_keyboard())
        else:
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + 2810 WHERE user_id = ?", (chat_id,))
            bot.send_message(chat_id, "⚠️ Stokta hesap kalmadı, hesabına 2810 Volt eklendi!", reply_markup=get_main_keyboard())

    conn.commit()
    conn.close()

if __name__ == "__main__":
    db_init()
    print("Bot Kesintisiz Dinlemede...")
    bot.infinity_polling(skip_pending=True)
