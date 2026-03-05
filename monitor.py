import sqlite3
import re
import asyncio
import os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import requests

# --- WARNA TERMINAL ---
CLR = {
    "HEADER": "\033[95m", "BLUE": "\033[94m", "CYAN": "\033[96m",
    "GREEN": "\033[92m", "YELLOW": "\033[93m", "RED": "\033[91m",
    "BOLD": "\033[1m", "END": "\033[0m"
}

# --- CONFIG UTAMA ---
API_ID = 31560960 
API_HASH = '00bf63fc4eca476cfb11ce8bfb561cd5' 
MAIN_BOT_TOKEN = '8605602270:AAG_DVEAEr2EV29CU8vjT0R7GgCVkbP-K8k' 

CHANNELS_TO_WATCH = [
    '@affectionadr',    
    -1001525948158,
    -1001611324665,
    -1001475463454,
    -1001770726607,
    -1001904753976,
    -1002517145182,
    -1001928438462,
    -1001274048263,
    -1001202510480,
    -1001303979309,
    -1001260932905,
    -1001434752203,
    -1002801755350,
    -1002217227171
] 

user_bot_instances = {} 

def init_db():
    conn = sqlite3.connect('monitorboy.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, bot_token TEXT, keywords TEXT, wording TEXT)''')
    conn.commit()
    conn.close()

main_bot = TelegramClient('main_bot_session', API_ID, API_HASH)
userbot = TelegramClient('session_monitorboy', API_ID, API_HASH)

# --- FUNGSI AUTO-RESTART BOT USER ---

async def start_user_bot(user_id, bot_token):
    """Loop utama untuk memastikan bot user selalu hidup (Auto-Restart)"""
    retry_delay = 10 # Detik tunggu sebelum mencoba restart jika gagal
    
    while True:
        try:
            print(f"{CLR['CYAN']}🔄 Connecting{CLR['END']} | User: {user_id}")
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.start(bot_token=bot_token)
            
            user_bot_instances[user_id] = client

            @client.on(events.CallbackQuery(data=re.compile(b"sw\|")))
            async def send_wording_callback(event):
                try:
                    data = event.data.decode().split('|')
                    channel_id, msg_id = int(data[1]), int(data[2])
                    
                    conn = sqlite3.connect('monitorboy.db')
                    user_data = conn.execute("SELECT wording FROM users WHERE user_id = ?", (user_id,)).fetchone()
                    conn.close()

                    if not user_data: return await event.answer("❌ Wording belum diatur!", alert=True)
                    wording = user_data[0]

                    channel_msg = await userbot.get_messages(channel_id, ids=msg_id)
                    if channel_msg and channel_msg.replies:
                        await userbot.send_message(entity=channel_id, message=wording, comment_to=msg_id)
                        await event.answer("✅ KOMENTAR TERKIRIM!", alert=True)
                        print(f"{CLR['GREEN']}💬 Comment Sent{CLR['END']} | User: {user_id} | Chan: {channel_id}")
                    else:
                        await userbot.send_message(channel_id, wording, reply_to=msg_id)
                        await event.answer("✅ REPLY TERKIRIM!", alert=True)
                        print(f"{CLR['GREEN']}📩 Reply Sent{CLR['END']} | User: {user_id} | Chan: {channel_id}")
                except Exception as e:
                    print(f"{CLR['RED']}❌ Callback Error{CLR['END']} | User: {user_id} | {e}")
                    await event.answer(f"❌ Error: {str(e)[:30]}", alert=True)

            print(f"{CLR['GREEN']}✅ Bot Online{CLR['END']} | User: {user_id}")
            await client.run_until_disconnected()
            
        except Exception as e:
            print(f"{CLR['RED']}❌ Bot Offline{CLR['END']} | User: {user_id} | Error: {e}")
            if user_id in user_bot_instances:
                del user_bot_instances[user_id]
            
            # Jika error karena token tidak valid, hentikan restart loop untuk user ini
            if "Unauthorized" in str(e):
                print(f"{CLR['BOLD']}{CLR['RED']}🚫 Loop Halted{CLR['END']} | Token User {user_id} Invalid.")
                break
                
            print(f"{CLR['YELLOW']}⏳ Restarting in {retry_delay}s...{CLR['END']}")
            await asyncio.sleep(retry_delay)

# --- MONITORING (USERBOT LO) ---

