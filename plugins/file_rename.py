import shutil
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
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
import asyncio

renaming_operations = {}

# Episode patterns
episode_patterns = [
    re.compile(r'S(\d+)(?:E|EP)(\d+)'),                 # Pattern 1: S01E02 or S01EP02
    re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)'),       # Pattern 2: S01 E02 or S01 - E02
    re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+))'),      # Pattern 3: E02 or EP02
    re.compile(r'(?:\s*-\s*(\d+)\s*)'),                 # Pattern 3_2: - 02
    re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE),    # Pattern 4: S2 09 (ex)
    re.compile(r'(\d+)')                                # Pattern X: Standalone episode
]

# Quality patterns
quality_patterns = {
    re.compile(r'\b(?:.*?(\d{3,4}p).*?|.*?(\d{3,4}[^\dp]*p))\b', re.IGNORECASE): lambda m: m.group(1) or m.group(2),
    re.compile(r'\s*4k\s*', re.IGNORECASE): lambda m: "4k",
    re.compile(r'\s*2k\s*', re.IGNORECASE): lambda m: "2k",
    re.compile(r'\bHdRip\b', re.IGNORECASE): lambda m: "HdRip",
    re.compile(r'\s*4kX264\s*', re.IGNORECASE): lambda m: "4kX264",
    re.compile(r'\s*4kx265\s*', re.IGNORECASE): lambda m: "4kx265"
}


def extract_episode_number(filename):
    for pattern in episode_patterns:
        match = re.search(pattern, filename)
        if match:
            return match.group(2) if len(match.groups()) > 1 else match.group(1)
    return None


def extract_quality(filename):
    for pattern, func in quality_patterns.items():
        match = re.search(pattern, filename)
        if match:
            return func(match)
    return "Unknown"


@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    media_preference = await codeflixbots.get_media_preference(user_id)

    if not format_template:
        return await message.reply_text("Please set an auto-rename format first using /autorename.")

    media_type, file_id, file_name = None, None, None
    if message.document:
        media_type = media_preference or "document"
        file_id = message.document.file_id
        file_name = message.document.file_name
    elif message.video:
        media_type = media_preference or "video"
        file_id = message.video.file_id
        file_name = f"{message.video.file_name}.mp4"
    elif message.audio:
        media_type = media_preference or "audio"
        file_id = message.audio.file_id
        file_name = f"{message.audio.file_name}.mp3"
    else:
        return await message.reply_text("Unsupported file type.")

    # Anti-NSFW Check (if applicable)
    if await check_anti_nsfw(file_name, message):
        return await message.reply_text("NSFW content detected. File upload rejected.")

    if file_id in renaming_operations and (datetime.now() - renaming_operations[file_id]).seconds < 10:
        return

    renaming_operations[file_id] = datetime.now()

    # Extract episode and quality
    episode_number = extract_episode_number(file_name)
    quality = extract_quality(file_name)

    # Format file name based on user template
    if episode_number:
        format_template = format_template.replace("{episode}", str(episode_number))
    format_template = format_template.replace("{quality}", quality)

    _, file_extension = os.path.splitext(file_name)
    renamed_file_name = f"{format_template}{file_extension}"
    renamed_file_path = f"downloads/{renamed_file_name}"
    metadata_file_path = f"Metadata/{renamed_file_name}"
    os.makedirs(os.path.dirname(renamed_file_path), exist_ok=True)
    os.makedirs(os.path.dirname(metadata_file_path), exist_ok=True)

    download_msg = await message.reply_text("Downloading...")

    try:
        path = await client.download_media(
            message,
            file_name=renamed_file_path,
            progress=progress_for_pyrogram,
            progress_args=("Download Started...", download_msg, time.time()),
        )
    except Exception as e:
        del renaming_operations[file_id]
        return await download_msg.edit(f"Download error: {e}")

    await download_msg.edit("Renaming and adding metadata...")

    try:
        os.rename(path, renamed_file_path)
        path = renamed_file_path

        ffmpeg_cmd = shutil.which('ffmpeg')
        metadata_command = [
            ffmpeg_cmd, '-i', path,
            '-metadata', f'title={await codeflixbots.get_title(user_id)}',
            '-metadata', f'artist={await codeflixbots.get_artist(user_id)}',
            '-metadata', f'author={await codeflixbots.get_author(user_id)}',
            '-metadata:s:v', f'title={await codeflixbots.get_video(user_id)}',
            '-metadata:s:a', f'title={await codeflixbots.get_audio(user_id)}',
            '-metadata:s:s', f'title={await codeflixbots.get_subtitle(user_id)}',
            '-map', '0', '-c', 'copy', '-loglevel', 'error', metadata_file_path
        ]

        process = await asyncio.create_subprocess_exec(
            *metadata_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode()
            await download_msg.edit(f"Metadata error:\n{error_message}")
            return

        # Replace path with the new metadata file
        path = metadata_file_path

        # Upload the file
        upload_msg = await download_msg.edit("Uploading...")

        ph_path = None
        c_caption = await codeflixbots.get_caption(message.chat.id)
        c_thumb = await codeflixbots.get_thumbnail(message.chat.id)

        caption = (
            c_caption.format(
                filename=renamed_file_name,
                filesize=humanbytes(message.document.file_size),
                duration=convert(0),
            ) if c_caption else f"**{renamed_file_name}**"
        )

        if c_thumb:
            ph_path = await client.download_media(c_thumb)
        elif media_type == "video" and message.video.thumbs:
            ph_path = await client.download_media(message.video.thumbs[0].file_id)

        if ph_path:
            img = Image.open(ph_path).convert("RGB")
            img = img.resize((320, 320))
            img.save(ph_path, "JPEG")

        send_func = {
            "document": client.send_document,
            "video": client.send_video,
            "audio": client.send_audio
        }.get(media_type)

        await send_func(
            message.chat.id,
            document=path if media_type == "document" else None,
            video=path if media_type == "video" else None,
            audio=path if media_type == "audio" else None,
            caption=caption,
            thumb=ph_path,
            progress=progress_for_pyrogram,
            progress_args=("Upload Started...", upload_msg, time.time()),
        )

    except FloodWait as e:
        await upload_msg.edit(f"Flood wait error: {str(e)}")
        return
    finally:
        if os.path.exists(path):
            os.remove(path)
        if ph_path and os.path.exists(ph_path):
            os.remove(ph_path)
        del renaming_operations[file_id]

    await download_msg.delete()
    await upload_msg.delete()
