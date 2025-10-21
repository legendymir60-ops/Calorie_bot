import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai.errors import APIError
from io import BytesIO
from PIL import Image
from flask import Flask, request # <--- КРИТИЧНЫЙ ИМПОРТ ДЛЯ WEBHOOKS

# ----------------------------------------
# 1. НАСТРОЙКИ И ИНИЦИАЛИЗАЦИЯ
# ----------------------------------------

# ВАШИ ТОКЕНЫ И КЛЮЧИ:
# Используйте переменные окружения, которые вы можете установить на Render.
# Если не установлены, используются заглушки, которые нужно заменить!
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8202084470:AAHAuO30oAjrbCR8XdDMehGu9gO7H_TWa2g") # Замените на ваш токен!
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "ВАШ_КЛЮЧ_GEMINI")

# Настройки логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Настройки модели
GEMINI_MODEL = "gemini-2.5-flash"
MODEL_PROMPT = """Ты - умный ассистент, который анализирует изображения еды. 
Оцени количество калорий в еде на фотографии и дай краткое описание. 
Ответ должен быть только на русском языке, в следующем формате:
Калорий: [число] ккал.
Описание: [Краткое описание блюда].
"""

# Инициализация Gemini
try:
    if GEMINI_API_KEY and GEMINI_API_KEY != "ВАШ_КЛЮЧ_GEMINI":
        genai.configure(api_key=GEMINI_API_KEY)
        client = genai.Client()
        logger.info("Gemini Client успешно инициализирован.")
    else:
        client = None
        logger.warning("Ключ Gemini API не установлен или является заглушкой.")
except Exception as e:
    logger.error(f"Ошибка инициализации Gemini: {e}")
    client = None


# ----------------------------------------
# 2. ОБРАБОТЧИКИ КОМАНД И ФОТО
# ----------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Отправь мне фотографию еды, и я оценю её калорийность и опишу блюдо. /help для справки.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Просто отправь мне любое изображение еды. Я использую искусственный интеллект для анализа калорийности.")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not client:
        await update.message.reply_text("Сервис Gemini API недоступен. Пожалуйста, убедитесь, что ваш API-ключ установлен.")
        return

    wait_message = await update.message.reply_text("Анализирую фото... Это может занять несколько секунд.")

    try:
        file_id = update.message.photo[-1].file_id
        new_file = await context.bot.get_file(file_id)
        photo_bytes = await new_file.download_as_bytes()
        
        image_stream = BytesIO(photo_bytes)
        img = Image.open(image_stream)

        response = await client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[MODEL_PROMPT, img]
        )
        
        await wait_message.edit_text(response.text)

    except APIError as e:
        logger.error(f"Ошибка Gemini API: {e}")
        await wait_message.edit_text(f"Произошла ошибка при обращении к Gemini API. Ошибка: {e.status_code}. Проверьте ключ и биллинг.")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        await wait_message.edit_text("Произошла непредвиденная ошибка при обработке фото. Попробуйте ещё раз.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Произошла ошибка: %s", context.error)
    if update and hasattr(update, 'message') and update.message:
        await update.message.reply_text("Извините, произошла внутренняя ошибка. Мы уже работаем над её устранением.")


# ----------------------------------------
# 3. НАСТРОЙКИ WEBHOOKS (FLASK)
# ----------------------------------------

# Создание экземпляра Flask
app = Flask(__name__)

# Render автоматически предоставит переменную PORT
PORT = int(os.environ.get('PORT', 10000))
# Путь для Webhook - должен быть уникальным
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"

# Глобальные переменные для доступа к боту из Flask
BOT = None
application = None

@app.route(WEBHOOK_PATH, methods=['POST'])
async def webhook_handler():
    """Обрабатывает входящие обновления от Telegram."""
    global application
    if request.method == "POST":
        update_data = request.get_json(force=True)
        # Обрабатываем обновление как объект Update
        update = Update.de_json(update_data, application.bot)
        
        # Обработка обновления через Application
        async with application:
            await application.process_update(update)
    return "ok"

# ----------------------------------------
# 4. ФУНКЦИЯ ЗАПУСКА (ОБНОВЛЕНА)
# ----------------------------------------

def main() -> None:
    """Настраивает Webhooks и запускает Flask сервер."""
    global BOT
    global application
    
    # 1. Строим приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 2. Регистрируем все обработчики:
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, photo_handler))
    application.add_error_handler(error_handler)
    
    # Сохраняем экземпляр бота
    BOT = application.bot

    # 3. Устанавливаем Webhook
    RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')
    
    if RENDER_URL:
        # Устанавливаем Webhook на стороне Telegram
        application.run_once(
            application.bot.set_webhook(url=f"{RENDER_URL}{WEBHOOK_PATH}")
        )
        logger.info(f"Webhook установлен на: {RENDER_URL}{WEBHOOK_PATH}")
    else:
        logger.error("Переменная RENDER_EXTERNAL_URL не найдена. Webhook не установлен.")
        
    # 4. Запуск Flask сервера (этот код предотвратит ошибку Polling!)
    logger.info(f"Запуск Webhook сервера на порту {PORT}")
    app.run(host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    main()
