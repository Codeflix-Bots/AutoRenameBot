from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from helper.database import codeflixbots

@Client.on_message(filters.private & filters.command("autorename"))
async def auto_rename_command(client, message):
    user_id = message.from_user.id
    command_text = message.text.split("/autorename", 1)[1].strip() if len(message.text.split("/autorename", 1)) > 1 else ""
    
    if command_text:
        # Save the format template to the database
        await codeflixbots.set_format_template(user_id, command_text)
        await message.reply_text(f"**🌟 ꜰᴀɴᴛᴀꜱᴛɪᴄ! ʏᴏᴜ'ʀᴇ ʀᴇᴀᴅʏ ᴛᴏ ᴀᴜᴛᴏ-ʀᴇɴᴀᴍᴇ ʏᴏᴜʀ ꜰɪʟᴇꜱ ᴛᴏ:\n {command_text} .\n\n📩 ꜱɪᴍᴘʟʏ ꜱᴇɴᴅ ᴛʜᴇ ꜰɪʟᴇ(ꜱ) ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʀᴇɴᴀᴍᴇ.\n\nʀᴇᴍᴇᴍʙᴇʀ, ᴍᴀʏʙᴇ ɪ'ʟʟ ʀᴇɴᴀᴍᴇ ʏᴏᴜʀ ꜰɪʟᴇꜱ ꜱʟᴏᴡ ʙᴜᴛ ɪ ꜱᴜʀᴇʟʏ ᴍᴀᴋᴇ ᴛʜᴇᴍ ᴘᴇʀꜰᴇᴄᴛ!✨**")
    else:
        await message.reply_text(
            "**ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴇᴡ ɴᴀᴍᴇ ᴀꜰᴛᴇʀ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ /Autorename\n\n"
            "ʜᴇʀᴇ'ꜱ ʜᴏᴡ ᴛᴏ ᴜꜱᴇ ɪᴛ:\n"
            "ᴇxᴀᴍᴘʟᴇ ꜰᴏʀᴍᴀᴛ: ᴍʏᴄᴏᴏʟᴠɪᴅᴇᴏ [ᴇᴘɪꜱᴏᴅᴇ] [ǫᴜᴀʟɪᴛʏ]**"
        )

@Client.on_message(filters.private & filters.command("setmedia"))
async def set_media_command(client, message):
    user_id = message.from_user.id    
    media_type = message.text.split("/setmedia", 1)[1].strip().lower()

    # Save the preferred media type to the database
    await codeflixbots.set_media_preference(user_id, media_type)

    await message.reply_text(f"**Media Preference Set To :** {media_type} ✅")
