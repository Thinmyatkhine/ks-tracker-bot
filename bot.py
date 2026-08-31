import os
import sys
import uuid
from datetime import datetime
import motor.motor_asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# Config Variables
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
OWNER_ID = int(os.environ.get("OWNER_ID", 0))
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))

client = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URL)
db = client["TelegramBotDB"]
files_col = db["files"]

bot = Client(
    "TrackerBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    text = message.text.split()
    user = message.from_user
    
    if len(text) > 1:
        file_code = text[1]
        file_data = await files_col.find_one({"_id": file_code})
        
        if not file_data:
            await message.reply_text("❌ ဖိုင်ရှာမတွေ့ပါ သို့မဟုတ် ဖျက်လိုက်ပါပြီ။")
            return

        file_id = file_data.get("file_id")
        caption = file_data.get("caption", "")
        file_type = file_data.get("file_type", "document")
        
        # Send protected file (Save/Forward ကာကွယ်ထားသည်)
        try:
            if file_type == "video":
                await client.send_video(
                    chat_id=message.chat.id,
                    video=file_id,
                    caption=caption,
                    protect_content=True
                )
            elif file_type == "document":
                await client.send_document(
                    chat_id=message.chat.id,
                    document=file_id,
                    caption=caption,
                    protect_content=True
                )
            elif file_type == "photo":
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=file_id,
                    caption=caption,
                    protect_content=True
                )
        except Exception as e:
            await message.reply_text(f"Error: {e}")
            return

        # Send User Log to LOG_CHANNEL
        username_str = f"@{user.username}" if user.username else "No Username"
        log_msg = (
            f"🚨 ဗီဒီယို ကြည့်ရှု/ရယူမှု မှတ်တမ်း\n\n"
            f"👤 Name: {user.mention}\n"
            f"🏷 Username: {username_str}\n"
            f"🆔 User ID: {user.id}\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📁 File Code: {file_code}"
        )
        try:
            await client.send_message(chat_id=LOG_CHANNEL, text=log_msg)
        except Exception as e:
            print(f"Log Error: {e}")
        return

    await message.reply_text(
        f"မင်္ဂလာပါ {user.mention} 👋\n\n"
        "ဗီဒီယိုဖိုင်များကို Tracking Link ဖြင့် ပေးပို့နိုင်သော Bot ဖြစ်ပါသည်။"
    )

@bot.on_message((filters.video | filters.document | filters.photo) & filters.private)
async def file_store_handler(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        await message.reply_text("⛔️ သင်သည် Admin မဟုတ်သဖြင့် ဖိုင်တင်ခွင့် မရှိပါ။")
        return

    status = await message.reply_text("⏳ ဖိုင်ကို Database ထဲသို့ သိမ်းဆည်းနေပါသည်...")
    
    file_type = "document"
    file_id = None
    if message.video:
        file_type = "video"
        file_id = message.video.file_id
    elif message.document:
        file_type = "document"
        file_id = message.document.file_id
    elif message.photo:
        file_type = "photo"
        file_id = message.photo.file_id

    caption = message.caption or ""
    code = uuid.uuid4().hex[:10]

    await files_col.insert_one({
        "_id": code,
        "file_id": file_id,
        "file_type": file_type,
        "caption": caption,
        "created_at": datetime.now()
    })
  bot_info = await client.get_me()
    share_link = f"https://t.me/{bot_info.username}?start={code}"

    reply_text = (
        f"✅ ဖိုင်သိမ်းဆည်းမှု အောင်မြင်ပါသည်!\n\n"
        f"🔗 Tracking Link:\n{share_link}\n\n"
        f"📌 *ဤ Link ကို Channel တွင် တင်ထားနိုင်ပြီး အဖွဲ့ဝင်များ ဝင်ကြည့်သည့်အခါတိုင်း Log Channel သို့ အကြောင်းကြားပါမည်။*"
    )
    await status.edit_text(reply_text)

if name == "main":
    print("Bot is starting...")
    bot.run()