@userbot.on(events.NewMessage(chats=CHANNELS_TO_WATCH))
async def monitoring(event):
    try:
    # --- AMBIL METADATA (TAMBAHKAN INI) ---
        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', 'Private Channel') # Nama Channel
        sender = await event.get_sender()
        sender_name = getattr(sender, 'first_name', 'Hidden User') # Nama Pengirim
        waktu_wib = event.date.strftime('%H:%M:%S') # Format Jam:Menit:Detik

        pesan_raw = event.raw_text
        pesan_lowered = pesan_raw.lower()
        
        conn = sqlite3.connect('monitorboy.db')
        all_users = conn.execute("SELECT user_id, keywords FROM users").fetchall()
        conn.close()

        for uid, kw_str in all_users:
            keywords = [k.strip().lower() for k in kw_str.split(',') if k.strip()]
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', pesan_lowered):
                    bot_client = user_bot_instances.get(uid)
                    if bot_client:
                        clean_id = str(event.chat_id).replace('-100', '')
                        link = f"https://t.me/c/{clean_id}/{event.id}"
                        
                        # --- UPDATE BAGIAN INI ---
                        text_notif = (
                            f"🎯 **KEYWORD TERDETEKSI!**\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔑 **Keyword:** `{kw.upper()}`\n"
                            f"📢 **Channel:** `{chat_title}`\n"
                            # f"👤 **Sender:** `{sender_name}`\n"
                            f"⏰ **Waktu:** `{waktu_wib} WIB`\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"📝 **Isi Pesan:**\n_{pesan_raw[:500]}_\n\n"
                            f"🔗 [Klik untuk Lihat Pesan Full]({link})"
                        )
                        # --------------------------
                        
                        try:
                            await bot_client.send_message(uid, text_notif, buttons=[Button.inline("🚀 Send Wording", f"sw|{event.chat_id}|{event.id}")])
                            print(f"{CLR['YELLOW']}🎯 Hit!{CLR['END']} | User: {uid} | Key: {CLR['BOLD']}{kw}{CLR['END']}")
                        except Exception as e:
                            print(f"{CLR['RED']}⚠️ Notif Failed{CLR['END']} | User: {uid} | {e}")
                    break
    except Exception as e:
        # Ini supaya kalau ada constructor error di satu channel, bot nggak mati total
        if "Constructor ID" in str(e):
            print(f"{CLR['YELLOW']}⚠️ Telegram Update Detected: Silakan update telethon & hapus session.{CLR['END']}")
        else:
            print(f"{CLR['RED']}⚠️ Monitoring Error:{CLR['END']} {e}")
   

# --- ALUR REGISTRASI (MAIN BOT) ---

user_steps = {}
@main_bot.on(events.NewMessage(pattern='/register'))
async def reg_start(event):
    user_steps[event.sender_id] = {'step': 'WAIT_TOKEN'}
    
    guide_msg = (
    "🤖 **Panduan Membuat Bot Telegram**\n\n"

    "🚀 **Langkah 1: Buat Bot di @BotFather**\n"
    "1. Buka @BotFather di Telegram\n"
    "2. Ketik `/newbot`\n"
    "3. Beri **nama bot** Anda (bebas, contoh: *Monitor Notif*)\n"
    "4. Buat **username bot** (harus diakhiri `bot`, contoh: *jual_robux_bot*)\n"
    "5. @BotFather akan memberikan **API TOKEN**\n"
    "6. **Copy token tersebut**\n\n"

    "⚠️ **Sebelum paste token:**\n"
    "1. Klik link bot Anda atau cari username bot\n"
    "2. Ketik `/start` di bot tersebut\n\n"

    "📌 **Langkah 2: Kirim Token ke Sini**\n"
    "Paste bot token Anda di chat ini.\n\n"

    "Contoh format token:\n"
    "`1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n"

    "⚠️ **PENTING:** Jangan share token ke orang lain!\n\n"

    "📺 **Tutorial Video:** @monitor_boys\n"
    "🆘 **Butuh bantuan?** Lihat tutorial: @tutormonitor\n\n"

    "❌ Ketik `/cancel` untuk membatalkan."
)
    await event.reply(guide_msg)


