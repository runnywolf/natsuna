import time, os, urllib.parse
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation # 💡 FuncAnimation 核心
import collections # 用於高效能的隊列管理

DEFAULT_TIME_OUT_MS = 5000 # 預設的 timeout (5s)

def print_divider() -> None: # print 一個分隔線到 terminal
	print("-" * 40)

def get_webui_auth_url() -> str: # Pegatron 5G ODU 的 webui 網址, 包含帳號密碼
	load_dotenv()
	webui_username = urllib.parse.quote(os.getenv("PEGATRON_WEBUI_USERNAME")) # 讀取 .env 的 webui 帳密, 並編碼 (url 不能有特殊字元)
	webui_password = urllib.parse.quote(os.getenv("PEGATRON_WEBUI_PASSWORD"))
	return f"http://{webui_username}:{webui_password}@192.168.225.1" # 附帶 username & password 的 localhost url

def get_element_inner_text(page: Page, selector: str) -> str: # 抓取某個元素的 innerText
	locator = page.locator(selector) # 搜尋元素
	locator.wait_for(timeout=DEFAULT_TIME_OUT_MS) # 等待元素出現
	return locator.inner_text().strip() # 回傳元素的 innerText, 並去掉頭尾空白

def crawler_loop(page: Page, start_time: float) -> None: # 爬蟲主迴圈 (主要爬訊號強度)
	rsrp_dbm = get_element_inner_text(page, 'div[name="rsrp_5g"]').rstrip(" dBm")
	rsrq_db = get_element_inner_text(page, 'div[name="rsrq_5g"]').rstrip(" dB")
	sinr_db = get_element_inner_text(page, 'div[name="sinr_5g"]').rstrip(" dB")
	print(time.time()-start_time, rsrp_dbm, rsrq_db, sinr_db)
	time.sleep(0.2) # 因為 Pegatron terminal 最快 3s 刷新一次, 所以 sleep 一下

def crawler(page: Page) -> None: # 爬蟲
	print(" Open the webui ...", end="", flush=True)
	page.goto(get_webui_auth_url(), timeout=DEFAULT_TIME_OUT_MS) # 開啟 webui 的網頁
	print(" [ok]")
	
	print(" Handling multi login ...", end="", flush=True) # 處理 multi login 問題
	page.locator('button[name="yes"]').wait_for(timeout=DEFAULT_TIME_OUT_MS) # 等待 "yes" 按鈕 (登出其他的 webui)
	page.click("button#yes") # 按下 "yes" 按鈕
	print(" [ok]")
	
	page.fill('input[name="autoRefresh_interval"]', "3") # 將 terminal 刷新間隔設為 3s
	
	print_divider()
	
	model_name = get_element_inner_text(page, 'span[name="span_module_name"]')
	mac = get_element_inner_text(page, 'span[name="span_sysmac"]')
	print(f" Model: {model_name}") # print 型號
	print(f" MAC: {mac}") # print MAC
	
	page.goto("http://192.168.225.1/cellular_info.html", timeout=DEFAULT_TIME_OUT_MS) # 進入到 Device Status - Cellular Info 頁面 
	imsi = get_element_inner_text(page, 'span[name="imsi"]')
	band_code = get_element_inner_text(page, 'span[name="band5g"]')
	print(f" IMSI: {imsi}") # print IMSI
	print(f" 5G Band: n{band_code}") # print band
	
	print_divider()
	
	while True: # 不停地抓取訊號強度
		try: crawler_loop(page, time.time())
		except KeyboardInterrupt: break # 按下 ctrl+C 會停止抓取訊號強度資訊
	
	print(" Stop.")

def main() -> None:
	with sync_playwright() as p:
		print_divider()
		
		print(" Launch chromium ...", end="", flush=True)
		browser = p.chromium.launch(headless=True)
		page = browser.new_page()
		print(" [ok]")
		
		try:
			crawler(page) # 開始爬 webui 的網頁
		except Exception as e: # 如果爬蟲出錯, 印出錯誤訊息
			print("\nError:")
			print(e)
		finally:
			print(" Closing browser...", end="", flush=True)
			try: browser.close()
			except Exception as e: pass
			print(" [ok]")
			print_divider()

main()
