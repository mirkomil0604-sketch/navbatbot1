import os
import logging
import httpx
import asyncio
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required")

API_URL = "http://localhost:8001/analyze"


def escape_markdown_v2(text: str) -> str:
    if not text:
        return ""
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', str(text))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡️ SHIELD.AI\n"
        "O'zbekcha xabarlarni noto'g'ri ma'lumotlarga tekshirish tizimi.\n\n"
        "Menga istalgan matnni yuboring, men uni tekshirib beraman.\n"
        "APK fayl yuborish orqali ilova xavfsizligini tekshirib beraman."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Buyruqlar:\n"
        "/start - Boshlash\n"
        "/help - Yordam\n"
        "/example - Namuna tekshirish\n\n"
        "APK fayl yuborish orqali ilovani zararli yoki xavfsizligini tekshirib beraman."
    )


async def example(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sample = "Bu soxta yangilik. Ozarbayjon Prezidenti iste'foga chiqdi."
    await update.message.reply_text(f"🔍 Namuna tekshiruv:\n\n{sample}")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(API_URL, json={"text": sample, "language": "uz"}, timeout=30.0)
            data = resp.json()
            await update.message.reply_text(
                f"✅ Natija: {data.get('verdict', 'nomalum')}\n"
                f"📊 Ishonch: {data.get('confidence', 0) * 100:.0f}%\n"
                f"📝 Tushuntirish: {data.get('explanation', '')}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(API_URL, json={"text": text, "language": "uz"}, timeout=30.0)
            data = resp.json()
            await update.message.reply_text(
                f"✅ Natija: {data.get('verdict', 'nomalum')}\n"
                f"📊 Ishonch: {data.get('confidence', 0) * 100:.0f}%\n"
                f"📝 Tushuntirish: {data.get('explanation', '')}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}")


async def handle_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document:
        return

    file_name = document.file_name or ""
    if not file_name.lower().endswith(".apk"):
        return

    await update.message.reply_text("🔍 APK fayl tahlil qilinmoqda...")

    file = await document.get_file()
    temp_path = f"temp_{document.file_unique_id}_{file_name}"

    try:
        await file.download_to_drive(temp_path)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _analyze_apk_sync, temp_path)

        risk = result["risk_score"]
        if risk < 20:
            verdict = "✅ Xavfsiz"
            emoji = "🟢"
        elif risk < 50:
            verdict = "⚠️ Ehtiyotkor bo'lish kerak"
            emoji = "🟡"
        elif risk < 80:
            verdict = "⚠️ Xavfli"
            emoji = "🟠"
        else:
            verdict = "❌ Zararli"
            emoji = "🔴"

        perms = result["permissions"]
        sms = ", ".join(p.split(".")[-1] for p in perms["sms"]) if perms["sms"] else "Yo'q"
        accessibility = ", ".join(p.split(".")[-1] for p in perms["accessibility"]) if perms["accessibility"] else "Yo'q"
        camera = ", ".join(p.split(".")[-1] for p in perms["camera"]) if perms["camera"] else "Yo'q"
        overlay = ", ".join(p.split(".")[-1] for p in perms["overlay"]) if perms["overlay"] else "Yo'q"

        report = (
            f"{emoji} *APK Tahlil Hisoboti*\n\n"
            f"📱 *Ilova:* `{escape_markdown_v2(result['app_name'])}`\n"
            f"📦 *Paket:* `{escape_markdown_v2(result['package_name'])}`\n"
            f"🔑 *SHA-256:* `{escape_markdown_v2(result['sha256'][:16])}...`\n\n"
            f"📊 *Xavf darajasi:* {risk}%\n"
            f"*Natija:* {verdict}\n\n"
            f"🔐 *Xavfli ruxsatlar:*\n"
            f"• SMS: {escape_markdown_v2(sms)}\n"
            f"• Accessibility: {escape_markdown_v2(accessibility)}\n"
            f"• Camera: {escape_markdown_v2(camera)}\n"
            f"• Overlay: {escape_markdown_v2(overlay)}\n"
        )

        await update.message.reply_text(report, parse_mode="MarkdownV2")
    except Exception as e:
        logger.exception("APK analysis failed")
        await update.message.reply_text(f"❌ Tahlil xatoligi: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _analyze_apk_sync(file_path: str) -> dict:
    from apk_scanner import analyze_apk
    return analyze_apk(file_path)


def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("example", example))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_apk))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
