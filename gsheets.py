import os
import json
import logging
import gspread
from google.oauth2.service_account import Credentials

# Настройка логирования
logger = logging.getLogger(__name__)

# Mock данные для fallback
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
                # Предполагаем структуру столбцов: ВСП, ФИО, Контакт, Мобильный, Город
                vsp = str(row[0]).strip() if row[0] else ''
                fio = str(row[1]).strip() if row[1] else ''
                contact = str(row[2]).strip() if row[2] else ''
                mobile = str(row[3]).strip() if row[3] else ''
                city = str(row[4]).strip() if row[4] else ''
                
                # Нормализуем код ВСП
                vsp = normalize_vsp_code(vsp)
                
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
        return None

def normalize_vsp_code(vsp_raw):
    """Нормализация кода ВСП"""
    if not vsp_raw:
        return ""
    
    # Удаляем лишние пробелы и приводим к верхнему регистру
    vsp = vsp_raw.strip().upper()
    
    # Заменяем различные разделители на стандартный слеш
    vsp = vsp.replace(' ', '/').replace('\\', '/').replace('|', '/')
    
    return vsp
