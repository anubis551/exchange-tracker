"""
logic/stock_alert_engine.py
股票 / ETF 觸發條件判斷。

四個觸發條件：
  1. 現在價格距 3 個月低點 ≤ 1%
  2. 現在價格距半年低點 ≤ 1%
  3. 現在價格低於加權平均成本（持有才觸發）
  4. 三天內跌幅 ≥ 5%
"""
from sqlalchemy.orm import Session
from database.stock_crud import (
    get_stock_alert_setting,
    get_stock_period_low,
    get_stock_holdings_summary,
    get_prices_last_n_days,
)
from config import config

# 沿用匯率的閾值設定
ALERT_THRESHOLD_PERCENT = config.ALERT_THRESHOLD_PERCENT   # 1.0
DROP_ALERT_PERCENT      = 5.0   # 三天跌幅觸發門檻
DROP_DAYS               = 3     # 觀察天數

STOCK_LABEL = {
    "VOO":   "VOO（Vanguard S&P500）",
    "0050":  "0050（元大台灣50）",
    "00919": "00919（群益台灣精選高息）",
}

TRACKED_STOCKS = ["VOO", "0050", "00919"]


def _pct_diff(current: float, base: float) -> float:
    """計算 current 距 base 的百分比差距（正值代表高於基準）。"""
    if base == 0:
        return 0.0
    return (current - base) / base * 100


def check_stock_alerts(
    db: Session,
    symbol: str,
    current_price: float,
) -> list[dict]:
    """
    對某標的執行所有觸發條件檢查。
    回傳所有觸發條件的 list。
    """
    setting = get_stock_alert_setting(db, symbol)
    if not setting:
        return []

    label  = STOCK_LABEL.get(symbol, symbol)
    alerts = []

    # ── 條件 1：3 個月低點 ────────────────────────────
    if setting.alert_3m_low:
        low_3m = get_stock_period_low(db, symbol, months=3)
        if low_3m is not None:
            diff = _pct_diff(current_price, low_3m)
            if 0 <= diff <= ALERT_THRESHOLD_PERCENT:
                alerts.append({
                    "symbol":    symbol,
                    "condition": "3m_low",
                    "triggered": True,
                    "message": (
                        f"📉 【{label}】接近 3 個月低點\n"
                        f"  現在：{current_price:.2f}\n"
                        f"  3個月低點：{low_3m:.2f}\n"
                        f"  距低點：{diff:.2f}%"
                    ),
                })

    # ── 條件 2：半年低點 ──────────────────────────────
    if setting.alert_6m_low:
        low_6m = get_stock_period_low(db, symbol, months=6)
        if low_6m is not None:
            diff = _pct_diff(current_price, low_6m)
            if 0 <= diff <= ALERT_THRESHOLD_PERCENT:
                alerts.append({
                    "symbol":    symbol,
                    "condition": "6m_low",
                    "triggered": True,
                    "message": (
                        f"📉 【{label}】接近半年低點\n"
                        f"  現在：{current_price:.2f}\n"
                        f"  半年低點：{low_6m:.2f}\n"
                        f"  距低點：{diff:.2f}%"
                    ),
                })

    # ── 條件 3：低於加權平均成本 ───────────────────────
    if setting.alert_below_avg:
        summary = get_stock_holdings_summary(db, symbol)
        avg_cost = summary.get("weighted_avg_cost")
        if avg_cost and current_price < avg_cost:
            diff = _pct_diff(current_price, avg_cost)
            alerts.append({
                "symbol":    symbol,
                "condition": "below_avg",
                "triggered": True,
                "message": (
                    f"💡 【{label}】現在低於你的加權平均成本\n"
                    f"  現在：{current_price:.2f}\n"
                    f"  持有均成本：{avg_cost:.2f}\n"
                    f"  若現在買入可攤低成本 {abs(diff):.2f}%"
                ),
            })

    # ── 條件 4：三天內跌幅 ≥ 5% ──────────────────────
    if setting.alert_3d_drop:
        daily_prices = get_prices_last_n_days(db, symbol, days=DROP_DAYS + 1)
        # 至少需要兩天的資料才能計算跌幅
        if len(daily_prices) >= 2:
            oldest_price = daily_prices[0].price
            drop_pct = _pct_diff(current_price, oldest_price)
            if drop_pct <= -DROP_ALERT_PERCENT:
                alerts.append({
                    "symbol":    symbol,
                    "condition": "3d_drop",
                    "triggered": True,
                    "message": (
                        f"⚠️ 【{label}】近三天急跌\n"
                        f"  {daily_prices[0].recorded_at.strftime('%m/%d')} 價格：{oldest_price:.2f}\n"
                        f"  現在：{current_price:.2f}\n"
                        f"  跌幅：{drop_pct:.2f}%"
                    ),
                })

    # ── 條件 5：達到自訂目標價 ─────────────────────────
    if setting.target_price and current_price <= setting.target_price:
        alerts.append({
            "symbol":    symbol,
            "condition": "target",
            "triggered": True,
            "message": (
                f"🎯 【{label}】已達到你的目標買入價\n"
                f"  現在：{current_price:.2f}\n"
                f"  目標：{setting.target_price:.2f}"
            ),
        })

    return alerts


def run_all_stock_checks(db: Session) -> list[dict]:
    """對所有追蹤標的執行檢查，回傳所有觸發的警示。"""
    from database.stock_crud import get_latest_stock_price

    all_alerts = []

    for symbol in TRACKED_STOCKS:
        latest = get_latest_stock_price(db, symbol)
        if not latest:
            print(f"[StockAlert] {symbol} 無歷史資料，略過")
            continue

        triggered = check_stock_alerts(db, symbol, current_price=latest.price)
        all_alerts.extend(triggered)

    return all_alerts
