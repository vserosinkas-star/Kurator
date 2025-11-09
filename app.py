import logging
import re
import os
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

app = Flask(__name__)

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.environ.get('BOT_TOKEN')  # Исправлено!
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
RANGE_NAME = 'Data!A:E'

# Временно убираем Google Sheets для теста
# Будем использовать mock-данные
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
    }
}

def normalize_city(city: str) -> str:
    if not city:
        return ''
    city = city.lower().strip()
    city = re.sub(r'(в\s+|во\s+|г\.?\s*|город\s*|городе\s*|г\s*)', '', city)
    city = re.sub(r'[еыуя]$', '', city)
    return city.capitalize()

@app.route('/')
def home():
    return "🚀 Бот куратор ВСП работает! Используйте /start в Telegram"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint для вебхука Telegram"""
    try:
        update = Update.de_json(request.get_json(), None)
        # Здесь будет обработка сообщений
        return jsonify({"status": "ok"})
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/debug')
def debug():
    """Endpoint для отладки"""
    return {
        "bot_token_exists": bool(TELEGRAM_TOKEN),
        "spreadsheet_id_exists": bool(SPREADSHEET_ID),
        "status": "running"
    }

# Инициализация бота (будет использоваться при настройке вебхука)
def init_bot():
    if not TELEGRAM_TOKEN:
        logging.error("BOT_TOKEN not found in environment variables")
        return None
    
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Добавляем обработчики
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "👋 Привет! Я бот-куратор ВСП.\n\n"
                "Отправьте:\n"
                "• Код ВСП — например, `8369/069`\n"
                "• Или город — например, `Салехард`",
                parse_mode="Markdown"
            )
        
        async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            text = update.message.text.strip()
            
            # Поиск по ВСП
            vsp_match = re.search(r'\b(\d{4}/\d{4})\b', text)
            if vsp_match:
                vsp = vsp_match.group(1)
                record = MOCK_DATA.get(vsp)
                if record:
                    city_part = f" г. {record['city']}" if record['city'] else ''
                    response = (
                        f"✅ **ВСП {vsp}{city_part}**\n\n"
                        f"👤 **{record['fio']}**\n"
                        f"📞 **Контакт:** {record['contact']}\n"
                        f"📱 **Мобильный:** {record['mobile']}"
                    )
                else:
                    response = f"❌ ВСП **{vsp}** не найден."
                await update.message.reply_text(response, parse_mode="Markdown")
                return
            
            # Поиск по городу
            norm_query = normalize_city(text)
            records = []
            for record in MOCK_DATA.values():
                if normalize_city(record['city']) == norm_query:
                    records.append(record)
            
            if not records:
                await update.message.reply_text(
                    f"❌ Не найдено кураторов по запросу «{text}».",
                    parse_mode="Markdown"
                )
                return
            
            if len(records) == 1:
                r = records[0]
                response = (
                    f"✅ **ВСП {r['vsp']} г. {r['city']}**\n\n"
                    f"👤 **{r['fio']}**\n"
                    f"📞 **Контакт:** {r['contact']}\n"
                    f"📱 **Мобильный:** {r['mobile']}"
                )
            else:
                vsp_list = ", ".join(r['vsp'] for r in records)
                response = (
                    f"📌 В городе **{records[0]['city']}** найдено несколько кураторов.\n"
                    f"Доступные ВСП: {vsp_list}"
                )
            await update.message.reply_text(response, parse_mode="Markdown")
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        return application
    except Exception as e:
        logging.error(f"Bot initialization error: {e}")
        return None

# Инициализируем бота при запуске
bot_application = init_bot()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
