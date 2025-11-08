import os
import json
import logging
import re
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# === ЗАГРУЗКА КОНФИГУРАЦИИ ===
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
RANGE_NAME = "Data!A:E"

# Создаём credentials.json из переменной окружения
creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if creds_json:
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    sheets_service = build("sheets", "v4", credentials=creds)
else:
    raise ValueError("GOOGLE_CREDENTIALS_JSON не задан")

app = Flask(__name__)

# Загрузка данных из Google Таблицы
def load_data():
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME
    ).execute()
    values = result.get("values", [])
    vsp_map = {}
    city_map = {}

    for row in values[1:]:
        if len(row) >= 5:
            vsp = row[0].strip()
            fio = row[1].strip()
            contact = row[2].strip()
            mobile = row[3].strip()
            city = row[4].strip()
            if not vsp or not fio:
                continue
            record = {"vsp": vsp, "fio": fio, "contact": contact, "mobile": mobile, "city": city}
            vsp_map[vsp] = record
            if city:
                city_map.setdefault(city, []).append(record)
    return vsp_map, city_map

def normalize_city(city: str) -> str:
    if not city:
        return ""
    city = city.lower().strip()
    city = re.sub(r"(в\s+|во\s+|г\.?\s*|город\s*|городе\s*|г\s*)", "", city)
    city = re.sub(r"[еыуя]$", "", city)
    return city.capitalize()

# Логика бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот-куратор ВСП.\n\n"
        "Отправьте:\n"
        "• Код ВСП — например, `8647/06001`\n"
        "• Или город — например, `Салехард`\n\n"
        "Я найду куратора и контакты!",
        parse_mode="Markdown",
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vsp_map, city_map = load_data()
    text = update.message.text.strip()

    # Поддержка ВСП: 4/4 или 4/5 (например, 8647/06001)
    vsp_match = re.search(r"\b(\d{4}/\d{4,5})\b", text)
    if vsp_match:
        vsp = vsp_match.group(1)
        record = vsp_map.get(vsp)
        if record:
            city_part = f" г. {record['city']}" if record["city"] else ""
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
    records = city_map.get(norm_query) or next(
        (v for k, v in city_map.items() if normalize_city(k) == norm_query), None
    )

    if not records:
        await update.message.reply_text(
            f"❌ Не найдено кураторов по запросу «{text}».\n"
            "Попробуйте: *Салехард*, *8647/06001*",
            parse_mode="Markdown",
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
        vsp_list = ", ".join(r["vsp"] for r in records)
        response = (
            f"📌 В городе **{records[0]['city']}** найдено несколько кураторов.\n"
            f"Пожалуйста, уточните **номер ВСП** (например, `{records[0]['vsp']}`).\n\n"
            f"Доступные ВСП: {vsp_list}"
        )
    await update.message.reply_text(response, parse_mode="Markdown")

# Инициализация Telegram-приложения
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook endpoint для Vercel
@app.route("/api/webhook", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        telegram_app.update_queue.put(update)
        return jsonify({"status": "ok"})
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

# Health-check
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# Обязательно: запуск приложения в режиме production
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))