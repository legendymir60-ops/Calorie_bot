import os
import logging
from io import BytesIO
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters,
    ConversationHandler
)
from PIL import Image

# Импорт для работы с Gemini
from google import genai
from google.genai.errors import APIError 

# ⬇️ 1. Настройка ключей и токенов ⬇️
# ВАШИ КЛЮЧИ ВСТАВЛЕНЫ СЮДА (СБРОСЬТЕ ИХ ПОСЛЕ ТЕСТИРОВАНИЯ!):
TELEGRAM_TOKEN = "8202084470:AAHAuO30oAjrbCR8XdDMehGu9gO7H_TWa2g"  
GEMINI_API_KEY = "AIzaSyAmMlywtFkMw5P9p03bC_hPjBp0IYXFyvo"  

# ----------------------------------------
# Настройка логирования
# ----------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация клиента Gemini
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    gemini_model = "gemini-2.5-flash" 
except ValueError:
    logger.error("Ошибка инициализации Gemini: Проверьте GEMINI_API_KEY.")
    gemini_client = None


# ----------------------------------------
# 2. МНОГОЯЗЫЧНЫЕ СООБЩЕНИЯ
# ----------------------------------------

MESSAGES = {
    'ru': {
        'start_welcome': 'Привет! 👋 Я ваш помощник по калориям. Отправь мне фото еды для анализа. Для персональных рекомендаций начни с команды /profile.',
        'select_lang': 'Выберите язык / Tilni tanlang / Choose your language:',
        'lang_set': 'Язык установлен на Русский. Начните с команды /start.',
        'profile_start': 'Давайте настроим ваш профиль для персонализированных рекомендаций.',
        'ask_gender': '1/5. Укажите ваш пол:',
        'ask_weight': '2/5. Введите ваш текущий вес (например, 75 кг):',
        'ask_height': '3/5. Введите ваш рост в сантиметрах (например, 180 см):',
        'ask_activity': '4/5. Укажите ваш уровень физической активности (Низкий - мало движения, Высокий - ежедневные тренировки):',
        'ask_goal': '5/5. Какова ваша основная цель:',
        'invalid_number': 'Пожалуйста, введите только число (например, 75).',
        'invalid_height': 'Пожалуйста, введите реальный рост в сантиметрах (например, от 100 до 250).',
        'profile_saved': '✅ Ваш профиль сохранен. Теперь отправляйте фото еды для анализа и персональных рекомендаций!',
        'profile_canceled': 'Настройка профиля отменена.',
        'no_profile': 'Для получения персональных рекомендаций, пожалуйста, сначала настройте свой профиль с помощью команды /profile.',
        'processing': '...Анализирую фото и составляю персональные рекомендации...',
        'crit_error': 'Критическая ошибка: Сервис Gemini недоступен. Проверьте ваш API-ключ.',
        'api_error': '❌ Ошибка Gemini API. Вероятно, неверный ключ, превышен лимит или проблема с квотой. Детали: ',
        'unknown_error': 'Произошла непредвиденная ошибка. Пожалуйста, попробуйте еще раз. Детали для разработчика: ',
        'analysis_header': '<b>✅ Анализ и персональные рекомендации:</b>\n\n'
    },
    'uz': {
        'start_welcome': 'Salom! 👋 Men sizning kaloriya boʻyicha yordamchingizman. Tahlil qilish uchun ovqatingizning rasmini yuboring. Shaxsiy tavsiyalar olish uchun /profile buyrugʻidan boshlang.',
        'select_lang': 'Выберите язык / Tilni tanlang / Choose your language:',
        'lang_set': 'Til Oʻzbekcha qilib oʻrnatildi. /start buyrugʻidan boshlang.',
        'profile_start': 'Shaxsiylashtirilgan tavsiyalar uchun profilingizni sozlaylik.',
        'ask_gender': '1/5. Jinsingizni kiriting:',
        'ask_weight': '2/5. Hozirgi vazningizni kiriting (masalan, 75 kg):',
        'ask_height': '3/5. Boʻyingizni santimetrda kiriting (masalan, 180 sm):',
        'ask_activity': '4/5. Jismoniy faollik darajangizni kiriting (Past - kam harakat, Yuqori - har kuni mashgʻulotlar):',
        'ask_goal': '5/5. Asosiy maqsadingiz qanday:',
        'invalid_number': 'Iltimos, faqat raqam kiriting (masalan, 75).',
        'invalid_height': 'Iltimos, boʻyingizni santimetrda kiriting (masalan, 100 dan 250 gacha).',
        'profile_saved': '✅ Profilingiz saqlandi. Endi tahlil va shaxsiy tavsiyalar uchun ovqat rasmini yuboring!',
        'profile_canceled': 'Profilni sozlash bekor qilindi.',
        'no_profile': 'Shaxsiylashtirilgan tavsiyalar olish uchun avval /profile buyrugʻi orqali profilingizni sozlang.',
        'processing': '...Rasmni tahlil qilmoqdaman va shaxsiy tavsiyalar tayyorlamoqdaman...',
        'crit_error': 'Kritik xato: Gemini xizmati mavjud emas. API kalitingizni tekshiring.',
        'api_error': '❌ Gemini API xatosi. Ehtimol, notoʻgʻri kalit yoki kvota muammosi. Tafsilotlar: ',
        'unknown_error': 'Kutilmagan xato yuz berdi. Iltimos, qaytadan urinib koʻring. Dasturchi uchun tafsilotlar: ',
        'analysis_header': '<b>✅ Tahlil va shaxsiy tavsiyalar:</b>\n\n'
    },
    'en': {
        'start_welcome': 'Hello! 👋 I am your calorie assistant. Send me a photo of your food for analysis. For personalized recommendations, start with the /profile command.',
        'select_lang': 'Выберите язык / Tilni tanlang / Choose your language:',
        'lang_set': 'Language set to English. Start with the /start command.',
        'profile_start': 'Let\'s set up your profile for personalized recommendations.',
        'ask_gender': '1/5. Enter your gender:',
        'ask_weight': '2/5. Enter your current weight (e.g., 75 kg):',
        'ask_height': '3/5. Enter your height in centimeters (e.g., 180 cm):',
        'ask_activity': '4/5. Enter your physical activity level (Low - sedentary, High - daily training):',
        'ask_goal': '5/5. What is your main goal:',
        'invalid_number': 'Please enter only a number (e.g., 75).',
        'invalid_height': 'Please enter a realistic height in centimeters (e.g., between 100 and 250).',
        'profile_saved': '✅ Your profile is saved. Now send a photo of your food for analysis and personalized recommendations!',
        'profile_canceled': 'Profile setup cancelled.',
        'no_profile': 'To receive personalized recommendations, please first set up your profile using the /profile command.',
        'processing': '...Analyzing photo and compiling personalized recommendations...',
        'crit_error': 'Critical error: Gemini service is unavailable. Check your API key.',
        'api_error': '❌ Gemini API error. Probably an incorrect key or quota issue. Details: ',
        'unknown_error': 'An unexpected error occurred. Please try again. Details for the developer: ',
        'analysis_header': '<b>✅ Analysis and personalized recommendations:</b>\n\n'
    }
}

