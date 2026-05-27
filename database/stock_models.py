"""
database/stock_models.py
股票 / ETF 追蹤所需的資料表定義。
刻意獨立成一個檔案，不動原本的 models.py。

新增三張表：
  StockPrice       — 歷史報價記錄
  StockRecord      — 我的持股買入記錄
  StockAlertSetting — 通知條件設定
"""
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, Boolean
from database.models import Base, engine   # 共用同一個 Base 和 engine


# ── 表四：歷史股價記錄 ─────────────────────────────────
class StockPrice(Base):
    __tablename__ = "stock_prices"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    symbol      = Column(String(10), nullable=False, index=True)   # VOO / 0050 / 00919
    price       = Column(Float, nullable=False)                    # 收盤 / 即時價
    open_price  = Column(Float, nullable=True)
    prev_close  = Column(Float, nullable=True)
    change_pct  = Column(Float, nullable=True)                     # 當日漲跌幅 %
    volume      = Column(Integer, nullable=True)
    recorded_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f"<StockPrice {self.symbol} {self.price} at {self.recorded_at}>"


# ── 表五：我的持股買入記錄 ─────────────────────────────
class StockRecord(Base):
    __tablename__ = "stock_records"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    symbol          = Column(String(10), nullable=False, index=True)
    shares          = Column(Float, nullable=False)      # 買入股數（支援小數，VOO 可能有零股）
    price_per_share = Column(Float, nullable=False)      # 成交單價
    total_cost      = Column(Float, nullable=False)      # 總成本（含手續費可手動填入）
    currency        = Column(String(5), nullable=False)  # USD / TWD
    purchased_at    = Column(DateTime, nullable=False)
    note            = Column(Text, nullable=True)

    def __repr__(self):
        return f"<StockRecord {self.symbol} x{self.shares} @ {self.price_per_share}>"


# ── 表六：股票通知條件設定 ─────────────────────────────
class StockAlertSetting(Base):
    __tablename__ = "stock_alert_settings"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    symbol          = Column(String(10), nullable=False, unique=True)
    target_price    = Column(Float, nullable=True)       # 自訂目標價（觸發買入）
    alert_3m_low    = Column(Boolean, default=True)      # 接近3個月低點
    alert_6m_low    = Column(Boolean, default=True)      # 接近半年低點
    alert_below_avg = Column(Boolean, default=True)      # 低於加權平均成本
    alert_3d_drop   = Column(Boolean, default=True)      # 三天跌幅 ≥ 5%

    def __repr__(self):
        return f"<StockAlertSetting {self.symbol} target={self.target_price}>"


# ── 建表 + 預設資料 ───────────────────────────────────
def init_stock_db():
    """建立股票相關資料表，並插入預設通知設定。"""
    from sqlalchemy.orm import sessionmaker
    from config import config

    Base.metadata.create_all(bind=engine)

    TRACKED_STOCKS = ["VOO", "0050", "00919"]

    Session = sessionmaker(bind=engine)
    with Session() as session:
        for symbol in TRACKED_STOCKS:
            exists = session.query(StockAlertSetting).filter_by(symbol=symbol).first()
            if not exists:
                session.add(StockAlertSetting(symbol=symbol))
        session.commit()

    print("✅ 股票資料表初始化完成")
