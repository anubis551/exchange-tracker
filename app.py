"""
app.py
Flask 主應用程式。
- 提供前端 Dashboard 的 API
- 啟動 APScheduler 定時抓取匯率並觸發通知
"""
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from config import config
from database.models import init_db, SessionLocal
from database import crud
from scraper.bot_scraper import fetch_all
from logic.alert_engine import run_all_checks
from notifier.line_bot import LineNotifier
from notifier.email_notify import EmailNotifier
from database.stock_models import init_stock_db
from database.stock_crud import (
    save_stock_price, get_latest_stock_price,
    get_stock_price_history, add_stock_record,
    get_all_stock_records, get_stock_holdings_summary,
    delete_stock_record, get_stock_alert_setting,
    update_stock_alert_setting,
)
from scraper.stock_scraper import fetch_all_stocks
from logic.stock_alert_engine import run_all_stock_checks


# ════════════════════════════════════════════════════
#  排程任務
# ════════════════════════════════════════════════════

def scheduled_fetch_and_alert():
    """定時執行：抓匯率 → 存資料庫 → 檢查條件 → 發通知。"""
    print(f"\n[Scheduler] 執行中 {datetime.now().strftime('%H:%M:%S')}")
    db = SessionLocal()
    try:
        # 匯率抓取
        results = fetch_all()
        if not results:
            print("[Scheduler] 抓取失敗，略過本次")
            return

        for code, data in results.items():
            crud.save_rate(db, code, data["buy"], data["sell"])

        alerts = run_all_checks(db)

        # 股票抓取
        stock_results = fetch_all_stocks()
        for sym, data in stock_results.items():
            save_stock_price(
                db, sym,
                price=data["price"],
                open_price=data["open"],
                prev_close=data["prev_close"],
                change_pct=data["change_pct"],
                volume=data["volume"],
            )

        stock_alerts = run_all_stock_checks(db)
        if stock_alerts:
            alerts.extend(stock_alerts)

        # 發通知
        if alerts:
            success = line_notifier.send_alerts(alerts)
            if not success:
                email_notifier.send_alerts(alerts)
        else:
            print("[Scheduler] 無觸發條件")

    finally:
        db.close()


# ════════════════════════════════════════════════════
#  API Routes — 匯率資料
# ════════════════════════════════════════════════════

@app.route("/api/rates/latest")
def api_latest_rates():
    """取得所有幣別最新匯率。"""
    db = SessionLocal()
    try:
        result = {}
        for currency in config.TRACKED_CURRENCIES:
            rate = crud.get_latest_rate(db, currency)
            if rate:
                result[currency] = {
                    "buy": rate.buy_rate,
                    "sell": rate.sell_rate,
                    "time": rate.recorded_at.strftime("%Y-%m-%d %H:%M")
                }
        return jsonify(result)
    finally:
        db.close()


@app.route("/api/rates/history/<currency>")
def api_rate_history(currency: str):
    """取得某幣別的歷史走勢（預設 90 天，可帶 ?days=180）。"""
    days = request.args.get("days", 90, type=int)
    db = SessionLocal()
    try:
        history = crud.get_rate_history(db, currency.upper(), days=days)
        data = [
            {
                "time": r.recorded_at.strftime("%Y-%m-%d %H:%M"),
                "buy": r.buy_rate,
                "sell": r.sell_rate
            }
            for r in history
        ]
        return jsonify(data)
    finally:
        db.close()


# ════════════════════════════════════════════════════
#  API Routes — 換匯記錄
# ════════════════════════════════════════════════════

@app.route("/api/records", methods=["GET"])
def api_get_records():
    """取得換匯記錄（可帶 ?currency=USD 篩選）。"""
    currency = request.args.get("currency", None)
    db = SessionLocal()
    try:
        records = crud.get_all_records(
            db, currency=currency.upper() if currency else None
        )
        return jsonify([
            {
                "id": r.id,
                "currency": r.currency,
                "twd_amount": r.twd_amount,
                "foreign_amount": r.foreign_amount,
                "rate_used": r.rate_used,
                "exchanged_at": r.exchanged_at.strftime("%Y-%m-%d"),
                "note": r.note or ""
            }
            for r in records
        ])
    finally:
        db.close()


