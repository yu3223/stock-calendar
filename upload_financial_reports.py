import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
import time
import os

# 1. 設定你的日曆 ID (請填入財報專用的日曆 ID)
CALENDAR_ID = 'b6385548f2de6f0a3babc863f286838a874544ee2e05e094a2ea7427870f919c@group.calendar.google.com'

# 2. 驗證並建立 Google Calendar API 服務
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'credentials.json'

print("正在連線到 Google Calendar...")
try:
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"錯誤：找不到 {SERVICE_ACCOUNT_FILE} 檔案。")
        exit()
        
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)
    print("連線成功！")
except Exception as e:
    print(f"連線失敗：{e}")
    exit()

# 3. 讀取財報公告 CSV
CSV_FILE = 'financial_reports.csv'
try:
    df = pd.read_csv(CSV_FILE)
    print(f"讀取到 {len(df)} 筆財報資料，準備進行檢查與上傳...")
except FileNotFoundError:
    print(f"錯誤：找不到 {CSV_FILE} 檔案。")
    exit()

def check_event_exists(summary, event_date):
    """檢查日曆中是否已存在相同標題與日期的行程 (全天事件精確修正版)"""
    # 針對全天事件的關鍵修正：將時區從 Z (UTC) 改為 +08:00 (台北)
    time_min = f"{event_date}T00:00:00+08:00"
    time_max = f"{event_date}T23:59:59+08:00"
    
    try:
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True
        ).execute()
        
        events = events_result.get('items', [])
        
        # 捨棄不穩定的模糊搜尋，改用 Python 進行 100% 精確字串比對
        for event in events:
            if event.get('summary') == summary:
                return True
        return False
        
    except Exception as e:
        print(f"檢查重複時發生錯誤: {e}")
        return False

# 4. 逐筆處理並新增
for index, row in df.iterrows():
    try:
        raw_date = str(row['日期']).strip()
        formatted_date = raw_date.replace('/', '-')
        
        summary = f"[財報] {row['代號']} {row['名稱']}"
        
        # --- 關鍵修正：檢查重複 (與法說會邏輯一致) ---
        if check_event_exists(summary, formatted_date):
            print(f"跳過已存在行程：{summary} ({formatted_date})")
            continue
        # ---------------------------------------------

        # 建立全天事件
        event = {
            'summary': summary,
            'description': f"公司代號：{row['代號']}\n預計財報公告日 (來源：MoneyDJ)",
            'start': {
                'date': formatted_date, 
                'timeZone': 'Asia/Taipei',
            },
            'end': {
                'date': formatted_date, 
                'timeZone': 'Asia/Taipei',
            },
        }

        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"成功新增：{summary} ({formatted_date})")
        
        time.sleep(0.5)
        
    except Exception as e:
        print(f"處理失敗：{row.get('名稱', '未知')}，錯誤：{e}")

print("財報行事曆同步完成！")