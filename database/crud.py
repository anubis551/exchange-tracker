"""
database/crud.py
所有資料庫的讀寫操作都在這裡。
上層程式碼只需呼叫這些函式，不直接碰 SQL。
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from database.models import ExchangeRate, ExchangeRecord, AlertSetting


# ════════════════════════════════════════════════════
#  ExchangeRate — 歷史匯率
# ════════════════════════════════════════════════════

def save_rate(db: Session, currency: str, buy: float, sell: float) -> ExchangeRate:
    """儲存一筆即時匯率。"""
    rate = ExchangeRate(
        currency=currency,
        buy_rate=buy,
        sell_rate=sell,
        recorded_at=datetime.now()
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


def get_latest_rate(db: Session, currency: str) -> Optional[ExchangeRate]:
    """取得某幣別最新一筆匯率。"""
    return (
        db.query(ExchangeRate)
        .filter(ExchangeRate.currency == currency)
        .order_by(ExchangeRate.recorded_at.desc())
        .first()
    )


def get_rates_since(db: Session, currency: str, months: int) -> list[ExchangeRate]:
    """取得過去 N 個月的匯率記錄。"""
    since = datetime.now() - timedelta(days=months * 30)
    return (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.currency == currency,
            ExchangeRate.recorded_at >= since
        )
        .order_by(ExchangeRate.recorded_at.asc())
        .all()
    )


def get_period_low(db: Session, currency: str, months: int) -> Optional[float]:
    """取得過去 N 個月的賣出價最低點。"""
    rates = get_rates_since(db, currency, months)
    if not rates:
        return None
    return min(r.sell_rate for r in rates)


def get_rate_history(db: Session, currency: str, days: int = 90) -> list[ExchangeRate]:
    """取得圖表用的歷史資料。"""
    since = datetime.now() - timedelta(days=days)
    return (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.currency == currency,
            ExchangeRate.recorded_at >= since
        )
        .order_by(ExchangeRate.recorded_at.asc())
        .all()
    )


# ════════════════════════════════════════════════════
#  ExchangeRecord — 我的換匯記錄
# ════════════════════════════════════════════════════

def add_exchange_record(
    db: Session,
    currency: str,
    twd_amount: float,
    foreign_amount: float,
    rate_used: float,
    exchanged_at: datetime,
    note: str = ""
) -> ExchangeRecord:
    """新增一筆換匯記錄。"""
    record = ExchangeRecord(
        currency=currency,
        twd_amount=twd_amount,
        foreign_amount=foreign_amount,
        rate_used=rate_used,
        exchanged_at=exchanged_at,
        note=note
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_all_records(db: Session, currency: Optional[str] = None) -> list[ExchangeRecord]:
    """取得所有換匯記錄（可依幣別篩選）。"""
    q = db.query(ExchangeRecord)
    if currency:
        q = q.filter(ExchangeRecord.currency == currency)
    return q.order_by(ExchangeRecord.exchanged_at.desc()).all()


def get_holdings_summary(db: Session, currency: str) -> dict:
    """
    計算某幣別的持有總覽：
    - 總台幣投入
    - 總外幣持有量
    - 加權平均匯率
    """
    records = (
        db.query(ExchangeRecord)
        .filter(ExchangeRecord.currency == currency)
        .all()
    )

    if not records:
        return {
            "currency": currency,
            "total_twd": 0.0,
            "total_foreign": 0.0,
            "weighted_avg_rate": None,
            "record_count": 0
        }

    total_twd     = sum(r.twd_amount for r in records)
    total_foreign = sum(r.foreign_amount for r in records)
    weighted_avg  = total_twd / total_foreign if total_foreign > 0 else None

    return {
        "currency": currency,
        "total_twd": round(total_twd, 2),
        "total_foreign": round(total_foreign, 4),
        "weighted_avg_rate": round(weighted_avg, 6) if weighted_avg else None,
        "record_count": len(records)
    }


def delete_exchange_record(db: Session, record_id: int) -> bool:
    """刪除指定換匯記錄。"""
    record = db.query(ExchangeRecord).filter(ExchangeRecord.id == record_id).first()
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


# ════════════════════════════════════════════════════
#  AlertSetting — 通知條件
# ════════════════════════════════════════════════════

def get_alert_setting(db: Session, currency: str) -> Optional[AlertSetting]:
    """取得某幣別的通知設定。"""
    return db.query(AlertSetting).filter(AlertSetting.currency == currency).first()


def update_alert_setting(
    db: Session,
    currency: str,
    target_rate: Optional[float] = None,
    alert_3m_low: Optional[bool] = None,
    alert_6m_low: Optional[bool] = None,
    alert_below_avg: Optional[bool] = None
) -> Optional[AlertSetting]:
    """更新通知設定（只傳要改的欄位）。"""
    setting = get_alert_setting(db, currency)
    if not setting:
        return None

    if target_rate is not None:
        setting.target_rate = target_rate
    if alert_3m_low is not None:
        setting.alert_3m_low = alert_3m_low
    if alert_6m_low is not None:
        setting.alert_6m_low = alert_6m_low
    if alert_below_avg is not None:
        setting.alert_below_avg = alert_below_avg

    db.commit()
    db.refresh(setting)
    return setting
