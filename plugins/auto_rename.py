from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper.database import codeflixbots

@Client.on_message(filters.private & filters.command("autorename"))
async def auto_rename_command(client, message):
    user_id = message.from_user.id

    # Extract and validate the format from the command
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2 or not command_parts[1].strip():
        await message.reply_text(
            "**Please provide a new name after the command /autorename**\n\n"
            "Here's how to use it:\n"
            "**Example format:** `/autorename Overflow [S{season}E{episode}] - [Dual] {quality}`"
        )
        return

    format_template = command_parts[1].strip()

    # Save the format template in the database
    await codeflixbots.set_format_template(user_id, format_template)

    # Send confirmation message with the template in monospaced font
    await message.reply_text(
        f"**🌟 Fantastic! You're ready to auto-rename your files.**\n\n"
        "📩 Simply send the file(s) you want to rename.\n\n"
        f"**Your saved template:** `{format_template}`\n\n"
        "Remember, it might take some time, but I'll ensure your files are renamed perfectly!✨"
    )


@Client.on_message(filters.private & filters.command("set_prefix"))
async def set_prefix_command(client, message):
    user_id = message.from_user.id
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        return await message.reply_text("Please provide a prefix. Example: `/set_prefix [MyPrefix]`")

    prefix = command_parts[1]
    if not prefix.endswith(" "):
        prefix += " "

    await codeflixbots.set_prefix(user_id, prefix)
    await message.reply_text(f"**Prefix saved:** `{prefix}`")


@Client.on_message(filters.private & filters.command("del_prefix"))
async def del_prefix_command(client, message):
    user_id = message.from_user.id
    await codeflixbots.set_prefix(user_id, "")
    await message.reply_text("**Prefix removed successfully!**")


@Client.on_message(filters.private & filters.command("set_suffix"))
async def set_suffix_command(client, message):
    user_id = message.from_user.id
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        return await message.reply_text("Please provide a suffix. Example: `/set_suffix @MyChannel`")

    suffix = command_parts[1]
    if not suffix.startswith(" "):
        suffix = " " + suffix

    await codeflixbots.set_suffix(user_id, suffix)
    await message.reply_text(f"**Suffix saved:** `{suffix}`")


@Client.on_message(filters.private & filters.command("del_suffix"))
async def del_suffix_command(client, message):
    user_id = message.from_user.id
    await codeflixbots.set_suffix(user_id, "")
    await message.reply_text("**Suffix removed successfully!**")


@Client.on_message(filters.private & filters.command("extract"))
async def extract_audio_command(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Telugu", callback_data="ext_tel"), InlineKeyboardButton("Hindi", callback_data="ext_hin")],
        [InlineKeyboardButton("English", callback_data="ext_eng"), InlineKeyboardButton("Tamil", callback_data="ext_tam")],
        [InlineKeyboardButton("Malayalam", callback_data="ext_mal"), InlineKeyboardButton("Kannada", callback_data="ext_kan")],
        [InlineKeyboardButton("Marathi", callback_data="ext_mar"), InlineKeyboardButton("Bengali", callback_data="ext_ben")],
        [InlineKeyboardButton("❌ Turn OFF Extraction ❌", callback_data="ext_off")]
    ])

    await message.reply_text(
        "🎧 **Select Audio Language to Extract** 🎧\n\n"
        "Choose the language track you want to keep. All other audio tracks will be stripped.",
        reply_markup=keyboard,
        quote=True
    )

@Client.on_callback_query(filters.regex(r"^ext_"))
async def handle_extract_selection(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    lang_code = callback_query.data.split("_", 1)[1]

    lang_map = {
        "tel": "Telugu",
        "hin": "Hindi",
        "eng": "English",
        "tam": "Tamil",
        "mal": "Malayalam",
        "kan": "Kannada",
        "mar": "Marathi",
        "ben": "Bengali",
        "off": "OFF"
    }

    selected_lang = lang_map.get(lang_code, "off")
    await codeflixbots.set_extract_language(user_id, lang_code)

    if lang_code == "off":
        await callback_query.answer("Extraction Disabled")
        await callback_query.message.edit_text("❌ **Audio Extraction Disabled** ❌\nAll original audio tracks will be kept.")
    else:
        await callback_query.answer(f"{selected_lang} Extraction Enabled")
        await callback_query.message.edit_text(f"✅ **Audio Extraction Enabled** ✅\nOnly **{selected_lang}** audio tracks will be kept.")


@Client.on_message(filters.private & filters.command("extend"))
async def extend_command(client, message):
    user_id = message.from_user.id
    plan_details = await codeflixbots.get_plan_details(user_id)

    if not plan_details:
        return await message.reply_text("Failed to fetch your plan details.")

    if plan_details.get("plan", "Free").lower() != "free":
        return await message.reply_text("🎉 **You are a Premium user!**\nYou don't need this extension.")

    if plan_details.get("extra_extracts", 0) > 0:
        return await message.reply_text("⏳ **You have already claimed your extension today!**\nTry again tomorrow.")

    await codeflixbots.update_usage(user_id, "extra_extracts", 5)
    await message.reply_text("🎁 **Bonus Claimed!**\nYou have been granted 5 extra audio extraction credits for today.")

@Client.on_message(filters.private & filters.command("multi"))
async def set_multi_command(client, message):
    user_id = message.from_user.id
    await codeflixbots.set_extract_language(user_id, "off")
    await message.reply_text("❌ **Audio Extraction Disabled** ❌\nAll original audio tracks will be kept.")

@Client.on_message(filters.private & filters.command("setmedia"))
async def set_media_command(client, message):
    """Initiate media type selection with a sleek inline keyboard."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Documents", callback_data="setmedia_document")],
        [InlineKeyboardButton("🎬 Videos", callback_data="setmedia_video")],
        [InlineKeyboardButton("🎵 Audio", callback_data="setmedia_audio")],  # Added audio option
    ])

    await message.reply_text(
        "✨ **Choose Your Media Vibe** ✨\n"
        "Select the type of media you'd like to set as your preference:",
        reply_markup=keyboard,
        quote=True
    )

@Client.on_callback_query(filters.regex(r"^setmedia_"))
async def handle_media_selection(client, callback_query: CallbackQuery):
    """Process the user's media type selection with flair and confirmation."""
    user_id = callback_query.from_user.id
    media_type = callback_query.data.split("_", 1)[1].capitalize()  # Extract and capitalize media type

    try:
        await codeflixbots.set_media_preference(user_id, media_type.lower())

        await callback_query.answer(f"Locked in: {media_type} 🎉")
        await callback_query.message.edit_text(
            f"🎯 **Media Preference Updated** 🎯\n"
            f"Your vibe is now set to: **{media_type}** ✅\n"
            f"Ready to roll with your choice!"
        )
    except Exception as e:
        await callback_query.answer("Oops, something went wrong! 😅")
        await callback_query.message.edit_text(
            f"⚠️ **Error Setting Preference** ⚠️\n"
            f"Couldn’t set {media_type} right now. Try again later!\n"
            f"Details: {str(e)}"
        )
