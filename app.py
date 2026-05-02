import os
import asyncio
import time
import math
import aiohttp
from aiohttp import web
from pyrogram import Client, filters, idle
import aria2p

# Environment variables
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Initialize Pyrogram Client
app = Client("leech_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize Aria2p connecting to the local daemon
aria2 = aria2p.API(aria2p.Client(host="http://localhost", port=6800, secret=""))

# Dictionary to hold user states for threaded replies
user_states = {}

# ---- DUMMY WEB SERVER FOR HUGGING FACE SPACES ----
async def handle_ping(request):
    return web.Response(text="Bhai, Bot zinda hai! 🚀")

async def web_server():
    server = web.Application()
    server.router.add_get('/', handle_ping)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 7860)
    await site.start()
# --------------------------------------------------

def format_bytes(size):
    if not size:
        return "0 B"
    power = 2**10
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size >= power and n < 4:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"

def format_time(seconds):
    if not seconds or math.isinf(seconds):
        return "N/A"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text(
        "Namaste! 🙏\n"
        "Main ek ultra-fast leech bot hoon. Mujhe koi bhi direct link bhejo aur main use download karke Telegram pe seedha upload kar dunga."
    )

@app.on_message(filters.regex(r"^https?://"))
async def url_handler(client, message):
    url = message.text.strip()
    user_states[message.from_user.id] = {"url": url}
    await message.reply_text(
        "Link mil gaya bhai! 🚀\n"
        "Ab batao kitne threads use karun download ke liye? (1 se 16 ke beech me koi number bhejo)"
    )

@app.on_message(filters.text & ~filters.command("start"))
async def thread_handler(client, message):
    user_id = message.from_user.id
    if user_id not in user_states or "url" not in user_states[user_id]:
        return
    
    try:
        threads = int(message.text.strip())
        if not (1 <= threads <= 16):
            raise ValueError()
    except ValueError:
        await message.reply_text("Arey bhai, sahi number likh. 1 se 16 ke beech ka number bhej. 🤦‍♂️")
        return

    url = user_states[user_id]["url"]
    del user_states[user_id] # Clear state
    
    status_msg = await message.reply_text("⏳ Download shuru ho raha hai...")
    
    try:
        download = aria2.add_uris(
            [url], 
            options={"split": str(threads), "max-connection-per-server": str(threads), "dir": "/app/downloads"}
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Error aagaya add karte waqt:\n`{e}`")
        return

    # Track download progress loop
    last_update_time = time.time()
    while not download.is_complete:
        download.update()
        
        if download.has_failed:
            await status_msg.edit_text("❌ Download fail ho gaya bhai. Link dobara check kar.")
            return
            
        current_time = time.time()
        # Edit message every 3 seconds to avoid FloodWait limits
        if current_time - last_update_time >= 3:
            try:
                progress = download.progress
                speed = download.download_speed
                eta = download.eta.total_seconds() if download.eta else 0
                completed = download.completed_length
                total = download.total_length
                
                text = (
                    f"📥 **Downloading...**\n"
                    f"📊 **Progress:** {progress:.2f}%\n"
                    f"🚀 **Speed:** {format_bytes(speed)}/s\n"
                    f"⏳ **ETA:** {format_time(eta)}\n"
                    f"📦 **Size:** {format_bytes(completed)} / {format_bytes(total)}"
                )
                await status_msg.edit_text(text)
                last_update_time = current_time
            except Exception:
                pass # Ignore Pyrogram message edit exceptions (e.g., if content is the same)
        
        await asyncio.sleep(1)

    # Download complete
    download.update()
    file_path = download.files[0].path
    await status_msg.edit_text("✅ Download poora ho gaya!\nAb Telegram pe upload kar raha hoon... Ruko zara, sabar karo.")
    
    # Trigger Local Server upload process
    await upload_file_local_server(client, message.chat.id, file_path, status_msg)

async def upload_file_local_server(client, chat_id, file_path, status_msg):
    # This is the endpoint for the locally running C++ Bot API server
    api_url = f"http://localhost:8081/bot{BOT_TOKEN}/sendDocument"
    
    # THE MAGIC TRICK: Pass the document as a local file URI. 
    # The C++ server will read it instantly from disk, bypassing Python's upload limitations.
    local_uri = f"file://{file_path}"
    
    data = {
        "chat_id": str(chat_id),
        "document": local_uri,
        "caption": "🎉 Lo bhai, tumhara file aa gaya! Maze karo."
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(api_url, data=data) as response:
                if response.status == 200:
                    await status_msg.edit_text("🚀 Upload Done! Superfast speed me.")
                    # Clean up the file from local storage after successful upload
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                else:
                    error_text = await response.text()
                    await status_msg.edit_text(f"❌ Upload me thoda issue aa gaya:\n`{error_text}`")
        except Exception as e:
            await status_msg.edit_text(f"❌ Exception aagaya upload me:\n`{str(e)}`")

async def main():
    # Run the dummy web server for HF Spaces
    asyncio.create_task(web_server())
    
    # Start the Pyrogram client
    await app.start()
    print("Bot is up and running via Pyrogram!")
    
    # Idle to keep the process alive
    await idle()
    
    # Graceful stop
    await app.stop()

if __name__ == "__main__":
    # Ensure event loop handles everything efficiently
    app.run(main())