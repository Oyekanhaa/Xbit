import time
import re
import random
import asyncio

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate
from pyrogram.errors.exceptions.flood_420 import SlowmodeWait
from ytSearch import VideosSearch

import config
from AnonXMusic import app
from AnonXMusic.misc import _boot_
from AnonXMusic.plugins.sudo.sudoers import sudoers_list
from AnonXMusic.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_lang,
    is_banned_user,
    is_on_off,
    blacklist_chat,
)
from AnonXMusic.utils.decorators.language import LanguageStart
from AnonXMusic.utils.formatters import get_readable_time
from AnonXMusic.utils.inline import help_pannel, private_panel, start_panel
from config import BANNED_USERS, LOGGER_ID
from strings import get_string


# ======================= START PRIVATE ======================= #

@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    await add_served_user(message.from_user.id)

    if message.text and len(message.text.split()) > 1:
        name = message.text.split(maxsplit=1)[1]

        # HELP
        if name.startswith("help"):
            from AnonXMusic.utils.inline.help import help_menu_markup
            from AnonXMusic.plugins.bot.help import HELP_MAIN_TEXT
            try:
                await message.delete()
            except:
                pass
            return await app.send_photo(
                chat_id=message.chat.id,
                photo=random.choice(config.START_IMG_URL),
                caption=HELP_MAIN_TEXT,
                reply_markup=help_menu_markup(),
            )

        # SUDO LIST
        if name.startswith("sud"):
            await sudoers_list(client=client, message=message, _=_)

            if await is_on_off(2) and LOGGER_ID:
                username = message.from_user.username or "No Username"
                return await app.send_message(
                    chat_id=LOGGER_ID,
                    text=f"{message.from_user.mention} checked <b>sudolist</b>.\n\n"
                         f"<b>User ID :</b> <code>{message.from_user.id}</code>\n"
                         f"<b>Username :</b> @{username}",
                )
            return

        # INFO (YT)
        if name.startswith("inf"):
            m = await message.reply_text("🔍 Searching Video Info...")

            query = name.replace("info_", "", 1)
            query = f"https://www.youtube.com/watch?v={query}"

            try:
                results = VideosSearch(query, limit=1)
                data = await results.next()

                if not data["result"]:
                    return await m.edit("❌ No results found.")

                result = data["result"][0]

                title = result["title"]
                duration = result["duration"]
                views = result["viewCount"]["short"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                channellink = result["channel"]["link"]
                channel = result["channel"]["name"]
                link = result["link"]
                published = result["publishedTime"]

            except Exception as e:
                return await m.edit(f"❌ Error:\n{e}")

            searched_text = _["start_6"].format(
                title, duration, views, published, channellink, channel, app.mention
            )

            key = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text=_["S_B_8"], url=link),
                        InlineKeyboardButton(text=_["S_B_9"], url=config.SUPPORT_CHAT),
                    ]
                ]
            )

            await m.delete()

            await app.send_photo(
                chat_id=message.chat.id,
                photo=thumbnail,
                caption=searched_text,
                reply_markup=key,
            )

            if await is_on_off(2) and LOGGER_ID:
                username = message.from_user.username or "No Username"
                return await app.send_message(
                    chat_id=LOGGER_ID,
                    text=f"{message.from_user.mention} checked track info.\n\n"
                         f"<b>User ID :</b> <code>{message.from_user.id}</code>\n"
                         f"<b>Username :</b> @{username}",
                )

    else:
        out = private_panel(_)

        try:
            await message.delete()
        except:
            pass

        img_url = random.choice(config.START_IMG_URL)
        text = _["start_2"].format(message.from_user.mention, app.mention)

        await app.send_message(
            chat_id=message.chat.id,
            text=f"{text}\n\n<a href='{img_url}'>&#8205;</a>",
            reply_markup=InlineKeyboardMarkup(out),
            disable_web_page_preview=False,
        )

        if await is_on_off(2) and LOGGER_ID:
            username = message.from_user.username or "No Username"
            return await app.send_message(
                chat_id=LOGGER_ID,
                text=f"{message.from_user.mention} started the bot.\n\n"
                     f"<b>User ID :</b> <code>{message.from_user.id}</code>\n"
                     f"<b>Username :</b> @{username}",
            )


# ======================= START GROUP ======================= #

@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    out = start_panel(_)
    uptime = int(time.time() - _boot_)

    try:
        try:
            await message.delete()
        except:
            pass

        img_url = random.choice(config.START_IMG_URL)
        text = _["start_1"].format(app.mention, get_readable_time(uptime))

        await app.send_message(
            chat_id=message.chat.id,
            text=f"{text}\n\n<a href='{img_url}'>&#8205;</a>",
            reply_markup=InlineKeyboardMarkup(out),
            disable_web_page_preview=False,
        )
        return await add_served_chat(message.chat.id)

    except ChannelPrivate:
        return

    except SlowmodeWait as e:
        await asyncio.sleep(e.value)
        try:
            img_url = random.choice(config.START_IMG_URL)
            text = _["start_1"].format(app.mention, get_readable_time(uptime))
            await app.send_message(
                chat_id=message.chat.id,
                text=f"{text}\n\n<a href='{img_url}'>&#8205;</a>",
                reply_markup=InlineKeyboardMarkup(out),
                disable_web_page_preview=False,
            )
            return await add_served_chat(message.chat.id)
        except:
            return


# ======================= WELCOME ======================= #

@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)

            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except:
                    pass

            if member.id == app.id:

                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await app.leave_chat(message.chat.id)

                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            app.mention,
                            f"https://t.me/{app.username}?start=sudolist",
                            config.SUPPORT_CHAT,
                        ),
                        disable_web_page_preview=True,
                    )
                    return await app.leave_chat(message.chat.id)

                ch = await app.get_chat(message.chat.id)

                if (ch.title and re.search(r'[\u1000-\u109F]', ch.title)) or \
                   (ch.description and re.search(r'[\u1000-\u109F]', ch.description)):

                    await blacklist_chat(message.chat.id)

                    await message.reply_text("This group is not allowed to play songs")

                    if LOGGER_ID:
                        await app.send_message(
                            LOGGER_ID,
                            f"Blacklisted group due to Myanmar text\n"
                            f"Title: {ch.title}\nID: {message.chat.id}"
                        )

                    return await app.leave_chat(message.chat.id)

                out = start_panel(_)

                await message.reply_photo(
                    photo=random.choice(config.START_IMG_URL),
                    caption=_["start_3"].format(
                        message.from_user.first_name,
                        app.mention,
                        message.chat.title,
                        app.mention,
                    ),
                    reply_markup=InlineKeyboardMarkup(out),
                )

                await add_served_chat(message.chat.id)
                await message.stop_propagation()

        except Exception as ex:
            print(ex)