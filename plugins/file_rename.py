import os
import re
import time
import shutil
import asyncio
import logging
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global dictionary to track ongoing operations
renaming_operations = {}
user_queues = {}
queue_locks = {}

# Enhanced regex patterns for season and episode extraction
SEASON_EPISODE_PATTERNS = [
    # Standard patterns (S01E02, S01EP02)
    (re.compile(r'S(\d+)(?:E|EP)(\d+)'), ('season', 'episode')),
    # Patterns with spaces/dashes (S01 E02, S01-EP02)
    (re.compile(r'S(\d+)[\s-]*(?:E|EP)(\d+)'), ('season', 'episode')),
    # Full text patterns (Season 1 Episode 2)
    (re.compile(r'Season\s*(\d+)\s*Episode\s*(\d+)', re.IGNORECASE), ('season', 'episode')),
    # Patterns with brackets/parentheses ([S01][E02])
    (re.compile(r'\[S(\d+)\]\[E(\d+)\]'), ('season', 'episode')),
    # Fallback patterns (S01 13, Episode 13)
    (re.compile(r'S(\d+)[^\d]*(\d+)'), ('season', 'episode')),
    (re.compile(r'(?:E|EP|Episode)\s*(\d+)', re.IGNORECASE), (None, 'episode')),
    # Final fallback (standalone number)
    (re.compile(r'\b(\d+)\b'), (None, 'episode'))
]

# Quality detection patterns
QUALITY_PATTERNS = [
    (re.compile(r'(?<!\d)(\d{3,4}[pi])(?!\d)', re.IGNORECASE), lambda m: m.group(1).lower()),  # 1080p, 720p
    (re.compile(r'(?i)(4k|2160p)', re.IGNORECASE), lambda m: "4k"),
    (re.compile(r'(?i)(2k|1440p)', re.IGNORECASE), lambda m: "2k"),
    (re.compile(r'\[(\d{3,4}[pi])\]', re.IGNORECASE), lambda m: m.group(1).lower()),  # [1080p]
    (re.compile(r'(?<!\d)(1080|720|480|360)(?:p|i)?(?!\d)', re.IGNORECASE), lambda m: f"{m.group(1)}p"), # Catch missing 'p' like 1080
    (re.compile(r'(?i)(HDRip|HDTV|BDRip|BRRip|WEB-DL|WEBRip|CAM|TS|DVDrip)', re.IGNORECASE), lambda m: m.group(1)),
    (re.compile(r'(?i)(4kX264|4kx265)', re.IGNORECASE), lambda m: m.group(1))
]

def extract_season_episode(filename):
    """Extract season and episode numbers from filename"""
    for pattern, (season_group, episode_group) in SEASON_EPISODE_PATTERNS:
        match = pattern.search(filename)
        if match:
            season = match.group(1) if season_group else None
            episode = match.group(2) if season_group and episode_group else match.group(1)
            logger.info(f"Extracted season: {season}, episode: {episode} from {filename}")
            return season, episode
    logger.warning(f"No season/episode pattern matched for {filename}")
    return None, None

def extract_quality(filename):
    """Extract quality information from filename"""
    for pattern, extractor in QUALITY_PATTERNS:
        match = pattern.search(filename)
        if match:
            quality = extractor(match)
            logger.info(f"Extracted quality: {quality} from {filename}")
            return quality
    logger.warning(f"No quality pattern matched for {filename}")
    return "Unknown"

# Language detection patterns
LANGUAGE_PATTERNS = [
    re.compile(r'(?i)(?<![a-z])(hi|hin|hindi)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(en|eng|english)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(te|tel|telugu)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(ta|tam|tamil)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(ml|mal|malayalam)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(kn|kan|kannada)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(mr|mar|marathi)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(gu|guj|gujarati)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(bn|ben|bengali)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(pa|pan|punjabi)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(or|ori|odia)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(ur|urd|urdu)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(as|ass|assamese)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(bho|bhojpuri)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(ja|jap|japanese)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(ko|kor|korean)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(es|spa|spanish)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(?<![a-z])(fr|fre|french)(?![a-z])', re.IGNORECASE),
    re.compile(r'(?i)(multi|dual[\s_.-]?audio)', re.IGNORECASE)
]

