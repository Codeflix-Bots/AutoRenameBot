import aiohttp, asyncio, warnings, pytz, datetime
from datetime import datetime
from pytz import timezone
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from config import Config
from aiohttp import web
from route import web_server
import pyrogram.utils
import pyromod

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647


class Bot(Client):

    def __init__(self):
        super().__init__(
            name="codeflixbots",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            workers=200,
            plugins={"root": "plugins"},
            sleep_threshold=15,
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username  
        self.uptime = Config.BOT_UPTIME     
        if Config.WEBHOOK:
            app = web.AppRunner(await web_server())
            await app.setup()       
            await web.TCPSite(app, "0.0.0.0", 8080).start()     
        print(f"{me.first_name} Is Started.....✨️")

        # Define the inline buttons
        buttons = [
            [
                InlineKeyboardButton("ᴏᴡɴᴇʀ", url="https://t.me/sewxiy"),
                InlineKeyboardButton("ᴜᴘᴅᴀᴛᴇs", url="https://t.me/codeflix_bots")
            ]
        ]

        # Send the message with the image and buttons
        image_url = "https://graph.org/file/a27d85469761da836337c.jpg"
        message_text = "ᴀɴʏᴀ ɪs ʀᴇsᴛᴀʀᴛᴇᴅ ᴀɢᴀɪɴ  !"
        
        for chat_id in [Config.LOG_CHANNEL, Config.SUPPORT_CHAT]:
            try:
                await self.send_photo(
                    chat_id,
                    photo=image_url,
                    caption=message_text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception as e:
                print(f"Failed to send message to {chat_id}: {e}")

        if Config.LOG_CHANNEL:
            try:
                curr = datetime.now(timezone("Asia/Kolkata"))
                date = curr.strftime('%d %B, %Y')
                time = curr.strftime('%I:%M:%S %p')
                await self.send_message(Config.LOG_CHANNEL, 
                    f"**{me.mention} Is Restarted !!**\n\n"
                    f"📅 Date : `{date}`\n"
                    f"⏰ Time : `{time}`\n"
                    f"🌐 Timezone : `Asia/Kolkata`\n\n"
                    f"🉐 Version : `v{__version__} (Layer {layer})`</b>"
                )
            except:
                print("Please Make This Is Admin In Your Log Channel")

Bot().run()
