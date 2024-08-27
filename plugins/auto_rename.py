from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from helper.database import codeflixbots

@Client.on_message(filters.private & filters.command("autorename"))
async def auto_rename_command(client, message):
    user_id = message.from_user.id

    # Extract the format from the command
    command_parts = message.text.split("/autorename", 1)
    if len(command_parts) < 2 or not command_parts[1].strip():
        await message.reply_text("**ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴇᴡ ɴᴀᴍᴇ ᴀꜰᴛᴇʀ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ /autorename**\n\n"
                                 "ʜᴇʀᴇ'ꜱ ʜᴏᴡ ᴛᴏ ᴜꜱᴇ ɪᴛ:\n"
                                 "**ᴇxᴀᴍᴘʟᴇ ꜰᴏʀᴍᴀᴛ:** `ᴍʏᴄᴏᴏʟᴠɪᴅᴇᴏ [ᴇᴘɪꜱᴏᴅᴇ] [ǫᴜᴀʟɪᴛʏ]`")
        return

    format_template = command_parts[1].strip()

    # Save the format template to the database
    await codeflixbots.set_format_template(user_id, format_template)

    # Send confirmation message with the template in mono font
    await message.reply_text(f"**🌟 ꜰᴀɴᴛᴀꜱᴛɪᴄ! ʏᴏᴜ'ʀᴇ ʀᴇᴀᴅʏ ᴛᴏ ᴀᴜᴛᴏ-ʀᴇɴᴀᴍᴇ ʏᴏᴜʀ ꜰɪʟᴇꜱ.**\n\n"
                             "📩 ꜱɪᴍᴘʟʏ ꜱᴇɴᴅ ᴛʜᴇ ꜰɪʟᴇ(ꜱ) ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʀᴇɴᴀᴍᴇ.\n\n"
                             f"**ʏᴏᴜʀ ꜱᴀᴠᴇᴅ ᴛᴇᴍᴘʟᴀᴛᴇ:** `{format_template}`\n\n"
                             "ʀᴇᴍᴇᴍʙᴇʀ, ᴍᴀʏʙᴇ ɪ'ʟʟ ʀᴇɴᴀᴍᴇ ʏᴏᴜʀ ꜰɪʟᴇꜱ ꜱʟᴏᴡ ʙᴜᴛ ɪ ꜱᴜʀᴇʟʏ ᴍᴀᴋᴇ ᴛʜᴇᴍ ᴘᴇʀꜰᴇᴄᴛ!✨")

@Client.on_message(filters.private & filters.command("setmedia"))
async def set_media_command(client, message):
    user_id = message.from_user.id
    
    # Define inline keyboard buttons
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("ᴅᴏᴄᴜᴍᴇɴᴛ", callback_data="setmedia_document")],
        [InlineKeyboardButton("ᴠɪᴅᴇᴏ", callback_data="setmedia_video")]
    ])
    
    # Send a message with inline buttons
    await message.reply_text(
        "**ᴘʟᴇᴀsᴇ sᴇʟᴇᴄᴛ ᴛʜᴇ ᴍᴇᴅɪᴀ ᴛʏᴘᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴇᴛ:**",
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("^setmedia_"))
async def handle_media_selection(client, callback_query):
    user_id = callback_query.from_user.id
    media_type = callback_query.data.split("_", 1)[1]
    
    # Save the preferred media type to the database
    await codeflixbots.set_media_preference(user_id, media_type)
    
    # Acknowledge the callback and reply with confirmation
    await callback_query.answer(f"**Media Preference Set To :** {media_type} ✅")
    await callback_query.message.edit_text(f"**Media Preference Set To :** {media_type} ✅")
