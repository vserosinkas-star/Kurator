from flask import Flask, request, jsonify
import requests
import os
import logging
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Mock данные
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
        logger.info(f"Received update: {update}")
        
        if 'message' in update:
            chat_id = update['message']['chat']['id']
            text = update['message'].get('text', '').strip()
            logger.info(f"Processing message: '{text}' from chat: {chat_id}")
            
            if text == '/start':
                response_text = (
                    "👋 Привет! Я бот-куратор ВСП.\n\n"
                    "Отправьте код ВСП (например: 8369/069) или название города."
                )
            else:
                # Поиск по коду ВСП
                vsp_match = re.search(r'\b(\d{4}/\d{2,5})\b', text)
                if vsp_match:
                    vsp_code = vsp_match.group(1)
                    logger.info(f"Searching for VSP: {vsp_code}")
                    
                    record = MOCK_DATA.get(vsp_code)
                    if record:
                        response_text = (
                            f"✅ ВСП {vsp_code} г. {record['city']}\n\n"
                            f"👤 {record['fio']}\n"
                            f"📞 Контакт: {record['contact']}\n"
                            f"📱 Мобильный: {record['mobile']}"
                        )
                    else:
                        response_text = f"❌ ВСП {vsp_code} не найден."
                
                # Поиск по городу
                else:
                    records = []
                    for record in MOCK_DATA.values():
                        if record['city'].lower() == text.lower():
                            records.append(record)
                    
                    if not records:
                        response_text = f"❌ Не найдено кураторов по запросу «{text}»."
                    elif len(records) == 1:
                        record = records[0]
                        response_text = (
                            f"✅ ВСП {record['vsp']} г. {record['city']}\n\n"
                            f"👤 {record['fio']}\n"
                            f"📞 Контакт: {record['contact']}\n"
                            f"📱 Мобильный: {record['mobile']}"
                        )
                    else:
                        vsp_list = ", ".join(record['vsp'] for record in records)
                        response_text = (
                            f"📍 В городе {records[0]['city']} найдено несколько кураторов.\n\n"
                            f"Пожалуйста, уточните номер ВСП:\n{vsp_list}"
                        )
            
            # Отправляем ответ
            success = send_telegram_message(chat_id, response_text)
            if success:
                logger.info("Message sent successfully")
            else:
                logger.error("Failed to send message")
        
        return jsonify({"status": "ok"})
        
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

def send_telegram_message(chat_id, text):
    """Отправка сообщения в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        response = requests.post(url, json=payload, timeout=10)
        logger.info(f"Telegram API response: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

@app.route('/debug')
def debug():
    return jsonify({
        "bot_token_exists": bool(BOT_TOKEN),
        "mock_data_records": len(MOCK_DATA),
        "status": "running"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
