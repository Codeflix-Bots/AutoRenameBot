from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InputMediaDocument, Message
from PIL import Image
from datetime import datetime
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from helper.utils import progress_for_pyrogram, humanbytes, convert
from helper.database import codeflixbots
from config import Config
import os
import time
import re
import subprocess
import asyncio

renaming_operations = {}

# Regular expression patterns for episode and quality extraction
episode_patterns = {
    "pattern1": re.compile(r'S(\d+)(?:E|EP)(\d+)'),
    "pattern2": re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)'),
    "pattern3": re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)'),
    "pattern3_2": re.compile(r'(?:\s*-\s*(\d+)\s*)'),
    "pattern4": re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE),
}

quality_patterns = {
    "pattern5": re.compile(r'\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b', re.IGNORECASE),
    "pattern6": re.compile(r'[([<{]?\s*4k\s*[)\]>}]?', re.IGNORECASE),
    "pattern7": re.compile(r'[([<{]?\s*2k\s*[)\]>}]?', re.IGNORECASE),
    "pattern8": re.compile(r'[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b', re.IGNORECASE),
    "pattern9": re.compile(r'[([<{]?\s*4kX264\s*[)\]>}]?', re.IGNORECASE),
    "pattern10": re.compile(r'[([<{]?\s*4kx265\s*[)\]>}]?', re.IGNORECASE),
}

def extract_quality(filename):
    """Extract video quality from the filename."""
    for key, pattern in quality_patterns.items():
        match = re.search(pattern, filename)
        if match:
            quality = match.group(1) if key == "pattern5" else key.split('pattern')[-1]
            return quality
    
    return "Unknown"

def extract_episode_number(filename):
    """Extract episode number from the filename."""
    for key, pattern in episode_patterns.items():
        match = re.search(pattern, filename)
        if match:
            return match.group(2) if key in ['pattern1', 'pattern2', 'pattern4'] else match.group(1)
    
    return None

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    """Automatically rename files based on user preferences."""
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    media_preference = await codeflixbots.get_media_preference(user_id)

    if not format_template:
        return await message.reply_text("Please Set An Auto Rename Format First Using /autorename")

    # Determine media type and filename
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        media_type = media_preference or "document"
    elif message.video:
        file_id = message.video.file_id
        file_name = f"{message.video.file_name}.mp4"
        media_type = media_preference or "video"
    elif message.audio:
        file_id = message.audio.file_id
        file_name = f"{message.audio.file_name}.mp3"
        media_type = media_preference or "audio"
    else:
        return await message.reply_text("Unsupported File Type")

    # Prevent duplicate renaming requests within a short period
    if file_id in renaming_operations:
        elapsed_time = (datetime.now() - renaming_operations[file_id]).seconds
        if elapsed_time < 10:
            return

    renaming_operations[file_id] = datetime.now()

    episode_number = extract_episode_number(file_name)
    if episode_number:
        placeholders = ["episode", "Episode", "EPISODE", "{episode}"]
        for placeholder in placeholders:
            format_template = format_template.replace(placeholder, str(episode_number), 1)

        # Extract quality and replace placeholders
        quality_placeholders = ["quality", "Quality", "QUALITY", "{quality}"]
        for quality_placeholder in quality_placeholders:
            if quality_placeholder in format_template:
                extracted_quality = extract_quality(file_name)
                format_template = format_template.replace(quality_placeholder, extracted_quality)

    # Prepare for file renaming and downloading
    _, file_extension = os.path.splitext(file_name)
    renamed_file_name = f"{format_template}{file_extension}"
    renamed_file_path = f"downloads/{renamed_file_name}"
    metadata_file_path = f"Metadata/{renamed_file_name}"
    os.makedirs(os.path.dirname(renamed_file_path), exist_ok=True)
    os.makedirs(os.path.dirname(metadata_file_path), exist_ok=True)

    download_msg = await message.reply_text("**__Downloading...__**")

    try:
        path = await client.download_media(
            message,
            file_name=renamed_file_path,
            progress=progress_for_pyrogram,
            progress_args=("Download Started...", download_msg, time.time()),
        )
    except Exception as e:
        del renaming_operations[file_id]
        return await download_msg.edit(f"**Download Error:** {e}")

    await download_msg.edit("**__Renaming and Adding Metadata...__**")

    try:
        # Rename the file first
        os.rename(path, renamed_file_path)
        path = renamed_file_path

        # Prepare metadata command
        metadata_command = [
            'ffmpeg',  # Or you can use ffmpeg_cmd if you have a custom path
            '-i', path,
            '-metadata', f'title={await codeflixbots.get_title(user_id)}',
            '-metadata', f'artist={await codeflixbots.get_artist(user_id)}',
            '-metadata', f'author={await codeflixbots.get_author(user_id)}',
            '-metadata:s:v', f'title={await codeflixbots.get_video(user_id)}',
            '-metadata:s:a', f'title={await codeflixbots.get_audio(user_id)}',
            '-metadata:s:s', f'title={await codeflixbots.get_subtitle(user_id)}',
            '-map', '0',
            '-c', 'copy',
            '-loglevel', 'error',
            metadata_file_path
        ]

        # Execute the metadata command
        process = await asyncio.create_subprocess_exec(
            *metadata_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode()
            await download_msg.edit(f"**Metadata Error:**\n{error_message}")
            return

        # Use the new metadata file path for the upload
        path = metadata_file_path

        # Upload the file
        upload_msg = await download_msg.edit("**__Uploading...__**")

        ph_path = None
        c_caption = await codeflixbots.get_caption(message.chat.id)
        c_thumb = await codeflixbots.get_thumbnail(message.chat.id)

        caption = (
            c_caption.format(
                filename=renamed_file_name,
                filesize=humanbytes(message.document.file_size),
                duration=convert(0),
            )
            if c_caption
            else f"**{renamed_file_name}**"
        )

        # Handle thumbnail processing
        if c_thumb:
            ph_path = await client.download_media(c_thumb)
        elif media_type == "video" and message.video.thumbs:
            ph_path = await client.download_media(message.video.thumbs[0].file_id)

        if ph_path:
            img = Image.open(ph_path).convert("RGB")
            img = img.resize((320, 320))
            img.save(ph_path, "JPEG")

        try:
            # Send the media based on its type
            if media_type == "document":
                await client.send_document(
                    message.chat.id,
                    document=path,
                    thumb=ph_path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
            elif media_type == "video":
                await client.send_video(
                    message.chat.id,
                    video=path,
                    caption=caption,
                    thumb=ph_path,
                    duration=0,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
            elif media_type == "audio":
                await client.send_audio(
                    message.chat.id,
                    audio=path,
                    caption=caption,
                    thumb=ph_path,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )

        except FloodWait as e:
            await upload_msg.edit(f"**FloodWait Error:** {str(e)}")
            return
        finally:
            if os.path.exists(path):
                os.remove(path)
            if ph_path and os.path.exists(ph_path):
                os.remove(ph_path)

        await download_msg.delete()
        await upload_msg.delete()
        del renaming_operations[file_id]

    except Exception as e:
        await download_msg.edit(f"**Error:** {str(e)}")
        del renaming_operations[file_id]
