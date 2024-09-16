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
import shutil  # Added for shutil.which()

renaming_operations = {}

# ... [Your regex patterns and other code above remain unchanged] ...

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
        # Rename the file first
        os.rename(path, renamed_file_path)
        path = renamed_file_path

        # Add metadata if needed
        user_metadata_enabled = await codeflixbots.get_metadata(user_id)
        if user_metadata_enabled == "On":

            # Generate a temporary file path
            temp_output_file = renamed_file_path.replace(file_extension, f"_temp{file_extension}")

            ffmpeg_cmd = shutil.which('ffmpeg')

            title = await codeflixbots.get_title(user_id)
            author = await codeflixbots.get_author(user_id)
            artist = await codeflixbots.get_artist(user_id)
            video = await codeflixbots.get_video(user_id)
            audio = await codeflixbots.get_audio(user_id)
            subtitle = await codeflixbots.get_subtitle(user_id)

            # Add metadata using subprocess and ffmpeg command
            metadata_command = [
                ffmpeg_cmd if ffmpeg_cmd else 'ffmpeg',
                '-i', path,
                '-metadata', f'title={title}',
                '-metadata', f'artist={artist}',
                '-metadata', f'author={author}',
                # '-metadata', 'comment=Join @Anime_Edge for more content',
                '-metadata', 'additional_key=additional_value',
                '-metadata:s:v', f'title={video}',
                '-metadata:s:a', f'title={audio}',
                '-metadata:s:s', f'title={subtitle}',
                '-map', '0',
                '-c', 'copy',
                '-loglevel', 'error',
                temp_output_file
            ]

            # Now execute the ffmpeg command
            try:
                process = await asyncio.create_subprocess_exec(
                    *metadata_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()
                if process.returncode == 0:
                    metadata_added = True
                    path = temp_output_file
                else:
                    error_message = stderr.decode()
                    await download_msg.edit(f"**Metadata Error:**\n{error_message}")
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
                    duration=0,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started...", upload_msg, time.time()),
                )
        except Exception as e:
            os.remove(renamed_file_path)
            if ph_path:
                os.remove(ph_path)
            # Mark the file as ignored
            return await upload_msg.edit(f"Error: {e}")

        await download_msg.delete() 
        os.remove(path)
        if ph_path:
            os.remove(ph_path)

    finally:
        # Clean up
        if os.path.exists(renamed_file_path):
            os.remove(renamed_file_path)
        temp_output_file = renamed_file_path.replace(file_extension, f"_temp{file_extension}")
        if os.path.exists(temp_output_file):
            os.remove(temp_output_file)
        if ph_path and os.path.exists(ph_path):
            os.remove(ph_path)
        del renaming_operations[file_id]
