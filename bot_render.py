import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

# ===================== CONFIG =====================
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# =================================================

logging.basicConfig(level=logging.INFO)

# admin_message_id -> user_chat_id
reply_map = {}
blocked_users = set()


def get_display_name(user):
    if user.username:
        return f"@{user.username}"
    return user.full_name or "Unknown"


# ---------- USER -> BOT ----------
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    if chat_id in blocked_users:
        return

    text = update.message.text
    name = get_display_name(user)

    # 🔹 ارسال عکس پروفایل (اگه داشته باشه)
    photos = await context.bot.get_user_profile_photos(user.id, limit=1)
    if photos.total_count > 0:
        file_id = photos.photos[0][-1].file_id
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=f"👤 عکس پروفایل {name}"
        )

    # 🔹 ارسال متن پیام به ادمین
    sent = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "📩 پیام جدید\n"
            f"از طرف: {name}\n"
            f"UserID: {chat_id}\n\n"
            f"{text}"
        )
    )

    # 🔹 اتصال پیام ادمین به پیام دقیق کاربر
    reply_map[sent.message_id] = {
        "chat_id": chat_id,
        "message_id": update.message.message_id
    }




# ---------- ADMIN -> BOT (REPLY) ----------
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message.reply_to_message:
        return

    replied_id = message.reply_to_message.message_id

    if replied_id not in reply_map:
        await message.reply_text("❌ این پیام به کاربری وصل نیست.")
        return

    data = reply_map[replied_id]

    await context.bot.send_message(
        chat_id=data["chat_id"],
        text=message.text,
        reply_to_message_id=data["message_id"]
    )



# ---------- COMMANDS ----------
async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ روی پیام کاربر Reply کن.")
        return

    mid = update.message.reply_to_message.message_id
    if mid not in reply_map:
        await update.message.reply_text("❌ کاربر پیدا نشد.")
        return

    blocked_users.add(reply_map[mid]["chat_id"])
    await update.message.reply_text("🚫 کاربر بلاک شد.")



async def close_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ روی پیام کاربر Reply کن.")
        return

    mid = update.message.reply_to_message.message_id
    if mid not in reply_map:
        await update.message.reply_text("❌ چت پیدا نشد.")
        return

    user_chat_id = reply_map.pop(mid)

    await context.bot.send_message(
        chat_id=user_chat_id,
        text="🔒 این مکالمه بسته شد."
    )

    await update.message.reply_text("✅ چت بسته شد.")


# ---------- MAIN ----------
# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("block", block_user))
    app.add_handler(CommandHandler("close", close_chat))

    # ادمین (ریپلای)
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.User(ADMIN_ID),
            handle_admin_reply,
        )
    )

    # کاربران
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.ChatType.PRIVATE & ~filters.User(ADMIN_ID),
            handle_user_message,
        )
    )

    print("🤖 Bot is running...")
    app.run_polling()  # خود PTB مدیریت event loop رو انجام میده

