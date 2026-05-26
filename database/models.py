"""
database/models.py
資料庫表格定義。使用 SQLAlchemy ORM，
換資料庫只需改 config.py 的 DATABASE_URL，這裡不動。
"""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, Float, String,
    DateTime, Text, Boolean
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from config import config


class Base(DeclarativeBase):
    pass


# ── 表一：歷史匯率記錄 ────────────────────────────────
class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    currency    = Column(String(10), nullable=False, index=True)
    buy_rate    = Column(Float, nullable=False)
    sell_rate   = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f"<ExchangeRate {self.currency} buy={self.buy_rate} at {self.recorded_at}>"


# ── 表二：我的換匯記錄 ────────────────────────────────
class ExchangeRecord(Base):
    __tablename__ = "exchange_records"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    currency       = Column(String(10), nullable=False, index=True)
    twd_amount     = Column(Float, nullable=False)
    foreign_amount = Column(Float, nullable=False)
    rate_used      = Column(Float, nullable=False)
    exchanged_at   = Column(DateTime, nullable=False)
    note           = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ExchangeRecord {self.currency} TWD={self.twd_amount} → {self.foreign_amount}>"


# ── 表三：通知條件設定 ────────────────────────────────
class AlertSetting(Base):
    __tablename__ = "alert_settings"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    currency        = Column(String(10), nullable=False, unique=True)
    target_rate     = Column(Float, nullable=True)
    alert_3m_low    = Column(Boolean, default=True)
    alert_6m_low    = Column(Boolean, default=True)
    alert_below_avg = Column(Boolean, default=True)

    def __repr__(self):
        return f"<AlertSetting {self.currency} target={self.target_rate}>"


# ── 資料庫初始化 ──────────────────────────────────────
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {}
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """建立所有表格，並插入預設的通知設定。"""
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        for currency in config.TRACKED_CURRENCIES:
            exists = session.query(AlertSetting).filter_by(currency=currency).first()
            if not exists:
                session.add(AlertSetting(currency=currency))
        session.commit()

    print("✅ 資料庫初始化完成")


def get_db():
    """Flask route 用的 session 產生器。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()"""
database/models.py
資料庫表格定義。使用 SQLAlchemy ORM，
換資料庫只需改 config.py 的 DATABASE_URL，這裡不動。
"""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, Float, String,
    DateTime, Text, Boolean
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from config import config


class Base(DeclarativeBase):
    pass


# ── 表一：歷史匯率記錄 ────────────────────────────────
class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    currency    = Column(String(10), nullable=False, index=True)
    buy_rate    = Column(Float, nullable=False)
    sell_rate   = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f"<ExchangeRate {self.currency} buy={self.buy_rate} at {self.recorded_at}>"


# ── 表二：我的換匯記錄 ────────────────────────────────
class ExchangeRecord(Base):
    __tablename__ = "exchange_records"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    currency       = Column(String(10), nullable=False, index=True)
    twd_amount     = Column(Float, nullable=False)
    foreign_amount = Column(Float, nullable=False)
    rate_used      = Column(Float, nullable=False)
    exchanged_at   = Column(DateTime, nullable=False)
    note           = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ExchangeRecord {self.currency} TWD={self.twd_amount} → {self.foreign_amount}>"


# ── 表三：通知條件設定 ────────────────────────────────
class AlertSetting(Base):
    __tablename__ = "alert_settings"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    currency        = Column(String(10), nullable=False, unique=True)
    target_rate     = Column(Float, nullable=True)
    alert_3m_low    = Column(Boolean, default=True)
    alert_6m_low    = Column(Boolean, default=True)
    alert_below_avg = Column(Boolean, default=True)

    def __repr__(self):
        return f"<AlertSetting {self.currency} target={self.target_rate}>"


# ── 資料庫初始化 ──────────────────────────────────────
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {}
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """建立所有表格，並插入預設的通知設定。"""
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        for currency in config.TRACKED_CURRENCIES:
            exists = session.query(AlertSetting).filter_by(currency=currency).first()
            if not exists:
                session.add(AlertSetting(currency=currency))
        session.commit()

    print("✅ 資料庫初始化完成")


def get_db():
    """Flask route 用的 session 產生器（用完自動關閉）。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
