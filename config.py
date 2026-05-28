"""
config.py
統一管理所有設定，從 .env 檔讀取。
換平台時只需在新平台設定相同的環境變數，程式碼不動。
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── 資料庫 ──────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///exchange_tracker.db")

    # ── LINE Messaging API ───────────────────────────
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    LINE_USER_ID: str = os.getenv("LINE_USER_ID", "")

    # ── Email 備用通知 ───────────────────────────────
    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_RECEIVER: str = os.getenv("EMAIL_RECEIVER", "")

    # ── 排程 ────────────────────────────────────────
    FETCH_INTERVAL_MINUTES: int = int(os.getenv("FETCH_INTERVAL_MINUTES", "60"))

    # ── Flask ────────────────────────────────────────
    SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # ── 追蹤標的 ─────────────────────────────────────
    TRACKED_CURRENCIES = ["USD", "JPY", "GOLD"]
    TRACKED_STOCKS = ["VOO", "0050.TW", "00919.TW"]

    # ── 觸發條件閾值 ──────────────────────────────────
    ALERT_THRESHOLD_PERCENT: float = 1.0
    LOW_PERIOD_MONTHS_SHORT: int = 3   # 3個月低點
    LOW_PERIOD_MONTHS_LONG: int = 6    # 半年低點


config = Config()
