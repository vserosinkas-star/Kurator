import os
import json
import re
import time
from flask import Flask, request, jsonify
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

app = Flask(__name__)
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Глобальная переменная для бота
bot_application = None

# Кэширование
data_cache = None
cache_timestamp = 0
CACHE_DURATION = 300  # 5 минут

# Mock данные как fallback
MOCK_DATA = {
    "8369/067": {
        "vsp": "8369/067", 
        "fio": "Гранкина Елена Михайловна",
        "contact": "8-5459-10-10",
        "mobile": "8-909-198-88-42",
        "city": "Аксарка"
    },
    "8369/068": {
        "vsp": "8369/068",
        "fio": "Гранкина Елена Михайловна", 
        "contact": "8-5459-10-10",
        "mobile": "8-909-198-88-42",
        "city": "Белоярск"
    },
    "8369/069": {
        "vsp": "8369/069",
        "fio": "Гранкина Елена Михайловна",
        "contact": "8-5459-10-10",
        "mobile": "8-909-198-88-42",
        "city": "Салехард"
    },
    "8369/070": {
        "vsp": "8369/070",
        "fio": "Гранкина Елена Михайловна",
        "contact": "8-5459-10-10",
        "mobile": "8-909-198-88-42",
        "city": "Лабытнанги"
    },
    "8369/071": {
        "vsp": "8369/071",
        "fio": "Гранкина Елена Михайловна",
        "contact": "8-5459-10-10",
        "mobile": "8-909-198-88-42",
        "city": "Харп"
    }
}

def get_data():
    """Получение данных с кэшированием"""
    global data_cache, cache_timestamp
    
    current_time = time.time()
    
    # Если кэш устарел или отсутствует, обновляем
    if data_cache is None or current_time - cache_timestamp > CACHE_DURATION:
        print("Updating data cache...")
        
        # Пытаемся загрузить из Google Sheets
        try:
            from gsheets import load_data_from_sheets
            sheets_data = load_data_from_sheets()
            if sheets_data:
                data_cache = sheets_data
                cache_timestamp = current_time
                print("Data loaded from Google Sheets")
                return data_cache
        except Exception as e:
            print(f"Error loading from Google Sheets: {e}")
        
        # Если Google Sheets не доступен, используем mock данные
        vsp_map = MOCK_DATA
        city_map = {}
        for record in MOCK_DATA.values():
            city = record['city']
            if city:
                if city not in city_map:
                    city_map[city] = []
                city_map[city].append(record)
        
        data_cache = (vsp_map, city_map)
        cache_timestamp = current_time
        print("Data loaded from MOCK_DATA (fallback)")
    
    return data_cache

def normalize_city(city: str) -> str:
    """Нормализация названия города для поиска"""
    if not city:
        return ''
    city = city.lower().strip()
    city = re.sub(r'(в\s+|во\s+|г\.?\s*|город\s*|городе\s*|г\s*)', '', city)
    city = re.sub(r'[еыуя]$', '', city)
    return city.capitalize()

def search_by_vsp(vsp_code):
    """Поиск по коду ВСП"""
    vsp_map, city_map = get_data()
    vsp_code = vsp_code.strip().upper().replace(' ', '')
    return vsp_map.get(vsp_code)

def search_by_city(city_name):
    """Поиск по городу"""
    vsp_map, city_map = get_data()
    norm_city = normalize_city(city_name)
    results = []
    
    for city, records in city_map.items():
        if normalize_city(city) == norm_city:
            results.extend(records)
    
    return results

