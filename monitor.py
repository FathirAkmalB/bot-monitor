import sqlite3
import re
import requests
import telethon  # TAMBAHKAN INI agar tidak NameError
from telethon import TelegramClient, events, Button, errors # Tambahkan errors di sini juga boleh

# --- CONFIG UTAMA ---
API_ID = 31560960 
API_HASH = '00bf63fc4eca476cfb11ce8bfb561cd5' 
MAIN_BOT_TOKEN = '8326958695:AAEZ86qM9L9HNaUTIzDFCaWiPy9QSsuQQLE' 

# Daftar 13 Channel Target (Contoh 3, silakan tambahkan sisanya)
CHANNELS_TO_WATCH = ['@affectionadr',-1001525948158, -1001475463454, -1001770726607, -1001904753976, -1002517145182, -1001928438462, -1001274048263, -1001202510480, -1001303979309, -1001260932905, -1002217227171, -1001632369750, -1001434752203, -1001434752203, -1002801755350] 

# 1. Inisialisasi Database SQLite
def init_db():
    conn = sqlite3.connect('monitorboy.db')
    c = conn.cursor()
    # Tabel user
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, bot_token TEXT, keywords TEXT, wording TEXT)''')
    # Tabel Log Komentar (Baru)
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (user_id INTEGER, channel_id INTEGER, msg_id INTEGER, 
                  PRIMARY KEY (user_id, channel_id, msg_id))''')
    conn.commit()
    conn.close()

init_db()

# 2. Inisialisasi Client (Main Bot & Userbot)
# Client untuk Bot Utama
main_bot = TelegramClient('main_bot_session', API_ID, API_HASH).start(bot_token=MAIN_BOT_TOKEN)
# Client Userbot (Akun kamu untuk memantau & reply)
userbot = TelegramClient('session_monitorboy', API_ID, API_HASH)

# Temporary state untuk alur registrasi
user_steps = {}

# --- 3. ALUR REGISTRASI (MAIN BOT) ---

@main_bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    name = event.sender.first_name

    caption = f"""🎉 Halo {name}, Selamat datang di Channel Monitor Boy Bot!

Bot ini akan membantu Anda mendapatkan notifikasi real-time dari 13 channel marketplace:
📢 @basewtb, @basewib, @hokabase, @basejajan, @basegamee, @giftfesss, @TXTRoblox, @Roblox_Fess
📢 @moneyfess, @swalayan, @berdagangonline, @dagangfess, @wantgift, @tosfess, @DuniaBA, @ZONAROBLOXX

✨ **Fitur:**
✅ Filter pesan berdasarkan keyword pilihan Anda

✅ Notifikasi instant via bot pribadi Anda

✅ Monitoring 24/7 otomatis

✅ Wording semudah klik tombol saja


📃 **Menu Utama:**
/register - Daftar bot baru
/status - Cek status & download keywords
/keywords - Ganti semua keywords
/addkeywords - Tambah keywords baru
/setwording - Atur wording

📖 Tutorial: @monitorboy_tutor

Mulai dengan /register untuk mendaftarkan bot Anda! 🚀
"""

    await main_bot.send_file(
        event.chat_id,
        "welcome.png",
        caption=caption
    )
@main_bot.on(events.NewMessage(pattern='/register'))
async def register_start(event):
    user_steps[event.sender_id] = {'step': 'WAIT_TOKEN'}

    message = """🚀 Ayo daftarkan bot kamu sekarang!

📌 Langkah 1: Buat Bot di @BotFather
1. Chat @BotFather
2. Ketik /newbot
3. Ikuti instruksi untuk beri nama bot
4. @BotFather akan memberikan Bot Token
5. Copy token tersebut

📌 Langkah 2: START Bot Anda ⚠️ PENTING!
Sebelum paste token:
1. Cari username bot Anda
2. Ketik /start di bot tersebut

📌 Langkah 3: Kirim Token ke Sini
Paste bot token Anda di chat ini.

Contoh format:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

⚠️ Jangan share token ke siapa pun!
📺 Tutorial lengkap: @monitorBoy_bot

Ketik /cancel untuk membatalkan.
"""

    await event.reply(message)

@main_bot.on(events.NewMessage)
async def register_flow(event):
    uid = event.sender_id
    if uid not in user_steps or event.text.startswith('/'): return
    
    state = user_steps[uid]
    
    # STEP 1: Terima Token
    if state['step'] == 'WAIT_TOKEN':
        token = event.text.strip()
        try:
            res = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
            if res['ok']:
                user_steps[uid].update({'step': 'WAIT_KEYWORDS', 'token': token, 'bot_user': res['result']['username']})
                await event.reply(f"✅ Bot Valid!\nBot: @{res['result']['username']}\n\nLangkah selanjutnya: **Set Keywords** (Pisahkan dengan koma)")
            else:
                raise Exception
        except:
            await event.reply("❌ Bot Token Tidak Valid!\nError: ETELEGRAM: 401 Unauthorized\n\nCoba lagi atau /cancel.")

    # STEP 2: Terima Keywords
    elif state['step'] == 'WAIT_KEYWORDS':
        user_steps[uid].update({'step': 'WAIT_WORDING', 'keywords': event.text})
        await event.reply("✅ Keyword berhasil disimpan!\n\nLangkah Terakhir: **Set Wording**")

    # STEP 3: Terima Wording & Simpan ke DB
    elif state['step'] == 'WAIT_WORDING':
        data = user_steps[uid]
        wording = event.text
        
        conn = sqlite3.connect('monitorboy.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO users (user_id, bot_token, keywords, wording) VALUES (?, ?, ?, ?)",
                  (uid, data['token'], data['keywords'], wording))
        conn.commit()
        conn.close()
        
        num_kw = len(data['keywords'].split(','))
        await event.reply(f"🎉 Registrasi Berhasil!\n\nUser ID: {uid}\nBot: @{data['bot_user']}\nTotal Keywords: {num_kw}\n\nSelamat memantau! 🚀")
        del user_steps[uid]
