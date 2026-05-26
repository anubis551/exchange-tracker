"""
run.py
Colab 測試用。直接跑一次完整流程驗證功能。

使用方式（Colab）：
  !python run.py
"""
from database.models import init_db, SessionLocal
from database import crud
from scraper.bot_scraper import fetch_all
from logic.alert_engine import run_all_checks
from datetime import datetime


def test_run():
    print("=" * 50)
    print("  Exchange Tracker — 測試執行")
    print("=" * 50)

    init_db()
    db = SessionLocal()

    try:
        # 1. 抓取匯率
        print("\n▶ 抓取台銀即時資料...")
        results = fetch_all()

        if not results:
            print("❌ 抓取失敗，請確認網路連線")
            return

        # 2. 存入資料庫
        print("\n▶ 儲存至資料庫...")
        for code, data in results.items():
            crud.save_rate(db, code, data["buy"], data["sell"])
            print(f"  已儲存 {code}: 買 {data['buy']} / 賣 {data['sell']}")

        # 3. 查詢最新匯率
        print("\n▶ 最新匯率查詢：")
        for code in results.keys():
            rate = crud.get_latest_rate(db, code)
            if rate:
                print(f"  {code}: 買入 {rate.buy_rate} / 賣出 {rate.sell_rate}")

        # 4. 觸發條件檢查
        print("\n▶ 觸發條件檢查：")
        alerts = run_all_checks(db)
        if alerts:
            for a in alerts:
                print(f"  ⚠️  {a['message']}")
        else:
            print("  目前無觸發條件（需累積歷史資料才有低點比較）")

        print("\n✅ 測試完成")

    finally:
        db.close()


if __name__ == "__main__":
    test_run()
