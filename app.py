import os
import json
import re
import time
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Кэширование
data_cache = None
cache_timestamp = 0
CACHE_DURATION = 300  # 5 минут

# Mock данные как fallback
MOCK_DATA = {
    "8369/069": {
        "vsp": "8369/069", 
        "fio": "Иванов Иван Иванович",
        "contact": "телеграм @ivanov",
        "mobile": "+79991234567",
        "city": "Салехард"
    },
    "8370/070": {
        "vsp": "8370/070",
        "fio": "Петров Петр Петрович", 
        "contact": "телеграм @petrov",
        "mobile": "+79997654321",
        "city": "Москва"
    },
    "8371/071": {
        "vsp": "8371/071",
        "fio": "Сидоров Алексей Владимирович",
        "contact": "телеграм @sidorov",
        "mobile": "+79995554433",
        "city": "Новый Уренгой"
    },
    "8372/072": {
        "vsp": "8372/072",
        "fio": "Козлова Мария Сергеевна",
        "contact": "телеграм @kozlova",
        "mobile": "+79993332211",
        "city": "Салехард"
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

@app.route('/')
def home():
    return "🚀 Бот куратор ВСП работает! Используйте /start в Telegram"

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
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
                    "Отправьте:\n"
                    "• Код ВСП — например, `8369/069`\n"
                    "• Или город — например, `Салехард`\n\n"
                    "Я найду куратора и контакты!"
                )
            elif text == '/help':
                response_text = (
                    "🤖 **Помощь по боту-куратору ВСП**\n\n"
                    "Доступные команды:\n"
                    "• /start - начать работу\n"
                    "• /help - показать эту справку\n"
                    "• /stats - статистика базы данных\n\n"
                    "Просто отправьте код ВСП или название города!"
                )
            elif text == '/stats':
                vsp_map, city_map = get_data()
                cities_count = len(city_map)
                records_count = len(vsp_map)
                response_text = (
                    f"📊 **Статистика базы данных:**\n\n"
                    f"• Всего ВСП: {records_count}\n"
                    f"• Городов: {cities_count}\n"
                    f"• Источник: {'Google Sheets' if os.environ.get('GOOGLE_CREDENTIALS') else 'Mock данные'}"
                )
            else:
                # Поиск по ВСП
                vsp_match = re.search(r'\b(\d{4}/\d{3,4})\b', text)
                if vsp_match:
                    vsp_code = vsp_match.group(1)
                    record = search_by_vsp(vsp_code)
                    
                    if record:
                        city_part = f" г. {record['city']}" if record['city'] else ''
                        response_text = (
                            f"✅ **ВСП {vsp_code}{city_part}**\n\n"
                            f"👤 **{record['fio']}**\n"
                            f"📞 **Контакт:** {record['contact']}\n"
                            f"📱 **Мобильный:** {record['mobile']}"
                        )
                    else:
                        response_text = f"❌ ВСП **{vsp_code}** не найден."
                
                # Поиск по городу
                else:
                    records = search_by_city(text)
                    
                    if not records:
                        response_text = (
                            f"❌ Не найдено кураторов по запросу «{text}».\n\n"
                            "Попробуйте:\n"
                            "• *Салехард*\n"
                            "• *8369/069*"
                        )
                    elif len(records) == 1:
                        record = records[0]
                        response_text = (
                            f"✅ **ВСП {record['vsp']} г. {record['city']}**\n\n"
                            f"👤 **{record['fio']}**\n"
                            f"📞 **Контакт:** {record['contact']}\n"
                            f"📱 **Мобильный:** {record['mobile']}"
                        )
                    else:
                        vsp_list = ", ".join(f"`{r['vsp']}`" for r in records)
                        response_text = (
                            f"📌 В городе **{records[0]['city']}** найдено несколько кураторов.\n\n"
                            f"Пожалуйста, уточните **номер ВСП**:\n{vsp_list}"
                        )
            
            send_message(chat_id, response_text)
        
        return jsonify({"status": "ok"})
        
    except Exception as e:
        print(f"!!! ERROR: {str(e)}")
        import traceback
        print(f"!!! TRACEBACK: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

def send_message(chat_id, text):
    """Отправка сообщения через Telegram API"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")

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
    get_data()  # Обновляем кэш
    return jsonify({"status": "cache refreshed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)


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
                "sample_records": list(vsp_map.values())[:3]  # Первые 3 записи
            })
        else:
            return jsonify({"success": False, "error": "No data returned from Google Sheets"})
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e),
            "error_type": type(e).__name__
        })
