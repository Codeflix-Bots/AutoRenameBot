from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from helper.database import codeflixbots as db
from config import Txt

# Inline buttons for metadata toggle
ON = [
    [InlineKeyboardButton('Metadata On ✅', callback_data='metadata_1')],
    [InlineKeyboardButton('Set Custom Metadata', callback_data='custom_metadata')],
    [InlineKeyboardButton('Set Title', callback_data='set_title')],
    [InlineKeyboardButton('Set Author', callback_data='set_author')],
    [InlineKeyboardButton('Set Artist', callback_data='set_artist')],
    [InlineKeyboardButton('Set Audio', callback_data='set_audio')],
    [InlineKeyboardButton('Set Subtitle', callback_data='set_subtitle')],
    [InlineKeyboardButton('Set Video', callback_data='set_video')]
]
OFF = [
    [InlineKeyboardButton('Metadata Off ❌', callback_data='metadata_0')],
    [InlineKeyboardButton('Set Custom Metadata', callback_data='custom_metadata')],
    [InlineKeyboardButton('Set Title', callback_data='set_title')],
    [InlineKeyboardButton('Set Author', callback_data='set_author')],
    [InlineKeyboardButton('Set Artist', callback_data='set_artist')],
    [InlineKeyboardButton('Set Audio', callback_data='set_audio')],
    [InlineKeyboardButton('Set Subtitle', callback_data='set_subtitle')],
    [InlineKeyboardButton('Set Video', callback_data='set_video')]
]

@Client.on_message(filters.private & filters.command('metadata'))
async def handle_metadata(bot: Client, message: Message):
    ms = await message.reply_text("**Please Wait...**", reply_to_message_id=message.id)
    bool_metadata = await db.get_metadata(message.from_user.id)
    
    metadata = {
        "title": await db.get_title(message.from_user.id),
        "author": await db.get_author(message.from_user.id),
        "artist": await db.get_artist(message.from_user.id),
        "audio": await db.get_audio(message.from_user.id),
        "subtitle": await db.get_subtitle(message.from_user.id),
        "video": await db.get_video(message.from_user.id),
    }
    
    user_metadata = await db.get_metadata_code(message.from_user.id)
    
    metadata_text = "\n".join(f"➜ **{key.capitalize()}**: `{value}`" for key, value in metadata.items() if value)
    metadata_text = metadata_text if metadata_text else "No metadata set."
    
    await ms.delete()
    
    if bool_metadata:
        return await message.reply_text(f"Your Current Metadata:\n\n{metadata_text}\n\n**Custom Metadata Code:** `{user_metadata}`", reply_markup=InlineKeyboardMarkup(ON))
    
    return await message.reply_text(f"Your Current Metadata:\n\n{metadata_text}\n\n**Custom Metadata Code:** `{user_metadata}`", reply_markup=InlineKeyboardMarkup(OFF))

@Client.on_callback_query(filters.regex('.*?(custom_metadata|metadata|set_).*?'))
async def query_metadata(bot: Client, query: CallbackQuery):
    data = query.data
    user_metadata = await db.get_metadata_code(query.from_user.id)
    
    if data.startswith('metadata_'):
        bool_meta = bool(eval(data.split('_')[1]))  # Evaluate the boolean value
        
        if bool_meta:
            await db.set_metadata(query.from_user.id, False)
            await query.message.edit(f"Your Current Metadata:\n\n➜ `{user_metadata}`", reply_markup=InlineKeyboardMarkup(OFF))
        else:
            await db.set_metadata(query.from_user.id, True)
            await query.message.edit(f"Your Current Metadata:\n\n➜ `{user_metadata}`", reply_markup=InlineKeyboardMarkup(ON))

    elif data == 'custom_metadata':
        await query.message.delete()
        await query.message.reply_text(Txt.SEND_METADATA)  # Prompt user for metadata
        await db.set_metadata_code(query.from_user.id, None)
        
    elif data.startswith('set_'):
        await query.message.delete()
        metadata_type = data.split('_', 1)[1]
        await query.message.reply_text(f"Please provide the new {metadata_type}:", reply_to_message_id=query.message.id)
        await db.set_metadata_code(query.from_user.id, metadata_type)

@Client.on_message(filters.private & filters.text)
async def handle_user_response(bot: Client, message: Message):
    user_id = message.from_user.id
    pending_metadata_type = await db.get_metadata_code(user_id)
    
    if pending_metadata_type:
        await getattr(db, f'set_{pending_metadata_type}')(user_id, message.text)
        await message.reply_text(f"**{pending_metadata_type.capitalize()} has been set to:** `{message.text}`")
        await db.set_metadata_code(user_id, None)  # Clear pending metadata request
    else:
        # Handle other text messages or commands
        pass

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
