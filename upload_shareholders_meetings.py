import os
import pandas as pd
import time
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- 設定區塊 ---
CSV_FILENAME = "shareholders_meetings_test.csv"
WHITELIST_FILENAME = "whitelist.txt"
CALENDAR_ID = "2ae554dfe64c53aed35ac7aae9dc5fa464be38b73b77ea8bb4d4a8a399b6af65@group.calendar.google.com"

# 請準備好從 Google Cloud Console 下載的服務帳戶金鑰檔案，並將檔名與路徑更新於此
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'credentials.json'

def load_whitelist(filepath):
    """讀取 whitelist.txt 並回傳清單"""
    if not os.path.exists(filepath):
        print(f"錯誤：找不到白名單檔案 {filepath}")
        return []
    
    with open(filepath, "r", encoding="utf-8") as f:
        # 讀取每一行，去除換行符號與空白，並過濾掉空行
        return [line.strip() for line in f if line.strip()]

def filter_data(csv_filename, whitelist):
    """讀取 CSV 並依照白名單篩選資料"""
    if not os.path.exists(csv_filename):
        print(f"錯誤：找不到資料檔案 {csv_filename}")
        return []

    try:
        df = pd.read_csv(csv_filename, dtype={"代碼": str})
    except Exception as e:
        print(f"讀取 CSV 時發生錯誤: {e}")
        return []

    filtered_df = df[df['代碼'].isin(whitelist)]
    upload_data = filtered_df.to_dict('records')
    
    print("-" * 40)
    print(f"資料總數：{len(df)} 筆 | 白名單篩選後：{len(upload_data)} 筆符合條件")
    print("-" * 40)
    
    return upload_data

def check_event_exists(service, summary, event_date_str):
    """檢查日曆中是否已存在相同標題的行程 (避免重複新增)"""
    # 建立當天 00:00 到 23:59 的搜尋範圍，加上台北時區 (+08:00)
    time_min = f"{event_date_str}T00:00:00+08:00"
    time_max = f"{event_date_str}T23:59:59+08:00"
    
    try:
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True
        ).execute()
        
        events = events_result.get('items', [])
        
        # 精確比對標題，如果已經有一模一樣的行程就回傳 True
        for event in events:
            if event.get('summary') == summary:
                return True
        return False
        
    except Exception as e:
        print(f"檢查重複時發生錯誤: {e}")
        return False

def upload_to_google_calendar(events_data):
    """將資料上傳至 Google 日曆"""
    if not events_data:
        print("沒有需要上傳的資料。")
        return

    # 1. 建立 Google Calendar API 連線
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build("calendar", "v3", credentials=creds)
        print("Google Calendar API 認證成功！")
    except Exception as e:
        print(f"認證失敗，請檢查 {SERVICE_ACCOUNT_FILE} 是否存在且設定正確。錯誤: {e}")
        return

    # 2. 逐筆上傳資料
    for event in events_data:
        try:
            # 整理時間格式 (將 2026/06/17 轉換為 2026-06-17)
            date_str = str(event["日期"]).replace("/", "-")
            time_str = event["時間"]
            
            # 防呆：如果網頁沒提供時間，預設設定為早上 9 點
            if pd.isna(time_str) or not str(time_str).strip():
                time_str = "09:00"

            # 統一設定行程標題
            summary = f"{event['股票名稱']} ({event['代碼']}) 股東會"
            
            # --- 核心防重複機制 ---
            if check_event_exists(service, summary, date_str):
                print(f"跳過已存在行程：{summary} ({date_str})")
                continue
            # ----------------------

            start_dt_str = f"{date_str}T{time_str}:00"
            start_dt = datetime.strptime(start_dt_str, "%Y-%m-%dT%H:%M:%S")
            
            # 假設股東會時間為 1 小時，計算結束時間
            end_dt = start_dt + timedelta(hours=1)

            # 準備打入 API 的事件內容格式 (包含公司名稱與代碼)
            event_body = {
                "summary": summary,
                "location": str(event["地點"]),
                "start": {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": "Asia/Taipei",
                },
                "end": {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": "Asia/Taipei",
                },
            }

            # 呼叫 API 寫入日曆
            created_event = service.events().insert(
                calendarId=CALENDAR_ID, body=event_body
            ).execute()
            
            print(f"成功新增: {summary} ({date_str} {time_str})")
            
            # 加上短暫休眠，避免連續寫入過快觸發 API 限制
            time.sleep(0.5)

        except Exception as e:
            print(f"處理 {event.get('股票名稱')} 時發生錯誤: {e}")

if __name__ == "__main__":
    print("啟動上傳程序...")
    
    # 步驟 1：載入白名單
    my_whitelist = load_whitelist(WHITELIST_FILENAME)
    if not my_whitelist:
        print("白名單為空或讀取失敗，程式結束。")
        exit()
    print(f"成功載入 {len(my_whitelist)} 筆白名單。")
    
    # 步驟 2：篩選資料
    ready_to_upload_data = filter_data(CSV_FILENAME, my_whitelist)
    
    # 步驟 3：上傳至日曆
    upload_to_google_calendar(ready_to_upload_data)
    
    print("行事曆同步完成！")