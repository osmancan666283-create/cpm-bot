import os
import random
import sqlite3
import string
import threading
import time
import datetime
import requests
from flask import Flask
import telebot

# --- 1. AYARLAR VE TOKEN ---
TOKEN = "8860966276:AAGoD1jxA8vY-nTBttAuWgQOkUvMFWtQVsg"
ADMIN_ID = 8520025523
GITHUB_STOCK_URL = "https://raw.githubusercontent.com/osmancan666283-create/cpm-bot/main/stok.txt"

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- 2. FLASK KEEP-ALIVE (Sunucu Çökmesini Önleyen Web Katmanı) ---
app = Flask('')

@app.route('/')
def home():
    return "Volt Coin CPM Bot 7/24 Aktif ve Çalışıyor, NEYOM!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 3. VERİTABANI BAĞLANTISI VE TABLOLAR ---
def db_init():
    conn = sqlite3.connect("cpm_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        cw_rk_balance INTEGER DEFAULT 0,
        is_vip BOOLEAN DEFAULT 0,
        vip_expire_time INTEGER DEFAULT 0,
        daily_spins_used INTEGER DEFAULT 0,
        ticket_rights INTEGER DEFAULT 0,
        referred_by INTEGER,
        last_spin_date TEXT DEFAULT '',
        last_daily_bonus TEXT DEFAULT '',
        task_count INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()

db_init()

# Bellek Durum Yönetimi (State & Temp Data)
user_states = {}
user_temp_data = {}
MAINTENANCE_MODE = False

# --- 4. ANA KLAVYE MENÜSÜ ---
def get_main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        telebot.types.KeyboardButton("🛒 VIP Hesap Mağazası"),
        telebot.types.KeyboardButton("⚡ Volt Coin Al"),
        telebot.types.KeyboardButton("🎁 Günlük Bonus (+20 Volt)"),
        telebot.types.KeyboardButton("🎯 Görev Yap & Kazan"),
        telebot.types.KeyboardButton("👑 VIP Üyelik Al"),
        telebot.types.KeyboardButton("🎡 Şans Çarkı"),
        telebot.types.KeyboardButton("🎟️ Sürpriz Promo Kod Al"),
        telebot.types.KeyboardButton("🎟️ Promo Kod Kullan"),
        telebot.types.KeyboardButton("🎫 Biletlerim & Kullan"),
        telebot.types.KeyboardButton("🎮 CPM1 İşlemleri"),
        telebot.types.KeyboardButton("🎮 CPM2 İşlemleri"),
        telebot.types.KeyboardButton("👥 Arkadaşını Davet Et"),
        telebot.types.KeyboardButton("👤 Profilim")
    )
    return markup

