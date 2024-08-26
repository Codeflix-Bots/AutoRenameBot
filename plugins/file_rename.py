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
from helper.utils import add_prefix_suffix
import os
import time
import re
import asyncio

# Dictionary to track renaming operations for rate limiting
renaming_operations = {}

# Regular expression patterns for episode and quality extraction
EPISODE_PATTERNS = [
    re.compile(r'S(\d+)(?:E|EP)(\d+)'),  # S01E02 or S01EP02
    re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)'),  # S01 E02 or S01 EP02 or S01 - E01 or S01 - EP02
    re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)'),  # Episode Number After "E" or "EP"
    re.compile(r'(?:\s*-\s*(\d+)\s*)'),  # episode number after - [hyphen]
    re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE),  # S2 09 example
    re.compile(r'(\d+)')  # Standalone Episode Number
]

QUALITY_PATTERNS = [
    re.compile(r'\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b', re.IGNORECASE),  # 3-4 digits before 'p' as quality
    re.compile(r'[([<{]?\s*4k\s*[)\]>}]?', re.IGNORECASE),  # Find 4k in brackets or parentheses
    re.compile(r'[([<{]?\s*2k\s*[)\]>}]?', re.IGNORECASE),  # Find 2k in brackets or parentheses
    re.compile(r'[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b', re.IGNORECASE),  # Find HdRip without spaces
    re.compile(r'[([<{]?\s*4kX264\s*[)\]>}]?', re.IGNORECASE),  # Find 4kX264 in brackets or parentheses
    re.compile(r'[([<{]?\s*4kx265\s*[)\]>}]?', re.IGNORECASE)  # Find 4kx265 in brackets or parentheses
]

def extract_episode_number(filename):
    """Extract the episode number from the filename."""
    for pattern in EPISODE_PATTERNS:
        match = re.search(pattern, filename)
        if match:
            return match.group(1) if len(match.groups()) == 1 else match.group(2)
    return None

def extract_quality(filename):
    """Extract the quality from the filename."""
    for pattern in QUALITY_PATTERNS:
        match = re.search(pattern, filename)
        if match:
            return match.group(1) or match.group(2)  # Extracted quality from both patterns
    return "Unknown"

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    media_preference = await codeflixbots.get_media_preference(user_id)

    if not format_template:
        return await message.reply_text("Please Set An Auto Rename Format First Using /autorename")

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

    # Rate limiting
    if file_id in renaming_operations:
        elapsed_time = (datetime.now() - renaming_operations[file_id]).seconds
        if elapsed_time < 10:
            return

    renaming_operations[file_id] = datetime.now()

    episode_number = extract_episode_number(file_name)
    quality = extract_quality(file_name)

    # Replace placeholders in format template
    if episode_number:
        placeholders = ["episode", "Episode", "EPISODE", "{episode}"]
        for placeholder in placeholders:
            format_template = format_template.replace(placeholder, str(episode_number), 1)

    quality_placeholders = ["quality", "Quality", "QUALITY", "{quality}"]
    for quality_placeholder in quality_placeholders:
        format_template = format_template.replace(quality_placeholder, quality)

    # Extracting necessary information for prefix and suffix
    prefix = await codeflixbots.get_prefix(message.chat.id)
    suffix = await codeflixbots.get_suffix(message.chat.id)

    _, file_extension = os.path.splitext(file_name)
    renamed_file_name = f"{format_template}{file_extension}"
    renamed_file_path = f"downloads/{renamed_file_name}"
    metadata_file_path = f"Metadata/{renamed_file_name}"
    
    # Add prefix and suffix using a custom function
    new_filename = add_prefix_suffix(renamed_file_name, prefix, suffix)
    os.makedirs(os.path.dirname(renamed_file_path), exist_ok=True)
    os.makedirs(os.path.dirname(metadata_file_path), exist_ok=True)

    download_msg = await message.reply_text("**__Downloading...__**")

    try:
        path = await client.download_media(
            message,
            file_name=renamed_file_path,
            progress=progress_for_pyrogram,
            progress_args=("Download Started...", download_msg, time.time())
        )
    except Exception as e:
        del renaming_operations[file_id]
        return await download_msg.edit(f"**Download Error:** {e}")

    await download_msg.edit("**__Renaming and Adding Metadata...__**")

    try:
        # Rename the file first
        os.rename(path, renamed_file_path)
        path = renamed_file_path

        # Add metadata if needed
        metadata_added = False
        _bool_metadata = await codeflixbots.get_metadata(user_id)
        if _bool_metadata:
            metadata = await codeflixbots.get_metadata_code(user_id)
            if metadata:
                cmd = f'ffmpeg -i "{renamed_file_path}"  -map 0 -c:s copy -c:a copy -c:v copy -metadata title="{metadata}" -metadata author="{metadata}" -metadata:s:s title="{metadata}" -metadata:s:a title="{metadata}" -metadata:s:v title="{metadata}"  "{metadata_file_path}"'
                try:
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await process.communicate()
                    if process.returncode == 0:
                        metadata_added = True
                        path = metadata_file_path
                    else:
                        error_message = stderr.decode()
                        await download_msg.edit(f"**Metadata Error:**\n{error_message}")
                except asyncio.TimeoutError:
                    await download_msg.edit("**ffmpeg command timed out.**")
                    return
                except Exception as e:
                    await download_msg.edit(f"**Exception occurred:**\n{str(e)}")
                    return
        else:
            metadata_added = True

        if not metadata_added:
            await download_msg.edit("Metadata addition failed. Uploading the renamed file only.")
            path = renamed_file_path

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

        if c_thumb:
            ph_path = await client.download_media(c_thumb)
        elif media_type == "video" and message.video.thumbs:
            ph_path = await client.download_media(message.video.thumbs[0].file_id)

        if ph_path:
            img = Image.open(ph_path).convert("RGB")
            img.save(ph_path, "JPEG")
        
        try:
            if media_type == "document":
                await message.reply_document(
                    document=path,
                    caption=caption,
                    thumb=ph_path,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
            elif media_type == "video":
                await message.reply_video(
                    video=path,
                    caption=caption,
                    thumb=ph_path,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
            elif media_type == "audio":
                await message.reply_audio(
                    audio=path,
                    caption=caption,
                    thumb=ph_path,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
            else:
                await message.reply_document(
                    document=path,
                    caption=caption,
                    thumb=ph_path,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
        except Exception as e:
            await upload_msg.edit(f"**Upload Error:** {e}")
    finally:
        del renaming_operations[file_id]
        os.remove(path)
        if ph_path:
            os.remove(ph_path)
        await upload_msg.delete()
