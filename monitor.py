from telethon import TelegramClient, events
import re
import requests

# === CONFIG USERBOT (Penyamar) ===
API_ID = 31560960  # Masukkan api_id
API_HASH = '00bf63fc4eca476cfb11ce8bfb561cd5'
client = TelegramClient('session_monitorboy', API_ID, API_HASH)

# === CONFIG BOT RESMI (Pengirim Notif) ===
BOT_TOKEN = '8584105605:AAFUEN4VTmvfin7BUoPumI_Wzy5qWOnWkAE'

# === DATABASE & TARGET ===
CHANNELS_TO_WATCH = [-1001611324665, -1001525948158, '@basegamee', -1001928438462,'@Roblox_Fess', '@affectionadr']
DATABASE_KEYWORDS = {
    1156428344: ["top up", "robux", "vilog", "500r", "80r", "1000r", "1kr"], # Ganti dengan ID kamu
    8303077005: ["robux", "robuxx", "rxb", "500r", "1000r", "robux vilog", "vilog robux", "robux prem", "robak", "robuk", "robax", "kr", "1kr", "2kr", "free prem", "vilog", "free prem", "heartopia", "heart diamond", "diamond heart"
] # Ganti dengan ID kamu

}

def send_bot_notification(user_id, text):
    """Fungsi dengan timeout agar tidak macet saat koneksi buruk"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False # Supaya link bisa diklik dengan preview
    }
    try:
        # Kita tambah timeout 10 detik agar tidak menunggu selamanya
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status() # Cek apakah ada error dari Telegram
        print(f"✅ Notifikasi terkirim ke {user_id}")
    except requests.exceptions.Timeout:
        print(f"❌ Koneksi Timeout: Server Telegram kelamaan responnya.")
    except Exception as e:
        print(f"❌ Gagal kirim via Bot API: {e}")

@client.on(events.NewMessage(chats=CHANNELS_TO_WATCH))
@client.on(events.NewMessage(chats=CHANNELS_TO_WATCH))
async def handler(event):
    pesan_masuk = event.raw_text
    pesan_lowered = pesan_masuk.lower()
    
    # Mendapatkan info channel dan ID pesan
    chat = await event.get_chat()
    channel_name = chat.title if hasattr(chat, 'title') else "Channel"
    msg_id = event.id # ID unik pesan di dalam channel tersebut
    
    # Membuat Link Pesan
    # Jika channel publik (punya username)
    if chat.username:
        link_pesan = f"https://t.me/{chat.username}/{msg_id}"
    else:
        # Jika channel privat (menggunakan format ID tanpa -100)
        chat_id_clean = str(event.chat_id).replace("-100", "")
        link_pesan = f"https://t.me/c/{chat_id_clean}/{msg_id}"

    for user_id, keywords in DATABASE_KEYWORDS.items():
        for word in keywords:
            pattern = r'\b' + re.escape(word.lower()) + r'\b'
            if re.search(pattern, pesan_lowered):
                
                # Tambahkan Link ke dalam teks notifikasi
                notif_text = (
                    f"🔔 **KEYWORD TERDETEKSI**\n\n"
                    f"📍 **Channel:** {channel_name}\n"
                    f"🔑 **Keyword:** `{word}`\n\n"
                    f"📝 **Isi:**\n{pesan_masuk[:500]}\n\n"
                    f"🔗 **Link Sumber:** [Klik di sini untuk ke Pesan]({link_pesan})"
                )
                
                send_bot_notification(user_id, notif_text)

if __name__ == '__main__':
    print("🚀 MonitorBoy Active: Userbot memantau, Bot resmi mengirim notif.")
    client.start()
    client.run_until_disconnected()