import time
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def fetch_all_shareholders_meetings():
    print("啟動瀏覽器中...")
    
    # 瀏覽器設定
    options = Options()
    
    # 1. 基礎無頭設定
    options.add_argument('--headless=new') 
    
    # 2. 伺服器環境必備 (防止記憶體不足與權限崩潰)
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # 3. 關閉不必要的圖形與擴充功能
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-software-rasterizer')
    
    # 4. 視窗大小與偽裝
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # 🌟 5. 關鍵新武器：強制設定為台灣繁體中文語系 (避免被導向英文首頁)
    options.add_argument('--lang=zh-TW')
    prefs = {
        "intl.accept_languages": "zh-TW,zh,en-US,en"
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    url = "https://stockservices.tdcc.com.tw/evote/index.html?submitted=true&selected=code"

    all_dataframes = []
    page_count = 1

    try:
        driver.get(url)
        print("正在載入網頁...")
        
        try:
            # 1. 等待表格出現 (把時間從 10 秒拉長到 30 秒)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            time.sleep(2)
        except Exception as timeout_e:
            # 如果等不到表格，就截圖存證
            print("❌ 網頁載入超時，可能被防爬蟲機制阻擋！")
            print(f"當前網頁標題: {driver.title}")
            driver.save_screenshot("error_screenshot.png")
            print("📸 已儲存錯誤截圖為 error_screenshot.png")
            raise timeout_e # 把錯誤丟出去讓程式停止
        
        while True:
            # 1. 等待表格出現 (確保資料已載入)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            time.sleep(2) # 額外等待 2 秒，確保 JS 渲染完成
            
            # 2. 擷取當前頁面的 HTML，並交給 BeautifulSoup 與 Pandas 解析
            print(f"正在抓取第 {page_count} 頁資料...")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find('table')
            
            if table:
                # 🛠️ 修正點 1：使用 StringIO 包裝 HTML 字串，避免 Pandas 誤判為檔案路徑
                df = pd.read_html(StringIO(str(table)))[0]
                all_dataframes.append(df)
            else:
                print("找不到表格資料！")
                break

            # 3. 尋找「下一頁」的按鈕
            try:
                # 🛠️ 修正點 2：根據實際網站結構，精準定位 class='btn-next' 的按鈕
                next_button = driver.find_element(By.XPATH, "//a[@class='btn-next']")
                
                # 如果這個按鈕在畫面上消失或被隱藏了，代表到了最後一頁
                if not next_button.is_displayed():
                    print("下一頁按鈕已隱藏，代表已經到達最後一頁，抓取完畢！")
                    break

                # 滾動畫面到按鈕處
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(1) # 稍微停頓，模擬人類動作
                
                # 🛠️ 修正點 3：使用 JavaScript 觸發點擊，避開按鈕被其他元素遮擋的問題
                driver.execute_script("arguments[0].click();", next_button)
                
                page_count += 1
                
                # ⚠️ 關鍵：點擊後必須等待網頁的 JavaScript 抽換掉表格裡的資料
                time.sleep(3) 
                
            except Exception as e:
                # 如果連這個元素都找不到，就結束迴圈
                print("找不到下一頁按鈕，結束翻頁。")
                break

        # 4. 將所有頁面的資料合併並輸出成 CSV
        if all_dataframes:
            final_df = pd.concat(all_dataframes, ignore_index=True)
            
            # 💡 存成 CSV (使用 utf-8-sig 編碼，讓 Excel 打開不會中文亂碼)
            csv_filename = "shareholders_meetings_test.csv"
            final_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            
            print(f"✅ 成功！共抓取 {len(final_df)} 筆資料，已儲存至 {csv_filename}")
            print(final_df.head()) # 印出前五筆檢查
        else:
            print("❌ 沒有抓取到任何資料。")

    finally:
        driver.quit()

if __name__ == "__main__":
    fetch_all_shareholders_meetings()