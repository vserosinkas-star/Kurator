import os
import json
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
BOT_TOKEN = os.environ.get('BOT_TOKEN')

@app.route('/')
def home():
    return "🚀 Бот куратор ВСП работает! Используйте /start в Telegram"

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return jsonify({"status": "webhook is active"})
    
    try:
        # Логируем входящий запрос
        print("=== INCOMING WEBHOOK ===")
        update = request.get_json()
        print(f"Update: {json.dumps(update, indent=2)}")
        
        # Проверяем структуру сообщения
        if 'message' in update:
            chat_id = update['message']['chat']['id']
            text = update['message'].get('text', '')
            
            print(f"Chat ID: {chat_id}, Text: {text}")
            
            if text == '/start':
                response_text = "👋 Привет! Я бот-куратор ВСП.\n\nОтправьте код ВСП (например: 8369/069) или название города."
            else:
                response_text = f"Вы сказали: {text}\n\nПопробуйте команду /start"
            
            # Отправляем ответ
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
        "status": "running"
    })

@app.route('/test')
def test():
    """Тестовый endpoint для проверки отправки сообщений"""
    try:
        # Отправляем тестовое сообщение себе (замените CHAT_ID на ваш)
        result = send_message(7826094158, "Тестовое сообщение от бота")
        return jsonify({"status": "sent", "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
