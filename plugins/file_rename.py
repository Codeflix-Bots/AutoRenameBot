from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from plugins.antinsfw import check_anti_nsfw
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
import shutil

renaming_operations = {}

# Define regex patterns
patterns = {
    "episode": [
        re.compile(r'S(\d+)(?:E|EP)(\d+)'),
        re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)'),
        re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)'),
        re.compile(r'(?:\s*-\s*(\d+)\s*)'),
        re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE),
        re.compile(r'(\d+)')
    ],
    "quality": [
        re.compile(r'\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b', re.IGNORECASE),
        re.compile(r'[([<{]?\s*4k\s*[)\]>}]?', re.IGNORECASE),
        re.compile(r'[([<{]?\s*2k\s*[)\]>}]?', re.IGNORECASE),
        re.compile(r'[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b', re.IGNORECASE),
        re.compile(r'[([<{]?\s*4kX264\s*[)\]>}]?', re.IGNORECASE),
        re.compile(r'[([<{]?\s*4kx265\s*[)\]>}]?', re.IGNORECASE)
    ]
}

def extract_quality(filename):
    for i, pattern in enumerate(patterns["quality"], start=5):
        match = re.search(pattern, filename)
        if match:
            return ["Unknown", "4k", "2k", "HdRip", "4kX264", "4kx265"][i-5]
    return "Unknown"

def extract_episode_number(filename):
    for pattern in patterns["episode"]:
        match = re.search(pattern, filename)
        if match:
            return match.group(2) or match.group(1)
    return None

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    media_preference = await codeflixbots.get_media_preference(user_id)
    filename = message.document.file_name if message.document else (message.video.file_name + ".mp4" if message.video else (message.audio.file_name + ".mp3" if message.audio else None))

    if not filename or await check_anti_nsfw(filename, message):
        return await message.reply_text("Unsupported File Type or NSFW Content Detected")

    if not format_template:
        return await message.reply_text("Please Set An Auto Rename Format First Using /autorename")

    if message.document:
        file_id, media_type = message.document.file_id, media_preference or "document"
    elif message.video:
        file_id, media_type = message.video.file_id, media_preference or "video"
    elif message.audio:
        file_id, media_type = message.audio.file_id, media_preference or "audio"

    if file_id in renaming_operations and (datetime.now() - renaming_operations[file_id]).seconds < 10:
        return

    renaming_operations[file_id] = datetime.now()
    episode_number = extract_episode_number(filename)

    if episode_number:
        for placeholder in ["episode", "Episode", "EPISODE", "{episode}"]:
            format_template = format_template.replace(placeholder, str(episode_number), 1)

        for placeholder in ["quality", "Quality", "QUALITY", "{quality}"]:
            if placeholder in format_template:
                extracted_quality = extract_quality(filename)
                if extracted_quality == "Unknown":
                    await message.reply_text("**__I Was Not Able To Extract The Quality Properly. Renaming As 'Unknown'...__**")
                    del renaming_operations[file_id]
                    return
                format_template = format_template.replace(placeholder, extracted_quality)

    _, file_extension = os.path.splitext(filename)
    renamed_file_name = f"{format_template}{file_extension}"
    renamed_file_path = f"downloads/{renamed_file_name}"
    os.makedirs(os.path.dirname(renamed_file_path), exist_ok=True)

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
        os.rename(path, renamed_file_path)
        path = renamed_file_path

        user_metadata_enabled = await codeflixbots.get_metadata(user_id)
        if user_metadata_enabled == "On":
            temp_output_file = renamed_file_path.replace(file_extension, f"_temp{file_extension}")
            ffmpeg_cmd = shutil.which('ffmpeg')

            metadata_command = [
                ffmpeg_cmd if ffmpeg_cmd else 'ffmpeg',
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
                temp_output_file
            ]

            try:
                process = await asyncio.create_subprocess_exec(
                    *metadata_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()
                if process.returncode == 0:
                    path = temp_output_file
                else:
                    await download_msg.edit(f"**Metadata Error:**\n{stderr.decode()}")
                    raise Exception("Metadata addition failed")
            except (asyncio.TimeoutError, Exception) as e:
                await download_msg.edit(f"**Exception occurred:**\n{str(e)}")
                return
        else:
            metadata_added = True

        if not metadata_added:
            await download_msg.edit("Metadata addition failed. Uploading the renamed file only.")
            path = renamed_file_path

        upload_msg = await download_msg.edit("**__Uploading...__**")
        ph_path = await download_thumbnail(client, message, media_type)

        try:
            if media_type == "document":
                await client.send_document(message.chat.id, document=path, thumb=ph_path, caption=await get_caption(message), progress=progress_for_pyrogram, progress_args=("Upload Started...", upload_msg, time.time()))
                await client.send_document(Config.DUMP_CHANNEL, document=path, thumb=ph_path, caption=await get_caption(message), progress=progress_for_pyrogram, progress_args=("Upload Started...", upload_msg, time.time()))
            elif media_type == "video":
                await client.send_video(message.chat.id, video=path, caption=await get_caption(message), thumb=ph_path, duration=0, progress=progress_for_pyrogram, progress_args=("Upload Started...", upload_msg, time.time()))
                await client.send_video(Config.DUMP_CHANNEL, video=path, caption=await get_caption(message), thumb=ph_path, duration=0, progress=progress_for_pyrogram, progress_args=("Upload Started...", upload_msg, time.time()))
            elif media_type == "audio":
                await client.send_audio(message.chat.id, audio=path, caption=await get_caption(message), thumb=ph_path, duration=0, progress=progress_for_pyrogram, progress_args=("Upload Started...", upload_msg, time.time()))
                await client.send_audio(Config.DUMP_CHANNEL, audio=path, caption=await get_caption(message), thumb=ph_path, duration=0, progress=progress_for_pyrogram, progress_args=("Upload Started...", upload_msg, time.time()))
        except Exception as e:
            os.remove(renamed_file_path)
            if ph_path:
                os.remove(ph_path)
            return await upload_msg.edit(f"Error: {e}")

        await download_msg.delete()
        os.remove(path)
        if ph_path:
            os.remove(ph_path)

    finally:
        if os.path.exists(renamed_file_path):
            os.remove(renamed_file_path)
        temp_output_file = renamed_file_path.replace(file_extension, f"_temp{file_extension}")
        if os.path.exists(temp_output_file):
            os.remove(temp_output_file)
        if ph_path and os.path.exists(ph_path):
            os.remove(ph_path)
        del renaming_operations[file_id]

async def download_thumbnail(client, message, media_type):
    if media_type == "document":
        return None
    elif media_type == "video":
        file_id = message.video.file_id
    elif media_type == "audio":
        file_id = message.audio.file_id
    else:
        return None

    thumb_msg = await client.get_messages(message.chat.id, limit=1, filter=filters.photo)
    thumb_path = f"downloads/{file_id}.jpg"

    try:
        await thumb_msg.download(file_name=thumb_path)
        return thumb_path
    except Exception as e:
        return None

async def get_caption(message: Message):
    title = f"{message.document.file_name if message.document else (message.video.file_name if message.video else message.audio.file_name)}"
    title += f"\nUploaded by: {message.from_user.first_name}"
    return title