@main_bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    welcome_text = (
        "👋 **Selamat Datang di MonitorBoy!**\n\n"
        "Bot ini dirancang untuk memantau marketplace secara real-time dan "
        "memberikan notifikasi langsung ke bot pribadi Anda.\n\n"
        "📢 **Channel Terafiliasi:**\n"
        "• @affectionadr\n"
        "• Base WTB/WTS (14+ Private Channels)\n\n"
        "🚀 **Benefit:**\n"
        "1. **Full Automation**: Balas pesan (Wording) hanya dengan satu klik.\n"
        "2. **White Label**: Notifikasi masuk ke bot Anda sendiri, bukan di sini.\n"
        "3. **Speed**: Deteksi keyword dalam hitungan milidetik.\n\n"
        "🛠 **Menu Utama:**\n"
        "• /register - Daftarkan Bot & Userbot Anda\n"
        "• /status - Cek status bot & detail konfigurasi\n"
        "• /help - Panduan penggunaan"
    )
    await event.reply(welcome_text)

    @main_bot.on(events.NewMessage(pattern="/status"))
    async def status_handler(event):
        uid = event.sender_id
        conn = sqlite3.connect("monitorboy.db")
        # Mengambil semua bot yang dimiliki user (antisipasi jika 1 user punya banyak bot)
        user_bots = conn.execute(
            "SELECT bot_token FROM users WHERE user_id = ?", (uid,)
        ).fetchall()
        conn.close()

        if not user_bots:
            return await event.reply(
                "❌ Anda belum mendaftarkan bot. Gunakan /register."
            )

        buttons = []
        for bot in user_bots:
            token_short = f"Bot {bot[0][:8]}..."  # Ambil 8 karakter awal token biar gak kepanjangan
            buttons.append([Button.inline(f"🤖 {token_short}", f"detail|{bot[0]}")])

        await event.reply(
            "📋 **Daftar Bot Anda:**\nKlik untuk melihat detail.", buttons=buttons
        )

    @main_bot.on(events.CallbackQuery(data=re.compile(b"detail\|")))
    async def bot_detail_callback(event):
        token = event.data.decode().split("|")[1]

        conn = sqlite3.connect("monitorboy.db")
        data = conn.execute(
            "SELECT keywords, wording FROM users WHERE bot_token = ?", (token,)
        ).fetchone()
        conn.close()

        if data:
            kw, wording = data
            detail_msg = (
                f"🛠 **Detail Konfigurasi Bot**\n\n"
                f"🔑 **Keywords:**\n`{kw}`\n\n"
                f"📝 **Wording:**\n`{wording}`"
            )
            # Tambahkan tombol aksi cepat
            actions = [
                [Button.inline("🔄 Ganti Semua Keyword", f"set_kw|{token}")],
                [Button.inline("➕ Tambah Keyword", f"add_kw|{token}")],
                [Button.inline("⬅️ Kembali", b"back_to_status")],
            ]
            await event.edit(detail_msg, buttons=actions)

        @main_bot.on(events.CallbackQuery(data=re.compile(b"(set_kw|add_kw)\|")))
        async def edit_kw_callback(event):
            action, token = event.data.decode().split("|")
            uid = event.sender_id

            user_steps[uid] = {"step": "WAIT_NEW_KW", "action": action, "token": token}

            if action == "set_kw":
                prompt = "📝 **Ganti Semua Keyword**\nKirim list keyword baru (pisahkan dengan koma):"
            else:
                prompt = "➕ **Tambah Keyword**\nKirim keyword tambahan yang ingin dimasukkan:"

            await event.respond(prompt)
            await event.answer()

        # --- HANDLER INPUT KEYWORD BARU ---
        @main_bot.on(events.NewMessage)
        async def update_kw_handler(event):
            uid = event.sender_id
            if uid not in user_steps or user_steps[uid]["step"] != "WAIT_NEW_KW":
                return

            new_input = event.text.strip()
            action = user_steps[uid]["action"]
            token = user_steps[uid]["token"]

            conn = sqlite3.connect("monitorboy.db")
            if action == "set_kw":
                # Overwrite semua
                conn.execute(
                    "UPDATE users SET keywords = ? WHERE bot_token = ?",
                    (new_input, token),
                )
                msg = "✅ Semua keyword berhasil diperbarui!"
            else:
                # Append ke yang sudah ada
                current_kw = conn.execute(
                    "SELECT keywords FROM users WHERE bot_token = ?", (token,)
                ).fetchone()[0]
                updated_kw = f"{current_kw}, {new_input}"
                conn.execute(
                    "UPDATE users SET keywords = ? WHERE bot_token = ?",
                    (updated_kw, token),
                )
                msg = f"✅ Keyword `{new_input}` berhasil ditambahkan!"

            conn.commit()
            conn.close()

            await event.reply(msg)
            del user_steps[uid]
            print(
                f"{CLR['GREEN']}💾 DB Updated{CLR['END']} | User: {uid} | Action: {action}"
            )