# --- 4. MONITORING & NOTIFIKASI (DIPERBAIKI) ---

@userbot.on(events.NewMessage(chats=CHANNELS_TO_WATCH))
async def monitoring(event):
    # PENTING: Abaikan pesan jika yang mengirim adalah akun Userbot itu sendiri
    # if event.out:
    #     return

    pesan_raw = event.raw_text
    pesan_lowered = pesan_raw.lower()
    
    conn = sqlite3.connect('monitorboy.db')
    c = conn.cursor()
    all_users = c.execute("SELECT user_id, keywords FROM users").fetchall()
    conn.close()

    for uid, kw_str in all_users:
        # Pecah keyword dan bersihkan spasi
        keywords = [k.strip().lower() for k in kw_str.split(',') if k.strip()]
        for kw in keywords:
            # Gunakan regex agar match kata yang utuh (bukan bagian dari kata lain)
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, pesan_lowered):
                
                # Format link pesan agar bisa langsung menuju chat sumber
                # Menghilangkan -100 dari ID untuk format link t.me/c/
                clean_chat_id = str(event.chat_id).replace('-100', '')
                link = f"https://t.me/c/{clean_chat_id}/{event.id}"
                
                text_notif = (
                    f"🔔 **KEYWORD TERDETEKSI**\n\n"
                    f"📍 **Channel:** {event.chat.title if hasattr(event.chat, 'title') else 'Unknown'}\n"
                    f"🔑 **Keyword:** `{kw}`\n\n"
                    f"📝 **Isi:**\n{pesan_raw[:500]}\n\n"
                    f"🔗 **Link Sumber:** [Klik di sini untuk ke Pesan]({link})"
                )
                
                try:
                    # Mengirim notif via bot utama dengan data callback yang benar
                    await main_bot.send_message(
                        uid, 
                        text_notif, 
                        buttons=[Button.inline("🚀 Send Wording", f"sw|{event.chat_id}|{event.id}")]
                    )
                except Exception as e:
                    print(f"Gagal kirim notif ke {uid}: {e}")
                
                # Berhenti mengecek keyword lain untuk user ini jika sudah ketemu satu
                break 

# --- 5. HANDLING TOMBOL "SEND WORDING" (MODE KOMENTAR) ---

@main_bot.on(events.CallbackQuery(data=re.compile(b"sw\|")))
async def send_wording_callback(event):
    try:
        data = event.data.decode().split('|')
        channel_id = int(data[1])
        msg_id = int(data[2])
        user_id = event.sender_id
        
        # Ambil Wording dari DB
        conn = sqlite3.connect('monitorboy.db')
        c = conn.cursor()
        user_data = c.execute("SELECT wording FROM users WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()

        if not user_data:
            return await event.answer("❌ Wording belum diatur!", alert=True)

        wording = user_data[0]

        # --- LOGIKA KOMENTAR ---
        # 1. Dapatkan detail pesan dari channel
        channel_msg = await userbot.get_messages(channel_id, ids=msg_id)
        
        # 2. Cek apakah channel punya fitur komentar (Grup Diskusi)
        if channel_msg and channel_msg.replies:
            # Kirim komentar dengan fitur .comment() dari Telethon
            await userbot.send_message(
                entity=channel_id,
                message=wording,
                comment_to=msg_id # Ini kunci untuk masuk ke kolom komentar
            )
            await event.answer("✅ KOMENTAR TERKIRIM! Cek kolom komentar channel.", alert=True)
            print(f"✅ Sukses komentar di {channel_id} untuk user {user_id}")
        else:
            # Jika tidak ada kolom komentar, coba balas langsung (seperti grup biasa)
            try:
                await userbot.send_message(channel_id, wording, reply_to=msg_id)
                await event.answer("✅ BERHASIL! Pesan terkirim sebagai reply.", alert=True)
            except errors.rpcerrorlist.ChatAdminRequiredError:
                await event.answer("❌ GAGAL: Channel ini tidak punya kolom komentar.", alert=True)

    except Exception as e:
        print(f"DEBUG Error: {e}")
        err_msg = str(e)[:40]
        await event.answer(f"❌ ERROR: {err_msg}...", alert=True)

# --- 6. JALANKAN SEMUA (HAPUS DOUBLE START) ---

async def main():
    # Start Userbot (Akun Pribadi)
    await userbot.start()
    print("✅ Userbot Active (Monitoring & Replying)")
    
    # Ambil info diri agar kita tahu ID akun Userbot
    me = await userbot.get_me()
    print(f"Logged in as: {me.first_name} (ID: {me.id})")
    
    # Jalankan bot utama sampai terputus
    # Note: main_bot.start() sudah dipanggil di bagian inisialisasi atas
    print("✅ Main Bot Active (Handling UI)")
    await main_bot.run_until_disconnected()

if __name__ == '__main__':
    import asyncio
    print("🚀 MonitorBoy SaaS Mode Active...")
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass

# Jalankan Semua
print("🚀 MonitorBoy SaaS Mode Active...")
userbot.start()
main_bot.run_until_disconnected()