# --- 5. KOMUTLAR VE BAŞLANGIÇ ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if MAINTENANCE_MODE and chat_id != ADMIN_ID:
        bot.send_message(chat_id, "🛠️ Bot şu an bakımda NEYOM, birazdan aktif olur.")
        return

    conn = sqlite3.connect("cpm_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (chat_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (chat_id,))
        conn.commit()
    conn.close()

    bot.send_message(chat_id, "👋 Hoş Geldin NEYOM! Volt Coin CPM Yönetim Paneline bağlandın. Seçimini yap:", reply_markup=get_main_keyboard())

@bot.message_handler(commands=['bakim'])
def toggle_maintenance(message):
    global MAINTENANCE_MODE
    if message.from_user.id != ADMIN_ID:
        return
    MAINTENANCE_MODE = not MAINTENANCE_MODE
    bot.send_message(message.chat.id, "⚙️ Bakım Modu: " + ("ACILDI" if MAINTENANCE_MODE else "KAPATILDI"))

@bot.message_handler(commands=['ekle'])
def admin_add_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
        bot.send_message(message.chat.id, "Kullanım: /ekle <user_id> <miktar>")
        return
    target_id, amount = int(args[1]), int(args[2])
    conn = sqlite3.connect("cpm_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + ? WHERE user_id = ?", (amount, target_id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ {target_id} ID'li kullanıcıya +{amount} Volt eklendi.")

# --- 6. TÜM MENÜ VE BUTON YÖNETİMİ ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text

    if MAINTENANCE_MODE and chat_id != ADMIN_ID:
        bot.send_message(chat_id, "🛠️ Bot bakımda.")
        return

    conn = sqlite3.connect("cpm_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT cw_rk_balance, is_vip, daily_spins_used, ticket_rights, last_spin_date, task_count FROM users WHERE user_id = ?", (chat_id,))
    row = cursor.fetchone()
    
    today_str = datetime.date.today().isoformat()

    if not row:
        cursor.execute("INSERT INTO users (user_id, last_spin_date) VALUES (?, ?)", (chat_id, today_str))
        conn.commit()
        cwrk, is_vip, spins_used, tickets, last_spin, task_count = 0, 0, 0, 0, today_str, 0
    else:
        cwrk, is_vip, spins_used, tickets, last_spin, task_count = row
        if last_spin != today_str:
            cursor.execute("UPDATE users SET daily_spins_used = 0, last_spin_date = ? WHERE user_id = ?", (today_str, chat_id))
            conn.commit()
            spins_used = 0

    current_state = user_states.get(chat_id)

    # --- DURUM (STATE) YÖNETİMİ (Mail / Şifre Girişleri) ---
    if current_state == "waiting_cpm1_mail":
        user_states[chat_id] = None
        bot.send_message(chat_id, f"✅ CPM1 E-posta değiştirme talebin alındı NEYOM!\nGirilen E-posta: `{text}`\n⚙️ İşlem sıraya konuldu.", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif current_state == "waiting_cpm1_pass":
        user_states[chat_id] = None
        bot.send_message(chat_id, f"✅ CPM1 Şifre değiştirme talebin alındı NEYOM!\nGirilen Şifre: `{text}`\n⚙️ İşlem sıraya konuldu.", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif current_state == "waiting_cpm2_mail":
        user_states[chat_id] = None
        bot.send_message(chat_id, f"✅ CPM2 E-posta değiştirme talebin alındı NEYOM!\nGirilen E-posta: `{text}`\n⚙️ İşlem sıraya konuldu.", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif current_state == "waiting_cpm2_pass":
        user_states[chat_id] = None
        bot.send_message(chat_id, f"✅ CPM2 Şifre değiştirme talebin alındı NEYOM!\nGirilen Şifre: `{text}`\n⚙️ İşlem sıraya konuldu.", reply_markup=get_main_keyboard())
        conn.close()
        return

    # --- CPM1 İŞLEMLERİ ALT MENÜ ---
    if text == "🎮 CPM1 İşlemleri":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(
            telebot.types.KeyboardButton("🔒 CPM1 Mail Değiş (1 Volt)"),
            telebot.types.KeyboardButton("🔑 CPM1 Şifre Değiş (1 Volt)"),
            telebot.types.KeyboardButton("⬅️ Ana Menü")
        )
        bot.send_message(chat_id, "🎮 **CPM1 İşlem Paneli:**", reply_markup=markup)
        conn.close()
        return

    elif text == "🔒 CPM1 Mail Değiş (1 Volt)":
        user_states[chat_id] = "waiting_cpm1_mail"
        bot.send_message(chat_id, "📧 Lütfen yeni yapmak istediğin **CPM1 E-posta adresini** yaz NEYOM:")
        conn.close()
        return

    elif text == "🔑 CPM1 Şifre Değiş (1 Volt)":
        user_states[chat_id] = "waiting_cpm1_pass"
        bot.send_message(chat_id, "🔑 Lütfen yeni yapmak istediğin **CPM1 şifresini** yaz NEYOM:")
        conn.close()
        return

    # --- CPM2 İŞLEMLERİ ALT MENÜ ---
    elif text == "🎮 CPM2 İşlemleri":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(
            telebot.types.KeyboardButton("🔒 CPM2 Mail Değiş (1 Volt)"),
            telebot.types.KeyboardButton("🔑 CPM2 Şifre Değiş (1 Volt)"),
            telebot.types.KeyboardButton("⬅️ Ana Menü")
        )
        bot.send_message(chat_id, "🎮 **CPM2 İşlem Paneli:**", reply_markup=markup)
        conn.close()
        return

    elif text == "🔒 CPM2 Mail Değiş (1 Volt)":
        user_states[chat_id] = "waiting_cpm2_mail"
        bot.send_message(chat_id, "📧 Lütfen yeni yapmak istediğin **CPM2 E-posta adresini** yaz NEYOM:")
        conn.close()
        return

    elif text == "🔑 CPM2 Şifre Değiş (1 Volt)":
        user_states[chat_id] = "waiting_cpm2_pass"
        bot.send_message(chat_id, "🔑 Lütfen yeni yapmak istediğin **CPM2 şifresini** yaz NEYOM:")
        conn.close()
        return

    # --- ANA MENÜ VE DİĞER BUTONLAR ---
    elif text == "⬅️ Ana Menü":
        user_states[chat_id] = None
        user_temp_data.pop(chat_id, None)
        bot.send_message(chat_id, "✅ Ana Menüdesin NEYOM.", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif text == "👤 Profilim":
        vip_status_text = "Aktif (5 Hak/Gün)" if is_vip else "Normal Üye (2 Hak/Gün)"
        bot.send_message(chat_id, f"👤 **Profil Bilgilerin NEYOM:**\n\n🆔 ID: `{chat_id}`\n⚡ Volt Bakiye: **{cwrk} Volt**\n👑 VIP Durumu: **{vip_status_text}**\n🎫 Bilet Hakları: {tickets}", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif text == "🎡 Şans Çarkı":
        max_limit = 5 if is_vip else 2
        if last_spin != today_str:
            spins_used = 0
            
        if spins_used >= max_limit:
            bot.send_message(chat_id, f"⚠️ Günlük şans çarkı hakkın bitti NEYOM!\n\n📌 Hakkın: **{spins_used}/{max_limit}**\n💡 Yarın tekrar deneyebilir veya VIP alarak hakkını 5'e çıkarabilirsin!", reply_markup=get_main_keyboard())
            conn.close()
            return

        reward = random.choice([10, 25, 50, 100, 200])
        new_spins_used = spins_used + 1
        cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + ?, daily_spins_used = ?, last_spin_date = ? WHERE user_id = ?", (reward, new_spins_used, today_str, chat_id))
        conn.commit()
        
        bot.send_message(chat_id, f"🎡 Çark çevrildi NEYOM!\n🎁 Kazandığın Ödül: **+{reward} Volt Coin**\n📊 Kalan Hak: **{max_limit - new_spins_used}/{max_limit}**", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif text == "🎁 Günlük Bonus (+20 Volt)":
        cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + 20 WHERE user_id = ?", (chat_id,))
        conn.commit()
        bot.send_message(chat_id, "🎁 Günlük bonusun eklendi: **+20 Volt!**", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif text == "🛒 VIP Hesap Mağazası":
        bot.send_message(chat_id, "🛒 **VIP Hesap Mağazası:** Stoklar güncelleniyor NEYOM, yakında aktif olacak.", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif text == "⚡ Volt Coin Al":
        bot.send_message(chat_id, "⚡ Volt Coin kazanmak için **Şans Çarkı** çevirebilir, **Günlük Bonus** alabilir veya **Görev Yapabilirsiniz** NEYOM!", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif text == "🎯 Görev Yap & Kazan":
        bot.send_message(chat_id, "🎯 Aktif görev bulunmuyor NEYOM. İlerleyen saatlerde tekrar kontrol et!", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif text == "👑 VIP Üyelik Al":
        bot.send_message(chat_id, "👑 VIP üyelik sayesinde çark hakkını günde 5'e çıkarabilir ve özel avantajlar elde edebilirsin NEYOM!", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif text == "🎟️ Sürpriz Promo Kod Al":
        bot.send_message(chat_id, "🎟️ Sürpriz promo kodlar yakında dağıtılacak NEYOM, takipte kal!", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif text == "🎟️ Promo Kod Kullan":
        bot.send_message(chat_id, "🎟️ Kullanmak istediğin promo kodu sohbete yazabilirsin NEYOM (Yapım aşamasında).", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif text == "🎫 Biletlerim & Kullan":
        bot.send_message(chat_id, f"🎫 Aktif bilet hakkın: **{tickets} adet**", reply_markup=get_main_keyboard())
        conn.close()
        return

    elif text == "👥 Arkadaşını Davet Et":
        bot.send_message(chat_id, f"👥 Arkadaşını davet et linkin:\n`https://t.me/Cpm1_hesapSatis_bot?start={chat_id}`\n\nHer davet ettiğin arkadaşın için ödül kazanırsın NEYOM!", reply_markup=get_main_keyboard())
        conn.close()
        return

    else:
        bot.send_message(chat_id, "Seçimin alındı NEYOM. İşleminiz işleniyor...", reply_markup=get_main_keyboard())
        conn.close()

# --- 7. ÇALIŞTIRMA BLOĞU ---
if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    print("Bot ve Web Sunucusu Başlatıldı...")
    bot.infinity_polling()
                       