def extract_languages(filename):
    """Extract languages from filename"""
    languages = []
    for pattern in LANGUAGE_PATTERNS:
        match = pattern.search(filename)
        if match:
            lang = match.group(1).capitalize()
            if lang.lower() in ['hi', 'hin']: lang = 'Hindi'
            elif lang.lower() in ['en', 'eng']: lang = 'English'
            elif lang.lower() in ['te', 'tel']: lang = 'Telugu'
            elif lang.lower() in ['ta', 'tam']: lang = 'Tamil'
            elif lang.lower() in ['ml', 'mal']: lang = 'Malayalam'
            elif lang.lower() in ['kn', 'kan']: lang = 'Kannada'
            elif lang.lower() in ['mr', 'mar']: lang = 'Marathi'
            elif lang.lower() in ['gu', 'guj']: lang = 'Gujarati'
            elif lang.lower() in ['bn', 'ben']: lang = 'Bengali'
            elif lang.lower() in ['pa', 'pan']: lang = 'Punjabi'
            elif lang.lower() in ['or', 'ori']: lang = 'Odia'
            elif lang.lower() in ['ur', 'urd']: lang = 'Urdu'
            elif lang.lower() in ['as', 'ass']: lang = 'Assamese'
            elif lang.lower() in ['bho']: lang = 'Bhojpuri'
            elif lang.lower() in ['ja', 'jap']: lang = 'Japanese'
            elif lang.lower() in ['ko', 'kor']: lang = 'Korean'
            elif lang.lower() in ['dual audio', 'dual-audio']: lang = 'Dual Audio'

            if lang not in languages:
                languages.append(lang)

    if languages:
        logger.info(f"Extracted languages: {', '.join(languages)} from {filename}")
        return ", ".join(languages)
    return "Unknown"

async def cleanup_files(*paths):
    """Safely remove files if they exist"""
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Error removing {path}: {e}")

async def process_thumbnail(thumb_path):
    """Process and resize thumbnail image"""
    if not thumb_path or not os.path.exists(thumb_path):
        return None
    
    try:
        with Image.open(thumb_path) as img:
            img = img.convert("RGB").resize((320, 320))
            img.save(thumb_path, "JPEG")
        return thumb_path
    except Exception as e:
        logger.error(f"Thumbnail processing failed: {e}")
        await cleanup_files(thumb_path)
        return None

