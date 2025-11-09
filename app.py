import logging
import re
import os
import asyncio
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

app = Flask(__name__)

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.environ.get('BOT_TOKEN')
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')

# Mock данные для теста
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

# Глобальная переменная для бота
bot_application = None

def normalize_city(city: str) -> str:
    if not city:
        return ''
    city = city.lower().strip()
    city = re.sub(r'(в\s+|во\s+|г\.?\s*|город\s*|городе\s*|г\s*)', '', city)
    city = re.sub(r'[еыуя]$', '', city)
    return city.capitalize()

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

def setup_bot():
    """Настройка бота"""
    global bot_application
    if not TELEGRAM_TOKEN:
        logging.error("BOT_TOKEN not found")
        return None
    
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        bot_application = application
        logging.info("Bot setup completed successfully")
        return application
    except Exception as e:
        logging.error(f"Bot setup error: {e}")
        return None

# Инициализируем бота при старте
setup_bot()

@app.route('/')
def home():
    return "🚀 Бот куратор ВСП работает! Используйте /start в Telegram"

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """Endpoint для вебхука Telegram"""
    if request.method == 'GET':
        return jsonify({"status": "webhook is active"})
    
    if not bot_application:
        return jsonify({"error": "Bot not initialized"}), 500
    
    try:
        # Получаем обновление от Telegram
        update_data = request.get_json()
        logging.info(f"Received update: {update_data}")
        
        # Создаем объект Update
        update = Update.de_json(update_data, bot_application.bot)
        
        # Обрабатываем обновление асинхронно
        async def process_update():
            await bot_application.process_update(update)
        
        # Запускаем асинхронную обработку
        asyncio.run(process_update())
        
        return jsonify({"status": "ok"})
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/debug')
def debug():
    """Endpoint для отладки"""
    return jsonify({
        "bot_token_exists": bool(TELEGRAM_TOKEN),
        "bot_initialized": bool(bot_application),
        "status": "running"
    })

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Установка вебхука"""
    if not TELEGRAM_TOKEN:
        return jsonify({"error": "BOT_TOKEN not set"})
    
    try:
        # URL вашего приложения на Vercel
        webhook_url = f"https://{request.host}/webhook"
        
        async def set_webhook_async():
            application = Application.builder().token(TELEGRAM_TOKEN).build()
            await application.bot.set_webhook(webhook_url)
            return await application.bot.get_webhook_info()
        
        webhook_info = asyncio.run(set_webhook_async())
        return jsonify({
            "status": "webhook set",
            "webhook_info": webhook_info.to_dict(),
            "webhook_url": webhook_url
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
