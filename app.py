from flask import Flask, request, jsonify
import requests
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
BOT_TOKEN = os.environ.get('BOT_TOKEN')

@app.route('/')
def home():
    return "✅ Бот работает! Используйте /start в Telegram"

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    logger.info("Webhook called")
    
    if request.method == 'GET':
        return jsonify({"status": "webhook is active"})
    
    try:
        # Логируем входящий запрос
        update = request.get_json()
        logger.info(f"Received update: {update}")
        
        if 'message' in update:
            chat_id = update['message']['chat']['id']
            text = update['message'].get('text', '')
            logger.info(f"Processing message: {text} from chat: {chat_id}")
            
            if text == '/start':
                response_text = "👋 Привет! Я бот-куратор ВСП. Отправьте код ВСП (например: 8369/069)"
            else:
                response_text = f"Вы сказали: {text}"
            
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
        "status": "running"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
