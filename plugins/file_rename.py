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
        re.compile(r'S(\d+)(?:E|EP)(\d+)'),  # S01E02 or S01EP02
        re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)'),  # S01 E02 or S01 EP02 or S01 - E01
        re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)'),  # E or EP pattern
        re.compile(r'(?:\s*-\s*(\d+)\s*)'),  # -E01 or -EP02
        re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE),  # S2 09 ex.
        re.compile(r'(\d+)')  # Standalone episode number
    ],
    "quality": [
        re.compile(r'\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b', re.IGNORECASE),  # e.g., 1080p
        re.compile(r'[([<{]?\s*4k\s*[)\]>}]?', re.IGNORECASE),  # 4k
        re.compile(r'[([<{]?\s*2k\s*[)\]>}]?', re.IGNORECASE),  # 2k
        re.compile(r'[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b', re.IGNORECASE),  # HdRip
        re.compile(r'[([<{]?\s*4kX264\s*[)\]>}]?', re.IGNORECASE),  # 4kX264
        re.compile(r'[([<{]?\s*4kx265\s*[)\]>}]?', re.IGNORECASE)  # 4kx265
    ]
}

def extract_quality(filename):
    for pattern in patterns["quality"]:
        match = re.search(pattern, filename)
        if match:
            quality = match.group(1) or match.group(2)
            return quality or "Unknown"
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

    # Initialize filename variable
    filename = None

    # Determine file type and set filename
    if message.document:
        filename = message.document.file_name
        file_info = {
            'id': message.document.file_id,
            'name': filename,
            'type': media_preference or "document"
        }
    elif message.video:
        filename = f"{message.video.file_name}.mp4"
        file_info = {
            'id': message.video.file_id,
            'name': filename,
            'type': media_preference or "video"
        }
    elif message.audio:
        filename = f"{message.audio.file_name}.mp3"
        file_info = {
            'id': message.audio.file_id,
            'name': filename,
            'type': media_preference or "audio"
        }
    else:
        return await message.reply_text("Unsupported File Type")

    if filename is None:
        return await message.reply_text("Filename is not available.")

    if await check_anti_nsfw(filename, message):
        return

    if file_info['id'] in renaming_operations:
        elapsed_time = (datetime.now() - renaming_operations[file_info['id']]).seconds
        if elapsed_time < 10:
            return

    renaming_operations[file_info['id']] = datetime.now()

    episode_number = extract_episode_number(filename)
    if episode_number:
        placeholders = ["episode", "Episode", "EPISODE", "{episode}"]
        for placeholder in placeholders:
            format_template = format_template.replace(placeholder, str(episode_number), 1)

        quality_placeholders = ["quality", "Quality", "QUALITY", "{quality}"]
        for quality_placeholder in quality_placeholders:
            if quality_placeholder in format_template:
                extracted_quality = extract_quality(filename)
                if extracted_quality == "Unknown":
                    await message.reply_text("**__I Was Not Able To Extract The Quality Properly. Renaming As 'Unknown'...__**")
                    del renaming_operations[file_info['id']]
                    return

                format_template = format_template.replace(quality_placeholder, extracted_quality)

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
        del renaming_operations[file_info['id']]
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
                    metadata_added = False
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
        elif file_info['type'] == "video" and message.video.thumbs:
            ph_path = await client.download_media(message.video.thumbs[0].file_id)

        if ph_path:
            img = Image.open(ph_path).convert("RGB")
            img = img.resize((320, 320))
            img.save(ph_path, "JPEG")

        try:
            if file_info['type'] == "document":
                await client.send_document(
                    message.chat.id,
                    document=path,
                    thumb=ph_path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
                await client.send_document(
                    Config.DUMP_CHANNEL,
                    document=path,
                    thumb=ph_path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
            elif file_info['type'] == "video":
                await client.send_video(
                    message.chat.id,
                    video=path,
                    thumb=ph_path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
                await client.send_video(
                    Config.DUMP_CHANNEL,
                    video=path,
                    thumb=ph_path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
            elif file_info['type'] == "audio":
                await client.send_audio(
                    message.chat.id,
                    audio=path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
                await client.send_audio(
                    Config.DUMP_CHANNEL,
                    audio=path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
        except FloodWait as e:
            await asyncio.sleep(e.x)
            await download_msg.edit(f"**FloodWait Error:** {e}")
        except Exception as e:
            await download_msg.edit(f"**Upload Error:** {e}")

        if os.path.exists(path):
            os.remove(path)
        if os.path.exists(ph_path):
            os.remove(ph_path)

    except Exception as e:
        await download_msg.edit(f"**Error:** {e}")
        if os.path.exists(renamed_file_path):
            os.remove(renamed_file_path)

    del renaming_operations[file_info['id']]
