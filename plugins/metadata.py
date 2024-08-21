from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from helper.database import codeflixbots
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

@Client.on_message(filters.private & filters.command('metadata'))
async def handle_metadata(client: Client, message: Message):
    try:
        # Notify the user that the request is being processed
        ms = await message.reply_text("**Please Wait...**", reply_to_message_id=message.id)
        
        # Retrieve current metadata status and user's custom metadata
        bool_metadata = await codeflixbots.get_metadata(message.from_user.id)
        user_metadata = await codeflixbots.get_metadata_code(message.from_user.id)
        
        # Remove the initial "Please Wait..." message
        await ms.delete()
        
        # Create the inline keyboard based on the current metadata status
        reply_markup = InlineKeyboardMarkup(ON if bool_metadata else OFF)
        
        # Send the current metadata to the user
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
            # Toggle the metadata on/off status
            bool_meta = data.split('_')[1] == "1"
            user_metadata = await codeflixbots.get_metadata_code(query.from_user.id)
            
            # Update the metadata status in the database
            await codeflixbots.set_metadata(query.from_user.id, bool_meta=not bool_meta)
            
            # Update the inline keyboard based on the new metadata status
            reply_markup = InlineKeyboardMarkup(ON if not bool_meta else OFF)
            
            # Edit the message with the updated metadata status
            await query.message.edit(
                f"**Your Current Metadata :-**\n\n➜ `{user_metadata}` ",
                reply_markup=reply_markup
            )

        elif data == 'custom_metadata':
            await query.message.delete()
            try:
                # Ask the user to provide custom metadata
                metadata = await client.ask(
                    text=Txt.SEND_METADATA,
                    chat_id=query.from_user.id,
                    filters=filters.text,
                    timeout=30,
                    disable_web_page_preview=True,
                    reply_to_message_id=query.message.id
                )
            except ListenerTimeout:
                # Handle timeout if the user doesn't respond in time
                await query.message.reply_text(
                    "⚠️ Error !!\n\n**Request Timed Out.**\n\nRestart By Using /metadata",
                    reply_to_message_id=query.message.id
                )
                return

            # Notify the user that the metadata is being set
            ms = await query.message.reply_text("**Please Wait...**", reply_to_message_id=metadata.id)
            
            # Store the custom metadata in the database
            await codeflixbots.set_metadata_code(query.from_user.id, metadata_code=metadata.text)
            
            # Confirm that the metadata was set successfully
            await ms.edit(
                "**Your Metadata Code Set Successfully ✅**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close')]])
            )
    except Exception as e:
        await query.message.reply_text(f"An error occurred: {str(e)}")
