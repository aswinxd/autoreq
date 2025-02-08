import traceback
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client, filters
from asyncio.exceptions import TimeoutError
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid
)
from config import API_ID, API_HASH
from plugins.database import db

SESSION_STRING_SIZE = 351

@Client.on_message(filters.private & ~filters.forwarded & filters.command(["logout"]))
async def logout(client, message):
    user_data = await db.get_session(message.from_user.id)  
    if user_data is None:
        return 
    await db.set_session(message.from_user.id, session=None)  
    await message.reply("**Logout Successfully** ♦")

@Client.on_message(filters.private & ~filters.forwarded & filters.command(["login"]))
async def main(bot: Client, message: Message):
    user_data = await db.get_session(message.from_user.id)
    if user_data is not None:
        await message.reply("**You are already logged in. First, /logout your old session and then login again.**")
        return 

    user_id = int(message.from_user.id)
    
    await message.reply(
        "<b>Please send your phone number including country code.</b>\n"
        "<b>Example:</b> <code>+13124562345, +9171828181889</code>"
    )

    try:
        phone_number_msg = await bot.listen(user_id, timeout=60)
    except TimeoutError:
        await message.reply("❌ You took too long. Please start the /login process again.")
        return

    if phone_number_msg.text == "/cancel":
        return await phone_number_msg.reply("<b>Process cancelled!</b>")
    
    phone_number = phone_number_msg.text

    client = Client(":memory:", API_ID, API_HASH)
    await client.connect()
    await phone_number_msg.reply("📲 Sending OTP...")

    try:
        code = await client.send_code(phone_number)

        await message.reply(
            "📩 Please check for an OTP in your official Telegram account.\n\n"
            "If OTP is `12345`, **please send it as** `1 2 3 4 5`.\n\n"
            "**Enter /cancel to cancel the process.**"
        )

        phone_code_msg = await bot.listen(user_id, timeout=600)

        if phone_code_msg.text == "/cancel":
            return await phone_code_msg.reply("<b>Process cancelled!</b>")
        
        phone_code = phone_code_msg.text.replace(" ", "")
        await client.sign_in(phone_number, code.phone_code_hash, phone_code)

    except PhoneNumberInvalid:
        await phone_number_msg.reply("❌ **The phone number is invalid.**")
        return
    except PhoneCodeInvalid:
        await phone_code_msg.reply("❌ **The OTP is incorrect.**")
        return
    except PhoneCodeExpired:
        await phone_code_msg.reply("❌ **The OTP has expired.**")
        return
    except SessionPasswordNeeded:
        await message.reply(
            "🔒 **Your account has two-step verification enabled.**\n\n"
            "Please send your password below.\n\n"
            "**Enter /cancel to cancel the process.**"
        )

        try:
            two_step_msg = await bot.listen(user_id, timeout=300)

            if two_step_msg.text == "/cancel":
                return await two_step_msg.reply("<b>Process cancelled!</b>")

            password = two_step_msg.text
            await client.check_password(password=password)

        except PasswordHashInvalid:
            await two_step_msg.reply("❌ **Invalid password.**")
            return

    string_session = await client.export_session_string()
    await client.disconnect()

    if len(string_session) < SESSION_STRING_SIZE:
        return await message.reply("❌ **Invalid session string.**")

    try:
        user_data = await db.get_session(message.from_user.id)
        if user_data is None:
            uclient = Client(":memory:", session_string=string_session, api_id=API_ID, api_hash=API_HASH)
            await uclient.connect()
            await db.set_session(message.from_user.id, session=string_session)

    except Exception as e:
        return await message.reply_text(f"⚠️ <b>ERROR IN LOGIN:</b> `{e}`")

    await bot.send_message(
        message.from_user.id,
        "<b>✅ Account Login Successful.\n\n"
        "If you get any AUTH KEY error, first /logout and then /login again.</b>"
    )
