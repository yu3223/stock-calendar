from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
from datetime import datetime
import pandas as pd

def fetch_yahoo_shareholders_meeting(target_date=None): 
    if target_date is None:
        target_date = datetime.today().strftime("%Y/%m/%d")
        
    print("啟動 Selenium 準備前往 Yahoo 股市...")
    print(f"本次抓取目標日期設定為：{target_date}")
    
    # --- 無標頭模式設定 (適用於本地與 GitHub Actions) ---
    options = Options()
    options.add_argument("--headless") # 開啟無標頭模式
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu") 
    options.add_argument("--no-sandbox") 
    options.add_argument("--disable-dev-shm-usage") 
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    url = "https://tw.stock.yahoo.com/calendar/holders-meeting"
    
    try:
        driver.get(url)
        print("等待初始網頁載入...")
        time.sleep(3)
        
        print(f"嘗試輸入目標日期：{target_date} ...")
        try:
            date_input = driver.find_element(By.XPATH, "//input[@placeholder='yyyy/mm/dd']")
            date_input.click()
            time.sleep(0.5)
            
            for _ in range(10):
                date_input.send_keys(Keys.BACKSPACE)
            
            date_input.send_keys(target_date)
            date_input.send_keys(Keys.ENTER)
            
            print("等待新日期的資料載入...")
            time.sleep(3) 
        except Exception as e:
            print(f"日期輸入階段發生異常，將直接抓取當前畫面資料。錯誤: {e}")

        print("開始向下捲動網頁以載入所有資料 (背景執行中)...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2) 
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("已經捲動到底部，資料全部載入完成！")
                break
            last_height = new_height
            
        print("正在解析網頁資料...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        all_data = []
        quote_links = soup.find_all('a', href=lambda href: href and href.startswith('/quote/'))
        
        print(f"找到 {len(quote_links)} 筆股東會資料，開始進行欄位切割...")
        print("-" * 40)
        
        for link in quote_links:
            try:
                # [萃取 名稱 與 代碼]
                code_div = link.find('div')
                raw_stock_code = code_div.text.strip() if code_div else ""
                
                # 1. 必須用原始包含 .TW 或 .TWO 的代碼去取代，否則股票名稱會殘留尾綴
                stock_name = link.text.replace(raw_stock_code, "").strip()
                
                # 2. 把代碼用 "." 切割，只取第一部分 (例如 "1465.TW" -> "1465")
                stock_code = raw_stock_code.split('.')[0] if '.' in raw_stock_code else raw_stock_code
                
                col1 = link.parent 
                row = col1.parent  
                
                cols = row.find_all('div', recursive=False)
                
                if len(cols) >= 3:
                    raw_date_time = cols[1].text.strip() 
                    location = cols[2].text.strip()  
                    
                    # --- 拆分日期與時間 ---
                    date_part = ""
                    time_part = ""
                    if " " in raw_date_time:
                        parts = raw_date_time.split(" ")
                        date_part = parts[0]
                        time_part = parts[1]
                    else:
                        date_part = raw_date_time
                    
                    meeting_info = {
                        "股票名稱": stock_name,
                        "代碼": stock_code,
                        "日期": date_part,
                        "時間": time_part,
                        "地點": location
                    }
                    all_data.append(meeting_info)
                    
                    print(f"{stock_name} ({stock_code}) | {date_part} | {time_part} | {location}")
                    
            except Exception as e:
                print(f"解析單筆資料時發生錯誤跳過: {e}")
                
        print("-" * 40)
        print(f"完美萃取出 {len(all_data)} 筆股東會資料！")
        
        if all_data:
            df = pd.DataFrame(all_data)
            csv_filename = "shareholders_meetings_test.csv"
            df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
            print(f"資料已成功儲存至 {csv_filename}")
        else:
            print("沒有抓取到任何資料，略過儲存 CSV。")
            
        return all_data
        
    except Exception as e:
        print(f"發生嚴重錯誤：{e}")
        return []
        
    finally:
        driver.quit()

if __name__ == "__main__":
    fetch_yahoo_shareholders_meeting()