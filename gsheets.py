import os
import json
import gspread
from google.oauth2.service_account import Credentials

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
            print("Failed to initialize Google Sheets client")
            return None
            
        SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
        if not SPREADSHEET_ID:
            print("SPREADSHEET_ID not found")
            return None
            
        print(f"Opening spreadsheet with ID: {SPREADSHEET_ID}")
        
        # Открываем таблицу
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.sheet1
        
        # Получаем все данные как сырые значения
        all_data = sheet.get_all_values()
        print(f"Raw data from Google Sheets: {len(all_data)} rows")
        
        if len(all_data) < 2:
            print("Not enough data in sheet")
            return None
        
        # Проверяем заголовки
        headers = all_data[0]
        print(f"Headers: {headers}")
        
        vsp_map = {}
        city_map = {}
        
        # Обрабатываем данные, начиная со второй строки
        for i, row in enumerate(all_data[1:], start=2):
            if len(row) < 5:
                print(f"Row {i} has less than 5 columns: {row}")
                continue
                
            # Извлекаем данные по позициям (так надежнее)
            vsp = str(row[0]).strip()  # Столбец A - ВСП
            fio = str(row[1]).strip()  # Столбец B - ФИО
            contact = str(row[2]).strip()  # Столбец C - Контакт
            mobile = str(row[3]).strip()  # Столбец D - Мобильный
            city = str(row[4]).strip()  # Столбец E - Город
            
            print(f"Processing row {i}: VSP={vsp}, FIO={fio}, City={city}")
            
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
        
        print(f"Successfully processed {len(vsp_map)} records from Google Sheets")
        return vsp_map, city_map
        
    except Exception as e:
        print(f"Error loading data from Google Sheets: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None
