import os
import re
import time
import shutil
import asyncio
from datetime import datetime
from PIL import Image
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InputMediaDocument, Message
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from plugins.antinsfw import check_anti_nsfw
from helper.utils import progress_for_pyrogram, humanbytes, convert
from helper.database import codeflixbots
from config import Config

# Global renaming operations tracker
renaming_operations = {}

# Regex patterns for extracting episode numbers and qualities
episode_patterns = {
    'S01E02': re.compile(r'S(\d+)(?:E|EP)(\d+)'),
    'S01 E02': re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)'),
    'E or EP': re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)'),
    'Hyphen': re.compile(r'(?:\s*-\s*(\d+)\s*)'),
    'S2 09': re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE),
    'Standalone': re.compile(r'(\d+)'),
}

quality_patterns = {
    'Quality 3-4 digits': re.compile(r'\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b', re.IGNORECASE),
    '4k': re.compile(r'[([<{]?\s*4k\s*[)\]>}]?', re.IGNORECASE),
    '2k': re.compile(r'[([<{]?\s*2k\s*[)\]>}]?', re.IGNORECASE),
    'HdRip': re.compile(r'[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b', re.IGNORECASE),
    '4kX264': re.compile(r'[([<{]?\s*4kX264\s*[)\]>}]?', re.IGNORECASE),
    '4kx265': re.compile(r'[([<{]?\s*4kx265\s*[)\]>}]?', re.IGNORECASE),
}

def extract_quality(filename):
    """Extract the quality from the filename based on defined patterns."""
    for quality_name, pattern in quality_patterns.items():
        match = re.search(pattern, filename)
        if match:
            return match.group(1) if match.group(1) else match.group(2)
    return "Unknown"

def extract_episode_number(filename):
    """Extract the episode number from the filename based on defined patterns."""
    for pattern_name, pattern in episode_patterns.items():
        match = re.search(pattern, filename)
        if match:
            return match.group(2) if pattern_name != 'Standalone' else match.group(1)
    return None

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    media_preference = await codeflixbots.get_media_preference(user_id)

    if not format_template:
        return await message.reply_text("Please Set An Auto Rename Format First Using /autorename")

    file_info = {}
    if message.document:
        file_info['id'] = message.document.file_id
        file_info['name'] = message.document.file_name
        media_type = media_preference or "document"
    elif message.video:
        file_info['id'] = message.video.file_id
        file_info['name'] = f"{message.video.file_name}.mp4"
        media_type = media_preference or "video"
    elif message.audio:
        file_info['id'] = message.audio.file_id
        file_info['name'] = f"{message.audio.file_name}.mp3"
        media_type = media_preference or "audio"
    else:
        return await message.reply_text("Unsupported File Type")

    # Anti-NSFW check
    if await check_anti_nsfw(file_info['name'], message):
        return await message.reply_text("NSFW content detected. File upload rejected.")

    if file_info['id'] in renaming_operations:
        elapsed_time = (datetime.now() - renaming_operations[file_info['id']]).seconds
        if elapsed_time < 10:
            return

    renaming_operations[file_info['id']] = datetime.now()

    episode_number = extract_episode_number(file_info['name'])
    if episode_number:
        format_template = format_template.replace("episode", str(episode_number), 1)
        format_template = format_template.replace("Episode", str(episode_number), 1)
        format_template = format_template.replace("EPISODE", str(episode_number), 1)
        format_template = format_template.replace("{episode}", str(episode_number), 1)

        # Add extracted qualities to the format template
        extracted_qualities = extract_quality(file_info['name'])
        format_template = format_template.replace("quality", extracted_qualities)

    _, file_extension = os.path.splitext(file_info['name'])
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
        del renaming_operations[file_info['id']]
        return await download_msg.edit(f"**Download Error:** {e}")

    await download_msg.edit("**__Renaming and Adding Metadata...__**")

    try:
        # Rename the file
        os.rename(path, renamed_file_path)
        path = renamed_file_path

        # Prepare metadata command
        ffmpeg_cmd = shutil.which('ffmpeg')
        metadata_command = [
            ffmpeg_cmd,
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
            send_media_func = {
                "document": client.send_document,
                "video": client.send_video,
                "audio": client.send_audio,
            }[media_type]

            await send_media_func(
                message.chat.id,
                document=path if media_type == "document" else None,
                video=path if media_type == "video" else None,
                audio=path if media_type == "audio" else None,
                thumb=ph_path,
                caption=caption,
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
        await upload_msg.edit("**__Upload Successful!__**")

    except Exception as e:
        await download_msg.edit(f"**Error:** {e}")
    finally:
        del renaming_operations[file_info['id']]
