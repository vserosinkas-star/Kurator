import os
import logging
import re
import time
from flask import Flask, request, jsonify
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Кэширование данных
data_cache = None
cache_timestamp = 0
CACHE_DURATION = 300  # 5 минут

def get_data():
    """Получение данных с кэшированием"""
    global data_cache, cache_timestamp
    
    current_time = time.time()
    
    # Если кэш устарел или отсутствует, обновляем
    if data_cache is None or current_time - cache_timestamp > CACHE_DURATION:
        logger.info("Updating data cache...")
        
        # Пытаемся загрузить из Google Sheets
        try:
            from gsheets import load_data_from_sheets
            sheets_data = load_data_from_sheets()
            if sheets_data:
                data_cache = sheets_data
                cache_timestamp = current_time
                logger.info(f"Data loaded from Google Sheets: {len(data_cache[0])} records")
                return data_cache
        except Exception as e:
            logger.error(f"Error loading from Google Sheets: {e}")
        
        # Если Google Sheets не доступен, используем mock данные
        from gsheets import MOCK_DATA
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
        logger.info("Data loaded from MOCK_DATA (fallback)")
    
    return data_cache

def get_main_keyboard():
    """Клавиатура главного меню"""
    return {
        "keyboard": [
            [{"text": "🏢 Поиск по ВСП"}, {"text": "🏙️ Поиск по городу"}],
            [{"text": "📍 Популярные города"}, {"text": "📊 Статистика"}],
            [{"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def get_cities_keyboard():
    """Клавиатура с популярными городами"""
    # Список конкретных городов, которые мы хотим показывать
    TARGET_CITIES = [
        "Екатеринбург", 
        "Уфа", 
        "Челябинск", 
        "Курган"
    ]
    
    # Получаем актуальные данные
    vsp_map, city_map = get_data()
    
    # Фильтруем города - оставляем только те, которые есть в данных
    available_cities = [city for city in TARGET_CITIES if city in city_map]
    
    # Если в данных нет наших целевых городов, берем первые 6 из доступных
    if not available_cities:
        available_cities = list(city_map.keys())[:6]
    
    # Создаем клавиатуру с городами (по 2 города в ряду)
    keyboard = []
    row = []
    for i, city in enumerate(available_cities):
        row.append({"text": city})
        if len(row) == 2 or i == len(available_cities) - 1:
            keyboard.append(row)
            row = []
    
    # Добавляем кнопку "Назад"
    keyboard.append([{"text": "↩️ Назад"}]),
    
    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

@app.route('/')
def home():
    return "✅ Бот куратор ВСП работает! Используйте /start в Telegram"

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    logger.info("Webhook called")
    
    if request.method == 'GET':
        return jsonify({"status": "webhook is active"})
    
    try:
        update = request.get_json()
        
        if 'message' in update:
            chat_id = update['message']['chat']['id']
            text = update['message'].get('text', '').strip()
            
            if text == '/start':
                response_text = (
                    "👋 Привет! Я бот-куратор ВСП.\n\n"
                    "Выберите тип поиска:"
                )
                keyboard = get_main_keyboard()
                send_telegram_message(chat_id, response_text, keyboard)
            
            elif text == "🏢 Поиск по ВСП":
                response_text = "🔍 Введите код ВСП (например: 8369/069):"
                send_telegram_message(chat_id, response_text)
            
            elif text == "🏙️ Поиск по городу":
                response_text = "🏙️ Введите название города (например: Салехард):"
                send_telegram_message(chat_id, response_text)
            
            elif text == "📍 Популярные города":
                response_text = "📍 Выберите город:"
                keyboard = get_cities_keyboard()
                send_telegram_message(chat_id, response_text, keyboard)
            
            elif text == "↩️ Назад":
                response_text = "Главное меню:"
                keyboard = get_main_keyboard()
                send_telegram_message(chat_id, response_text, keyboard)
            
            elif text == "❓ Помощь":
                response_text = (
                    "🤖 Помощь по боту-куратору ВСП\n\n"
                    "• Поиск по ВСП - найти по коду отделения\n"
                    "• Поиск по городу - найти всех кураторов в городе\n"
                    "• Популярные города - быстрый выбор городов\n"
                    "• Статистика - информация о базе данных\n\n"
                    "Просто нажмите на кнопку ниже или введите код ВСП/город!"
                )
                keyboard = get_main_keyboard()
                send_telegram_message(chat_id, response_text, keyboard)
            
            elif text == "📊 Статистика":
                vsp_map, city_map = get_data()
                stats_text = (
                    f"📊 Статистика базы данных\n\n"
                    f"• Всего ВСП: {len(vsp_map)}\n"
                    f"• Городов: {len(city_map)}\n"
                    f"• Обновлено: {time.strftime('%H:%M:%S')}\n\n"
                    
                )
                keyboard = get_main_keyboard()
                send_telegram_message(chat_id, stats_text, keyboard)
            
            else:
                vsp_map, city_map = get_data()
                
                # Поиск по коду ВСП
                vsp_match = re.search(r'\b(\d{4}/\d{2,5})\b', text)
                if vsp_match:
                    vsp_code = vsp_match.group(1)
                    logger.info(f"Searching for VSP: {vsp_code}")
                    
                    record = vsp_map.get(vsp_code)
                    if record:
                        response_text = (
                            f"✅ ВСП {vsp_code} г. {record['city']}\n\n"
                            f"👤 {record['fio']}\n"
                            f"📞 Контакт: {record['contact']}\n"
                           
                            f"🔄 Для нового поиска используйте кнопки ниже"
                        )
                    else:
                        response_text = f"❌ ВСП {vsp_code} не найден."
                    
                    keyboard = get_main_keyboard()
                    send_telegram_message(chat_id, response_text, keyboard)
                
                # Поиск по городу
                else:
                    records = city_map.get(text, [])
                    
                    if not records:
                        response_text = (
                            f"❌ Не найдено кураторов по запросу «{text}».\n\n"
                            "Попробуйте другой город или используйте кнопки ниже:"
                        )
                        keyboard = get_main_keyboard()
                        send_telegram_message(chat_id, response_text, keyboard)
                    elif len(records) == 1:
                        record = records[0]
                        response_text = (
                            f"✅ ВСП {record['vsp']} г. {record['city']}\n\n"
                            f"👤 {record['fio']}\n"
                            f"📞 Контакт: {record['contact']}\n"
                            
                            f"🔄 Для нового поиска используйте кнопки ниже"
                        )
                        keyboard = get_main_keyboard()
                        send_telegram_message(chat_id, response_text, keyboard)
                    else:
                        vsp_list = ", ".join(record['vsp'] for record in records)
                        response_text = (
                            f"📍 В городе {text} найдено {len(records)} ВСП.\n\n"
                            f"Пожалуйста, уточните номер ВСП:\n{vsp_list}"
                        )
                        keyboard = get_main_keyboard()
                        send_telegram_message(chat_id, response_text, keyboard)
        
        return jsonify({"status": "ok"})
        
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

def send_telegram_message(chat_id, text, reply_markup=None):
    """Отправка сообщения в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        response = requests.post(url, json=payload, timeout=10)
        logger.info(f"Telegram API response: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Telegram API error: {response.text}")
            
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

@app.route('/debug')
def debug():
    vsp_map, city_map = get_data()
    return jsonify({
        "bot_token_exists": bool(BOT_TOKEN),
        "google_credentials_exists": bool(os.environ.get('GOOGLE_CREDENTIALS')),
        "spreadsheet_id_exists": bool(os.environ.get('SPREADSHEET_ID')),
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

@app.route('/test_gsheets')
def test_gsheets():
    """Тестовый endpoint для проверки Google Sheets"""
    try:
        from gsheets import load_data_from_sheets
        result = load_data_from_sheets()
        
        if result:
            vsp_map, city_map = result
            return jsonify({
                "success": True,
                "records_loaded": len(vsp_map),
                "cities_loaded": len(city_map),
                "sample_records": list(vsp_map.values())[:3] if vsp_map else []
            })
        else:
            return jsonify({"success": False, "error": "No data returned from Google Sheets"})
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e),
            "error_type": type(e).__name__
        })

@app.route('/test_connection')
def test_connection():
    """Тест подключения к Google Sheets"""
    try:
        from gsheets import test_connection as gs_test
        result = gs_test()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/raw_data')
def raw_data():
    """Получение сырых данных из Google Sheets"""
    try:
        from gsheets import init_gsheets
        client = init_gsheets()
        if not client:
            return jsonify({"success": False, "error": "Failed to initialize client"})
            
        SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.sheet1
        
        # Получаем сырые данные
        all_values = sheet.get_all_values()
        
        return jsonify({
            "success": True,
            "row_count": len(all_values),
            "headers": all_values[0] if all_values else [],
            "first_rows": all_values[1:6] if len(all_values) > 1 else []  # первые 5 строк данных
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
