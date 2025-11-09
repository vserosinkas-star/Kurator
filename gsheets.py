import os
import json
import gspread
from google.oauth2.service_account import Credentials

def init_gsheets():
    """Инициализация Google Sheets"""
    try:
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
        if not credentials_json:
            print("GOOGLE_CREDENTIALS not found in environment variables")
            return None
            
        creds_dict = json.loads(credentials_json)
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Google Sheets init error: {e}")
        return None

def load_data_from_sheets():
    """Загрузка данных из Google Sheets с улучшенной обработкой"""
    try:
        client = init_gsheets()
        if not client:
            return None
            
        SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
        if not SPREADSHEET_ID:
            print("SPREADSHEET_ID not found")
            return None
        
        print(f"Opening spreadsheet: {SPREADSHEET_ID}")
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.sheet1
        
        # Получаем все значения, включая заголовок
        all_values = sheet.get_all_values()
        
        if len(all_values) < 2:
            print("Not enough rows in the sheet")
            return None
        
        # Предполагаем, что первая строка - заголовок, а данные со второй
        headers = all_values[0]
        data_rows = all_values[1:]
        
        print(f"Headers: {headers}")
        print(f"Number of data rows: {len(data_rows)}")
        
        vsp_map = {}
        city_map = {}
        
        for i, row in enumerate(data_rows):
            # Пропускаем пустые строки
            if not row:
                continue
                
            # Ожидаем минимум 5 столбцов, если нет - заполняем пустыми строками
            while len(row) < 5:
                row.append('')
            
            # Берем данные по индексам (независимо от заголовков)
            vsp = row[0].strip() if len(row) > 0 else ''
            fio = row[1].strip() if len(row) > 1 else ''
            contact = row[2].strip() if len(row) > 2 else ''
            mobile = row[3].strip() if len(row) > 3 else ''
            city = row[4].strip() if len(row) > 4 else ''
            
            # Если код ВСП и ФИО не пустые, то добавляем запись
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
        
        print(f"Processed {len(vsp_map)} records")
        return vsp_map, city_map
        
    except Exception as e:
        print(f"Error loading data from Google Sheets: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None
