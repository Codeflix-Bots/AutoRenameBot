from config import Config, Txt
from helper.database import codeflixbots
from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
import os, sys, time, asyncio, logging, datetime
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ADMIN_USER_ID = Config.ADMIN

# Flag to indicate if the bot is restarting
is_restarting = False

@Client.on_message(filters.private & filters.command("restart") & filters.user(ADMIN_USER_ID))
async def restart_bot(b, m):
    global is_restarting
    if not is_restarting:
        is_restarting = True
        await m.reply_text("**Restarting.....**")

        # Gracefully stop the bot's event loop
        b.stop()
        time.sleep(2)  # Adjust the delay duration based on your bot's shutdown time

        # Restart the bot process
        os.execl(sys.executable, sys.executable, *sys.argv)


@Client.on_message(filters.private & filters.command("addpremium") & filters.user(ADMIN_USER_ID))
async def add_premium_user(bot: Client, message: Message):
    if len(message.command) < 3:
        return await message.reply_text("⚠️ Usage: `/addpremium <user_id> <plan_name>`\nPlans: Bronze, Silver, Gold, Platinum, Diamond")

    try:
        target_id = int(message.command[1])
        plan_name = message.command[2].capitalize()
        valid_plans = ["Bronze", "Silver", "Gold", "Platinum", "Diamond"]

        if plan_name not in valid_plans:
            return await message.reply_text(f"❌ Invalid Plan!\nChoose from: {', '.join(valid_plans)}")

        await codeflixbots.set_user_plan(target_id, plan_name)
        await message.reply_text(f"✅ Successfully added User **{target_id}** to **{plan_name}** Premium plan.")

        # Try to notify the user
        try:
            await bot.send_message(target_id, f"🎉 **Congratulations!**\nYour account has been upgraded to the **{plan_name}** Premium Plan by an Admin.\nCheck your limits using /myplan.")
        except Exception:
            pass

    except ValueError:
        await message.reply_text("❌ User ID must be an integer.")

@Client.on_message(filters.private & filters.command("rmpremium") & filters.user(ADMIN_USER_ID))
async def rm_premium_user(bot: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("⚠️ Usage: `/rmpremium <user_id>`")

    try:
        target_id = int(message.command[1])
        await codeflixbots.set_user_plan(target_id, "Free")
        await message.reply_text(f"✅ Successfully downgraded User **{target_id}** to **Free** plan.")

        # Try to notify the user
        try:
            await bot.send_message(target_id, "⚠️ **Notice:** Your Premium plan has expired or been revoked by an Admin. You are now on the Free plan.")
        except Exception:
            pass

    except ValueError:
        await message.reply_text("❌ User ID must be an integer.")

@Client.on_message(filters.private & filters.command("myplan"))
async def my_plan_command(bot: Client, message: Message):
    user_id = message.from_user.id
    plan_details = await codeflixbots.get_plan_details(user_id)

    if not plan_details:
        return await message.reply_text("Failed to fetch plan details.")

    plan_name = plan_details.get("plan", "Free").capitalize()
    used_renames = plan_details.get("used_renames", 0)
    used_extracts = plan_details.get("used_extracts", 0)

    limits = {
        "Free": {"rename": 20, "extract": 0},
        "Bronze": {"rename": 40, "extract": 20},
        "Silver": {"rename": 60, "extract": 30},
        "Gold": {"rename": 100, "extract": 50},
        "Platinum": {"rename": "Unlimited", "extract": 100},
        "Diamond": {"rename": "Unlimited", "extract": "Unlimited"}
    }

    user_limits = limits.get(plan_name, limits["Free"])

    text = (
        f"📊 **Your Current Plan:** `{plan_name}`\n\n"
        f"🔄 **Renames Today:** `{used_renames} / {user_limits['rename']}`\n"
        f"🎧 **Extracts Today:** `{used_extracts} / {user_limits['extract']}`\n\n"
    )

    if plan_name == "Free":
        text += "💡 **Tip:** Use `/extend` to get 5 free extra extracts today, or upgrade to a Premium plan!"

    await message.reply_text(text)


@Client.on_message(filters.private & filters.command("tutorial"))
async def tutorial(bot: Client, message: Message):
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    await message.reply_text(
        text=Txt.FILE_NAME_TXT.format(format_template=format_template),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴏᴡɴᴇʀ", url="https://t.me/cosmic_freak"),
             InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ", url="https://t.me/codeflix_bots")]
        ])
    )


@Client.on_message(filters.command(["stats", "status"]) & filters.user(Config.ADMIN))
async def get_stats(bot, message):
    total_users = await codeflixbots.total_users_count()
    uptime = time.strftime("%Hh%Mm%Ss", time.gmtime(time.time() - bot.uptime))    
    start_t = time.time()
    st = await message.reply('**Accessing The Details.....**')    
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await st.edit(text=f"**--Bot Status--** \n\n**⌚️ Bot Uptime :** {uptime} \n**🐌 Current Ping :** `{time_taken_s:.3f} ms` \n**👭 Total Users :** `{total_users}`")

@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN) & filters.reply)
async def broadcast_handler(bot: Client, m: Message):
    await bot.send_message(Config.LOG_CHANNEL, f"{m.from_user.mention} or {m.from_user.id} Is Started The Broadcast......")
    all_users = await codeflixbots.get_all_users()
    broadcast_msg = m.reply_to_message
    sts_msg = await m.reply_text("Broadcast Started..!") 
    done = 0
    failed = 0
    success = 0
    start_time = time.time()
    total_users = await codeflixbots.total_users_count()
    async for user in all_users:
        sts = await send_msg(user['_id'], broadcast_msg)
        if sts == 200:
           success += 1
        else:
           failed += 1
        if sts == 400:
           await codeflixbots.delete_user(user['_id'])
        done += 1
        if not done % 20:
           await sts_msg.edit(f"Broadcast In Progress: \n\nTotal Users {total_users} \nCompleted : {done} / {total_users}\nSuccess : {success}\nFailed : {failed}")
    completed_in = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts_msg.edit(f"Bʀᴏᴀᴅᴄᴀꜱᴛ Cᴏᴍᴩʟᴇᴛᴇᴅ: \nCᴏᴍᴩʟᴇᴛᴇᴅ Iɴ `{completed_in}`.\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nFailed: {failed}")
           
async def send_msg(user_id, message):
    try:
        await message.copy(chat_id=int(user_id))
        return 200
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return send_msg(user_id, message)
    except InputUserDeactivated:
        logger.info(f"{user_id} : Deactivated")
        return 400
    except UserIsBlocked:
        logger.info(f"{user_id} : Blocked The Bot")
        return 400
    except PeerIdInvalid:
        logger.info(f"{user_id} : User ID Invalid")
        return 400
    except Exception as e:
        logger.error(f"{user_id} : {e}")
        return 500