@main_bot.on(events.NewMessage)
async def reg_flow(event):
    uid = event.sender_id
    if uid not in user_steps or event.text.startswith('/'): return
    
    current_step = user_steps[uid]['step']

    # --- STEP 1: VALIDASI TOKEN & INFO BOT ---
    if current_step == 'WAIT_TOKEN':
        token = event.text.strip()
        # Validasi Token ke Telegram API
        try:
            res = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
            if res.get("ok"):
                bot_info = res["result"]
                user_steps[uid].update({
                    'token': token, 
                    'bot_name': bot_info['first_name'],
                    'bot_username': bot_info['username'],
                    'step': 'WAIT_KEYWORDS'
                })
                
                success_msg = (
                    f"✅ **Bot Terdeteksi!**\n"
                    f"Display Name: `{bot_info['first_name']}`\n"
                    f"Username: @{bot_info['username']}\n\n"
                    "📍 **Langkah berikutnya: Masukkan Keywords**\n"
                    "Keywords adalah kata kunci yang ingin Anda pantau. Gunakan koma sebagai pemisah.\n\n"
                    "💡 **Panduan Keywords yang Relevan:**\n"
                    "• Gunakan kata yang spesifik agar tidak banyak spam.\n"
                    "• Contoh: `roblox, robux, wtb roblox, wts robux`.\n"
                    "• Hindari satu huruf atau kata terlalu umum seperti `a, saya, bot`."
                )
                await event.reply(success_msg)
            else:
                await event.reply("❌ **Token Invalid!** Pastikan Anda menyalin token dengan benar dari @BotFather.")
        except Exception as e:
         # PRINT INI SANGAT PENTING untuk debug di local
            print(f"{CLR['RED']}❌ DEBUG ERROR VALIDASI:{CLR['END']} {e}") 
            await event.reply("⚠️ Terjadi gangguan koneksi saat memvalidasi token.")

    # --- STEP 2: PANDUAN KEYWORDS ---
    elif current_step == 'WAIT_KEYWORDS':
        user_steps[uid].update({'keywords': event.text, 'step': 'WAIT_WORDING'})
        
        wording_guide = (
            "✅ **Keywords Disimpan!**\n\n"
            "📍 **Langkah 3: Masukkan Wording Balasan**\n"
            "Wording adalah pesan otomatis yang akan terkirim saat Anda menekan tombol 'Send Wording'.\n\n"
            "✨ **Tips Wording yang Keren & Profesional:**\n"
            "1. **Langsung & Jelas**: Sebutkan apa yang Anda tawarkan/cari.\n"
            "2. **Call to Action**: Ajak mereka chat ke akun utama Anda.\n\n"
            "📝 **Contoh Wording:**\n"
            "• _'Halo kak! Saya ready stok Robux harga miring. Langsung gas chat @username ya!'_\n"
            "• _'WTB Akun GTA V PC, budget aman. Ada? PM @username fast respond.'_\n"
            "• _'Ready jasa upfoll murah meriah, cek testi di @channeltesti.'_"
        )
        await event.reply(wording_guide)

    # --- STEP 3: FINALISASI & SUMMARY ---
    elif current_step == 'WAIT_WORDING':
        data = user_steps[uid]
        wording = event.text
        
        conn = sqlite3.connect('monitorboy.db')
        conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", 
                     (uid, data['token'], data['keywords'], wording))
        conn.commit()
        conn.close()
        
        final_summary = (
            "🎉 **REGISTRASI BERHASIL!**\n"
            "Bot Anda sudah mulai memantau channel sekarang.\n\n"
            "📊 **Konfigurasi Bot Anda:**\n"
            f"👤 **Display Name:** `{data['bot_name']}`\n"
            f"🤖 **Username:** @{data['bot_username']}\n\n"
            f"🔑 **Keywords:** `{data['keywords']}`\n\n"
            f"📝 **Wording:** `{wording}`\n\n"
            "Powered by **MonitorBoy System** 🚀"
        )
        
        await event.reply(final_summary)
        print(f"{CLR['GREEN']}✨ Reg Success{CLR['END']} | User: {uid} | Bot: @{data['bot_username']}")
        
        # Jalankan instance bot user
        asyncio.create_task(start_user_bot(uid, data['token']))
        del user_steps[uid]

# --- MAIN RUNNER ---

async def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"""
{CLR['CYAN']}{CLR['BOLD']}╔══════════════════════════════════════════════╗
║        MONITOR BOY - AUTO RESTART ON         ║
╚══════════════════════════════════════════════╝{CLR['END']}
    """)
    init_db()
    
    print(f"{CLR['CYAN']}⚙️ Starting Userbot & Main Bot...{CLR['END']}")
    await asyncio.gather(userbot.start(), main_bot.start(bot_token=MAIN_BOT_TOKEN))
    
    conn = sqlite3.connect('monitorboy.db')
    users = conn.execute("SELECT user_id, bot_token FROM users").fetchall()
    conn.close()
    
    for uid, token in users:
        asyncio.create_task(start_user_bot(uid, token))

    print(f"{CLR['GREEN']}{CLR['BOLD']}🚀 ALL SYSTEMS OPERATIONAL{CLR['END']}\n")
    await main_bot.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{CLR['RED']}🛑 System Shutdown.{CLR['END']}")