from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InputMediaDocument, Message
from PIL import Image
from datetime import datetime, timedelta
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

# Configurable auto-delete timer in seconds (default: 10 minutes)
DEL_TIMER = 10

renaming_operations = {}
auto_delete_tasks = {}

# Pattern Definitions for Filename Parsing
pattern1 = re.compile(r'S(\d+)(?:E|EP)(\d+)')
pattern2 = re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)')
pattern3 = re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)')
pattern3_2 = re.compile(r'(?:\s*-\s*(\d+)\s*)')
pattern4 = re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE)
patternX = re.compile(r'(\d+)')
pattern5 = re.compile(r'\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b', re.IGNORECASE)
pattern6 = re.compile(r'[([<{]?\s*4k\s*[)\]>}]?', re.IGNORECASE)
pattern7 = re.compile(r'[([<{]?\s*2k\s*[)\]>}]?', re.IGNORECASE)
pattern8 = re.compile(r'[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b', re.IGNORECASE)
pattern9 = re.compile(r'[([<{]?\s*4kX264\s*[)\]>}]?', re.IGNORECASE)
pattern10 = re.compile(r'[([<{]?\s*4kx265\s*[)\]>}]?', re.IGNORECASE)

def extract_quality(filename):
    # Quality extraction logic
    for idx, pattern in enumerate([pattern5, pattern6, pattern7, pattern8, pattern9, pattern10], start=5):
        match = re.search(pattern, filename)
        if match:
            quality = match.group(1) or match.group(2)
            print(f"Matched Pattern {idx}, Quality: {quality}")
            return quality

    print("Quality: Unknown")
    return "Unknown"
    

def extract_episode_number(filename):
    # Episode number extraction logic
    for idx, pattern in enumerate([pattern1, pattern2, pattern3, pattern3_2, pattern4, patternX], start=1):
        match = re.search(pattern, filename)
        if match:
            print(f"Matched Pattern {idx}, Episode: {match.group(2) if idx == 1 or idx == 2 else match.group(1)}")
            return match.group(2) if idx == 1 or idx == 2 else match.group(1)

    return None


async def auto_delete_file(file_path):
    """Automatically delete the file after a specified delay."""
    await asyncio.sleep(DEL_TIMER)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
    except Exception as e:
        print(f"Error deleting file: {e}")


@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    media_preference = await codeflixbots.get_media_preference(user_id)

    if not format_template:
        return await message.reply_text(
            "Please Set An Auto Rename Format First Using /autorename"
        )

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

        # Add extracted qualities to the format template
        quality_placeholders = ["quality", "Quality", "QUALITY", "{quality}"]
        for quality_placeholder in quality_placeholders:
            if quality_placeholder in format_template:
                extracted_qualities = extract_quality(file_name)
                if extracted_qualities == "Unknown":
                    await message.reply_text("**__I Was Not Able To Extract The Quality Properly. Renaming As 'Unknown'...__**")
                    # Mark the file as ignored
                    del renaming_operations[file_id]
                    return  # Exit the handler if quality extraction fails
                
                format_template = format_template.replace(quality_placeholder, "".join(extracted_qualities))

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
            # Metadata addition failed; upload the renamed file only
            await download_msg.edit(
                "Metadata addition failed. Uploading the renamed file only."
            )
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
            img = img.resize((320, 320))
            img.save(ph_path, "JPEG")

        try:
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
                    thumb=ph_path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
            elif media_type == "audio":
                await client.send_audio(
                    message.chat.id,
                    audio=path,
                    thumb=ph_path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
        except FloodWait as e:
            await asyncio.sleep(e.x)

        # Schedule the file for auto-deletion
        auto_delete_tasks[path] = asyncio.create_task(auto_delete_file(path))
        await upload_msg.edit(f"**__Successfully Renamed to: {renamed_file_name}__**")
    except Exception as e:
        await download_msg.edit(f"**Error during upload or renaming:** {e}")
    finally:
        if ph_path:
            os.remove(ph_path)
        del renaming_operations[file_id]
