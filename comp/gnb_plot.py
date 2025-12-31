import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt

def mean(l: list) -> float: # 取平均
	if len(l) == 0: return 0
	return sum(l) / len(l)

load_dotenv()
WINDOW_SIZE_SEC = int(os.getenv("WINDOW_SIZE_SEC", 60)) # 時間窗口大小, 超過 60 秒的資料會被捨棄

with open("comp/gnb_output.txt", mode="r", encoding="utf-8") as f: gnb_output = f.read()
lines = gnb_output.split("\n")
lines = [l for l in lines if len(l) != 0 and "DL" not in l and "rsrp" not in l]

data = reversed([l.split() for l in lines])
x_times = []
y_rsrp = []
y_mcs = []
for i, d in enumerate(data):
	if d[13] != "n/a":
		x_times.append(-i)
		y_rsrp.append(float(d[13]))
		y_mcs.append(int(d[15]))

fig, axe = plt.subplots(2, 1, figsize=(4, 6)) # 圖表 [0] 為 rsrp, 圖表 [1] 為 sinr
fig.canvas.manager.set_window_title("srsRAN gNB Signal Analysis") # system window title

axe[0].set_title("gNB RSRP")
axe[0].set_xlabel("Time (s)")
axe[0].set_ylabel("dBm")
axe[0].set_xlim(-WINDOW_SIZE_SEC, 0)
axe[0].set_ylim(-100, 0) # rsrp range
axe[0].grid(True)
axe[0].plot(x_times, y_rsrp, '.', lw=2) # 將訊號資訊繪製成折線圖
axe[0].plot([0, -WINDOW_SIZE_SEC], [mean(y_rsrp), mean(y_rsrp)], '-', lw=1, color="red") # 將訊號資訊繪製成折線圖
text_rsrp = fig.text(
    0.215, 0.588, f"min/max/avg = {min(y_rsrp)}/{max(y_rsrp)}/{mean(y_rsrp):.1f}", ha="left", va="bottom", fontsize=10
) # 圖表右下角的 now/min/max/avg

axe[1].set_title("gNB MCS")
axe[1].set_xlabel("Time (s)")
axe[1].set_ylabel("Index")
axe[1].set_xlim(-WINDOW_SIZE_SEC, 0)
axe[1].set_ylim(-1, 32) # MCS = 0 ~ 31
axe[1].grid(True)
line_sinr, = axe[1].plot(x_times, y_mcs, '.', lw=2)
text_rsrp = fig.text(
    0.215, 0.1, f"min/max = {min(y_mcs)}/{max(y_mcs)}", ha="left", va="bottom", fontsize=10
) # 圖表右下角的 now/min/max/avg

plt.tight_layout()
plt.show()
