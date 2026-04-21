import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from config import LOGGER_ID as LOG_GROUP_ID
from AnonXMusic import app 
from pyrogram.errors import RPCError
from typing import Union, Optional
from PIL import Image, ImageDraw, ImageFont
import asyncio, os, aiohttp
from pathlib import Path
from pyrogram.enums import ParseMode

photo = [
    "https://i.ibb.co/ksMjt454/x.jpg",
    "https://i.ibb.co/MxcHhWNK/x.jpg",
    "https://i.ibb.co/MDyzfxwh/x.jpg",
    "https://i.ibb.co/n8jRZNX3/x.jpg",
    "https://i.ibb.co/whhVtChq/x.jpg",
    "https://i.ibb.co/zT184Cq0/x.jpg",
    "https://i.ibb.co/0pp5Bthd/x.jpg",
    "https://i.ibb.co/fJLzjgY/x.jpg",
    "https://i.ibb.co/8n5ZVp3c/x.jpg"
]

@app.on_message(filters.new_chat_members, group=2)
async def join_watcher(_, message):    
    chat = message.chat
    for member in message.new_chat_members:
        if member.id == app.id:
            try:
                link = await app.export_chat_invite_link(chat.id)
            except Exception:
                link = None

            count = await app.get_chat_members_count(chat.id)

            # Safe from_user (None for anonymous admin / channel posts)
            added_by = message.from_user.mention if message.from_user else "𝐀ɴᴏɴʏᴍᴏᴜs / 𝐔ɴᴋɴᴏᴡɴ"

            # Safe username (private groups have no username)
            username_str = f"@{chat.username}" if chat.username else "𝐏ʀɪᴠᴀᴛᴇ 𝐆ʀᴏᴜᴘ"

            msg = (
                f"📝 ᴍᴜsɪᴄ ʙᴏᴛ ᴀᴅᴅᴇᴅ ɪɴ ᴀ ɴᴇᴡ ɢʀᴏᴜᴘ\n"
                f"____\n"
                f"📌 ᴄʜᴀᴛ ɴᴀᴍᴇ: {chat.title}\n"
                f"🍂 ᴄʜᴀᴛ ɪᴅ: {chat.id}\n"
                f"🔐 ᴄʜᴀᴛ ᴜsᴇʀɴᴀᴍᴇ: {username_str}\n"
                f"🛰 ᴄʜᴀᴛ ʟɪɴᴋ: [ᴄʟɪᴄᴋ]({link if link else 'N/A'})\n"
                f"📈 ɢʀᴏᴜᴘ ᴍᴇᴍʙᴇʀs: {count}\n"
                f"🤔 ᴀᴅᴅᴇᴅ ʙʏ: {added_by}"
            )

            buttons = []
            if link:
                buttons.append([InlineKeyboardButton("sᴇᴇ ɢʀᴏᴜᴘ👀", url=link)])

            await app.send_photo(
                LOG_GROUP_ID,
                photo=random.choice(photo),
                has_spoiler=True,
                caption=msg,
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
            )

@app.on_message(filters.left_chat_member)
async def on_left_chat_member(_, message: Message):
    if (await app.get_me()).id == message.left_chat_member.id:
        remove_by = message.from_user.mention if message.from_user else "𝐔ɴᴋɴᴏᴡɴ 𝐔sᴇʀ"
        title = message.chat.title
        username = f"@{message.chat.username}" if message.chat.username else "𝐏ʀɪᴠᴀᴛᴇ 𝐂ʜᴀᴛ"
        chat_id = message.chat.id
        left = f"✫ <b><u>#𝐋ᴇғᴛ_𝐆ʀᴏᴜᴘ</u></b> ✫\n\n𝐂ʜᴀᴛ 𝐓ɪᴛʟᴇ : {title}\n\n𝐂ʜᴀᴛ 𝐈ᴅ : {chat_id}\n\n𝐑ᴇᴍᴏᴠᴇᴅ 𝐁ʏ : {remove_by}\n\n𝐁ᴏᴛ : @{app.username}"
        await app.send_photo(LOG_GROUP_ID, photo=random.choice(photo), has_spoiler=True, caption=left)