@app.route("/api/records", methods=["POST"])
def api_add_record():
    """
    新增換匯記錄。
    Body（JSON）：
    {
      "currency": "USD",
      "twd_amount": 50000,
      "foreign_amount": 1570.5,
      "rate_used": 31.83,
      "exchanged_at": "2026-05-26",
      "note": "第一次換匯"
    }
    """
    data = request.json
    required = ["currency", "twd_amount", "foreign_amount", "rate_used", "exchanged_at"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"缺少欄位：{field}"}), 400

    try:
        exchanged_at = datetime.strptime(data["exchanged_at"], "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "日期格式錯誤，請用 YYYY-MM-DD"}), 400

    db = SessionLocal()
    try:
        record = crud.add_exchange_record(
            db,
            currency=data["currency"].upper(),
            twd_amount=float(data["twd_amount"]),
            foreign_amount=float(data["foreign_amount"]),
            rate_used=float(data["rate_used"]),
            exchanged_at=exchanged_at,
            note=data.get("note", "")
        )
        return jsonify({"success": True, "id": record.id}), 201
    finally:
        db.close()


@app.route("/api/records/<int:record_id>", methods=["DELETE"])
def api_delete_record(record_id: int):
    """刪除換匯記錄。"""
    db = SessionLocal()
    try:
        success = crud.delete_exchange_record(db, record_id)
        if success:
            return jsonify({"success": True})
        return jsonify({"error": "找不到該記錄"}), 404
    finally:
        db.close()


@app.route("/api/holdings")
def api_holdings():
    """取得各幣別持有總覽（含加權平均匯率）。"""
    db = SessionLocal()
    try:
        result = {}
        for currency in config.TRACKED_CURRENCIES:
            result[currency] = crud.get_holdings_summary(db, currency)
        return jsonify(result)
    finally:
        db.close()


# ════════════════════════════════════════════════════
#  API Routes — 通知設定
# ════════════════════════════════════════════════════

@app.route("/api/alerts/<currency>", methods=["GET"])
def api_get_alert(currency: str):
    """取得某幣別的通知設定。"""
    db = SessionLocal()
    try:
        s = crud.get_alert_setting(db, currency.upper())
        if not s:
            return jsonify({"error": "找不到設定"}), 404
        return jsonify({
            "currency": s.currency,
            "target_rate": s.target_rate,
            "alert_3m_low": s.alert_3m_low,
            "alert_6m_low": s.alert_6m_low,
            "alert_below_avg": s.alert_below_avg
        })
    finally:
        db.close()


@app.route("/api/alerts/<currency>", methods=["PATCH"])
def api_update_alert(currency: str):
    """
    更新通知設定。
    Body 範例：{"target_rate": 30.5, "alert_6m_low": true}
    """
    data = request.json
    db = SessionLocal()
    try:
        s = crud.update_alert_setting(
            db,
            currency=currency.upper(),
            target_rate=data.get("target_rate"),
            alert_3m_low=data.get("alert_3m_low"),
            alert_6m_low=data.get("alert_6m_low"),
            alert_below_avg=data.get("alert_below_avg")
        )
        if not s:
            return jsonify({"error": "找不到設定"}), 404
        return jsonify({"success": True})
    finally:
        db.close()


# ════════════════════════════════════════════════════
#  API Routes — 股票即時價格
# ════════════════════════════════════════════════════
 
@app.route("/api/stocks/latest")
def api_latest_stocks():
    """取得所有追蹤標的最新價格。"""
    db = SessionLocal()
    try:
        result = {}
        for symbol in ["VOO", "0050", "00919"]:
            price = get_latest_stock_price(db, symbol)
            if price:
                result[symbol] = {
                    "price":      price.price,
                    "open":       price.open_price,
                    "prev_close": price.prev_close,
                    "change_pct": price.change_pct,
                    "volume":     price.volume,
                    "time":       price.recorded_at.strftime("%Y-%m-%d %H:%M"),
                }
        return jsonify(result)
    finally:
        db.close()
 
 
@app.route("/api/stocks/history/<symbol>")
def api_stock_history(symbol: str):
    """取得某標的歷史走勢（預設 90 天，可帶 ?days=180）。"""
    days = request.args.get("days", 90, type=int)
    db = SessionLocal()
    try:
        history = get_stock_price_history(db, symbol.upper(), days=days)
        data = [
            {
                "time":       r.recorded_at.strftime("%Y-%m-%d %H:%M"),
                "price":      r.price,
                "change_pct": r.change_pct,
            }
            for r in history
        ]
        return jsonify(data)
    finally:
        db.close()
 
 
# ════════════════════════════════════════════════════
#  API Routes — 持股記錄
# ════════════════════════════════════════════════════
 
@app.route("/api/stocks/records", methods=["GET"])
def api_get_stock_records():
    """取得持股記錄（可帶 ?symbol=VOO 篩選）。"""
    symbol = request.args.get("symbol", None)
    db = SessionLocal()
    try:
        records = get_all_stock_records(
            db, symbol=symbol.upper() if symbol else None
        )
        return jsonify([
            {
                "id":               r.id,
                "symbol":           r.symbol,
                "shares":           r.shares,
                "price_per_share":  r.price_per_share,
                "total_cost":       r.total_cost,
                "currency":         r.currency,
                "purchased_at":     r.purchased_at.strftime("%Y-%m-%d"),
                "note":             r.note or "",
            }
            for r in records
        ])
    finally:
        db.close()
 
 
@app.route("/api/stocks/records", methods=["POST"])
def api_add_stock_record():
    """
    新增持股記錄。
    Body（JSON）：
    {
      "symbol":          "VOO",
      "shares":          10,
      "price_per_share": 520.5,
      "total_cost":      5205,
      "currency":        "USD",
      "purchased_at":    "2026-05-27",
      "note":            "第一次買入"
    }
    """
    data = request.json
    required = ["symbol", "shares", "price_per_share", "total_cost", "currency", "purchased_at"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"缺少欄位：{field}"}), 400
 
    try:
        purchased_at = datetime.strptime(data["purchased_at"], "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "日期格式錯誤，請用 YYYY-MM-DD"}), 400
 
    db = SessionLocal()
    try:
        record = add_stock_record(
            db,
            symbol=data["symbol"].upper(),
            shares=float(data["shares"]),
            price_per_share=float(data["price_per_share"]),
            total_cost=float(data["total_cost"]),
            currency=data["currency"].upper(),
            purchased_at=purchased_at,
            note=data.get("note", ""),
        )
        return jsonify({"success": True, "id": record.id}), 201
    finally:
        db.close()
 
 
@app.route("/api/stocks/records/<int:record_id>", methods=["DELETE"])
def api_delete_stock_record(record_id: int):
    """刪除持股記錄。"""
    db = SessionLocal()
    try:
        success = delete_stock_record(db, record_id)
        if success:
            return jsonify({"success": True})
        return jsonify({"error": "找不到該記錄"}), 404
    finally:
        db.close()
 
 
@app.route("/api/stocks/holdings")
def api_stock_holdings():
    """取得各標的持股總覽（含加權平均成本）。"""
    db = SessionLocal()
    try:
        result = {}
        for symbol in ["VOO", "0050", "00919"]:
            result[symbol] = get_stock_holdings_summary(db, symbol)
        return jsonify(result)
    finally:
        db.close()
 
 
# ════════════════════════════════════════════════════
#  API Routes — 股票通知設定
# ════════════════════════════════════════════════════
 
@app.route("/api/stocks/alerts/<symbol>", methods=["GET"])
def api_get_stock_alert(symbol: str):
    """取得某標的的通知設定。"""
    db = SessionLocal()
    try:
        s = get_stock_alert_setting(db, symbol.upper())
        if not s:
            return jsonify({"error": "找不到設定"}), 404
        return jsonify({
            "symbol":          s.symbol,
            "target_price":    s.target_price,
            "alert_3m_low":    s.alert_3m_low,
            "alert_6m_low":    s.alert_6m_low,
            "alert_below_avg": s.alert_below_avg,
            "alert_3d_drop":   s.alert_3d_drop,
        })
    finally:
        db.close()
 
 
@app.route("/api/stocks/alerts/<symbol>", methods=["PATCH"])
def api_update_stock_alert(symbol: str):
    """
    更新股票通知設定。
    Body 範例：{"target_price": 500.0, "alert_3d_drop": true}
    """
    data = request.json
    db = SessionLocal()
    try:
        s = update_stock_alert_setting(
            db,
            symbol=symbol.upper(),
            target_price=data.get("target_price"),
            alert_3m_low=data.get("alert_3m_low"),
            alert_6m_low=data.get("alert_6m_low"),
            alert_below_avg=data.get("alert_below_avg"),
            alert_3d_drop=data.get("alert_3d_drop"),
        )
        if not s:
            return jsonify({"error": "找不到設定"}), 404
        return jsonify({"success": True})
    finally:
        db.close()


# ════════════════════════════════════════════════════
#  前端頁面
# ════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=config.DEBUG)
