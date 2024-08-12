from pyrogram import Client, filters, enums 
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import UserNotParticipant
from config import Config
from helper.database import codeflixbots

async def not_subscribed(_, client, message):
    await codeflixbots.add_user(client, message)
    if not Config.FORCE_SUB:
        return False
    try:             
        user = await client.get_chat_member(Config.FORCE_SUB, message.from_user.id) 
        if user.status == enums.ChatMemberStatus.BANNED:
            return True 
        else:
            return False                
    except UserNotParticipant:
        pass
    return True


@Client.on_message(filters.private & filters.create(not_subscribed))
async def forces_sub(client, message):
    buttons = [
        [InlineKeyboardButton(text="• ᴜᴘᴅᴀᴛᴇs •", url=f"https://t.me/{Config.FORCE_SUB}")],
        [InlineKeyboardButton(text="• sᴜᴘᴘᴏʀᴛ •", url="https://t.me/CodeflixSupport")]
    ]
    text = "<b>ʙʀᴏ/sɪs\n\nʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ᴍʏ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ɢʀᴏᴜᴘ ᴛᴏ ᴜsᴇ ᴍᴇ\n\nᴋɪɴᴅʟʏ ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ.</b>"
    try:
        user = await client.get_chat_member(Config.FORCE_SUB, message.from_user.id)    
        if user.status == enums.ChatMemberStatus.BANNED:                                   
            return await client.send_message(message.from_user.id, text="Sorry You Are Banned To Use Me")  
    except UserNotParticipant:                       
        return await message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    return await message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
