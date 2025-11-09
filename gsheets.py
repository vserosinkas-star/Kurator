import os
import json
import logging
import gspread
from google.oauth2.service_account import Credentials

# Настройка логирования
logger = logging.getLogger(__name__)

def init_gsheets():
    """Инициализация Google Sheets"""
    try:
        # Получаем credentials из переменной окружения
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
        if not credentials_json:
            logger.error("GOOGLE_CREDENTIALS not found in environment variables")
            return None
            
        # Парсим JSON
        creds_dict = json.loads(credentials_json)
        
        # Настраиваем авторизацию
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        return client
    except Exception as e:
        logger.error(f"Google Sheets init error: {e}")
        return None

def load_data_from_sheets():
    """Загрузка данных из Google Sheets"""
    try:
        client = init_gsheets()
        if not client:
            logger.error("Failed to initialize Google Sheets client")
            return None
            
        SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
        if not SPREADSHEET_ID:
            logger.error("SPREADSHEET_ID not found")
            return None
            
        logger.info(f"Opening spreadsheet with ID: {SPREADSHEET_ID}")
        
        # Открываем таблицу
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.sheet1
        
        # Получаем все данные
        data = sheet.get_all_records()
        logger.info(f"Retrieved {len(data)} rows from Google Sheets")
        
        if not data:
            logger.warning("No data found in Google Sheets")
            return None
        
        # Преобразуем в нужный формат
        vsp_map = {}
        city_map = {}
        
        for row in data:
            if len(row) >= 5:
                vsp = str(row[0]).strip() if row[0] else ''
                fio = str(row[1]).strip() if row[1] else ''
                contact = str(row[2]).strip() if row[2] else ''
                mobile = str(row[3]).strip() if row[3] else ''
                city = str(row[4]).strip() if row[4] else ''
                
                if vsp and fio:
                    record = {
                        'vsp': vsp,
                        'fio': fio,
                        'contact': contact,
                        'mobile': mobile,
                        'city': city
                    }
                    vsp_map[vsp] = record
                    
                    if city:
                        if city not in city_map:
                            city_map[city] = []
                        city_map[city].append(record)
        
        logger.info(f"Successfully processed {len(vsp_map)} records from Google Sheets")
        return vsp_map, city_map
        
    except Exception as e:
        logger.error(f"Error loading data from Google Sheets: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def normalize_vsp_code(vsp_raw):
    """Нормализация кода ВСП (дополнительная функция)"""
    if not vsp_raw:
        return ""
    
    # Удаляем символы валют и лишние пробелы
    vsp = vsp_raw.replace('$', '').replace(',', '.').strip()
    
    # Заменяем пробелы на слеши
    if ' ' in vsp:
        vsp = vsp.replace(' ', '/')
    
    return vsp

def normalize_phone(phone_raw):
    """Нормализация номера телефона (дополнительная функция)"""
    if not phone_raw:
        return ""
    
    # Удаляем все нецифровые символы кроме +
    import re
    phone = re.sub(r'[^\d+]', '', phone_raw)
    
    # Добавляем +7 если номер начинается с 9 и имеет 10 цифр
    if phone.startswith('9') and len(phone) == 10:
        phone = '+7' + phone
    elif phone.startswith('89') and len(phone) == 11:
        phone = '+7' + phone[1:]
    
    return phone
