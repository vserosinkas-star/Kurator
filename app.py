import os
import json
import re
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Mock данные для теста (расширенный набор)
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

def normalize_city(city: str) -> str:
    """Нормализация названия города для поиска"""
    if not city:
        return ''
    city = city.lower().strip()
    # Удаляем префиксы и окончания
    city = re.sub(r'(в\s+|во\s+|г\.?\s*|город\s*|городе\s*|г\s*)', '', city)
    city = re.sub(r'[еыуя]$', '', city)
    return city.capitalize()

def search_by_vsp(vsp_code):
    """Поиск по коду ВСП"""
    return MOCK_DATA.get(vsp_code)

def search_by_city(city_name):
    """Поиск по городу"""
    norm_city = normalize_city(city_name)
    results = []
    
    for record in MOCK_DATA.values():
        if normalize_city(record['city']) == norm_city:
            results.append(record)
    
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
        print(f"Update: {json.dumps(update, indent=2)}")
        
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
            else:
                # Поиск по ВСП (формат XXXX/XXXX)
                vsp_match = re.search(r'\b(\d{4}/\d{4})\b', text)
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
        print(f"Telegram API response: {response.status_code}")
        if response.status_code != 200:
            print(f"Telegram API error: {response.text}")
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")

@app.route('/debug')
def debug():
    return jsonify({
        "bot_token_exists": bool(BOT_TOKEN),
        "mock_records_count": len(MOCK_DATA),
        "status": "running"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
