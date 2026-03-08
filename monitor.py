import sqlite3
import re
import asyncio
import os
import logging
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# --- 1. LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 2. CONFIG UTAMA ---
# Saran: Di Railway, ganti ini dengan os.getenv('NAMA_VAR')
API_ID = 31560960 
API_HASH = '00bf63fc4eca476cfb11ce8bfb561cd5' 
MAIN_BOT_TOKEN = '8605602270:AAG_DVEAEr2EV29CU8vjT0R7GgCVkbP-K8k' 

CHANNELS_TO_WATCH = [
    '@affectionadr', -1001525948158, -1001611324665, -1001475463454,
    -1001770726607, -1001904753976, -1002517145182, -1001928438462,
    -1001274048263, -1001202510480, -1001303979309, -1001260932905,
    -1001434752203, -1002801755350, -1002217227171
]

# --- 3. INITIALIZE CLIENTS ---
# Tambahkan connection_retries supaya nggak gampang "Server Closed Connection"
userbot = TelegramClient(
    'session_monitorboy', 
    API_ID, API_HASH,
    connection_retries=None, 
    retry_delay=5
)

main_bot = TelegramClient(
    'main_bot_session', 
    API_ID, API_HASH,
    connection_retries=None,
    retry_delay=5
)

user_bot_instances = {}
cached_users = []

# --- 4. DATABASE LAYER ---
def init_db():
    # Pastikan folder database ada jika menggunakan path subfolder
    with sqlite3.connect('monitorboy.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
                     (user_id INTEGER PRIMARY KEY, bot_token TEXT, keywords TEXT, wording TEXT)''')
        conn.commit()

def reload_cache():
    global cached_users
    try:
        with sqlite3.connect('monitorboy.db') as conn:
            cached_users = conn.execute("SELECT user_id, keywords FROM users").fetchall()
        logger.info("✅ Cache User diupdate.")
    except Exception as e:
        logger.error(f"❌ Gagal reload cache: {e}")

# --- 5. CORE MONITORING (USERBOT) ---
@userbot.on(events.NewMessage(chats=CHANNELS_TO_WATCH))
async def monitoring_handler(event):
    if not event.raw_text: return
    
    pesan_lowered = event.raw_text.lower()
    
    for uid, kw_str in cached_users:
        keywords = [k.strip().lower() for k in kw_str.split(',') if k.strip()]
        for kw in keywords:
            # Gunakan regex untuk pencarian kata yang presisi
            if re.search(r'\b' + re.escape(kw) + r'\b', pesan_lowered):
                bot_client = user_bot_instances.get(uid)
                if bot_client:
                    try:
                        clean_id = str(event.chat_id).replace('-100', '')
                        link = f"https://t.me/c/{clean_id}/{event.id}"
                        text_notif = (
                            f"🔔 **KEYWORD TERDETEKSI**\n\n"
                            f"🔑 Keyword: `{kw}`\n"
                            f"📝 Isi: {event.raw_text[:300]}...\n\n"
                            f"🔗 [Lihat Pesan]({link})"
                        )
                        
                        # Kirim notifikasi via bot milik user
                        await bot_client.send_message(
                            uid, text_notif, 
                            buttons=[Button.inline("🚀 Send Wording", f"sw|{event.chat_id}|{event.id}")]
                        )
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        logger.error(f"Gagal kirim notif ke {uid}: {e}")
                break

# --- 6. DYNAMIC USER BOTS LOGIC ---
async def start_user_bot(user_id, bot_token):
    if user_id in user_bot_instances: return
    
    try:
        # Gunakan StringSession() kosong agar bot user berjalan di memori (RAM)
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.start(bot_token=bot_token)
        user_bot_instances[user_id] = client

        @client.on(events.CallbackQuery(data=re.compile(rb"sw\|")))
        async def callback_handler(event):
            try:
                # Ambil ID Chat dan ID Pesan dari data tombol
                _, chat_id, msg_id = event.data.decode().split('|')
                chat_id, msg_id = int(chat_id), int(msg_id)
                
                with sqlite3.connect('monitorboy.db') as conn:
                    res = conn.execute("SELECT wording FROM users WHERE user_id = ?", (user_id,)).fetchone()
                
                if not res: 
                    return await event.answer("❌ Data tidak ditemukan!", alert=True)
                
                wording = res[0]
                
                # Coba kirim sebagai komentar, jika gagal kirim sebagai reply biasa
                try:
                    await userbot.send_message(chat_id, wording, comment_to=msg_id)
                except:
                    await userbot.send_message(chat_id, wording, reply_to=msg_id)
                
                await event.answer("✅ BALASAN TERKIRIM!", alert=True)
            except Exception as e:
                logger.error(f"Callback Error User {user_id}: {e}")
                await event.answer("❌ Gagal mengirim balasan.", alert=True)

        logger.info(f"🟢 Bot User {user_id} Online.")
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"🔴 Bot User {user_id} Offline/Error: {e}")
        user_bot_instances.pop(user_id, None)

# --- 7. MAIN BOT REGISTRATION ---
@main_bot.on(events.NewMessage(pattern='/register'))
async def registration_handler(event):
    uid = event.sender_id
    async with main_bot.conversation(uid, timeout=300) as conv:
        try:
            await conv.send_message("🛡️ **MonitorBoy Setup**\n\n1. Kirim **Bot Token** dari @BotFather:")
            token = (await conv.get_response()).text.strip()
            
            await conv.send_message("2. Masukkan **Keywords** (pisahkan dengan koma):")
            kws = (await conv.get_response()).text.strip()
            
            await conv.send_message("3. Masukkan **Wording Balasan**:")
            word = (await conv.get_response()).text.strip()
            
            with sqlite3.connect('monitorboy.db') as conn:
                conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (uid, token, kws, word))
                conn.commit()
            
            reload_cache()
            asyncio.create_task(start_user_bot(uid, token))
            await conv.send_message("🎉 **Registrasi Berhasil!** Bot Anda sudah aktif memantau channel.")
        except asyncio.TimeoutError:
            await conv.send_message("⏰ Waktu habis. Silakan ulangi /register.")
        except Exception as e:
            await conv.send_message(f"❌ Terjadi kesalahan: {e}")

# --- 8. RUNNER ---
async def main():
    logger.info("Memulai inisialisasi...")
    init_db()
    reload_cache()
    
    # Jalankan Client Utama (Userbot lo & Main Bot lo)
    await userbot.start()
    await main_bot.start(bot_token=MAIN_BOT_TOKEN)
    
    # Start bot-bot milik user yang sudah ada di DB
    with sqlite3.connect('monitorboy.db') as conn:
        users = conn.execute("SELECT user_id, bot_token FROM users").fetchall()
    
    for uid, token in users:
        asyncio.create_task(start_user_bot(uid, token))

    logger.info("🚀 MONITORBOY FULLY OPERATIONAL!")
    
    # Menunggu selamanya agar tidak exit
    await asyncio.gather(
        userbot.run_until_disconnected(),
        main_bot.run_until_disconnected()
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Sistem dimatikan oleh pengguna.")