# ----------------------------------------
# 3. Состояния для ConversationHandler (Язык и Профиль)
# ----------------------------------------

# Состояние для выбора языка
SELECTING_LANGUAGE = 0
# Состояния для профиля
GENDER, WEIGHT, HEIGHT, ACTIVITY, GOAL = range(1, 6) 
USER_PROFILE_KEY = 'profile'
USER_LANG_KEY = 'language'

# ----------------------------------------
# 4. Функции помощники
# ----------------------------------------

async def get_text(context, key):
    """Получает сообщение на установленном языке."""
    lang = context.user_data.get(USER_LANG_KEY, 'ru')
    return MESSAGES.get(lang, MESSAGES['ru']).get(key, MESSAGES['ru'][key])

async def select_language_start(update: Update, context) -> int:
    """Запускает диалог выбора языка (ENTRY POINT)."""
    reply_keyboard = [['Русский', 'Oʻzbekcha', 'English']]
    
    await update.message.reply_text(
        MESSAGES['ru']['select_lang'], 
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    # Возвращаем состояние для обработки выбора языка
    return SELECTING_LANGUAGE

async def set_language(update: Update, context) -> int:
    """Сохраняет выбранный язык и приветствует пользователя."""
    choice = update.message.text
    if choice == 'Русский':
        context.user_data[USER_LANG_KEY] = 'ru'
    elif choice == 'Oʻzbekcha':
        context.user_data[USER_LANG_KEY] = 'uz'
    elif choice == 'English':
        context.user_data[USER_LANG_KEY] = 'en'
    else:
        # Если прислали что-то другое, повторяем запрос
        return SELECTING_LANGUAGE 

    # Отправляем сообщение на установленном языке
    await update.message.reply_text(
        await get_text(context, 'lang_set'),
        reply_markup=ReplyKeyboardRemove(),
    )
    # Завершаем conversation handler
    return ConversationHandler.END


# ----------------------------------------
# 5. Функции обработчики команд и профиля (Многоязычные)
# ----------------------------------------

async def start_command_handler(update: Update, context) -> int:
    """
    Обрабатывает команду /start.
    Если язык не установлен, переводит в режим выбора языка.
    Если установлен, выводит приветствие и завершает conversation.
    """
    if USER_LANG_KEY not in context.user_data:
        # Если язык не установлен, начинаем выбор языка
        return await select_language_start(update, context)
    else:
        # Если язык установлен, просто выводим приветствие
        await update.message.reply_text(
            await get_text(context, 'start_welcome'),
            parse_mode='HTML'
        )
        return ConversationHandler.END


async def profile_start(update: Update, context) -> int:
    """Начинает диалог настройки профиля, спрашивает пол."""
    if USER_LANG_KEY not in context.user_data:
        # Если язык не установлен, просим сначала выбрать язык
        await update.message.reply_text(MESSAGES['ru']['select_lang'])
        return ConversationHandler.END
        
    reply_keyboard = [['Мужчина', 'Женщина']]
    await update.message.reply_text(
        await get_text(context, 'profile_start') + '\n' + await get_text(context, 'ask_gender'),
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Выберите пол"
        ),
    )
    return GENDER

