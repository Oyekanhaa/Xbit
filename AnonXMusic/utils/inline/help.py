from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from AnonXMusic import app


def help_menu_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛠 Admins", callback_data="help_cat_admin"),
            InlineKeyboardButton("🌍 Public", callback_data="help_cat_public"),
        ],
        [
            InlineKeyboardButton("👑 Owner", callback_data="help_cat_owner"),
            InlineKeyboardButton("⚡ Sudoers", callback_data="help_cat_sudoer"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="settings_back_helper"),
        ],
    ])


# Alias for backward compatibility (used in start.py)
def help_pannel(_, is_sudo=False, START=None):
    return help_menu_markup()


def help_category_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ Back", callback_data="settings_back_helper"),
        ]
    ])


def help_back_markup(_):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ Back", callback_data="settings_back_helper"),
        ]
    ])


def private_help_panel(_):
    return [
        [
            InlineKeyboardButton(
                text=_["S_B_4"],
                url=f"https://t.me/{app.username}?start=help",
            ),
        ],
    ]
