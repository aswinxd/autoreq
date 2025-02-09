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
                [InlineKeyboardButton("Add bot to your group / channel", url=f"https://t.me/{c.me.username}?startgroup=true")]
            ])

            await m.reply_text(
                f"Hello {m.from_user.mention},\n\n"
                "Key Features:\n"
                "1. Automatically approve join requests in groups and channels.\n"
                "2. Use /accept to accept all pending join requests.\n"
                "3. Add me as an admin in your group or channel with admin rights.\n",
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
                [InlineKeyboardButton("", url=f"https://t.me/{c.me.username}?startgroup=true")]
            ])

            await cb.message.edit(
                f"Hello {cb.from_user.mention},\n\n"
                "Key Features:\n"
                "1. Automatically approve join requests in groups and channels.\n"
                "2. Use /accept to accept all pending join requests.\n"
                "3. Add me as an admin in your group or channel with full rights.\n"
                "4. Dont worry if the approving is stopped it is to avoid flood it will continue after some seconds.",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )

    except UserNotParticipant:
        await cb.answer("You have not joined the required channel. Please join and try again.", show_alert=True)

import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, BadRequest

BATCH_SIZE = 10  
DELAY_BETWEEN_BATCHES = 5  

@Client.on_message(filters.command('accept') & filters.private)
async def accept(client, message):
    """Handles the /accept command and starts processing join requests."""
    user_data = await db.get_session(message.from_user.id)
    if user_data is None:
        await message.reply("⚠️ Please log in first using /login.")
        return

    try:
        acc = Client(
            "joinrequest",
            session_string=user_data,
            api_hash=API_HASH,
            api_id=API_ID
        )
        await acc.connect()
    except Exception as e:
        logging.error(f"❌ Error connecting session: {str(e)}")
        return await message.reply("⚠️ Your login session has expired. Please log in again using /login.")

    chat_id_msg = await client.ask(
        message.chat.id,
        "📢 Enter the **channel/group ID** where you want to approve join requests:"
    )

    try:
        chat_id = int(chat_id_msg.text)

        try:
            await acc.get_chat(chat_id)  
        except Exception as e:
            logging.error(f"❌ Error accessing chat: {str(e)}")
            await message.reply("⚠️ Error: Ensure your account is an admin with approval rights.")
            return

        msg = await message.reply("🔄 Processing join requests...")
        await approve_requests(acc, chat_id, msg)

    except ValueError:
        await message.reply("⚠️ Please enter a **valid** channel or group ID.")


async def approve_requests(client, chat_id, msg):
    """Approves join requests in batches while ensuring logs & error handling."""
    logging.info(f"🚀 Starting approval process for chat {chat_id}")

    while True:
        try:
            approved_count = 0
            pending_requests = 0  

            async for request in client.get_chat_join_requests(chat_id, limit=BATCH_SIZE):
                if request:
                    pending_requests += 1  

                    try:
                        await client.approve_chat_join_request(chat_id, request.user.id)
                        approved_count += 1
                        logging.info(f"✅ Approved user: {request.user.id}")
                    except BadRequest as e:
                        if "USER_CHANNELS_TOO_MUCH" in str(e) or "INPUT_USER_DEACTIVATED" in str(e):
                            logging.warning(f"⚠️ Skipping user {request.user.id} - {str(e)}")
                            continue  
                        else:
                            raise e  

                    await asyncio.sleep(1)  # Prevent rate limits

            if pending_requests == 0:  
                logging.info("No more pending join requests.")
                await msg.edit("All pending join requests **have been approved**.")
                return

            logging.info(f" Approved {approved_count} users. Waiting {DELAY_BETWEEN_BATCHES} seconds before next batch...")
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)  

        except FloodWait as e:
            logging.warning(f"🚨 FloodWait: Sleeping for {e.value} seconds.")
            await msg.edit(f"🚨 Telegram rate limit reached. Waiting {e.value} seconds...")
            await asyncio.sleep(e.value)  

        except BadRequest as e:
            logging.error(f"⚠️ BadRequest: {str(e)}")
            if "HIDE_REQUESTER_MISSING" in str(e):
                logging.info("⚠️ No more visible requests. Stopping process.")
                await msg.edit("⚠️ No more visible requests. Process stopped.")
                break

        except Exception as e:
            logging.error(f"🔥 Unexpected error: {str(e)}")
            await msg.edit(f"🔥 Unexpected error: {str(e)}")
            break
