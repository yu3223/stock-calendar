import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import time
import os

# ==========================================
# 1. 設定區
# ==========================================
# 股東會專用的日曆 ID
CALENDAR_ID = 'bc5ec611babb02ea0f0f27a5e40796a5c427669472b01cf91bf6bb53ce0790ed@group.calendar.google.com' 

SERVICE_ACCOUNT_FILE = 'credentials.json'
CSV_FILE = 'shareholders_meetings_test.csv'
WHITELIST_FILE = 'whitelist.txt'

# ==========================================
# 2. 輔助函式 (股東會專屬邏輯)
# ==========================================
def load_whitelist(filepath):
    """讀取 txt 檔案並回傳股票代號列表"""
    if not os.path.exists(filepath):
        print(f"⚠️ 找不到白名單檔案：{filepath}，請確認檔案與程式在同一資料夾！")
        return []
    with open(filepath, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file if line.strip()]

def convert_roc_to_gregorian(roc_date_str):
    """民國年轉西元年 (115/06/30 -> 2026-06-30)"""
    try:
        parts = str(roc_date_str).strip().split('/')
        if len(parts) == 3:
            year = int(parts[0]) + 1911
            month = parts[1].zfill(2)
            day = parts[2].zfill(2)
            return f"{year}-{month}-{day}"
    except Exception as e:
        print(f"日期轉換失敗: {roc_date_str} - {e}")
    return None

# ==========================================
# 3. 驗證並建立 Google Calendar API 服務
# ==========================================
print("正在連線到 Google Calendar...")
try:
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"錯誤：找不到 {SERVICE_ACCOUNT_FILE} 檔案。")
        exit()
        
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/calendar'])
    service = build('calendar', 'v3', credentials=creds)
    print("連線成功！")
except Exception as e:
    print(f"連線失敗：{e}")
    exit()

# ==========================================
# 4. 定義檢查重複函式 (沿用財報程式的精確比對邏輯)
# ==========================================
def check_event_exists(summary, event_date):
    """檢查日曆中是否已存在相同標題與日期的行程 (全天事件精確修正版)"""
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
        
        # 100% 精確字串比對
        for event in events:
            if event.get('summary') == summary:
                return True
        return False
        
    except Exception as e:
        print(f"檢查重複時發生錯誤: {e}")
        return False

# ==========================================
# 5. 主程式：讀取、過濾與上傳
# ==========================================
def main():
    # 載入白名單
    whitelist = load_whitelist(WHITELIST_FILE)
    if not whitelist:
        print("❌ 白名單為空或讀取失敗，程式終止。")
        return
    print(f"📄 成功載入白名單，共 {len(whitelist)} 檔股票。")

    # 讀取 CSV
    try:
        df = pd.read_csv(CSV_FILE)
        print(f"讀取到 {len(df)} 筆原始股東會資料，準備過濾...")
    except FileNotFoundError:
        print(f"錯誤：找不到 {CSV_FILE} 檔案，請先執行爬蟲。")
        return

    # 清理資料：萃取代號與名稱
    df['股票代號'] = df['證券代號/名稱'].astype(str).str.extract(r'(\d{4,})')
    df['公司名稱'] = df['證券代號/名稱'].astype(str).str.replace(r'\d+', '', regex=True).str.strip()

    # 白名單過濾
    target_df = df[df['股票代號'].isin(whitelist)]
    if target_df.empty:
        print("CSV 中沒有符合白名單的股東會資料。")
        return
        
    print(f"✅ 找到 {len(target_df)} 筆符合白名單的資料，準備進行檢查與上傳...")

    # 逐筆處理並新增
    for index, row in target_df.iterrows():
        try:
            stock_code = row['股票代號']
            stock_name = row['公司名稱']
            roc_meeting_date = row['會議日期']
            voting_period = row['投票起迄日']

            # 轉換日期
            formatted_date = convert_roc_to_gregorian(roc_meeting_date)
            if not formatted_date:
                continue

            summary = f"[股東會] {stock_code} {stock_name}"
            
            # --- 檢查重複 ---
            if check_event_exists(summary, formatted_date):
                print(f"🔄 跳過已存在行程：{summary} ({formatted_date})")
                continue
            # ----------------

            # 建立全天事件
            event_description = (
                f"📈 公司：{stock_name} ({stock_code})\n"
                f"🗓️ 股東會日期：{roc_meeting_date}\n"
                f"🗳️ 電子投票起迄日：{voting_period}\n"
                f"\n自動化排程更新"
            )

            event = {
                'summary': summary,
                'description': event_description,
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
            print(f"✅ 成功新增：{summary} ({formatted_date})")
            
            # 避免 API 呼叫過快被鎖
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ 處理失敗：{row.get('證券代號/名稱', '未知')}，錯誤：{e}")

    print("🎉 股東會行事曆同步完成！")

if __name__ == '__main__':
    main()