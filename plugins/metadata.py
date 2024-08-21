from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from helper.database import codeflixbots
from pyromod import listen
from pyromod.exceptions import ListenerTimeout
from config import Txt

# Define the inline keyboard options
ON = [
    [InlineKeyboardButton('• ᴍᴇᴛᴀᴅᴀᴛᴀ ᴏɴ •', callback_data='metadata_1')],
    [InlineKeyboardButton('• sᴇᴛ ᴄᴜsᴛᴏᴍ ᴍᴇᴛᴀᴅᴀᴛᴀ •', callback_data='custom_metadata')]
]

OFF = [
    [InlineKeyboardButton('• ᴍᴇᴛᴀᴅᴀᴛᴀ ᴏғғ •', callback_data='metadata_0')],
    [InlineKeyboardButton('• sᴇᴛ ᴄᴜsᴛᴏᴍ ᴍᴇᴛᴀᴅᴀᴛᴀ •', callback_data='custom_metadata')]
]

# Use the Client instance method decorator
@Client.on_message(filters.private & filters.command('metadata'))
async def handle_metadata(client: Client, message: Message):
    try:
        ms = await message.reply_text("**Please Wait...**", reply_to_message_id=message.id)
        bool_metadata = await codeflixbots.get_metadata(message.from_user.id)
        user_metadata = await codeflixbots.get_metadata_code(message.from_user.id)
        await ms.delete()
        
        reply_markup = InlineKeyboardMarkup(ON if bool_metadata else OFF)
        await message.reply_text(
            f"**Your Current Metadata :-**\n\n➜ `{user_metadata}` ",
            quote=True,
            reply_markup=reply_markup
        )
    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")

@Client.on_callback_query(filters.regex('.*?(custom_metadata|metadata).*?'))
async def query_metadata(client: Client, query: CallbackQuery):
    try:
        data = query.data

        if data.startswith('metadata_'):
            bool_meta = data.split('_')[1] == "1"
            user_metadata = await codeflixbots.get_metadata_code(query.from_user.id)
            
            await codeflixbots.set_metadata(query.from_user.id, bool_meta=not bool_meta)
            reply_markup = InlineKeyboardMarkup(ON if not bool_meta else OFF)
            await query.message.edit(
                f"**Your Current Metadata :-**\n\n➜ `{user_metadata}` ",
                reply_markup=reply_markup
            )

        elif data == 'custom_metadata':
            await query.message.delete()
            try:
                metadata = await client.ask(
                    text=Txt.SEND_METADATA,
                    chat_id=query.from_user.id,
                    filters=filters.text,
                    timeout=30,
                    disable_web_page_preview=True,
                    reply_to_message_id=query.message.id
                )
            except ListenerTimeout:
                await query.message.reply_text(
                    "⚠️ Error !!\n\n**Request Timed Out.**\n\nRestart By Using /metadata",
                    reply_to_message_id=query.message.id
                )
                return

            ms = await query.message.reply_text("**Please Wait...**", reply_to_message_id=metadata.id)
            await codeflixbots.set_metadata_code(query.from_user.id, metadata_code=metadata.text)
            await ms.edit(
                "**Your Metadata Code Set Successfully ✅**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close')]])
            )
