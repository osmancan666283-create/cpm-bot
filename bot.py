# =====================================================================
# PROJE ADI: Telegram CPM & VIP Mağaza Botu (Gelişmiş Sürüm)
# AÇIKLAMA: Bu bot Telegram Yıldızları (XTR) ile Volt Coin yükleme, 
# VIP üyelik satın alma, şans çarkı çevirme ve yerel stoktan 
# otomatik hesap teslimatı yapma özelliklerini barındırır.
# =====================================================================

import telebot
import sqlite3
import random
import time

# --- BOT YAPILANDIRMA VE BAĞLANTI AYARLARI ---
BOT_TOKEN = "YENI_TOKEN_BURAYA"  # Yeni tokenini buraya tırnak içine yapıştıracaksın reis
ADMIN_ID = 8520025523            # Bot yöneticisinin Telegram ID numarası

print("Sistem başlatılıyor, lütfen bekleyin...")
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# Yerel hesap stok listesi (GitHub bağımlılığı kaldırıldı)
LOCAL_STOCK = [
    "cpm_user_1:sifre123",
    "cpm_user_2:sifre456",
    "cpm_user_3:sifre789",
    "vip_cpm_ornek:pass987"
]


# --- VERİTABANI YÖNETİM FONKSİYONLARI ---
def db_init():
    """
    Uygulama ilk kez ayağa kalktığında SQLite veritabanını ve 
    gerekli olan 'users' tablosunu oluşturur.
    """
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    
    # Kullanıcı tablosunun oluşturulması (Bakiye, VIP durumu, süreler ve haklar)
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
    print("Veritabanı bağlantısı ve tablo kontrolleri başarılı.")


