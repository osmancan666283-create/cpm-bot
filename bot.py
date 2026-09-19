import telebot
import sqlite3
import random
import time
import string
import requests

BOT_TOKEN = "8860966276:AAGoD1jxA8vY-nTBttAuWgQOkUvMFWtQVsg"
ADMIN_ID = 8520025523

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
GITHUB_STOCK_URL = "https://raw.githubusercontent.com/osmancan666283-create/cpm-bot/main/stok.txt"

user_states = {}
MAINTENANCE_MODE = False

def generate_random_code():
    return "VOLT-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def db_init():
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, cw_rk_balance REAL DEFAULT 0, is_vip BOOLEAN DEFAULT 0, vip_expire_time INTEGER DEFAULT 0, daily_spins INTEGER DEFAULT 1, ticket_rights INTEGER DEFAULT 0, referred_by INTEGER, last_spin_day TEXT DEFAULT '', last_daily_bonus TEXT DEFAULT '', task_count INTEGER DEFAULT 0)")
    
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

    cursor.execute("CREATE TABLE IF NOT EXISTS dynamic_promo_codes (code TEXT PRIMARY KEY, reward_type TEXT, reward_value REAL DEFAULT 0, is_used INTEGER DEFAULT 0)")
    
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
    markup.add(
        telebot.types.KeyboardButton("🛒 VIP Hesap Mağazası"),
        telebot.types.KeyboardButton("⚡ Volt Coin Al"),
        telebot.types.KeyboardButton("🎁 Günlük Bonus (+20 Volt)"),
        telebot.types.KeyboardButton("🎯 Görev Yap & Kazan"),
        telebot.types.KeyboardButton("👑 VIP Üyelik Al"),
        telebot.types.KeyboardButton("🎡 Şans Çarkı"),
        telebot.types.KeyboardButton("🎟️ Sürpriz Promo Kod Al (8 Yıldız)"),
        telebot.types.KeyboardButton("🎟️ Promo Kod Kullan"),
        telebot.types.KeyboardButton("🎫 Biletlerim & Kullan"),
        telebot.types.KeyboardButton("👥 Arkadaşını Davet Et"),
        telebot.types.KeyboardButton("👤 Profilim")
    )
    return markup

def send_star_invoice(chat_id, title, description, payload, amount_in_stars):
    prices = [telebot.types.LabeledPrice(label=title, amount=amount_in_stars)]
    bot.send_invoice(chat_id=chat_id, title=title, description=description, invoice_payload=payload, provider_token="", currency="XTR", prices=prices, start_parameter="buy_stars")

@bot.message_handler(commands=['bakim'])
def toggle_maintenance(message):
    global MAINTENANCE_MODE
    if message.from_user.id != ADMIN_ID:
        return
    MAINTENANCE_MODE = not MAINTENANCE_MODE
    bot.send_message(message.chat.id, "⚙️ Bakım Durumu: " + ("ACILDI" if MAINTENANCE_MODE else "KAPATILDI"))

