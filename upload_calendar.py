import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
import time

# 1. 設定你的日曆 ID
CALENDAR_ID = '7f6dc359e22bf90a02f4d50aa04eb0a0ce2abd21b02359603f9f7bfdf886b4d0@group.calendar.google.com'

# 2. 驗證並建立 Google Calendar API 服務
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'credentials.json'

print("🌐 正在連線到 Google Calendar...")
try:
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)
    print("✅ 連線成功！")
except Exception as e:
    print(f"❌ 連線失敗：{e}")
    exit()

# 3. 讀取爬蟲產出的 CSV
try:
    df = pd.read_csv('investor_conferences_filtered.csv')
    print(f"📄 讀取到 {len(df)} 筆資料，準備進行檢查與上傳...")
except FileNotFoundError:
    print("❌ 找不到 CSV 檔案。")
    exit()

def check_event_exists(summary, start_date):
    """檢查日曆中是否已存在相同標題與日期的行程"""
    # 設定搜尋範圍為該日期的整天
    time_min = f"{start_date}T00:00:00Z"
    time_max = f"{start_date}T23:59:59Z"
    
    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        q=summary, # 使用關鍵字搜尋摘要
        singleEvents=True
    ).execute()
    
    events = events_result.get('items', [])
    return len(events) > 0

# 4. 逐筆檢查並新增
for index, row in df.iterrows():
    try:
        # 日期格式化邏輯
        tw_date = str(row['法說會日期']).strip()
        parts = tw_date.split('/')
        if len(parts) != 3: continue
            
        year_str = parts[0]
        if len(year_str) >= 7:
            gregorian_year = int(year_str[-4:])
        elif len(year_str) == 3:
            gregorian_year = int(year_str) + 1911
        else:
            gregorian_year = int(year_str)
        
        formatted_date = f"{gregorian_year}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
        
        summary = f"[法說會] {row['公司代號']} {row['公司名稱']}"
        
        # --- 🌟 關鍵修正：檢查重複 ---
        if check_event_exists(summary, formatted_date):
            print(f"⏩ 跳過已存在行程：{summary} ({formatted_date})")
            continue
        # ----------------------------

        time_str = str(row['時間']).strip() if pd.notna(row['時間']) else "09:00"
        start_time_str = f"{formatted_date}T{time_str}:00"
        
        start_dt = datetime.datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S")
        end_dt = start_dt + datetime.timedelta(hours=1)
        end_time_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

        event = {
            'summary': summary,
            'location': str(row['地點']) if pd.notna(row['地點']) else "無地點資訊",
            'description': f"相關說明：{str(row['說明'])}",
            'start': {'dateTime': start_time_str, 'timeZone': 'Asia/Taipei'},
            'end': {'dateTime': end_time_str, 'timeZone': 'Asia/Taipei'},
        }

        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"✨ 成功新增：{summary}")
        
        # 避免 API 呼叫過快
        time.sleep(0.5)
        
    except Exception as e:
        print(f"⚠️ 處理失敗：{row.get('公司名稱', '未知')}，錯誤：{e}")

print("🎉 日曆同步完成！")