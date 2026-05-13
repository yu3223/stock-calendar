# 目前需要手動將 top_1_300.csv、top_301_600.csv 匯入專案根目錄，再執行這支程式。https://www.money-link.com.tw/stxba/imwcontent0.asp?page=INVC1&ID=INVC1
import csv

# 準備一個空名單來放篩選後的代號
target_stocks = []

# 把你的兩個 CSV 檔名放在這個列表裡
csv_files = ['top_1_300.csv', 'top_301_600.csv']

for file_name in csv_files:
    try:
        # encoding 使用 utf-8-sig 避免亂碼
        with open(file_name, mode='r', encoding='utf-8-sig') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                if '代號' in row:
                    stock_id = row['代號'].strip()
                    
                    # 篩選邏輯：長度為 4、必須都是數字，且大於 1000 以排除 ETF [cite: 11]
                    if len(stock_id) == 4 and stock_id.isdigit() and int(stock_id) > 1000:
                        if stock_id not in target_stocks:
                            target_stocks.append(stock_id)
                            
    except FileNotFoundError:
        print(f"找不到檔案：{file_name}，請確認檔名是否正確！")

# 將結果存成一個 txt 檔案，供後續爬蟲讀取
with open('whitelist.txt', mode='w', encoding='utf-8') as output_file:
    for stock in target_stocks:
        output_file.write(f"{stock}\n")

print(f"成功！已將 {len(target_stocks)} 家符合條件的公司代號存入 whitelist.txt")