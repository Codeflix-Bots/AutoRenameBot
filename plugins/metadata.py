from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from helper.database import codeflixbots as db
from pyromod.exceptions import ListenerTimeout
from config import Txt

# Inline buttons for metadata toggle
ON = [[InlineKeyboardButton('Metadata On ✅', callback_data='metadata_1')], 
      [InlineKeyboardButton('Set Custom Metadata', callback_data='custom_metadata')]]
OFF = [[InlineKeyboardButton('Metadata Off ❌', callback_data='metadata_0')], 
       [InlineKeyboardButton('Set Custom Metadata', callback_data='custom_metadata')]]

@Client.on_message(filters.private & filters.command('metadata'))
async def handle_metadata(bot: Client, message: Message):
    ms = await message.reply_text("**Please Wait...**", reply_to_message_id=message.id)
    bool_metadata = await db.get_metadata(message.from_user.id)
    user_metadata = await db.get_metadata_code(message.from_user.id)
    await ms.delete()
    
    if bool_metadata:
        return await message.reply_text(f"Your Current Metadata:\n\n➜ `{user_metadata}`", reply_markup=InlineKeyboardMarkup(ON))
    
    return await message.reply_text(f"Your Current Metadata:\n\n➜ `{user_metadata}`", reply_markup=InlineKeyboardMarkup(OFF))

@Client.on_callback_query(filters.regex('.*?(custom_metadata|metadata).*?'))
async def query_metadata(bot: Client, query: CallbackQuery):
    data = query.data
    user_metadata = await db.get_metadata_code(query.from_user.id)
    
    if data.startswith('metadata_'):
        _bool = data.split('_')[1]
        bool_meta = bool(eval(_bool))
        
        if bool_meta:
            await db.set_metadata(query.from_user.id, bool_meta=False)
            await query.message.edit(f"Your Current Metadata:\n\n➜ `{user_metadata}`", reply_markup=InlineKeyboardMarkup(OFF))
        else:
            await db.set_metadata(query.from_user.id, bool_meta=True)
            await query.message.edit(f"Your Current Metadata:\n\n➜ `{user_metadata}`", reply_markup=InlineKeyboardMarkup(ON))

    elif data == 'custom_metadata':
        await query.message.delete()
        try:
            metadata = await bot.ask(text=Txt.SEND_METADATA, chat_id=query.from_user.id, filters=filters.text, timeout=30, disable_web_page_preview=True)
            if not metadata:
                raise ListenerTimeout()
            ms = await query.message.reply_text("**Please Wait...**", reply_to_message_id=metadata.id)
            await db.set_metadata_code(query.from_user.id, metadata_code=metadata.text)
            await ms.edit("**Your Metadata Code Set Successfully ✅**")
        except ListenerTimeout:
            await query.message.reply_text("⚠️ Error!!\n\n**Request timed out.**\nRestart by using /metadata", reply_to_message_id=query.message.id)
        except Exception as e:
            print(e)

@Client.on_message(filters.private & filters.command('settitle'))
async def set_title(bot: Client, message: Message):
    await set_metadata(bot, message, 'title')

@Client.on_message(filters.private & filters.command('setauthor'))
async def set_author(bot: Client, message: Message):
    await set_metadata(bot, message, 'author')

@Client.on_message(filters.private & filters.command('setartist'))
async def set_artist(bot: Client, message: Message):
    await set_metadata(bot, message, 'artist')

@Client.on_message(filters.private & filters.command('setaudio'))
async def set_audio(bot: Client, message: Message):
    await set_metadata(bot, message, 'audio')

@Client.on_message(filters.private & filters.command('setsubtitle'))
async def set_subtitle(bot: Client, message: Message):
    await set_metadata(bot, message, 'subtitle')

@Client.on_message(filters.private & filters.command('setvideo'))
async def set_video(bot: Client, message: Message):
    await set_metadata(bot, message, 'video')

async def set_metadata(bot: Client, message: Message, metadata_type: str):
    user_id = message.from_user.id
    bool_metadata = await db.get_metadata(user_id)
    
    if not bool_metadata:
        await message.reply_text("**Metadata editing is currently disabled. Use /metadata to enable it.**")
        return
    
    command_parts = message.text.split(f"/set{metadata_type}", 1)
    if len(command_parts) < 2 or not command_parts[1].strip():
        await message.reply_text(f"**Please provide a {metadata_type} after the command /set{metadata_type}.**\n\n"
                                 f"**Example:** `/set{metadata_type} My Custom {metadata_type.capitalize()}`")
        return

    metadata_value = command_parts[1].strip()
    await getattr(db, f'set_{metadata_type}')(user_id, metadata_value)
    await message.reply_text(f"**{metadata_type.capitalize()} has been set to:** `{metadata_value}`")