def get_main_keyboard():
    """Клавиатура главного меню"""
    keyboard = [
        [KeyboardButton("🏢 Поиск по ВСП"), KeyboardButton("🏙️ Поиск по городу")],
        [KeyboardButton("📍 Популярные города"), KeyboardButton("❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cities_keyboard():
    """Клавиатура с популярными городами"""
    keyboard = [
        [KeyboardButton("Салехард"), KeyboardButton("Лабытнанги")],
        [KeyboardButton("Харп"), KeyboardButton("Аксарка")],
        [KeyboardButton("Белоярск"), KeyboardButton("↩️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_vsp_buttons(records):
    """Создание инлайн-кнопок для выбора ВСП"""
    keyboard = []
    for record in records:
        keyboard.append([InlineKeyboardButton(
            f"🏢 {record['vsp']} - {record['fio'].split()[0]}", 
            callback_data=f"vsp_{record['vsp']}"
        )])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = (
        "👋 Добро пожаловать в бот-куратор ВСП!\n\n"
        "Я помогу найти контакты кураторов.\n"
        "Выберите тип поиска:"
    )
    await update.message.reply_text(
        welcome_text, 
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды помощи"""
    help_text = (
        "🤖 *Помощь по боту-куратору ВСП*\n\n"
        "• *Поиск по ВСП* - найти по коду отделения\n"
        "• *Поиск по городу* - найти всех кураторов в городе\n"
        "• *Популярные города* - быстрый выбор городов\n\n"
        "Просто нажмите на кнопку ниже или введите код ВСП/город!"
    )
    await update.message.reply_text(
        help_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text.strip()
    
    if text == "🏢 Поиск по ВСП":
        await update.message.reply_text(
            "🔍 Введите код ВСП (например: *8369/069*):",
            parse_mode="Markdown"
        )
    
    elif text == "🏙️ Поиск по городу":
        await update.message.reply_text(
            "🏙️ Введите название города (например: *Салехард*):",
            parse_mode="Markdown"
        )
    
    elif text == "📍 Популярные города":
        await update.message.reply_text(
            "📍 Выберите город:",
            reply_markup=get_cities_keyboard()
        )
    
    elif text == "↩️ Назад":
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_keyboard()
        )
    
    elif text == "❓ Помощь":
        await help_command(update, context)
    
    else:
        # Автоматическое определение типа запроса
        vsp_match = re.search(r'\b(\d{4}/\d{2,5})\b', text)
        
        if vsp_match:
            # Поиск по ВСП
            vsp_code = vsp_match.group(1)
            record = search_by_vsp(vsp_code)
            
            if record:
                response_text = format_record_response(record, vsp_code)
            else:
                response_text = f"❌ ВСП *{vsp_code}* не найден."
            
            await update.message.reply_text(
                response_text,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        
        else:
            # Поиск по городу
            records = search_by_city(text)
            
            if not records:
                await update.message.reply_text(
                    f"❌ Не найдено кураторов по запросу *{text}*.\n\n"
                    "Попробуйте другой город или используйте кнопки ниже:",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
            
            elif len(records) == 1:
                record = records[0]
                response_text = format_record_response(record)
                await update.message.reply_text(
                    response_text,
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
            
            else:
                # Несколько кураторов - показываем кнопки для выбора
                city_name = records[0]['city']
                await update.message.reply_text(
                    f"📍 В городе *{city_name}* найдено *{len(records)}* кураторов:\n\n"
                    "Выберите ВСП:",
                    parse_mode="Markdown",
                    reply_markup=get_vsp_buttons(records)
                )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на инлайн-кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('vsp_'):
        vsp_code = query.data[4:]  # Убираем префикс 'vsp_'
        record = search_by_vsp(vsp_code)
        
        if record:
            response_text = format_record_response(record, vsp_code)
        else:
            response_text = f"❌ ВСП *{vsp_code}* не найден."
        
        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown"
        )

def format_record_response(record, vsp_code=None):
    """Форматирование ответа с информацией о кураторе"""
    if vsp_code is None:
        vsp_code = record['vsp']
    
    city_part = f" г. {record['city']}" if record['city'] else ''
    
    return (
        f"✅ *ВСП {vsp_code}{city_part}*\n\n"
        f"👤 *{record['fio']}*\n"
        f"📞 *Контакт:* {record['contact']}\n"
        f"📱 *Мобильный:* {record['mobile']}\n\n"
        f"🔄 Для нового поиска используйте кнопки ниже"
    )

def setup_bot():
    """Настройка бота"""
    global bot_application
    if not BOT_TOKEN:
        print("BOT_TOKEN not found")
        return None
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        bot_application = application
        print("Bot setup completed successfully")
        return application
    except Exception as e:
        print(f"Bot setup error: {e}")
        return None

# Инициализируем бота при старте
setup_bot()

# Flask endpoints
@app.route('/')
def home():
    return "🚀 Бот куратор ВСП работает! Используйте /start в Telegram"

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return jsonify({"status": "webhook is active"})
    
    if not bot_application:
        return jsonify({"error": "Bot not initialized"}), 500
    
    try:
        update_data = request.get_json()
        update = Update.de_json(update_data, bot_application.bot)
        
        # Обрабатываем обновление асинхронно
        import asyncio
        asyncio.run(bot_application.process_update(update))
        
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/debug')
def debug():
    vsp_map, city_map = get_data()
    return jsonify({
        "bot_token_exists": bool(BOT_TOKEN),
        "records_count": len(vsp_map),
        "cities_count": len(city_map),
        "cache_age_seconds": int(time.time() - cache_timestamp) if data_cache else None,
        "status": "running"
    })

@app.route('/refresh_cache')
def refresh_cache():
    """Принудительное обновление кэша"""
    global data_cache, cache_timestamp
    data_cache = None
    cache_timestamp = 0
    get_data()
    return jsonify({"status": "cache refreshed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
