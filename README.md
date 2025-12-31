# NaTsuNa
NTN 計畫需要測 gNB 和 UE 的訊號強度，因為一直盯著 terminal 去抓 RSRP 好麻煩，所以才做這個。

## 功能
自動抓取 srsRAN gNB 的 terminal 輸出，以及 Pegatron 5G ODU 的儀錶板資訊，轉為圖表分析。

## 如何使用 
```
git clone https://github.com/runnywolf/natsuna.git
```

### UE 端
1. 確保 ODU 那台白色方塊有接上 POE injector 並供電。
2. 照著說明書將 RJ45 插上你的 PC。
3. 用 PC 訪問 `http://192.168.225.1` (ODU webui) 完成註冊。
4. 將 `.env.example` 檔名改為 `.env`，並將註冊好的 webui 帳密填寫進去。
5. 執行 `ue.py`，如果卡住可以執行第二次，因為有時候 webui 載入很慢。

### gNB 端
1. 將 srsRAN gNB 開起來 (假設你的 `Core <-> gNB <-> USRP <-> UE` 是成功運作的)。
2. gNB 成功啟動後，輸入 `t`，此時若成功與 UE 連線，那 terminal 應該會跳出很多連線資訊，就像範例的 `gnb_output.txt`。
3. 如果想擷取最近的 60 秒資料，那就再按下 `t` 暫停 terminal 實時輸出，複製最近的 60 筆資訊，貼上到 `gnb_output.txt`。
4. 執行 gnb_plot.py

## 已知問題
1. 因為 srsRAN 官方說可以透過 localhost socket 取得 log，但我研究很久發現沒有用。
2. gNB 連線資訊的 terminal，python 抓不出文字，所以這個方法也失敗。(但 gNB 啟動資訊是抓得到的)
