"""
logic/alert_engine.py
觸發條件判斷。

觸發條件：
  1. 現在匯率距 3個月低點 ≤ 1%
  2. 現在匯率距 半年低點 ≤ 1%
  3. 現在匯率低於目前持有的加權平均匯率
  4. 現在匯率達到（低於）自訂目標價
"""
from typing import Optional
from sqlalchemy.orm import Session
from database import crud
from config import config


CURRENCY_LABEL = {
    "USD": "美元",
    "JPY": "日圓",
    "GOLD": "黃金存摺",
}


def _pct_diff(current: float, low: float) -> float:
    """計算 current 距 low 的百分比差距（正值代表高於低點）。"""
    if low == 0:
        return 0.0
    return (current - low) / low * 100


def check_alerts(db: Session, currency: str, current_sell: float) -> list[dict]:
    """
    對某幣別的當前賣出價執行所有觸發條件檢查。
    回傳所有觸發條件的 list。
    """
    setting = crud.get_alert_setting(db, currency)
    if not setting:
        return []

    label = CURRENCY_LABEL.get(currency, currency)
    alerts = []

    # ── 條件 1：3個月低點 ─────────────────────────────
    if setting.alert_3m_low:
        low_3m = crud.get_period_low(db, currency, months=config.LOW_PERIOD_MONTHS_SHORT)
        if low_3m is not None:
            diff = _pct_diff(current_sell, low_3m)
            if 0 <= diff <= config.ALERT_THRESHOLD_PERCENT:
                alerts.append({
                    "currency": currency,
                    "condition": "3m_low",
                    "triggered": True,
                    "message": (
                        f"📉 【{label}】接近 3 個月低點\n"
                        f"  現在：{current_sell:.4f}\n"
                        f"  3個月低點：{low_3m:.4f}\n"
                        f"  距低點：{diff:.2f}%"
                    )
                })

    # ── 條件 2：半年低點 ──────────────────────────────
    if setting.alert_6m_low:
        low_6m = crud.get_period_low(db, currency, months=config.LOW_PERIOD_MONTHS_LONG)
        if low_6m is not None:
            diff = _pct_diff(current_sell, low_6m)
            if 0 <= diff <= config.ALERT_THRESHOLD_PERCENT:
                alerts.append({
                    "currency": currency,
                    "condition": "6m_low",
                    "triggered": True,
                    "message": (
                        f"📉 【{label}】接近半年低點\n"
                        f"  現在：{current_sell:.4f}\n"
                        f"  半年低點：{low_6m:.4f}\n"
                        f"  距低點：{diff:.2f}%"
                    )
                })

    # ── 條件 3：低於加權平均匯率 ───────────────────────
    if setting.alert_below_avg:
        summary = crud.get_holdings_summary(db, currency)
        weighted_avg = summary.get("weighted_avg_rate")
        if weighted_avg and current_sell < weighted_avg:
            savings_pct = _pct_diff(current_sell, weighted_avg)
            alerts.append({
                "currency": currency,
                "condition": "below_avg",
                "triggered": True,
                "message": (
                    f"💡 【{label}】現在低於你的加權平均成本\n"
                    f"  現在：{current_sell:.4f}\n"
                    f"  持有加權平均：{weighted_avg:.4f}\n"
                    f"  若現在換匯可攤低成本 {abs(savings_pct):.2f}%"
                )
            })

    # ── 條件 4：達到自訂目標價 ─────────────────────────
    if setting.target_rate and current_sell <= setting.target_rate:
        alerts.append({
            "currency": currency,
            "condition": "target",
            "triggered": True,
            "message": (
                f"🎯 【{label}】已達到你的目標匯率\n"
                f"  現在：{current_sell:.4f}\n"
                f"  目標：{setting.target_rate:.4f}"
            )
        })

    return alerts


def run_all_checks(db: Session) -> list[dict]:
    """對所有追蹤幣別執行檢查，回傳所有觸發的警示。"""
    all_alerts = []

    for currency in config.TRACKED_CURRENCIES:
        latest = crud.get_latest_rate(db, currency)
        if not latest:
            print(f"[Alert] {currency} 無歷史資料，略過")
            continue

        triggered = check_alerts(db, currency, current_sell=latest.sell_rate)
        all_alerts.extend(triggered)

    return all_alerts
