import os
import sqlite3
import random
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- FLASK KEEP-ALIVE (Render için zorunlu web sunucusu) ---
app = Flask('')

@app.route('/')
def home():
    print("Ping alındı, bot aktif!")
    return "Bot Aktif ve Çalışıyor, NEYOM!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- VERİTABANI BAĞLANTISI VE KURULUMU ---
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    # Kullanıcılar Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            vip_status INTEGER DEFAULT 0
        )
    ''')
    # Biletler Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            status TEXT DEFAULT 'Açık'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- BOT KOMUTLARI VE MENÜLER ---
TOKEN = os.environ.get("BOT_TOKEN", "BURAYA_BOT_TOKEN_YAZILACAK")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, balance, vip_status) VALUES (?, ?, 100, 0)', 
                   (user.id, user.username))
    conn.commit()
    conn.close()

    keyboard = [
        [InlineKeyboardButton("🎮 CPM / PUBG Menüsü", callback_data='menu_cpm')],
        [InlineKeyboardButton("🎡 Şans Çarkı", callback_data='menu_wheel'), InlineKeyboardButton("💎 VIP Sistemi", callback_data='menu_vip')],
        [InlineKeyboardButton("🎟️ Destek Biletlerim", callback_data='menu_tickets'), InlineKeyboardButton("👤 Profilim", callback_data='menu_profile')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Selamlar NEYOM! 👑 Botun ana paneline hoş geldin.\n"
        f"İşlemlerini aşağıdaki menüden seçebilirsin:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'menu_cpm':
        keyboard = [
            [InlineKeyboardButton("🔄 CPM 1 Mail / Şifre Değiştir", callback_data='cpm1_mail')],
            [InlineKeyboardButton("🔄 CPM 2 Mail / Şifre Değiştir", callback_data='cpm2_mail')],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
        ]
        await query.edit_message_text("🛠️ **Hesap Yönetim ve Değişim Menüsü**\n\nİstediğin işlemi seç:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'cpm1_mail':
        await query.edit_message_text("📧 **CPM 1 Mail ve Şifre Değiştirme**\n\nLütfen yeni mail ve şifreyi `mail:sifre` formatında gönderin veya işlem için talimatları takip edin.\n\n🔙 [Geri Dön](tg://btn_menu_cpm)", parse_mode="Markdown")

    elif data == 'cpm2_mail':
        await query.edit_message_text("📧 **CPM 2 Mail ve Şifre Değiştirme**\n\nCPM2 sistemine ait değişim paneli aktif. Bilgileri girerek güncelleyebilirsin.\n\n🔙 [Geri Dön](tg://btn_menu_cpm)", parse_mode="Markdown")

    elif data == 'menu_wheel':
        reward = random.choice([10, 25, 50, 100, 250, 500])
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (reward, query.from_user.id))
        conn.commit()
        conn.close()
        
        keyboard = [[InlineKeyboardButton("🔄 Tekrar Çevir", callback_data='menu_wheel')], [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]]
        await query.edit_message_text(f"🎡 Çark çevrildi!\n🎁 Kazandığın Ödül: **{reward} Bakiye** Puan!", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == 'menu_vip':
        keyboard = [[InlineKeyboardButton("🌟 VIP Üyelik Satın Al (500 Puan)", callback_data='buy_vip')], [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]]
        await query.edit_message_text("💎 **VIP Sistemine Hoş Geldin!**\n\nVIP üyeler özel komutlara ve ekstra indirimlere sahip olur.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == 'buy_vip':
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT balance, vip_status FROM users WHERE user_id = ?', (query.from_user.id,))
        res = cursor.fetchone()
        if res and res[0] >= 500:
            cursor.execute('UPDATE users SET balance = balance - 500, vip_status = 1 WHERE user_id = ?', (query.from_user.id,))
            conn.commit()
            conn.close()
            await query.edit_message_text("Tebrikler! VIP üyelik başarıyla tanımlandı. 🎉\n\n🔙 Ana menüye dönmek için /start komutunu kullanabilirsin.")
        else:
            conn.close()
            await query.edit_message_text("⚠️ Yetersiz bakiye! Çark çevirerek bakiye kazanabilirsin.\n\n🔙 Ana menüye dönmek için /start komutunu kullanabilirsin.")

    elif data == 'menu_tickets':
        keyboard = [[InlineKeyboardButton("➕ Yeni Bilet Aç", callback_data='new_ticket')], [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]]
        await query.edit_message_text("🎟️ Destek taleplerin burada listelenir.", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'new_ticket':
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO tickets (user_id, subject) VALUES (?, ?)', (query.from_user.id, "Genel Destek Talebi"))
        conn.commit()
        conn.close()
        await query.edit_message_text("✅ Destek biletiniz başarıyla açıldı! En kısa sürede ilgilenilecektir.\n\n🔙 [Ana Menüye Dön](tg://btn_main)", parse_mode="Markdown")

    elif data == 'menu_profile':
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT balance, vip_status FROM users WHERE user_id = ?', (query.from_user.id,))
        res = cursor.fetchone()
        conn.close()
        balance = res[0] if res else 0
        vip = "Aktif 🌟" if res and res[1] == 1 else "Normal Üye"
        
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]]
        await query.edit_message_text(f"👤 **Profil Bilgilerin:**\n\nID: `{query.from_user.id}`\nKullanıcı: @{query.from_user.username}\nBakiye: **{balance} Puan**\nDurum: **{vip}**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == 'main_menu':
        keyboard = [
            [InlineKeyboardButton("🎮 CPM / PUBG Menüsü", callback_data='menu_cpm')],
            [InlineKeyboardButton("🎡 Şans Çarkı", callback_data='menu_wheel'), InlineKeyboardButton("💎 VIP Sistemi", callback_data='menu_vip')],
            [InlineKeyboardButton("🎟️ Destek Biletlerim", callback_data='menu_tickets'), InlineKeyboardButton("👤 Profilim", callback_data='menu_profile')]
        ]
        await query.edit_message_text("Ana menüye döndün NEYOM:", reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    # Flask sunucusunu arka planda başlat (Render port hatasını önler)
    keep_alive()
    
    # Telegram Bot uygulamasını başlat
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot başarıyla başlatıldı ve dinleniyor...")
    application.run_polling()

if __name__ == '__main__':
    main()
    