async def profile_gender(update: Update, context) -> int:
    """Сохраняет пол, спрашивает вес."""
    gender = update.message.text
    context.user_data[USER_PROFILE_KEY] = {'gender': gender}
    await update.message.reply_text(
        await get_text(context, 'ask_weight'),
        reply_markup=ReplyKeyboardRemove(),
    )
    return WEIGHT

async def profile_weight(update: Update, context) -> int:
    """Сохраняет вес, спрашивает рост."""
    try:
        weight = float(update.message.text.split()[0].replace(',', '.'))
        context.user_data[USER_PROFILE_KEY]['weight'] = weight
    except ValueError:
        await update.message.reply_text(await get_text(context, 'invalid_number'))
        return WEIGHT
    
    await update.message.reply_text(
        await get_text(context, 'ask_height'),
        reply_markup=ReplyKeyboardRemove(),
    )
    return HEIGHT

async def profile_height(update: Update, context) -> int:
    """Сохраняет рост, спрашивает уровень активности."""
    try:
        height = float(update.message.text.split()[0].replace(',', '.'))
        if height < 50 or height > 300:
             await update.message.reply_text(await get_text(context, 'invalid_height'))
             return HEIGHT
             
        context.user_data[USER_PROFILE_KEY]['height'] = height
    except ValueError:
        await update.message.reply_text(await get_text(context, 'invalid_number'))
        return HEIGHT
    
    reply_keyboard = [['Низкий', 'Средний', 'Высокий']]
    await update.message.reply_text(
        await get_text(context, 'ask_activity'),
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Выберите уровень"
        ),
    )
    return ACTIVITY

async def profile_activity(update: Update, context) -> int:
    """Сохраняет активность, спрашивает цель."""
    activity = update.message.text
    context.user_data[USER_PROFILE_KEY]['activity'] = activity
    
    reply_keyboard = [['Сброс веса (сушка)', 'Набор массы (рост мышц)', 'Поддержание веса']]
    await update.message.reply_text(
        await get_text(context, 'ask_goal'),
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Выберите цель"
        ),
    )
    return GOAL

