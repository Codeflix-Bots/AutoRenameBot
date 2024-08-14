from pyrogram import Client, filters
from helper.database import codeflixbots

# Global variable to track metadata status
metadata_enabled = {}

@Client.on_message(filters.private & filters.command("metadata"))
async def toggle_metadata(client, message):
    user_id = message.from_user.id
    if user_id in metadata_enabled:
        metadata_enabled[user_id] = not metadata_enabled[user_id]
    else:
        metadata_enabled[user_id] = True

    status = "enabled" if metadata_enabled[user_id] else "disabled"
    await message.reply_text(f"**Metadata editing is now {status}.**")

# Command to set custom metadata
@Client.on_message(filters.private & filters.command("settitle"))
async def set_title(client, message):
    await set_metadata(client, message, "title")

@Client.on_message(filters.private & filters.command("setauthor"))
async def set_author(client, message):
    await set_metadata(client, message, "author")

@Client.on_message(filters.private & filters.command("setartist"))
async def set_artist(client, message):
    await set_metadata(client, message, "artist")

@Client.on_message(filters.private & filters.command("setaudio"))
async def set_audio(client, message):
    await set_metadata(client, message, "audio title")

@Client.on_message(filters.private & filters.command("setsubtitle"))
async def set_subtitle(client, message):
    await set_metadata(client, message, "subtitle")

@Client.on_message(filters.private & filters.command("setvideo"))
async def set_video(client, message):
    await set_metadata(client, message, "video title")

async def set_metadata(client, message, metadata_type):
    user_id = message.from_user.id

    if not metadata_enabled.get(user_id, False):
        await message.reply_text("**Metadata editing is currently disabled. Use /metadata to enable it.**")
        return

    # Extract the metadata value from the command
    command_parts = message.text.split(f"/set{metadata_type}", 1)
    if len(command_parts) < 2 or not command_parts[1].strip():
        await message.reply_text(f"**Please provide a {metadata_type} after the command /set{metadata_type}.**\n\n"
                                 f"**Example:** `/set{metadata_type} My Custom {metadata_type.capitalize()}`")
        return

    metadata_value = command_parts[1].strip()

    # Save the metadata value to the database
    await codeflixbots.set_metadata(user_id, metadata_type, metadata_value)

    await message.reply_text(f"**{metadata_type.capitalize()} has been set to:** `{metadata_value}`")

# codeflix_bots
