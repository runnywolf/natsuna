import time, os, urllib.parse, threading, collections, warnings
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError, Browser, Page
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

warnings.simplefilter("ignore", UserWarning)

load_dotenv()
DEFAULT_TIME_OUT_MS = int(os.getenv("DEFAULT_TIME_OUT_MS", 5000)) # 預設的 timeout (5s)
WINDOW_SIZE_SEC = int(os.getenv("WINDOW_SIZE_SEC", 60)) # 時間窗口大小, 超過 60 秒的資料會被捨棄
PLOT_ANIMATION_FPS = int(os.getenv("PLOT_ANIMATION_FPS", 2)) # 圖表每秒刷新幾次

data = collections.deque() # threads share data (ODU 訊號資料)
data_lock = threading.Lock() # lock

def print_divider() -> None: # print 一個分隔線到 terminal
	print("-" * 40)

def get_webui_auth_url() -> str: # Pegatron 5G ODU 的 webui 網址, 包含帳號密碼
	webui_username = urllib.parse.quote(os.getenv("PEGATRON_WEBUI_USERNAME")) # 讀取 .env 的 webui 帳密, 並編碼 (url 不能有特殊字元)
	webui_password = urllib.parse.quote(os.getenv("PEGATRON_WEBUI_PASSWORD"))
	return f"http://{webui_username}:{webui_password}@192.168.225.1" # 附帶 username & password 的 localhost url

def get_element_inner_text(page: Page, selector: str, timeout = DEFAULT_TIME_OUT_MS) -> str: # 抓取某個元素的 innerText
	locator = page.locator(selector) # 搜尋元素
	locator.wait_for(timeout=timeout) # 等待元素出現
	return locator.inner_text().strip() # 回傳元素的 innerText, 並去掉頭尾空白

def plot_thread() -> None: # 用於繪製圖表的 thread
	fig, axe = plt.subplots(2, 1, figsize=(4, 6)) # 圖表 [0] 為 rsrp, 圖表 [1] 為 sinr
	fig.canvas.manager.set_window_title("Pegatron ODU Signal Analysis") # system window title
	
	axe[0].set_title("UE RSRP")
	axe[0].set_xlabel("Time")
	axe[0].set_ylabel("dBm")
	axe[0].set_xlim(-WINDOW_SIZE_SEC, 0)
	axe[0].set_ylim(-140, -44) # Pegatron terminal 的 rsrp range
	axe[0].grid(True)
	line_rsrp, = axe[0].plot([], [], '-', lw=2)
	
	axe[1].set_title("UE SINR")
	axe[1].set_xlabel("Time")
	axe[1].set_ylabel("dB")
	axe[1].set_xlim(-WINDOW_SIZE_SEC, 0)
	axe[1].set_ylim(-23, 40) # Pegatron terminal 的 sinr range
	axe[1].grid(True)
	line_sinr, = axe[1].plot([], [], '-', lw=2)
	
	def update(frame): # 更新資料
		with data_lock:
			if not data: return (line_rsrp, line_sinr)
			
			time_now = time.time()
			x_times = [signal_data["time"] - time_now for signal_data in data]
			y_rsrp = [signal_data["rsrp_dbm"] for signal_data in data]
			y_sinr = [signal_data["sinr_db"] for signal_data in data]
		
		line_rsrp.set_data(x_times, y_rsrp)
		line_sinr.set_data(x_times, y_sinr)
		return (line_rsrp, line_sinr)
	
	ani = FuncAnimation(fig, update, interval=1000/PLOT_ANIMATION_FPS, blit=True, save_count=200) # 建立動畫
	plt.tight_layout()
	plt.show()

class Timer: # 自訂計時器
	_start_time = 0
	
	@staticmethod
	def start(message: str) -> None:
		print(message, end="", flush=True)
		Timer._start_time = time.time()
	
	@staticmethod
	def end() -> None:
		during_time_ms = (time.time() - Timer._start_time) * 1000
		print(f" [ok, {during_time_ms:.0f}ms]")

def crawler(browser: Browser) -> None: # 爬蟲
	Timer.start(" Open the webui ...")
	page = browser.new_page()
	page.goto(get_webui_auth_url(), timeout=DEFAULT_TIME_OUT_MS) # 開啟 webui 的網頁
	Timer.end()
	
	Timer.start(" Handle multi login ...") # 處理 multi login 問題
	try:
		page.locator('button[name="yes"]').wait_for(timeout=1000) # 等待 "yes" 按鈕出現
		page.click('button[name="yes"]') # 按下 "yes" 按鈕 (登出其他的 webui)
	except TimeoutError: # 若不需要重新登入, 則跳過這一步
		pass
	Timer.end()
	
	Timer.start(" Read dashboard info ...")
	model_name = get_element_inner_text(page, 'span[name="span_module_name"]')
	mac = get_element_inner_text(page, 'span[name="span_sysmac"]')
	Timer.end()
	
	Timer.start(" Goto cellular page & Reading info ...")
	page.goto("http://192.168.225.1/cellular_info.html", timeout=DEFAULT_TIME_OUT_MS) # 進入到 Device Status - Cellular Info 頁面
	imsi = get_element_inner_text(page, 'span[name="imsi"]')
	band_code = get_element_inner_text(page, 'span[name="band5g"]')
	Timer.end()
	
	Timer.start(" Set auto refresh interval ...")
	page.fill('input[name="autoRefresh_interval"]', "3") # 將 terminal 刷新間隔設為 3s
	Timer.end()
	
	print_divider()
	
	print(f" Model: {model_name}") # print 型號
	print(f" MAC: {mac}") # print MAC
	print(f" IMSI: {imsi}") # print IMSI
	print(f" 5G Band: n{band_code}") # print band
	
	print_divider()
	
	while True: # 不停地抓取訊號強度
		try:
			rsrp_dbm_str = get_element_inner_text(page, 'div[name="rsrp_5g"]', 1000)
			rsrq_db_str = get_element_inner_text(page, 'div[name="rsrq_5g"]', 1000)
			sinr_db_str = get_element_inner_text(page, 'div[name="sinr_5g"]', 1000)
		except TimeoutError:
			page.goto(get_webui_auth_url(), timeout=DEFAULT_TIME_OUT_MS) # 重新登入 (因為 terminal 一段時間後會登出)
			page.goto("http://192.168.225.1/cellular_info.html", timeout=DEFAULT_TIME_OUT_MS) # 進入到 Device Status - Cellular Info 頁面
			page.fill('input[name="autoRefresh_interval"]', "3") # 將 terminal 刷新間隔設為 3s
			continue # 繼續迴圈
		
		data.append({
			"time": time.time(),
			"rsrp_dbm": int(rsrp_dbm_str.rstrip(" dBm")),
			"rsrq_db": int(rsrq_db_str.rstrip(" dB")),
			"sinr_db": int(sinr_db_str.rstrip(" dB"))
		})
		while len(data) > 1 and data[0]["time"] - time.time() < -WINDOW_SIZE_SEC:
			data.popleft() # 刪除舊資料 (只保留時間範圍內的資料)

def main() -> None:
	threading.Thread(target=plot_thread, daemon=True).start() # 啟動圖表繪製的 thread
	
	with sync_playwright() as p:
		print_divider()
		
		Timer.start(" Launch chromium ...")
		browser = p.chromium.launch(headless=True)
		Timer.end()
		
		try:
			crawler(browser) # 開始爬 webui 的網頁
		except KeyboardInterrupt:
			pass
		except Exception as e: # 如果爬蟲出錯, 印出錯誤訊息
			print("\nError:")
			print(e)

if __name__ == "__main__":
	main()
