# Exchange Tracker

個人匯率追蹤與換匯通知系統。

## 追蹤標的
- 美元（USD）
- 日圓（JPY）
- 黃金存摺（GOLD）

## 通知觸發條件
1. 現在匯率距 3 個月低點 ≤ 1%
2. 現在匯率距半年低點 ≤ 1%
3. 現在匯率低於目前持有的加權平均匯率
4. 現在匯率達到自訂目標價

## 專案結構
exchange-tracker/
├── config.py              # 所有設定集中管理
├── app.py                 # Flask 主程式 + 排程
├── run.py                 # Colab 測試腳本
├── requirements.txt       # 套件清單
├── .env.example           # 環境變數範本
├── scraper/
│   └── bot_scraper.py     # 台銀爬蟲
├── database/
│   ├── models.py          # 資料表定義
│   └── crud.py            # 讀寫操作
├── logic/
│   └── alert_engine.py    # 觸發條件判斷
└── notifier/
├── base.py            # 通知介面
├── line_bot.py        # LINE Messaging API
└── email_notify.py    # Email 備援

## 環境變數設定
複製 `.env.example` 為 `.env` 並填入實際值。

## 本地測試
```bash
pip install -r requirements.txt
python run.py
```
