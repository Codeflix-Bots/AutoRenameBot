from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from helper.database import codeflixbots as db
from config import Txt

# Inline buttons for metadata toggle
ON = [[InlineKeyboardButton('Metadata On ✅', callback_data='metadata_1')],
      [InlineKeyboardButton('Metadata Commands', callback_data='metadata_commands')]]
OFF = [[InlineKeyboardButton('Metadata Off ❌', callback_data='metadata_0')],
       [InlineKeyboardButton('Metadata Commands', callback_data='metadata_commands')]]

# Buttons for metadata commands
METADATA_COMMANDS_BUTTONS = [
    [InlineKeyboardButton('Set Title', callback_data='set_title')],
    [InlineKeyboardButton('Set Author', callback_data='set_author')],
    [InlineKeyboardButton('Set Artist', callback_data='set_artist')],
    [InlineKeyboardButton('Set Audio', callback_data='set_audio')],
    [InlineKeyboardButton('Set Subtitle', callback_data='set_subtitle')],
    [InlineKeyboardButton('Set Video', callback_data='set_video')],
    [InlineKeyboardButton('Back to Metadata', callback_data='back_to_metadata')]
]

@Client.on_message(filters.private & filters.command('metadata'))
async def handle_metadata(bot: Client, message: Message):
    ms = await message.reply_text("**Please Wait...**", reply_to_message_id=message.id)
    bool_metadata = await db.get_metadata(message.from_user.id)
    user_metadata = await db.get_metadata_code(message.from_user.id)
    await ms.delete()
    
    if bool_metadata:
        await message.reply_text(f"Your Current Metadata:\n\n➜ `{user_metadata}`", reply_markup=InlineKeyboardMarkup(ON))
    else:
        await message.reply_text(f"Your Current Metadata:\n\n➜ `{user_metadata}`", reply_markup=InlineKeyboardMarkup(OFF))

@Client.on_callback_query(filters.regex('.*?(metadata|set_).*?'))
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

    elif data == 'metadata_commands':
        await query.message.edit("**Select Metadata Command to Set:**", reply_markup=InlineKeyboardMarkup(METADATA_COMMANDS_BUTTONS))

    elif data == 'back_to_metadata':
        bool_metadata = await db.get_metadata(query.from_user.id)
        user_metadata = await db.get_metadata_code(query.from_user.id)
        if bool_metadata:
            await query.message.edit(f"Your Current Metadata:\n\n➜ `{user_metadata}`", reply_markup=InlineKeyboardMarkup(ON))
        else:
            await query.message.edit(f"Your Current Metadata:\n\n➜ `{user_metadata}`", reply_markup=InlineKeyboardMarkup(OFF))

    elif data.startswith('set_'):
        metadata_type = data.split('_')[1]
        metadata_prompt = {
            'title': 'Gɪᴠᴇ Tʜᴇ Tɪᴛʟᴇ',
            'author': 'Gɪᴠᴇ Tʜᴇ Aᴜᴛʜᴏʀ',
            'artist': 'Gɪᴠᴇ Tʜᴇ Aʀᴛɪsᴛ',
            'audio': 'Gɪᴠᴇ Tʜᴇ Aᴜᴅɪᴏ Tɪᴛʟᴇ',
            'subtitle': 'Gɪᴠᴇ Tʜᴇ Sᴜʙᴛɪᴛʟᴇ',
            'video': 'Gɪᴠᴇ Tʜᴇ Vɪᴅᴇᴏ Tɪᴛʟᴇ'
        }
        await query.message.reply_text(metadata_prompt[metadata_type], reply_markup=InlineKeyboardMarkup([]))  # Send prompt
        await db.set_metadata_code(query.from_user.id, metadata_type)  # Set the pending metadata type

@Client.on_message(filters.private & filters.text)
async def handle_user_response(bot: Client, message: Message):
    user_id = message.from_user.id
    pending_metadata_code = await db.get_metadata_code(user_id)
    
    if pending_metadata_code:
        # Ensure pending_metadata_code is clean
        if pending_metadata_code in ['title', 'author', 'artist', 'audio', 'subtitle', 'video']:
            await getattr(db, f'set_{pending_metadata_code}')(user_id, message.text)
            await message.reply_text(f"**Your Metadata `{pending_metadata_code}` Set Successfully ✅**")
        else:
            await message.reply_text("⚠️ Invalid metadata type. Please try again.")
        await db.set_metadata_code(user_id, None)  # Clear pending metadata type
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
