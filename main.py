import os
import json
from pdf2docx import Converter
from docx2pdf import convert
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8049955791:AAH3ioL6Huqp_e73deLUibdBQwGCcrrWkYk"
WEBHOOK_URL = "https://your-app-name.onrender.com"  # رابط الاستضافة
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
FREE_TRIALS = 3
USERS_FILE = "users.json"

# ------------------ Helpers ------------------

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f)

def get_user(user_id):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {
            "trials": FREE_TRIALS,
            "invited": 0
        }
        save_users(users)
    return users

def decrease_trial(user_id):
    users = load_users()
    users[str(user_id)]["trials"] -= 1
    save_users(users)

def add_trial(user_id):
    users = load_users()
    users[str(user_id)]["trials"] += 1
    save_users(users)

# ------------------ Commands ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users = get_user(user_id)

    # referral system
    if context.args:
        ref_id = context.args[0]
        if ref_id != str(user_id):
            users_data = load_users()
            if ref_id in users_data:
                add_trial(ref_id)
                users_data[ref_id]["invited"] += 1
                save_users(users_data)

    await update.message.reply_text(
        f"👋 أهلاً بك\n\n"
        f"يمكنك تحويل:\n"
        f"PDF ⇄ DOCX\n\n"
        f"📌 المحاولات المتبقية: {users[str(user_id)]['trials']}\n"
        f"📎 الحد الأقصى للملف: 10MB"
    )

# ------------------ File Handler ------------------

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users = get_user(user_id)

    if users[str(user_id)]["trials"] <= 0:
        referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
        await update.message.reply_text(
            "❌ انتهت محاولاتك المجانية.\n\n"
            "📢 شارك البوت مع أصدقائك.\n"
            "✅ كل شخص يبدأ البوت عبر رابطك = محاولة جديدة.\n\n"
            f"🔗 رابطك:\n{referral_link}"
        )
        return

    doc = update.message.document

    if doc.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("⚠️ حجم الملف أكبر من 10MB.")
        return

    file = await doc.get_file()
    input_file = doc.file_name

    await file.download_to_drive(input_file)

    try: 
        if input_file.endswith(".pdf"):
            output = "output.docx"
            cv = Converter(input_file)
            cv.convert(output)
            cv.close()

        elif input_file.endswith(".docx"):
            output = "output.pdf"
            convert(input_file, output)

        else:
            await update.message.reply_text("❌ الصيغة غير مدعومة.")
            return

        await update.message.reply_document(open(output, "rb"))
        decrease_trial(user_id)

    except Exception as e:
        await update.message.reply_text("⚠️ حدث خطأ أثناء التحويل.")

    finally:
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists("output.docx"):
            os.remove("output.docx")
        if os.path.exists("output.pdf"):
            os.remove("output.pdf")

# ------------------ App ------------------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 10000)),
    webhook_url=WEBHOOK_URL
)