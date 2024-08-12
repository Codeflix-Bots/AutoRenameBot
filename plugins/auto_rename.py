from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from helper.database import codeflixbots

@Client.on_message(filters.private & filters.command("autorename"))
async def auto_rename_command(client, message):
    user_id = message.from_user.id

    # Extract the format from the command
    format_template = message.text.split("/autorename", 1)[1].strip()

    # Save the format template to the database
    await codeflixbots.set_format_template(user_id, format_template)

    await message.reply_text("**🌟 ꜰᴀɴᴛᴀꜱᴛɪᴄ! ʏᴏᴜ'ʀᴇ ʀᴇᴀᴅʏ ᴛᴏ ᴀᴜᴛᴏ-ʀᴇɴᴀᴍᴇ ʏᴏᴜʀ ꜰɪʟᴇꜱ ᴛᴏ:\n<code>{format_template}</code>.\n\n📩 ꜱɪᴍᴘʟʏ ꜱᴇɴᴅ ᴛʜᴇ ꜰɪʟᴇ(ꜱ) ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʀᴇɴᴀᴍᴇ.\n\nʀᴇᴍᴇᴍʙᴇʀ, ᴍᴀʏʙᴇ ɪ'ʟʟ ʀᴇɴᴀᴍᴇ ʏᴏᴜʀ ꜰɪʟᴇꜱ ꜱʟᴏᴡ ʙᴜᴛ ɪ ꜱᴜʀᴇʟʏ ᴍᴀᴋᴇ ᴛʜᴇᴍ ᴘᴇʀꜰᴇᴄᴛ!✨**")

@Client.on_message(filters.private & filters.command("setmedia"))
async def set_media_command(client, message):
    user_id = message.from_user.id    
    media_type = message.text.split("/setmedia", 1)[1].strip().lower()

    # Save the preferred media type to the database
    await codeflixbots.set_media_preference(user_id, media_type)

    await message.reply_text(f"**Media Preference Set To :** {media_type} ✅")
