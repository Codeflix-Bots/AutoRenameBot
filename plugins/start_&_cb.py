import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, CallbackQuery, Message, InputMediaPhoto

from helper.database import codeflixbots
from config import *

@Client.on_message(filters.private & filters.command("start"))
async def start(client, message):
    user = message.from_user
    await codeflixbots.add_user(client, message)                
    button = InlineKeyboardMarkup([[
      InlineKeyboardButton("• ᴍʏ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs •", callback_data='help')
    ],[
      InlineKeyboardButton('• ᴜᴘᴅᴀᴛᴇs', url='https://t.me/Codeflix_Bots'),
      InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ •', url='https://t.me/CodeflixSupport')
    ],[
      InlineKeyboardButton('• ᴀʙᴏᴜᴛ', callback_data='about'),
      InlineKeyboardButton('ᴘʀᴇᴍɪᴜᴍ •', callback_data='premium')
    ]])
    if Config.START_PIC:
        await message.reply_photo(Config.START_PIC, caption=Txt.START_TXT.format(user.mention), reply_markup=button)       
    else:
        await message.reply_text(text=Txt.START_TXT.format(user.mention), reply_markup=button, disable_web_page_preview=True)   

@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data 
    user_id = query.from_user.id  
    
    if data == "home":
        await query.message.edit_text(
            text=Txt.START_TXT.format(query.from_user.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("• ᴍʏ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs •", callback_data='help')
                ],[
                InlineKeyboardButton('• ᴜᴘᴅᴀᴛᴇs', url='https://t.me/Codeflix_Bots'),
                InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ •', url='https://t.me/CodeflixSupport')
                ],[
                InlineKeyboardButton('• ᴀʙᴏᴜᴛ', callback_data='about'),
                InlineKeyboardButton('ᴘʀᴇᴍɪᴜᴍ •', callback_data='premium')
                ]])
        )
    elif data == "caption":
        await query.message.edit_text(
            text=Txt.CAPTION_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")
            ]])            
        )

@Client.on_message(filters.command("donate"))
async def donation(client, message):
    btn = [[
        InlineKeyboardButton(text="ʙᴀᴄᴋ", callback_data="help"),
        InlineKeyboardButton(text="ᴏᴡɴᴇʀ", url=f'https://t.me/sewxiy'),
    ]]
    yt=await message.reply_photo(photo='https://graph.org/file/1919fe077848bd0783d4c.jpg', caption=script.DONATE_TXT, reply_markup=InlineKeyboardMarkup(btn))
    await asyncio.sleep(300)
    await yt.delete()
    await message.delete()

@Client.on_message(filters.command("premium"))
async def premium(bot, message):
    btn = [[
         InlineKeyboardButton("ᴏᴡɴᴇʀ", url="https://t.me/sewxuy"),
         InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")
    ]]
    yt=await message.reply_photo(photo='https://graph.org/file/8b50e21db819f296661b7.jpg', caption=script.PREMIUM_TXT, reply_markup=InlineKeyboardMarkup(btn))
    await asyncio.sleep(300)
    await yt.delete()
    await message.delete()

@Client.on_message(filters.command("plan"))
async def premium(bot, message):
    btn = [[
         InlineKeyboardButton("sᴇɴᴅ ᴘᴀʏᴍᴇɴᴛ sᴄʀᴇᴀɴsʜᴏᴛ ʜᴇʀᴇ", url="https://t.me/sewxuy"),
         InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")
    ]]
    yt=await message.reply_photo(photo='https://graph.org/file/8b50e21db819f296661b7.jpg', caption=script.PREPLANS_TXT, reply_markup=InlineKeyboardMarkup(btn))
    await asyncio.sleep(300)
    await yt.delete()
    await message.delete()

@Client.on_message(filters.command("bought") & filters.private)
async def bought(client, message):
    msg = await message.reply('Wait im checking...')
    replyed = message.reply_to_message
    if not replyed:
        await msg.edit("<b>Please reply with the screenshot of your payment for the premium purchase to proceed.\n\nFor example, first upload your screenshot, then reply to it using the '/bought' command</b>")
    if replyed and replyed.photo:
        await client.send_photo(
            photo=replyed.photo.file_id,
            chat_id=LOG_CHANNEL,
            caption=f'<b>User - {message.from_user.mention}\nUser id - <code>{message.from_user.id}</code>\nusername - <code>{message.from_user.username}</code>\nUser Name - <code>{message.from_user.first_name}</code></b>',
            reply_markup=InlineKeyboardMarkup(
                [
                    
                    [
                        InlineKeyboardButton(
                            "Close", callback_data="close_data"
                        )
                    ]
                    
                ]
            )
        )
        await msg.edit_text('<b>Your screenshot has been sent to Admins</b>')

    elif data == "help":
        await query.message.edit_text(
            text=Txt.HELP_TXT.format(client.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("• ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ •", callback_data='file_names')
                ],[
                InlineKeyboardButton('• ᴛʜᴜᴍʙɴᴀɪʟ', callback_data='thumbnail'),
                InlineKeyboardButton('ᴄᴀᴘᴛɪᴏɴ •', callback_data='caption')
                ],[
                InlineKeyboardButton('• ʜᴏᴍᴇ', callback_data='home'),
                InlineKeyboardButton('ᴅᴏɴᴀᴛᴇ •', callback_data='donate')
                ]])
        )
    elif data == "donate":
        await query.message.edit_text(
            text=Txt.DONATE_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                InlineKeyboardButton("ᴏᴡɴᴇʀ •", url='https://t.me/sewxiy')
            ]])          
        )
    
    elif data == "file_names":
        format_template = await madflixbotz.get_format_template(user_id)
        await query.message.edit_text(
            text=Txt.FILE_NAME_TXT.format(format_template=format_template),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")
            ]])
        )      
    
    elif data == "thumbnail":
        await query.message.edit_caption(
            caption=Txt.THUMBNAIL_TXT,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help"),
            ]]),
        )

    elif data == "premium":
        await query.message.edit_caption(
            caption=Txt.PREMIUM_TXT,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                InlineKeyboardButton("ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", url='https://t.me/sewxiy'),
            ]]),
        )

    elif data == "plans":
        await query.message.edit_caption(
            caption=Txt.PREPLANS_TXT,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"),
                InlineKeyboardButton("ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", url='https://t.me/sewxiy'),
            ]]),
        )

    elif data == "about":
        await query.message.edit_text(
            text=Txt.ABOUT_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("• sᴜᴘᴘᴏʀᴛ", url='https://t.me/CodeflixSupport'),
                InlineKeyboardButton("ᴄᴏᴍᴍᴀɴᴅs •", callback_data="help")
            ],[
                InlineKeyboardButton("• ᴅᴇᴠᴇʟᴏᴘᴇʀ", url='https://t.me/cosmic_freak'),
                InlineKeyboardButton("ɴᴇᴛᴡᴏʀᴋ •", url='https://t.me/otakuflix_network')
            ],[
                InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="home")
            ]])          
        )
    
    
    elif data == "close":
        try:
            await query.message.delete()
            await query.message.reply_to_message.delete()
            await query.message.continue_propagation()
        except:
            await query.message.delete()
            await query.message.continue_propagation()
