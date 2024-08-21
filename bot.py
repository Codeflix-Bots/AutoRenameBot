from datetime import datetime
from pytz import timezone
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from config import Config
from aiohttp import web
from route import web_server
import pyrogram.utils

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="renamer",
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
        print(f"{me.first_name} is starting...")

        if Config.WEBHOOK:
            try:
                app = web.AppRunner(await web_server())
                await app.setup()
                await web.TCPSite(app, "0.0.0.0", 8080).start()
                print("Webhook is set up and running.")
            except Exception as e:
                print(f"Failed to set up webhook: {e}")

        for admin_id in Config.ADMIN:
            try:
                await self.send_message(Config.LOG_CHANNEL, f"**{me.first_name} is started...✨️**")
            except Exception as e:
                print(f"Failed to send start message to admin {admin_id}: {e}")

        if Config.LOG_CHANNEL:
            try:
                curr = datetime.now(timezone("Asia/Kolkata"))
                date = curr.strftime('%d %B, %Y')
                time = curr.strftime('%I:%M:%S %p')
                await self.send_message(
                    Config.LOG_CHANNEL,
                    f"**{me.mention} is restarted!**\n\n"
                    f"📅 Date: `{date}`\n"
                    f"⏰ Time: `{time}`\n"
                    f"🌐 Timezone: `Asia/Kolkata`\n\n"
                    f"🉐 Version: `v{__version__} (Layer {layer})`"
                )
            except Exception as e:
                print(f"Failed to send log channel message: {e}")

        print(f"{me.first_name} is fully started and running...✨️")

Bot().run()
