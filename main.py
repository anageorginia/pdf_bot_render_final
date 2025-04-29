import logging
import os
import zipfile
import asyncio

from flask import Flask
from threading import Thread

from pdf2image import convert_from_path
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

BOT_TOKEN = "7842250880:AAEPK586WXhyLeGyfanoEbRyZTBqrXUKbu8"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Веб-сервер для поддержки UptimeRobot
app = Flask('')

@app.route('/')
def home():
    return "PDF bot работает!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет) Пришли мне PDF-файл, и я верну ZIP-архив со скринами."
    )

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message.document:
        await message.reply_text("Ты втираешь мне какую-то дичь! Пришли, пожалуйста, PDF-документ.")
        return

    doc = message.document
    file_name = doc.file_name.lower()

    if not (file_name.endswith('.pdf') or doc.mime_type == 'application/pdf'):
        await message.reply_text("Ты втираешь мне какую-то дичь! Пришли, пожалуйста, PDF-документ.")
        return

    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        await message.reply_text("Прости, друг, файл слишком большой (>20MB). Telegram не даёт боту его скачать. Попробуй уменьшить PDF.")
        return

    await message.reply_text("Скачиваю PDF...")

    os.makedirs("temp", exist_ok=True)
    pdf_file_path = os.path.join("temp", file_name)

    try:
        file = await context.bot.get_file(doc.file_id)
        await file.download_to_drive(custom_path=pdf_file_path)
    except Exception as e:
        await message.reply_text(f"Ошибка при загрузке файла: {e}")
        return

    await message.reply_text("Конвертирую PDF в картинки...")

    images = convert_from_path(pdf_file_path, dpi=150)
    zip_filename = file_name.replace('.pdf', '_pages.zip')
    zip_filepath = os.path.join("temp", zip_filename)

    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for i, img in enumerate(images):
            page_num = i + 1
            img_filename = f"page_{page_num}.png"
            img_path = os.path.join("temp", img_filename)
            img.save(img_path, "PNG")
            zipf.write(img_path, arcname=img_filename)
            os.remove(img_path)

    with open(zip_filepath, 'rb') as f:
        await message.reply_document(
            document=InputFile(f, filename=zip_filename),
            caption="Вот твой ZIP со скриншотами, обращайся 🫡"
        )

    os.remove(pdf_file_path)
    os.remove(zip_filepath)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.ALL, handle_pdf))
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    keep_alive()
    asyncio.run(main())