# --- VIP DURUM KONTROLÜ ---
def check_vip_status(user_id):
    """
    Belirtilen kullanıcının VIP üyelik süresinin dolup dolmadığını 
    anlık zaman damgasına (timestamp) bakarak kontrol eder.
    Süre bittiyse otomatik olarak VIP yetkisini düşürür.
    """
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_vip, vip_expire_time FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row and row[0] == 1:
        # Eğer mevcut zaman epoch süresinden büyükse VIP süresi dolmuştur
        if int(time.time()) >= row[1]:
            cursor.execute("UPDATE users SET is_vip = 0, vip_expire_time = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            return False
        conn.close()
        return True
        
    conn.close()
    return False


# --- YEREL STOK ÇEKME FONKSİYONU ---
def get_account_from_local_stock():
    """
    Yerel listeden rastgele bir hesap seçerek kullanıcıya teslim eder.
    """
    if LOCAL_STOCK:
        return random.choice(LOCAL_STOCK)
    return None


# --- KLAVYE DÜZENLERİ (MENÜLER) ---
def get_main_keyboard():
    """
    Kullanıcının botla etkileşime girerken kullandığı ana klavye menüsünü oluşturur.
    """
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


# --- TELEGRAM YILDIZ FATURA OLUŞTURUCU ---
def send_star_invoice(chat_id, title, description, payload, amount_in_stars):
    """
    Telegram Stars (XTR) birimiyle ödeme yapılabilmesi için 
    ilgili faturayı kullanıcıya gönderir.
    """
    prices = [telebot.types.LabeledPrice(label=title, amount=amount_in_stars)]
    bot.send_invoice(
        chat_id=chat_id, 
        title=title, 
        description=description,
        invoice_payload=payload, 
        provider_token="", 
        currency="XTR", 
        prices=prices, 
        start_parameter="buy_stars"
    )


# --- KOMUT YÖNETİCİLERİ (/start) ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """
    Kullanıcı /start komutunu gönderdiğinde çalışır. 
    Kullanıcı veritabanında yoksa kaydını açar ve ana menüyü gönderir.
    """
    chat_id = message.chat.id
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (chat_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (chat_id,))
        conn.commit()
        
    conn.close()
    bot.send_message(chat_id, "👋 Hoş Geldin! Menüden seçim yapabilirsin:", reply_markup=get_main_keyboard())


# --- MESAJ VE BUTON YÖNETİCİSİ ---
@bot.message_handler(func=lambda message: True)
def handle_menu_clicks(message):
    """
    Kullanıcının klavyeden gönderdiği tüm metin komutlarını ve 
    seçenekleri tek tek işleyen ana yönlendirici fonksiyondur.
    """
    chat_id = message.chat.id
    text = message.text

    # Kullanıcının aktif VIP durumunu sorgula
    is_user_vip = check_vip_status(chat_id)
    
    # Kullanıcı verilerini veritabanından çek
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

    # 1. ALT MENÜ: Volt Coin Al Seçenekleri
    if text == "⚡ Volt Coin Al":
        bot.send_message(chat_id, "⚡ Volt Paketleri Seçin:", reply_markup=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(
            telebot.types.KeyboardButton("⚡ 1 Volt (10 ⭐)"),
            telebot.types.KeyboardButton("⚡ 5,000 Volt (250 ⭐)"),
            telebot.types.KeyboardButton("⚡ 25,000 Volt (1,000 ⭐)"),
            telebot.types.KeyboardButton("⚡ 93,250 Volt (3,000 ⭐)"),
            telebot.types.KeyboardButton("⬅️ Ana Menü")
        ))

    elif text == "⚡ 1 Volt (10 ⭐)":
        send_star_invoice(chat_id, "1 Volt", "Volt Yükleme", "buy_volt_1", 10)
    elif text == "⚡ 5,000 Volt (250 ⭐)":
        send_star_invoice(chat_id, "5000 Volt", "Volt Yükleme", "buy_volt_5000", 250)
    elif text == "⚡ 25,000 Volt (1,000 ⭐)":
        send_star_invoice(chat_id, "25000 Volt", "Volt Yükleme", "buy_volt_25000", 1000)
    elif text == "⚡ 93,250 Volt (3,000 ⭐)":
        send_star_invoice(chat_id, "93250 Volt", "Volt Yükleme", "buy_volt_93250", 3000)

    # 2. ALT MENÜ: VIP Üyelik Al Seçenekleri
    elif text == "👑 VIP Üyelik Al":
        bot.send_message(chat_id, "👑 VIP Süresini Seçin (1 Aydan 36 Aya):", reply_markup=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(
            telebot.types.KeyboardButton("👑 1 Ay VIP (150 ⭐)"),
            telebot.types.KeyboardButton("👑 3 Ay VIP (400 ⭐)"),
            telebot.types.KeyboardButton("👑 6 Ay VIP (750 ⭐)"),
            telebot.types.KeyboardButton("👑 12 Ay VIP (1,200 ⭐)"),
            telebot.types.KeyboardButton("👑 24 Ay VIP (2,000 ⭐)"),
            telebot.types.KeyboardButton("👑 36 Ay VIP (2,800 ⭐)"),
            telebot.types.KeyboardButton("⬅️ Ana Menü")
        ))

    elif text == "👑 1 Ay VIP (150 ⭐)":
        send_star_invoice(chat_id, "1 Ay VIP", "VIP Üyelik", "buy_vip_1m", 150)
    elif text == "👑 3 Ay VIP (400 ⭐)":
        send_star_invoice(chat_id, "3 Ay VIP", "VIP Üyelik", "buy_vip_3m", 400)
    elif text == "👑 6 Ay VIP (750 ⭐)":
        send_star_invoice(chat_id, "6 Ay VIP", "VIP Üyelik", "buy_vip_6m", 750)
    elif text == "👑 12 Ay VIP (1,200 ⭐)":
        send_star_invoice(chat_id, "12 Ay VIP", "VIP Üyelik", "buy_vip_12m", 1200)
    elif text == "👑 24 Ay VIP (2,000 ⭐)":
        send_star_invoice(chat_id, "24 Ay VIP", "VIP Üyelik", "buy_vip_24m", 2000)
    elif text == "👑 36 Ay VIP (2,800 ⭐)":
        send_star_invoice(chat_id, "36 Ay VIP", "VIP Üyelik", "buy_vip_36m", 2800)

    # 3. MAĞAZA: VIP Hesap Satın Alımı
    elif text == "🛒 VIP Hesap Mağazası":
        send_star_invoice(chat_id, "VIP Hesap", "Hesap Mağazası", "buy_vip_acc_star", 100)

    # 4. GÜNLÜK BONUS SİSTEMİ
    elif text == "🎁 Günlük Bonus (+20 Volt)":
        if last_bonus == today:
            bot.send_message(chat_id, "❌ Bugün zaten bonusunu aldın, yarın tekrar dene!", reply_markup=get_main_keyboard())
        else:
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + 20, last_daily_bonus = ? WHERE user_id = ?", (today, chat_id))
            conn.commit()
            bot.send_message(chat_id, "🎉 Tebrikler! Günlük +20 Volt hesabına eklendi.", reply_markup=get_main_keyboard())

    # 5. ŞANS ÇARKI ÖZELLİĞİ
    elif text == "🎡 Şans Çarkı":
        if last_day != today:
            spins = 3 if is_user_vip else 1
            cursor.execute("UPDATE users SET daily_spins = ?, last_spin_day = ? WHERE user_id = ?", (spins, today, chat_id))
            conn.commit()

        if spins <= 0:
            bot.send_message(chat_id, "❌ Günlük çevirme hakkın bitti! Yarın tekrar dene veya VIP olarak hakkını artır.", reply_markup=get_main_keyboard())
        else:
            won = round(random.uniform(1.0, 7.0), 2) if is_user_vip else round(random.uniform(1.0, 1.5), 2)
            new_spins = spins - 1
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + ?, daily_spins = ? WHERE user_id = ?", (won, new_spins, chat_id))
            conn.commit()
            bot.send_message(chat_id, f"🎡 Çark döndürülüyor...\n\n🎉 Şansına {won} Volt Kazandın!\nKalan çevirme hakkın: {new_spins}", reply_markup=get_main_keyboard())

    # 6. KULLANICI PROFİL GÖRÜNTÜLEME
    elif text == "👤 Profilim":
        vip_durum_metni = "Aktif 👑" if is_user_vip else "Normal Üye"
        bot.send_message(chat_id, f"👤 **Kullanıcı Profilin**\n\n🆔 ID: `{chat_id}`\n⚡ Bakiye: `{cwrk}` Volt\n💎 Üyelik Durumu: {vip_durum_metni}", reply_markup=get_main_keyboard())

    # 7. ANA MENÜYE DÖNÜŞ
    elif text == "⬅️ Ana Menü":
        bot.send_message(chat_id, "✅ Ana menüye dönüldü.", reply_markup=get_main_keyboard())

    else:
        bot.send_message(chat_id, "Lütfen menüdeki butonları kullanarak geçerli bir seçim yapın.", reply_markup=get_main_keyboard())

    conn.close()


# --- ÖDEME ÖNCESİ DOĞRULAMA (PRE-CHECKOUT) ---
@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout_query(pre_checkout_query):
    """
    Telegram üzerinden yapılan ödeme isteklerinin onay aşamasıdır.
    """
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


# --- BAŞARILI ÖDEME İŞLEMLERİ (SUCCESSFUL PAYMENT) ---
@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    """
    Kullanıcı yıldız ile ödemeyi tamamladığında tetiklenir.
    Satın alınan ürüne göre veritabanını günceller veya stok teslimatı yapar.
    """
    payload = message.successful_payment.invoice_payload
    chat_id = message.chat.id
    conn = sqlite3.connect("cpm_bot.db")
    cursor = conn.cursor()

    # Volt yükleme paketlerinin haritası
    volt_amounts = {
        "buy_volt_1": 1,
        "buy_volt_5000": 5000,
        "buy_volt_25000": 25000,
        "buy_volt_93250": 93250
    }

    # VIP üyelik paketlerinin haritası (Ay cinsinden)
    vip_months = {
        "buy_vip_1m": 1,
        "buy_vip_3m": 3,
        "buy_vip_6m": 6,
        "buy_vip_12m": 12,
        "buy_vip_24m": 24,
        "buy_vip_36m": 36
    }

    # Eğer volt satın alındıysa bakiyeyi artır
    if payload in volt_amounts:
        amt = volt_amounts[payload]
        cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + ? WHERE user_id = ?", (amt, chat_id))
        bot.send_message(chat_id, f"🎉 Başarılı! Hesabına +{amt} Volt yüklendi.", reply_markup=get_main_keyboard())

    # Eğer VIP üyelik satın alındıysa süreyi uzat
    elif payload in vip_months:
        months = vip_months[payload]
        days = months * 30
        cursor.execute("SELECT vip_expire_time FROM users WHERE user_id = ?", (chat_id,))
        row = cursor.fetchone()
        current_time = int(time.time())
        base_time = row[0] if row and row[0] > current_time else current_time
        expire_timestamp = base_time + (days * 24 * 3600)
        
        cursor.execute("UPDATE users SET is_vip = 1, vip_expire_time = ?, daily_spins = 3 WHERE user_id = ?", (expire_timestamp, chat_id))
        bot.send_message(chat_id, f"🎉 Tebrikler! {months} Aylık VIP Üyeliğin başarıyla tanımlandı.", reply_markup=get_main_keyboard())

    # Eğer mağazadan hesap satın alındıysa
    elif payload == "buy_vip_acc_star":
        account = get_account_from_local_stock()
        if account:
            bot.send_message(chat_id, f"🎉 Satın Aldığın Hesap:\n`{account}`", reply_markup=get_main_keyboard())
        else:
            # Stokta hesap kalmadıysa alternatif olarak bakiye yükle
            cursor.execute("UPDATE users SET cw_rk_balance = cw_rk_balance + 2810 WHERE user_id = ?", (chat_id,))
            conn.commit()
            bot.send_message(chat_id, "⚠️ Üzgünüz, şu an stokta hesap kalmadı! Telafi olarak hesabına 2810 Volt eklendi.", reply_markup=get_main_keyboard())

    conn.commit()
    conn.close()


# --- BOTU BAŞLATMA BLOKLARI ---
if __name__ == "__main__":
    db_init()
    print("Bot Çalışıyor ve Kesintisiz Dinlemede...")
    bot.infinity_polling(none_stop=True)
        
