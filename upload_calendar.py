import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime

# 1. 設定你的日曆 ID (請務必替換成你剛剛複製的 ID)
CALENDAR_ID = '00a2987f060a55a0037e011c728524e8a63fd5e2ba63835bf1401f0dcb8a4696@group.calendar.google.com'

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
    print(f"❌ 連線失敗，請檢查 credentials.json 檔案是否存在且正確。錯誤訊息：{e}")
    exit()

# 3. 讀取我們剛剛爬下來的 CSV 檔案
try:
    df = pd.read_csv('investor_conferences_filtered.csv')
    print(f"📄 成功讀取 CSV，共有 {len(df)} 筆資料準備上傳...")
except FileNotFoundError:
    print("❌ 找不到 CSV 檔案，請確認你已經成功執行了 Selenium 爬蟲程式。")
    exit()

# 4. 將資料逐筆新增到日曆
for index, row in df.iterrows():
    try:
        # 💡 處理奇怪的日期格式 (例如: "1152026/05/28" 或 "115/05/28")
        tw_date = str(row['法說會日期']).strip()
        parts = tw_date.split('/')
        if len(parts) != 3:
            continue # 日期格式不對就跳過
            
        # --- 🌟 新增的智慧年份判斷邏輯 ---
        year_str = parts[0]
        if len(year_str) >= 7:
            # 處理 "1152026" 黏在一起的狀況，直接取字串的「最後 4 碼」當作西元年
            gregorian_year = int(year_str[-4:])
        elif len(year_str) == 3:
            # 處理正常的民國年 "115"
            gregorian_year = int(year_str) + 1911
        else:
            # 如果它剛好已經是 "2026"
            gregorian_year = int(year_str)
        # --------------------------------
        
        # 組合出正確的格式 (例如 2026-05-28)
        formatted_date = f"{gregorian_year}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
        
        # 處理時間 (抓取時間字串，如果沒有時間則預設為早上 9 點)
        time_str = str(row['時間']).strip() if pd.notna(row['時間']) else "09:00"
        start_time_str = f"{formatted_date}T{time_str}:00"
        
        # 計算結束時間 (通常法說會抓 1 小時)
        start_dt = datetime.datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S")
        end_dt = start_dt + datetime.timedelta(hours=1)
        end_time_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

        # 處理 NaN 空值避免報錯
        location = str(row['地點']) if pd.notna(row['地點']) else "無地點資訊"
        description = str(row['說明']) if pd.notna(row['說明']) else "無說明"

        # 準備行事曆事件的 JSON 內容
        event = {
            'summary': f"[法說會] {row['公司代號']} {row['公司名稱']}",
            'location': location,
            'description': f"相關說明：{description}",
            'start': {
                'dateTime': start_time_str,
                'timeZone': 'Asia/Taipei',
            },
            'end': {
                'dateTime': end_time_str,
                'timeZone': 'Asia/Taipei',
            },
        }

        # 呼叫 API 寫入日曆
        event_result = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"✨ 成功新增：{event['summary']} ({formatted_date} {time_str})")
        
    except Exception as e:
        print(f"⚠️ 新增失敗：{row.get('公司名稱', '未知')}，錯誤原因：{e}")

print("=" * 40)
print("🎉 所有行程已處理完畢！快打開你的 Google 日曆檢查看看！")