async def profile_goal(update: Update, context) -> int:
    """Сохраняет цель и завершает диалог."""
    goal = update.message.text
    context.user_data[USER_PROFILE_KEY]['goal'] = goal
    
    profile_data = context.user_data[USER_PROFILE_KEY]
    
    await update.message.reply_text(
        f"{await get_text(context, 'profile_saved')}\n\n"
        f"Пол: {profile_data['gender']}\n"
        f"Вес: {profile_data['weight']} кг\n"
        f"Рост: {profile_data['height']} см\n"
        f"Активность: {profile_data['activity']}\n"
        f"Цель: {profile_data['goal']}\n",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END

async def profile_cancel(update: Update, context) -> int:
    """Отменяет диалог настройки профиля."""
    await update.message.reply_text(
        await get_text(context, 'profile_canceled'), reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# ----------------------------------------
# 6. Функция обработки фото
# ----------------------------------------

async def handle_photo(update: Update, context) -> None:
    """Обрабатывает входящую фотографию, включает персонализированные рекомендации."""
    if not gemini_client:
        await update.message.reply_text(await get_text(context, 'crit_error'))
        return

    # Если язык не выбран, просим его выбрать
    if USER_LANG_KEY not in context.user_data:
        await update.message.reply_text(MESSAGES['ru']['select_lang'])
        return

    profile_data = context.user_data.get(USER_PROFILE_KEY)
    lang_code = context.user_data.get(USER_LANG_KEY, 'ru')
    
    # 1. Формирование контекста пользователя
    if not profile_data:
        await update.message.reply_text(await get_text(context, 'no_profile'))
        return

    user_context = (
        f"УЧТИТЕ ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ для рекомендаций:\n"
        f"Пол: {profile_data['gender']}, "
        f"Вес: {profile_data['weight']} кг, "
        f"Рост: {profile_data['height']} см, "
        f"Активность: {profile_data['activity']}, "
        f"Цель: {profile_data['goal']}. "
        f"Добавьте раздел '5. Рекомендации на день', исходя из этой цели, и составьте простой план питания на оставшийся день. "
        f"Ответ форматируйте на {lang_code} языке."
    )

    processing_message = await update.message.reply_text(await get_text(context, 'processing'))

    try:
        photo_file = await update.message.photo[-1].get_file()
        buffer = BytesIO()
        await photo_file.download_to_memory(buffer)
        buffer.seek(0)
        image = Image.open(buffer)

        # 2. ПРОМПТ с рекомендациями и HTML-разметкой
        prompt = (
            f"{user_context}\n\n"
            "Сначала проанализируй изображение. Определи вид продукта или блюда, оцени "
            "примерный вес порции в граммах и посчитай общую калорийность (Ккал) и состав макронутриентов. "
            f"Отвечай только на {lang_code} языке. Ответ форматируй строго как список:\n"
            "1. Блюдо/Продукт: [Название]\n"
            "2. Оценка веса: [Число] г\n"
            "3. Калорийность: [Число] Ккал\n"
            "4. Состав макронутриентов:\n"
            "   - Белки: [Число] г\n"
            "   - Жиры: [Число] г\n"
            "   - Углеводы: [Число] г\n\n"
            "5. Рекомендации на день (с учетом цели): [Простой и легкий план питания на оставшийся день]. В начале этого ответа (до пункта 1) используй заголовок <b>✅ Анализ и персональные рекомендации:</b> и используй теги <b></b> для выделения текста жирным."
        )
        
        # Вызов API Gemini
        response = gemini_client.models.generate_content(
            model=gemini_model,
            contents=[prompt, image]
        )
        
        await update.message.reply_text(
            await get_text(context, 'analysis_header') + response.text,
            parse_mode='HTML'
        )

    except APIError as e:
        logger.error(f"Ошибка Gemini API: {e}")
        await update.message.reply_text(
            f"❌ {await get_text(context, 'api_error')} {e}", parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        await update.message.reply_text(
            f"{await get_text(context, 'unknown_error')} <b>{type(e).__name__}</b>: {e}",
            parse_mode='HTML'
        )
    finally:
        await processing_message.delete()


# ----------------------------------------
# 7. Основная функция запуска бота
# ----------------------------------------

def main() -> None:
    """Запускает бота."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Создаем ОТДЕЛЬНЫЙ обработчик для команды /language
    # Он должен прерывать любой ConversationHandler
    language_command_handler = ConversationHandler(
        entry_points=[CommandHandler('language', select_language_start)],
        states={
            SELECTING_LANGUAGE: [MessageHandler(filters.Text(['Русский', 'Oʻzbekcha', 'English']) & ~filters.COMMAND, set_language)],
        },
        fallbacks=[CommandHandler('cancel', profile_cancel)],
        # ВАЖНО: ConversationHandler по умолчанию имеет приоритет и отменяет текущий ConversationHandler
    )
    application.add_handler(language_command_handler)

    
    # Объединенный ConversationHandler для /start и /profile
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start_command_handler),
            CommandHandler('profile', profile_start)
        ],
        states={
            # ВНИМАНИЕ: SELECTING_LANGUAGE здесь больше не нужен,
            # так как он перенесен в отдельный language_command_handler.
            # Но если /start требует выбора языка, он переводит в это состояние.
            SELECTING_LANGUAGE: [MessageHandler(filters.Text(['Русский', 'Oʻzbekcha', 'English']) & ~filters.COMMAND, set_language)],
            
            # Состояния для настройки профиля
            GENDER: [MessageHandler(filters.Text(['Мужчина', 'Женщина']) & ~filters.COMMAND, profile_gender)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_weight)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_height)], 
            ACTIVITY: [MessageHandler(filters.Text(['Низкий', 'Средний', 'Высокий']) & ~filters.COMMAND, profile_activity)],
            GOAL: [MessageHandler(filters.Text(['Сброс веса (сушка)', 'Набор массы (рост мышц)', 'Поддержание веса']) & ~filters.COMMAND, profile_goal)],
        },
        fallbacks=[CommandHandler('cancel', profile_cancel)],
        allow_reentry=True 
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))

    # Запуск бота
    logger.info("Бот запущен. Ожидание сообщений...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