async def add_metadata(input_path, output_path, user_id):
    """Add metadata to media file using ffmpeg"""
    ffmpeg = shutil.which('ffmpeg')
    ffprobe = shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:
        raise RuntimeError("FFmpeg/FFprobe not found in PATH")
    
    metadata = {
        'title': await codeflixbots.get_title(user_id),
        'artist': await codeflixbots.get_artist(user_id),
        'author': await codeflixbots.get_author(user_id),
        'video_title': await codeflixbots.get_video(user_id),
        'audio_title': await codeflixbots.get_audio(user_id),
        'subtitle': await codeflixbots.get_subtitle(user_id)
    }
    
    extract_lang = await codeflixbots.get_extract_language(user_id)

    # Dictionary of lang codes to search for
    lang_codes_map = {
        "tel": ["tel", "te"],
        "hin": ["hin", "hi"],
        "eng": ["eng", "en"],
        "tam": ["tam", "ta"],
        "mal": ["mal", "ml"],
        "kan": ["kan", "kn"],
        "mar": ["mar", "mr"],
        "ben": ["ben", "bn"]
    }

    lang_maps = []

    if extract_lang and extract_lang != "off":
        # Probe file to see if the requested audio language exists
        probe_cmd = [
            ffprobe, '-v', 'error', '-select_streams', 'a',
            '-show_entries', 'stream=index:stream_tags=language',
            '-of', 'csv=p=0', input_path
        ]

        probe_process = await asyncio.create_subprocess_exec(
            *probe_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await probe_process.communicate()

        output = stdout.decode().strip()
        target_codes = lang_codes_map.get(extract_lang, [extract_lang])

        # Output format is something like "1,tel\n2,hin"
        for line in output.split('\n'):
            if not line: continue
            parts = line.split(',')
            if len(parts) >= 2:
                stream_index, stream_lang = parts[0], parts[1].lower()
                if stream_lang in target_codes:
                    lang_maps.extend(['-map', f'0:{stream_index}'])

    # If user wants extraction but stream is NOT found, fallback to copying all streams
    # to avoid FFmpeg crashing with "Stream map matches no streams" or creating a silent file.
    if extract_lang and extract_lang != "off" and lang_maps:
        cmd = [
            ffmpeg,
            '-i', input_path,
            '-map', '0:v?'
        ] + lang_maps + [
            '-map', '0:s?',
            '-c', 'copy',
            '-metadata', f'title={metadata["title"]}',
            '-metadata', f'artist={metadata["artist"]}',
            '-metadata', f'author={metadata["author"]}',
            '-metadata:s:v', f'title={metadata["video_title"]}',
            '-metadata:s:a', f'title={metadata["audio_title"]}',
            '-metadata:s:s', f'title={metadata["subtitle"]}',
            '-loglevel', 'error',
            output_path
        ]
    else:
        # Default behavior: copy everything
        cmd = [
            ffmpeg,
            '-i', input_path,
            '-map', '0',
            '-c', 'copy',
            '-metadata', f'title={metadata["title"]}',
            '-metadata', f'artist={metadata["artist"]}',
            '-metadata', f'author={metadata["author"]}',
            '-metadata:s:v', f'title={metadata["video_title"]}',
            '-metadata:s:a', f'title={metadata["audio_title"]}',
            '-metadata:s:s', f'title={metadata["subtitle"]}',
            '-loglevel', 'error',
            output_path
        ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {stderr.decode()}")

async def process_queue(client, user_id):
    """Process files in the user's queue in sorted order based on episode"""
    if user_id not in queue_locks:
        queue_locks[user_id] = asyncio.Lock()

    async with queue_locks[user_id]:
        if not user_queues.get(user_id):
            return

        # Wait a moment to allow a batch of forwarded files to all arrive
        await asyncio.sleep(2)

        while user_queues.get(user_id):
            # Sort queue by episode number if possible
            def sort_key(item):
                msg = item['message']
                fname = ""
                if msg.document: fname = msg.document.file_name or ""
                elif msg.video: fname = msg.video.file_name or ""
                elif msg.audio: fname = msg.audio.file_name or ""

                season, episode = extract_season_episode(fname)
                if episode and episode.isdigit():
                    return int(episode)
                return 999999 # Put files without episode at the end

            user_queues[user_id].sort(key=sort_key)

            # Pop the first item
            current_task = user_queues[user_id].pop(0)
            try:
                await execute_rename(client, current_task['message'])
            except Exception as e:
                logger.error(f"Error processing file in queue: {e}")
                await current_task['message'].reply_text(f"Error processing this file: {e}")


@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    """Main handler for auto-renaming files - Adds to queue"""
    user_id = message.from_user.id

    if user_id not in user_queues:
        user_queues[user_id] = []

    user_queues[user_id].append({'message': message})

    # Notify user that file is added to queue
    await message.reply_text("⏳ File added to queue. Processing in order...", quote=True)

    # Start queue processing if not already running (handled by lock)
    if not (queue_locks.get(user_id) and queue_locks[user_id].locked()):
        asyncio.create_task(process_queue(client, user_id))


async def execute_rename(client, message):
    """Execute the actual renaming process"""
    user_id = message.from_user.id

    # Check token expiry first
    from config import Config
    import time
    expiry = await codeflixbots.get_token_expiry(user_id)
    if expiry < time.time() and user_id not in Config.ADMIN:
        await message.reply_text("⏳ **Your token has expired!**\n\nPlease generate a new token using /token to continue renaming files.")
        return

    format_template = await codeflixbots.get_format_template(user_id)
    
    if not format_template:
        return await message.reply_text("Please set a rename format using /autorename")

    # Check limits based on plan
    plan_details = await codeflixbots.get_plan_details(user_id)
    if not plan_details:
        return await message.reply_text("Failed to fetch plan details.")

    user_plan = plan_details.get("plan", "Free").lower()
    used_renames = plan_details.get("used_renames", 0)
    used_extracts = plan_details.get("used_extracts", 0)
    extra_extracts = plan_details.get("extra_extracts", 0)
    extract_lang = await codeflixbots.get_extract_language(user_id)
    is_extracting = extract_lang and extract_lang != "off"

    # Define limits
    limits = {
        "free": {"rename": 20, "extract": 0},
        "bronze": {"rename": 40, "extract": 20},
        "silver": {"rename": 60, "extract": 30},
        "gold": {"rename": 100, "extract": 50},
        "platinum": {"rename": float('inf'), "extract": 100},
        "diamond": {"rename": float('inf'), "extract": float('inf')}
    }

    user_limits = limits.get(user_plan, limits["free"])

    if user_id not in Config.ADMIN:
        if used_renames >= user_limits["rename"]:
            return await message.reply_text(f"⚠️ **Rename Limit Reached!**\nYou have exhausted your {user_plan} plan's daily rename limit ({user_limits['rename']} files).\nWait 24 hours or upgrade your plan.")

        if is_extracting:
            total_allowed_extracts = user_limits["extract"] + extra_extracts
            if used_extracts >= total_allowed_extracts:
                if user_plan == "free" and extra_extracts == 0:
                    return await message.reply_text(f"⚠️ **Extraction Limit Reached!**\nFree users don't have audio extraction limits. You can claim 5 free extracts using `/extend`.")
                return await message.reply_text(f"⚠️ **Extraction Limit Reached!**\nYou have exhausted your {user_plan} plan's daily extract limit.\nWait 24 hours or upgrade your plan.")

    # Get file information
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_size = message.document.file_size
    elif message.video:
        file_id = message.video.file_id
        file_name = message.video.file_name or "video"
        file_size = message.video.file_size
    elif message.audio:
        file_id = message.audio.file_id
        file_name = message.audio.file_name or "audio"
        file_size = message.audio.file_size
    else:
        return await message.reply_text("Unsupported file type")

    # Get media preference
    media_preference = await codeflixbots.get_media_preference(user_id)
    if media_preference:
        media_type = media_preference
    else:
        if message.document:
            media_type = "document"
        elif message.video:
            media_type = "video"
        elif message.audio:
            media_type = "audio"

    # NSFW check
    if await check_anti_nsfw(file_name, message):
        return await message.reply_text("NSFW content detected")

    # Prevent duplicate processing
    if file_id in renaming_operations:
        if (datetime.now() - renaming_operations[file_id]).seconds < 10:
            return
    renaming_operations[file_id] = datetime.now()

    download_path = None
    metadata_path = None
    thumb_path = None

    try:
        # Extract metadata from filename
        season, episode = extract_season_episode(file_name)
        quality = extract_quality(file_name)
        languages = extract_languages(file_name)
        
        # Replace placeholders in template
        replacements = {
            '{season}': season or 'XX',
            '{episode}': episode or 'XX',
            '{quality}': quality,
            '{languages}': languages,
            'Season': season or 'XX',
            'Episode': episode or 'XX',
            'QUALITY': quality,
            'LANGUAGES': languages
        }
        
        for placeholder, value in replacements.items():
            format_template = format_template.replace(placeholder, value)

        # Get and apply prefix and suffix
        prefix = await codeflixbots.get_prefix(user_id)
        suffix = await codeflixbots.get_suffix(user_id)

        # Prepare file paths
        ext = os.path.splitext(file_name)[1] or ('.mp4' if media_type == 'video' else '.mp3')
        new_filename = f"{prefix}{format_template}{suffix}{ext}"
        download_path = f"downloads/{new_filename}"
        metadata_path = f"metadata/{new_filename}"
        
        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)

        # Download file
        msg = await message.reply_text("**Downloading...**")
        try:
            file_path = await client.download_media(
                message,
                file_name=download_path,
                progress=progress_for_pyrogram,
                progress_args=("Downloading...", msg, time.time())
            )
        except Exception as e:
            await msg.edit(f"Download failed: {e}")
            raise

        # Process metadata
        await msg.edit("**Processing metadata...**")
        try:
            await add_metadata(file_path, metadata_path, user_id)
            file_path = metadata_path
        except Exception as e:
            await msg.edit(f"Metadata processing failed: {e}")
            raise

        # Prepare for upload
        await msg.edit("**Preparing upload...**")

        # Format the custom default caption
        default_caption = (
            f"<b>{new_filename}</b>\n\n"
            f"<b>🎥 Quality: {quality}</b>\n"
            f"<b>🔊 Audio: {languages}</b>\n\n"
            f"<b>🎦Main ¢нαииєℓs:-</b>\n"
            f"<b>⭕️ Main:</b>\n"
            f"<b> https://t.me/+uMOWx3CdNzYwN2E1</b>\n"
            f"<b>⭕️ Network:</b>\n"
            f"<b>https://t.me/CartoonAndAnime1Telugu</b>"
        )

        caption = await codeflixbots.get_caption(message.chat.id)
        if caption:
            # Re-apply replacements to the custom caption
            for placeholder, value in replacements.items():
                caption = caption.replace(placeholder, value)
            caption = caption.replace('{filename}', new_filename).replace('{filename}', new_filename) # Double replace just in case
        else:
            caption = default_caption

        thumb = await codeflixbots.get_thumbnail(message.chat.id)
        thumb_path = None

        # Handle thumbnail
        if thumb:
            thumb_path = await client.download_media(thumb)
        elif message.video and message.video.thumbs:
            thumb_path = await client.download_media(message.video.thumbs[0].file_id)
        
        thumb_path = await process_thumbnail(thumb_path)

        # Upload file
        await msg.edit("**Uploading...**")
        try:
            upload_params = {
                'chat_id': message.chat.id,
                'caption': caption,
                'thumb': thumb_path,
                'progress': progress_for_pyrogram,
                'progress_args': ("Uploading...", msg, time.time())
            }

            if media_type == "document":
                final_msg = await client.send_document(document=file_path, **upload_params)
            elif media_type == "video":
                final_msg = await client.send_video(video=file_path, **upload_params)
            elif media_type == "audio":
                final_msg = await client.send_audio(audio=file_path, **upload_params)

            await msg.delete()

            # Send log to LOG_CHANNEL
            try:
                log_caption = f"**User:** {message.from_user.mention}\n**ID:** `{message.from_user.id}`\n**File:** `{new_filename}`"
                await final_msg.copy(chat_id=Config.LOG_CHANNEL, caption=log_caption)
            except Exception as e:
                logger.error(f"Error sending log to channel: {e}")

            # Update usage stats
            await codeflixbots.update_usage(user_id, "used_renames", 1)
            if is_extracting:
                await codeflixbots.update_usage(user_id, "used_extracts", 1)

        except Exception as e:
            await msg.edit(f"Upload failed: {e}")
            raise

    except Exception as e:
        logger.error(f"Processing error: {e}")
        await message.reply_text(f"Error: {str(e)}")
    finally:
        # Clean up files
        await cleanup_files(download_path, metadata_path, thumb_path)
        renaming_operations.pop(file_id, None)
