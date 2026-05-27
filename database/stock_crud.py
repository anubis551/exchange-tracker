"""
database/stock_crud.py
股票 / ETF 所有資料庫讀寫操作。
對應 stock_models.py 的三張表。
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from database.stock_models import StockPrice, StockRecord, StockAlertSetting


# ════════════════════════════════════════════════════
#  StockPrice — 歷史股價
# ════════════════════════════════════════════════════

def save_stock_price(
    db: Session,
    symbol: str,
    price: float,
    open_price: float = None,
    prev_close: float = None,
    change_pct: float = None,
    volume: int = None,
) -> StockPrice:
    """儲存一筆即時股價。"""
    record = StockPrice(
        symbol=symbol,
        price=price,
        open_price=open_price,
        prev_close=prev_close,
        change_pct=change_pct,
        volume=volume,
        recorded_at=datetime.now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_latest_stock_price(db: Session, symbol: str) -> Optional[StockPrice]:
    """取得某標的最新一筆價格。"""
    return (
        db.query(StockPrice)
        .filter(StockPrice.symbol == symbol)
        .order_by(StockPrice.recorded_at.desc())
        .first()
    )


def get_stock_prices_since(db: Session, symbol: str, months: int) -> list[StockPrice]:
    """取得過去 N 個月的價格記錄。"""
    since = datetime.now() - timedelta(days=months * 30)
    return (
        db.query(StockPrice)
        .filter(
            StockPrice.symbol == symbol,
            StockPrice.recorded_at >= since,
        )
        .order_by(StockPrice.recorded_at.asc())
        .all()
    )


def get_stock_period_low(db: Session, symbol: str, months: int) -> Optional[float]:
    """取得過去 N 個月的最低價。"""
    prices = get_stock_prices_since(db, symbol, months)
    if not prices:
        return None
    return min(p.price for p in prices)


def get_stock_price_history(db: Session, symbol: str, days: int = 90) -> list[StockPrice]:
    """取得圖表用的歷史資料。"""
    since = datetime.now() - timedelta(days=days)
    return (
        db.query(StockPrice)
        .filter(
            StockPrice.symbol == symbol,
            StockPrice.recorded_at >= since,
        )
        .order_by(StockPrice.recorded_at.asc())
        .all()
    )


def get_prices_last_n_days(db: Session, symbol: str, days: int) -> list[StockPrice]:
    """
    取得最近 N 天的價格記錄（用於計算短期跌幅）。
    每天只取最新一筆，避免重複計算。
    """
    since = datetime.now() - timedelta(days=days)
    rows = (
        db.query(StockPrice)
        .filter(
            StockPrice.symbol == symbol,
            StockPrice.recorded_at >= since,
        )
        .order_by(StockPrice.recorded_at.asc())
        .all()
    )

    # 每天只保留最後一筆
    daily: dict[str, StockPrice] = {}
    for row in rows:
        key = row.recorded_at.strftime("%Y-%m-%d")
        daily[key] = row

    return list(daily.values())


# ════════════════════════════════════════════════════
#  StockRecord — 持股買入記錄
# ════════════════════════════════════════════════════

def add_stock_record(
    db: Session,
    symbol: str,
    shares: float,
    price_per_share: float,
    total_cost: float,
    currency: str,
    purchased_at: datetime,
    note: str = "",
) -> StockRecord:
    """新增一筆持股買入記錄。"""
    record = StockRecord(
        symbol=symbol,
        shares=shares,
        price_per_share=price_per_share,
        total_cost=total_cost,
        currency=currency,
        purchased_at=purchased_at,
        note=note,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_all_stock_records(
    db: Session, symbol: Optional[str] = None
) -> list[StockRecord]:
    """取得所有持股記錄（可依標的篩選）。"""
    q = db.query(StockRecord)
    if symbol:
        q = q.filter(StockRecord.symbol == symbol)
    return q.order_by(StockRecord.purchased_at.desc()).all()


def get_stock_holdings_summary(db: Session, symbol: str) -> dict:
    """
    計算某標的的持股總覽：
    - 總股數
    - 總成本
    - 加權平均成本（總成本 / 總股數）
    """
    records = (
        db.query(StockRecord)
        .filter(StockRecord.symbol == symbol)
        .all()
    )

    if not records:
        return {
            "symbol": symbol,
            "total_shares": 0.0,
            "total_cost": 0.0,
            "weighted_avg_cost": None,
            "currency": None,
            "record_count": 0,
        }

    total_shares = sum(r.shares for r in records)
    total_cost   = sum(r.total_cost for r in records)
    weighted_avg = total_cost / total_shares if total_shares > 0 else None
    currency     = records[0].currency  # 同標的幣別相同

    return {
        "symbol":            symbol,
        "total_shares":      round(total_shares, 4),
        "total_cost":        round(total_cost, 2),
        "weighted_avg_cost": round(weighted_avg, 4) if weighted_avg else None,
        "currency":          currency,
        "record_count":      len(records),
    }


def delete_stock_record(db: Session, record_id: int) -> bool:
    """刪除指定持股記錄。"""
    record = db.query(StockRecord).filter(StockRecord.id == record_id).first()
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


# ════════════════════════════════════════════════════
#  StockAlertSetting — 通知條件
# ════════════════════════════════════════════════════

def get_stock_alert_setting(db: Session, symbol: str) -> Optional[StockAlertSetting]:
    """取得某標的的通知設定。"""
    return (
        db.query(StockAlertSetting)
        .filter(StockAlertSetting.symbol == symbol)
        .first()
    )


def update_stock_alert_setting(
    db: Session,
    symbol: str,
    target_price: Optional[float] = None,
    alert_3m_low: Optional[bool] = None,
    alert_6m_low: Optional[bool] = None,
    alert_below_avg: Optional[bool] = None,
    alert_3d_drop: Optional[bool] = None,
) -> Optional[StockAlertSetting]:
    """更新通知設定（只傳要改的欄位）。"""
    setting = get_stock_alert_setting(db, symbol)
    if not setting:
        return None

    if target_price    is not None: setting.target_price    = target_price
    if alert_3m_low    is not None: setting.alert_3m_low    = alert_3m_low
    if alert_6m_low    is not None: setting.alert_6m_low    = alert_6m_low
    if alert_below_avg is not None: setting.alert_below_avg = alert_below_avg
    if alert_3d_drop   is not None: setting.alert_3d_drop   = alert_3d_drop

    db.commit()
    db.refresh(setting)
    return setting
