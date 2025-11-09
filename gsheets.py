import os
import json
import gspread
from google.oauth2.service_account import Credentials
from flask import Flask

def init_gsheets():
    """Инициализация Google Sheets"""
    try:
        # Получаем credentials из переменной окружения
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
        if not credentials_json:
            print("GOOGLE_CREDENTIALS not found in environment variables")
            return None
            
        # Парсим JSON
        creds_dict = json.loads(credentials_json)
        
        # Настраиваем авторизацию
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        return client
    except Exception as e:
        print(f"Google Sheets init error: {e}")
        return None

def load_data_from_sheets():
    """Загрузка данных из Google Sheets с улучшенной обработкой ошибок"""
    try:
        client = init_gsheets()
        if not client:
            print("Failed to initialize Google Sheets client")
            return None
            
        SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
        if not SPREADSHEET_ID:
            print("SPREADSHEET_ID not found in environment variables")
            return None
        
        print(f"Attempting to open spreadsheet with ID: {SPREADSHEET_ID}")
        
        # Открываем таблицу
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.sheet1  # Первая вкладка
        
        # Получаем все данные
        data = sheet.get_all_records()
        print(f"Retrieved {len(data)} rows from Google Sheets")
        
        if not data:
            print("No data found in Google Sheets")
            return None
        
        # Преобразуем в нужный формат
        vsp_map = {}
        city_map = {}
        
        for i, row in enumerate(data):
            # Преобразуем row в словарь если это необходимо
            if hasattr(row, '_values'):
                # gspread возвращает объект Row
                values = row._values
                if len(values) < 5:
                    continue
                vsp, fio, contact, mobile, city = values[0], values[1], values[2], values[3], values[4]
            else:
                # Уже словарь
                vsp = row.get('Код ВСП') or row.get('vsp') or ''
                fio = row.get('ФИО') or row.get('fio') or ''
                contact = row.get('Контакт') or row.get('contact') or ''
                mobile = row.get('Мобильный') or row.get('mobile') or ''
                city = row.get('Город') or row.get('city') or ''
            
            # Очистка и проверка данных
            vsp = str(vsp).strip() if vsp else ''
            fio = str(fio).strip() if fio else ''
            
            if vsp and fio:
                record = {
                    'vsp': vsp,
                    'fio': fio,
                    'contact': str(contact).strip() if contact else '',
                    'mobile': str(mobile).strip() if mobile else '',
                    'city': str(city).strip() if city else ''
                }
                vsp_map[vsp] = record
                
                if city:
                    city = str(city).strip()
                    if city not in city_map:
                        city_map[city] = []
                    city_map[city].append(record)
        
        print(f"Successfully processed {len(vsp_map)} records from Google Sheets")
        return vsp_map, city_map
        
    except Exception as e:
        print(f"Error loading data from Google Sheets: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None