@bot.message_handler(commands=['vipver'])
def admin_give_vip(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        bot.send_message(message.chat.id, "Kullanim: /vipver <user_id>")
        return
    
    target_id = int(args[1])
    expire_timestamp = int(time.time()) + (30 * 24 * 3600) # 30 günlük VIP
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, is_vip, vip_expire_time, daily_spins) VALUES (?, 1, ?, 3)", (target_id, expire_timestamp))
    else:
        cursor.execute("UPDATE users SET is_vip = 1, vip_expire_time = ?, daily_spins = 3 WHERE user_id = ?", (expire_timestamp, target_id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ {target_id} ID'li kullanıcıya 30 günlük VIP üyelik tanımlandı!")

@bot.message_handler(commands=['ekle'])
def admin_add_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) != 3:
        bot.send_message(message.chat.id, "Kullanim: /ekle <user_id> <miktar>")
        return
    try:
        target_id = int(args[1])
        amount = float(args[2])
    except Exception:
        bot.send_message(message.chat.id, "Kullanim: /ekle <user_id> <miktar>")
        return

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
                    bot.send_message(ref_id, "🎉 Arkadaşın katıldı! +50 Volt kazandın.")
                except Exception:
                    pass
        cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (chat_id, ref_by))
        conn.commit()
    conn.close()
    bot.send_message(chat_id, "👋 Hoş Geldin! Menüden seçim yapabilirsin:", reply_markup=get_main_keyboard())

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

    if text == "⬅️ Ana Menü":
        user_states[chat_id] = None
        bot.send_message(chat_id, "✅ Ana Menüdesin.", reply_markup=get_main_keyboard())

    elif text == "🎯 Görev Yap & Kazan":
        task_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        task_markup.add(
            telebot.types.KeyboardButton("📢 Kanal Paylaşım Görevi Ekle"),
            telebot.types.KeyboardButton("🔍 Kanal Kontrol Et"),
            telebot.types.KeyboardButton("⬅️ Ana Menü")
        )
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
            won_reward = round(random.uniform(1.0, 5.0), 2)
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + ?, task_count = 15 WHERE user_id = ?", (won_reward, chat_id))
            conn.commit()
            bot.send_message(chat_id, f"🎉 15 Görev Tamamlandı! +{won_reward} Volt Eklendi!", reply_markup=get_main_keyboard())
        else:
            cursor.execute("UPDATE users SET task_count = ? WHERE user_id = ?", (task_count, chat_id))
            conn.commit()
            bot.send_message(chat_id, f"✅ Kaydedildi! İlerleme: {task_count} / 15", reply_markup=get_main_keyboard())

    elif text == "⚡ Volt Coin Al":
        bot.send_message(chat_id, "⚡ Volt Paketleri Seçin:", reply_markup=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(
            telebot.types.KeyboardButton("⚡ 1 Volt (50 ⭐)"),
            telebot.types.KeyboardButton("⚡ 500 Volt (350 ⭐)"),
            telebot.types.KeyboardButton("⚡ 1500 Volt (950 ⭐)"),
            telebot.types.KeyboardButton("⚡ 3000 Volt (1800 ⭐)"),
            telebot.types.KeyboardButton("⚡ 5800 Volt (3500 ⭐)"),
            telebot.types.KeyboardButton("⬅️ Ana Menü")
        ))

    elif text == "⚡ 1 Volt (50 ⭐)":
        send_star_invoice(chat_id, "1 Volt", "Yukleme", "buy_volt_1", 50)
    elif text == "⚡ 500 Volt (350 ⭐)":
        send_star_invoice(chat_id, "500 Volt", "Yukleme", "buy_volt_500", 350)
    elif text == "⚡ 1500 Volt (950 ⭐)":
        send_star_invoice(chat_id, "1500 Volt", "Yukleme", "buy_volt_1500", 950)
    elif text == "⚡ 3000 Volt (1800 ⭐)":
        send_star_invoice(chat_id, "3000 Volt", "Yukleme", "buy_volt_3000", 1800)
    elif text == "⚡ 5800 Volt (3500 ⭐)":
        send_star_invoice(chat_id, "5800 Volt", "Yukleme", "buy_volt_5800", 3500)

    elif text == "👑 VIP Üyelik Al":
        bot.send_message(chat_id, "👑 Süre Seçin:", reply_markup=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(
            telebot.types.KeyboardButton("👑 7 Günlük VIP (150 ⭐)"),
            telebot.types.KeyboardButton("👑 1 Aylık VIP (500 ⭐)"),
            telebot.types.KeyboardButton("👑 3 Aylık VIP (1,300 ⭐)"),
            telebot.types.KeyboardButton("⬅️ Ana Menü")
        ))

    elif text == "👑 7 Günlük VIP (150 ⭐)":
        send_star_invoice(chat_id, "7 Gunluk VIP", "VIP", "buy_vip_7d", 150)
    elif text == "👑 1 Aylık VIP (500 ⭐)":
        send_star_invoice(chat_id, "1 Aylik VIP", "VIP", "buy_vip_1m", 500)
    elif text == "👑 3 Aylık VIP (1,300 ⭐)":
        send_star_invoice(chat_id, "3 Aylik VIP", "VIP", "buy_vip_3m", 1300)

    elif text == "🛒 VIP Hesap Mağazası":
        bot.send_message(chat_id, "🛒 Mağaza:", reply_markup=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1).add(
            telebot.types.KeyboardButton("⭐ Yıldız İle Al (120 Yıldız)"),
            telebot.types.KeyboardButton("⚡ Volt İle Al (3 Volt)"),
            telebot.types.KeyboardButton("⬅️ Ana Menü")
        ))

    elif text == "⭐ Yıldız İle Al (120 Yıldız)":
        send_star_invoice(chat_id, "VIP Hesap", "Hesap", "buy_vip_acc_star", 120)

    elif text == "⚡ Volt İle Al (3 Volt)":
        if cwrk >= 3:
            account = get_account_from_github_stock()
            if account:
                cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance - 3 WHERE user_id = ?", (chat_id,))
                conn.commit()
                bot.send_message(chat_id, f"🎉 Hesap:\n`{account}`", reply_markup=get_main_keyboard())
            else:
                cursor.execute("UPDATE users SET cw_rk_balance = (cw_rk_balance - 3) + 2810 WHERE user_id = ?", (chat_id,))
                conn.commit()
                bot.send_message(chat_id, "⚠️ Stokta hesap kalmadi, hesabina 2810 Volt eklendi!", reply_markup=get_main_keyboard())
        else:
            bot.send_message(chat_id, f"❌ Yetersiz bakiye! Mevcut: {cwrk} Volt", reply_markup=get_main_keyboard())

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
            if is_user_vip:
                won = round(random.uniform(1.0, 7.0), 2)
            else:
                won = round(random.uniform(1.0, 1.5), 2)

            new_spins = spins - 1
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + ?, daily_spins = ? WHERE user_id = ?", (won, new_spins, chat_id))
            conn.commit()
            bot.send_message(chat_id, f"🎡 Çark döndü...\n\n🎉 {won} Volt Kazandın!\nKalan hak: {new_spins}", reply_markup=get_main_keyboard())

    elif text == "🎟️ Sürpriz Promo Kod Al (8 Yıldız)":
        send_star_invoice(chat_id, "Surpriz Kod", "Kod", "buy_surprise_promo", 8)

    elif text == "🎟️ Promo Kod Kullan":
        user_states[chat_id] = "waiting_promo"
        bot.send_message(chat_id, "🎟️ Kodunu yaz:")

    elif user_states.get(chat_id) == "waiting_promo":
        user_states[chat_id] = None
        input_code = text.strip().upper()
        
        cursor.execute("SELECT reward_value, is_used FROM dynamic_promo_codes WHERE code = ?", (input_code,))
        dyn_promo = cursor.fetchone()
        
        if dyn_promo:
            reward_val, is_used = dyn_promo
            if is_used == 0:
                cursor.execute("UPDATE dynamic_promo_codes SET is_used = 1 WHERE code = ?", (input_code,))
                cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + ? WHERE user_id = ?", (reward_val, chat_id))
                conn.commit()
                bot.send_message(chat_id, f"🎉 Tebrikler! Kod geçerliydi.\n⚡ Hesabınıza **+{reward_val} Volt** eklendi!", reply_markup=get_main_keyboard())
            else:
                bot.send_message(chat_id, "❌ Bu promosyon kodu daha önce başkası tarafından kullanılmış!", reply_markup=get_main_keyboard())
        else:
            bot.send_message(chat_id, "❌ Geçersiz veya hatalı kod!", reply_markup=get_main_keyboard())

    elif text == "🎫 Biletlerim & Kullan":
        bot.send_message(chat_id, f"🎫 Bilet Hakkın: {tickets}", reply_markup=get_main_keyboard())

    elif text == "👥 Arkadaşını Davet Et":
        try:
            invite_link = f"https://t.me/{bot.get_me().username}?start={chat_id}"
        except Exception:
            invite_link = f"https://t.me/BotHazirlikBot?start={chat_id}"
        bot.send_message(chat_id, f"👥 Davet Linkin:\n`{invite_link}`", reply_markup=get_main_keyboard())

    elif text == "👤 Profilim":
        vip_text = "👑 VIP Üye" if is_user_vip else "👤 Normal Üye"
        bot.send_message(chat_id, f"👤 Profil\n🆔 ID: `{chat_id}`\n⚡ Bakiye: {cwrk} Volt\nDurum: {vip_text}", reply_markup=get_main_keyboard())

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

    if payload.startswith("buy_volt_"):
        amounts = {"buy_volt_1": 1, "buy_volt_500": 500, "buy_volt_1500": 1500, "buy_volt_3000": 3000, "buy_volt_5800": 5800}
        amt = amounts.get(payload, 0)
        cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + ? WHERE user_id = ?", (amt, chat_id))
        bot.send_message(chat_id, f"🎉 +{amt} Volt Yüklendi!", reply_markup=get_main_keyboard())
    elif payload.startswith("buy_vip_"):
        expire_timestamp = int(time.time()) + (7 * 24 * 3600 if payload == "buy_vip_7d" else 30 * 24 * 3600)
        cursor.execute("UPDATE users SET is_vip = 1, vip_expire_time = ?, daily_spins = 3 WHERE user_id = ?", (expire_timestamp, chat_id))
        bot.send_message(chat_id, f"🎉 VIP Üyeliğin Tanımlandı!", reply_markup=get_main_keyboard())
    elif payload == "buy_surprise_promo":
        selected_reward = random.randint(1500, 8000)
        generated_code = generate_random_code()
        cursor.execute("INSERT INTO dynamic_promo_codes (code, reward_type, reward_value, is_used) VALUES (?, ?, ?, 0)", (generated_code, "volt", selected_reward))
        conn.commit()
        bot.send_message(chat_id, f"🎉 Sürpriz Kodun: `{generated_code}` ({selected_reward} Volt)", reply_markup=get_main_keyboard())
    elif payload == "buy_vip_acc_star":
        account = get_account_from_github_stock()
        if account:
            bot.send_message(chat_id, f"🎉 Hesap:\n`{account}`", reply_markup=get_main_keyboard())
        else:
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + 2810 WHERE user_id = ?", (chat_id,))
            conn.commit()
            bot.send_message(chat_id, "⚠️ Stokta hesap kalmadi, hesabina 2810 Volt eklendi!", reply_markup=get_main_keyboard())

    conn.commit()
    conn.close()

db_init()
print("Bot Çalışıyor ve Dinlemede...")
bot.infinity_polling(none_stop=True)
