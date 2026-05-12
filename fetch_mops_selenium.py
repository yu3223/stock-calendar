from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_with_selenium():
    url = "https://www.money-link.com.tw/stxba/imwcontent0.asp?page=INVC1&ID=INVC1"
    
    # 設定 Chrome 選項
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 不開啟瀏覽器視窗 (背景執行)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("window-size=1920,1080")

    print("正在啟動瀏覽器偵測網頁內容...")
    
    # 自動安裝並啟動 Chrome
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get(url)
        # 等待網頁 JavaScript 加載資料 (暫定 5 秒)
        time.sleep(5)
        
        # 獲取渲染後的 HTML
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 找到所有的表格列
        all_data = []
        rows = soup.find_all('tr')
        
        print(f"掃描到 {len(rows)} 個列結構，正在提取資料...")
        
        for row in rows:
            cols = row.find_all('td')
            # 根據該網頁結構，有效的資料列通常有 7 欄左右
            if len(cols) >= 5:
                text_cols = [ele.get_text(strip=True) for ele in cols]
                # 過濾標題列與空白列
                if "公司代號" not in text_cols[0] and text_cols[0] != "":
                    # 確保不是導覽選單（通常導覽選單的文字會很長或很特殊）
                    if len(text_cols[0]) < 20: 
                        all_data.append(text_cols)

        if all_data:
            # 轉換為 DataFrame
            df = pd.DataFrame(all_data)
            
            # 定義可能的欄位標題
            columns = ["法說會日期", "公司代號", "公司名稱", "時間", "地點", "說明", "備註"]
            # 依照實際抓到的欄位數量進行裁剪
            df = df.iloc[:, :len(columns)]
            df.columns = columns[:df.shape[1]]
            
            print("\n--- 抓取成功！ ---")
            print(df.head())
            
            df.to_csv("investor_conferences_final.csv", index=False, encoding="utf-8-sig")
            print("\n檔案已儲存為: investor_conferences_final.csv")
        else:
            print("依然找不到資料。這可能是網頁使用了 iframe，或者資料需要點擊按鈕才會顯示。")
            
    except Exception as e:
        print(f"發生錯誤: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_with_selenium()