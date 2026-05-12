from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import os # 新增：用來檢查檔案是否存在

def scrape_with_selenium_and_filter():
    # ==========================================
    # 步驟 1：讀取我們辛苦建立的白名單
    # ==========================================
    whitelist = []
    if os.path.exists('whitelist.txt'):
        with open('whitelist.txt', 'r', encoding='utf-8') as f:
            # 讀取每一行，並去掉空白與換行符號
            whitelist = [line.strip() for line in f if line.strip()]
        print(f"✅ 成功讀取白名單，共載入 {len(whitelist)} 筆目標公司代號。")
    else:
        print("⚠️ 找不到 whitelist.txt！請確認檔案在同一個資料夾中。程式將停止。")
        return

    # ==========================================
    # 步驟 2：Selenium 爬蟲設定與啟動
    # ==========================================
    url = "https://www.money-link.com.tw/stxba/imwcontent0.asp?page=INVC1&ID=INVC1"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 不開啟瀏覽器視窗 (背景執行)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("window-size=1920,1080")

    print("🌐 正在啟動瀏覽器偵測網頁內容...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get(url)
        time.sleep(5) # 等待網頁 JavaScript 加載資料
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        all_data = []
        rows = soup.find_all('tr')
        
        print(f"🔍 掃描到 {len(rows)} 個列結構，正在比對白名單...")
        
        # ==========================================
        # 步驟 3：解析資料並進行白名單篩選
        # ==========================================
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 5:
                text_cols = [ele.get_text(strip=True) for ele in cols]
                
                # 過濾標題列與空白列
                if "公司代號" not in text_cols[0] and text_cols[0] != "" and len(text_cols[0]) < 20:
                    
                    # 💡 根據你的 dataframe 設定，index 1 是「公司代號」
                    stock_id = text_cols[1]
                    
                    # 🎯 核心邏輯：如果代號在白名單內，才加入最終資料清單
                    if stock_id in whitelist:
                        all_data.append(text_cols)

        # ==========================================
        # 步驟 4：輸出結果與存檔
        # ==========================================
        if all_data:
            df = pd.DataFrame(all_data)
            columns = ["法說會日期", "公司代號", "公司名稱", "時間", "地點", "說明", "備註"]
            df = df.iloc[:, :len(columns)]
            df.columns = columns[:df.shape[1]]
            
            print(f"\n🎯 --- 抓取成功！共找到 {len(df)} 筆【符合白名單】的法說會 ---")
            print(df.head())
            
            # 檔名加個 filtered 區分一下
            df.to_csv("investor_conferences_filtered.csv", index=False, encoding="utf-8-sig")
            print("\n📁 檔案已儲存為: investor_conferences_filtered.csv")
        else:
            print("💡 掃描完成，但本月份沒有發現『符合白名單』的法說會資料。")
            
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_with_selenium_and_filter()