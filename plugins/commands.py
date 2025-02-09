from pyrogram import Client, filters, enums, errors
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import UserNotParticipant
from config import LOG_CHANNEL, API_ID, API_HASH, FSUB, CHID
from plugins.database import db
from plugins.database2 import add_user, add_group, all_users, all_groups, users, remove_user
import random

LOG_TEXT = """New User:
ID - {}
Name - {}"""

@Client.on_message(filters.command('start'))
async def start_message(c, m):
    try:
        await c.get_chat_member(CHID, m.from_user.id)
        if not await db.is_user_exist(m.from_user.id):
            await db.add_user(m.from_user.id, m.from_user.first_name)
            await c.send_message(LOG_CHANNEL, LOG_TEXT.format(m.from_user.id, m.from_user.mention))

        if m.chat.type == enums.ChatType.PRIVATE:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀᴛ", url=f"https://t.me/{c.me.username}?startgroup=true")]
            ])

            await m.reply_text(
                f"Hello {m.from_user.mention},\n\n"
                "Key Features:\n"
                "1. Automatically approve join requests in groups and channels.\n"
                "2. Use /accept to accept all pending join requests.\n"
                "3. Add me as an admin in your group or channel with full rights.\n",
                reply_markup=keyboard
            )

        elif m.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Start me private", url=f"https://t.me/{c.me.username}?start=start")]
            ])
            add_group(m.chat.id)
            await m.reply_text(
                "Start me private for more details.",
                reply_markup=keyboard
            )

    except UserNotParticipant:
        key = InlineKeyboardMarkup([
            [InlineKeyboardButton("Check Again", "chk")]
        ])
        await m.reply_text(
            f"Access Denied!\n\nPlease join @{FSUB} to use this bot. Once joined, click 'Check Again'.",
            reply_markup=key
        )

@Client.on_callback_query(filters.regex("chk"))
async def chk(c, cb):
    try:
        await c.get_chat_member(CHID, cb.from_user.id)
        if cb.message.chat.type == enums.ChatType.PRIVATE:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴄʜᴀᴛ", url=f"https://t.me/{c.me.username}?startgroup=true")]
            ])

            await cb.message.edit(
                f"Hello {cb.from_user.mention},\n\n"
                "Key Features:\n"
                "1. Automatically approve join requests in groups and channels.\n"
                "2. Use /accept to accept all pending join requests.\n"
                "3. Add me as an admin in your group or channel with full rights.\n",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )

    except UserNotParticipant:
        await cb.answer("You have not joined the required channel. Please join and try again.", show_alert=True)

@Client.on_message(filters.command('accept') & filters.private)
async def accept(client, message):
    user_data = await db.get_session(message.from_user.id)
    if user_data is None:
        await message.reply("To accept pending requests, please log in first using /login.")
        return

    try:
        acc = Client(
            "joinrequest",
            session_string=user_data,
            api_hash=API_HASH,
            api_id=API_ID
        )
        await acc.connect()
    except:
        return await message.reply("Your login session has expired. Please log in again using /login.")

    chat_id_msg = await client.ask(
        message.chat.id,
        "Please enter the channel or group ID where you want to accept join requests."
    )

    try:
        chat_id = int(chat_id_msg.text)

        try:
            await acc.get_chat(chat_id)
        except:
            await message.reply("Error: Ensure your logged-in account is an admin with the necessary rights.")
            return

        msg = await message.reply("Processing join requests...")
        try:
            await acc.approve_all_chat_join_requests(chat_id)
            await msg.edit("Successfully accepted all join requests.")
        except:
            await msg.edit("An error occurred during the process.")

    except ValueError:
        await message.reply("Please enter a valid channel or group ID.")

import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, BadRequest

BATCH_SIZE = 10  # Adjust batch size if needed

@Client.on_chat_join_request(filters.group | filters.channel & ~filters.private)
async def handle_new_join_request(client, message: Message):
    """Starts the approval process when a new join request is received."""
    chat_id = message.chat.id
    logging.info(f"New join request detected in {chat_id}. Starting batch approval...")
    await approve_requests(client, chat_id)

async def approve_requests(client, chat_id):
    """Approves join requests in batches while handling errors properly."""
    logging.info(f"Starting approval process for chat {chat_id}")

    while True:
        try:
            async for request in client.get_chat_join_requests(chat_id, limit=BATCH_SIZE):
                if request is None:
                    logging.info("No more pending join requests.")
                    await client.send_message(chat_id, "All pending join requests have been approved.")
                    break

                try:
                    await client.approve_chat_join_request(chat_id, request.user.id)
                    logging.info(f"Approved user: {request.user.id}")
                except BadRequest as e:
                    if "USER_CHANNELS_TOO_MUCH" in str(e):
                        logging.warning(f"Cannot approve {request.user.id}: User has joined too many channels.")
                        continue
                    elif "INPUT_USER_DEACTIVATED" in str(e):
                        logging.warning(f"Cannot approve {request.user.id}: User account is deleted.")
                        continue
                    else:
                        raise e  

                await asyncio.sleep(1)  # Prevent hitting rate limits

        except FloodWait as e:
            logging.warning(f"FloodWait triggered: Sleeping for {e.value} seconds.")
            await asyncio.sleep(e.value)  
        except BadRequest as e:
            logging.error(f"BadRequest: {str(e)}")
            if "HIDE_REQUESTER_MISSING" in str(e):
                logging.info("No more visible requests. Stopping process.")
                break
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            break

