import os
import sys
import uuid
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import motor.motor_asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import Message

# Render Web Service Alive Check Server
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

threading.Thread(target=start_health_server, daemon=True).start()

# Config Variables
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "0"))

mongo_client = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URL)
database = mongo_client["TrackerBotDB"]
collection = database["stored_files"]

bot = Client(
    "TrackerBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@bot.on_message(filters.command("start") & filters.private)
async def handle_start(client: Client, message: Message):
    args = message.text.split()
    user = message.from_user

    if len(args) > 1:
        code = args[1]
        data = await collection.find_one({"_id": code})

        if not data:
            await message.reply_text("❌ ဖိုင်ရှာမတွေ့ပါ သို့မဟုတ် ဖျက်လိုက်ပါပြီ။")
            return

        file_id = data.get("file_id")
        caption = data.get("caption", "")
        media_type = data.get("media_type", "document")

        try:
            if media_type == "video":
                await client.send_video(
                    chat_id=message.chat.id,
                    video=file_id,
                    caption=caption,
                    protect_content=True
                )
            elif media_type == "photo":
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=file_id,
                    caption=caption,
                    protect_content=True
                )
            else:
                await client.send_document(
                    chat_id=message.chat.id,
                    document=file_id,
                    caption=caption,
                    protect_content=True
                )
        except Exception as err:
            await message.reply_text(f"Error: {err}")
            return

        user_name = user.mention
        username_text = f"@{user.username}" if user.username else "No Username"
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_text = (
            f"🚨 **အဖွဲ့ဝင် ကြည့်ရှုမှု မှတ်တမ်း**\n\n"
            f"👤 **Name:** {user_name}\n"
            f"🏷 **Username:** {username_text}\n"
            f"🆔 **User ID:** `{user.id}`\n"
            f"⏰ **Time:** `{now_time}`\n"
            f"📁 **File Code:** `{code}`"
        )
        try:
            await client.send_message(chat_id=LOG_CHANNEL, text=log_text)
        except Exception as e:
            print(f"Log Error: {e}")
        return

    await message.reply_text(
        f"မင်္ဂလာပါ {user.mention} 👋\n\n"
        "ဗီဒီယိုဖိုင်များကို Tracking Link ဖြင့် ပေးပို့နိုင်သော Bot ဖြစ်ပါသည်။"
    )

@bot.on_message((filters.video | filters.document | filters.photo) & filters.private)
async def handle_media_upload(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        await message.reply_text("⛔️ သင်သည် Admin မဟုတ်သဖြင့် ဖိုင်တင်ခွင့် မရှိပါ။")
        return

    msg = await message.reply_text("⏳ ဖိုင်ကို Database ထဲသို့ သိမ်းဆည်းနေပါသည်...")

    media_type = "document"
    file_id = ""

    if message.video:
        media_type = "video"
        file_id = message.video.file_id
    elif message.photo:
        media_type = "photo"
        file_id = message.photo.file_id
    elif message.document:
        media_type = "document"
        file_id = message.document.file_id

    caption = message.caption or ""
    code_id = uuid.uuid4().hex[:10]

    await collection.insert_one({
        "_id": code_id,
        "file_id": file_id,
        "media_type": media_type,
        "caption": caption,
        "date": datetime.now()
    })

    bot_info = await client.get_me()
    link = f"https://t.me/{bot_info.username}?start={code_id}"

    success_msg = (
        f"✅ **ဖိုင်သိမ်းဆည်းမှု အောင်မြင်ပါသည်!**\n\n"
        f"🔗 **Tracking Link:**\n`{link}`\n\n"
        f"📌 *ဤ Link ကို Channel တွင် တင်ထားနိုင်ပြီး အဖွဲ့ဝင်များ ဝင်ကြည့်သည့်အခါတိုင်း Log Channel သို့ အကြောင်းကြားပါမည်။*"
    )
    await msg.edit_text(success_msg)

async def main():
    await bot.start()
    print("Bot is successfully running!")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
