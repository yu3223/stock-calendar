from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re 
import time
import pandas as pd
import os
import datetime

def get_whitelist(file_path="whitelist.txt"):
    """讀取白名單的自訂函式"""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            print(f"找到白名單檔案 '{file_path}'，啟用過濾機制。")
            return [line.strip() for line in f.readlines() if line.strip()]
    else:
        print("未檢測到白名單檔案，將抓取網頁上所有公司。")
        return []

def scrape_moneydj_calendar():
    chrome_options = Options()
    # 提醒：如果要放到 GitHub Actions 上跑，請把下面這行註解拿掉
    # chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)
    
    # --- 【神級修正：動態取得當天日期】 ---
    today = datetime.datetime.now()
    # 組合出類似 "2024-5-14" 的字串
    date_str = f"{today.year}-{today.month}-{today.day}"
    current_year = today.year 
    
    # 定義要爬取的網址清單 (將寫死的日期換成動態變數)
    urls = [
        f"https://www.moneydj.com/z/ze/zej/zej.djhtm?A=EV000180&B={date_str}&C=0",
        f"https://www.moneydj.com/z/ze/zej/zej.djhtm?A=EV000180&B={date_str}&C=2"
    ]
    
    all_data = []
    whitelist = get_whitelist()
    
    try:
        print(f"\n--- 開始執行網頁自動化 (基準日: {date_str}) ---")
        
        for url in urls:
            week_type = "本週" if "C=0" in url else "下兩週"
            print(f"\n正在前往網址抓取：{week_type}")
            
            driver.get(url)
            time.sleep(3) 

            # 保險起見，再次確認下拉選單是財報公告
            try:
                select_element = Select(driver.find_element(By.NAME, "selEvent"))
                select_element.select_by_value("EV000180")
                time.sleep(2) 
            except:
                pass

            # 擷取網頁原始碼進行解析
            soup = BeautifulSoup(driver.page_source, "html.parser")
            rows = soup.select("table.t01 > tbody > tr")
            current_date = "" 
            
            for row in rows:
                # 排除外層巢狀表格
                if row.find("table"):
                    continue

                # 1. 找日期
                t2_cell = row.select_one("td.t2")
                if t2_cell:
                    raw_text = t2_cell.get_text(strip=True) 
                    match = re.search(r'(\d{2}/\d{2})', raw_text)
                    if match:
                        current_date = f"{current_year}/{match.group(1)}"
                
                if not current_date:
                    continue
                    
                # 2. 找公司
                companies = row.select("td.t3n0 a")
                for comp in companies:
                    comp_text = comp.get_text(strip=True)
                    if comp_text and len(comp_text) > 4: 
                        stock_id = comp_text[:4]
                        stock_name = comp_text[4:]
                        
                        # 白名單過濾
                        if whitelist and stock_id not in whitelist:
                            continue
                            
                        all_data.append({
                            "日期": current_date,
                            "代號": stock_id,
                            "名稱": stock_name
                        })
                        print(f"抓取成功: [{current_date}] {stock_id} {stock_name}")

    except Exception as e:
        print(f"\n執行過程中發生錯誤: {e}")
    
    finally:
        driver.quit()
        print("\n--- 爬蟲執行完畢，正在處理資料 ---")

        if all_data:
            df = pd.DataFrame(all_data)
            
            # 去除重複
            df.drop_duplicates(subset=['代號', '日期'], inplace=True) 
            
            # 排序日期
            df = df.sort_values(by=['日期', '代號'])
            
            output_file = "financial_reports.csv"
            df.to_csv(output_file, index=False, encoding="utf-8-sig")
            
            print(f"大功告成！共合併抓取 {len(df)} 筆有效資料。")
            print(f"資料已成功儲存至：{output_file}")
        else:
            print("條件內沒有抓到任何資料。")

if __name__ == "__main__":
    scrape_moneydj_calendar()