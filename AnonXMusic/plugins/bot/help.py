import random
from typing import Union

from pyrogram import filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import MessageNotModified

import config
from AnonXMusic import app
from AnonXMusic.misc import SUDOERS
from AnonXMusic.utils.database import get_lang
from AnonXMusic.utils.decorators.language import LanguageStart
from AnonXMusic.utils.inline.help import private_help_panel, help_menu_markup, help_category_markup
from config import BANNED_USERS, SUPPORT_CHAT
from strings import get_string


ADMIN_HELP = """🛠 <b>Admin Commands</b>

<i>Music and playback control tools for admins to handle playback easily.</i>

<b>Commands:</b>
/speed - Change playback speed
/skip - Skip the current song
/pause - Pause the current playback
/resume - Resume paused playback
/replay - Replay the current song
/mute - Mute playback
/unmute - Unmute playback
/seek - Seek forward by a few seconds
/seekback - Seek backward by a few seconds
/jump - Jump to a given time in track
/move - Move a queued track to another position
/clear - Clear all songs from queue
/remove - Remove a specific track from queue
/shuffle - Shuffle all queued tracks
/loop - Enable or disable looping
/stop - Stop playback and leave VC"""

PUBLIC_HELP = """🌍 <b>Public Commands</b>

<i>Features for playing songs, viewing queues, checking latency, and reporting bugs.</i>

<b>Commands:</b>
/play - Play a song
/queue - View all tracks currently queued
/ping - Check bot's network latency
/start - Start the bot
/help - Show help menu
/bug - Report an issue or problem
/position - Show current track's timestamp
/reload - Reload admin or cache data
/json - Show message JSON structure
/sudolist - View sudo user list"""

OWNER_HELP = """👑 <b>Owner Commands</b>

<i>Exclusive tools for managing sudoers, executing system code, and performing bot administration securely.</i>

<b>Commands:</b>
/addsudo - Add a new user to bot's sudolist
/delsudo - Remove a user from bot's sudolist
/eval - Execute code snippets
/maintenance - Manage the bot's maintenance mode
/restart - Restart the bot
/sh - Run shell commands"""

SUDOER_HELP = """⚡ <b>Sudoer Commands</b>

<i>Advanced tools for managing bot behavior, monitoring performance, and controlling logging and automation.</i>

<b>Commands:</b>
/active - Shows total active chats
/autoleave - Toggle automatic chat leaving
/logger - Enable or disable logger
/stats - Display the bot & system stats
/logs - Get the system logs"""

HELP_MAIN_TEXT = "📚 <b>Help Menu</b>\n\nSelect a category below to explore detailed commands and their usage for managing, controlling, and customizing the bot."


@app.on_message(filters.command(["help"]) & filters.private & ~BANNED_USERS)
async def help_command(client, message: Message):
    try:
        await message.delete()
    except:
        pass
    await client.send_photo(
        chat_id=message.chat.id,
        photo=random.choice(config.START_IMG_URL),
        caption=HELP_MAIN_TEXT,
        reply_markup=help_menu_markup(),
    )


# Back button — message is a photo, so edit_message_caption
@app.on_callback_query(filters.regex("^settings_back_helper$") & ~BANNED_USERS)
async def back_to_help(client, callback: CallbackQuery):
    try:
        await callback.answer()
    except:
        pass
    try:
        await callback.edit_message_caption(
            caption=HELP_MAIN_TEXT,
            reply_markup=help_menu_markup(),
        )
    except MessageNotModified:
        pass
    except Exception:
        pass


@app.on_message(filters.command(["help"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def help_com_group(client, message: Message, _):
    keyboard = private_help_panel(_)
    await message.reply_text(_["help_2"], reply_markup=InlineKeyboardMarkup(keyboard))


@app.on_callback_query(filters.regex("^help_cat_") & ~BANNED_USERS)
async def help_category_cb(client, callback: CallbackQuery):
    try:
        await callback.answer()
    except:
        pass

    cat = callback.data.replace("help_cat_", "")

    if cat == "admin":
        text = ADMIN_HELP
    elif cat == "public":
        text = PUBLIC_HELP
    elif cat == "owner":
        text = OWNER_HELP
    elif cat == "sudoer":
        text = SUDOER_HELP
    else:
        return

    try:
        await callback.edit_message_caption(
            caption=text,
            reply_markup=help_category_markup(),
        )
    except MessageNotModified:
        pass
