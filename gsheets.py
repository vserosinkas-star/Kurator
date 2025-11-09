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
    """Загрузка данных из Google Sheets"""
    try:
        client = init_gsheets()
        if not client:
            return None
            
        SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
        if not SPREADSHEET_ID:
            print("SPREADSHEET_ID not found")
            return None
            
        # Открываем таблицу
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.sheet1  # Первая вкладка
        
        # Получаем все данные
        data = sheet.get_all_records()
        
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
        
        print(f"Loaded {len(vsp_map)} records from Google Sheets")
        return vsp_map, city_map
        
    except Exception as e:
        print(f"Error loading data from Google Sheets: {e}")
        return None