"""
scraper/stock_scraper.py
抓取股票 / ETF 即時或收盤價。

資料來源：
  VOO（美股 ETF）→ Yahoo Finance API（非官方 v8）
  0050 / 00919  → Yahoo Finance（台股後綴 .TW）
"""
import requests
from datetime import datetime
from typing import Optional

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# 追蹤標的設定
STOCK_TARGETS = {
    "VOO":   {"yahoo_symbol": "VOO",      "currency": "USD", "label": "Vanguard S&P500"},
    "0050":  {"yahoo_symbol": "0050.TW",  "currency": "TWD", "label": "元大台灣50"},
    "00919": {"yahoo_symbol": "00919.TW", "currency": "TWD", "label": "群益台灣精選高息"},
}


def _fetch_yahoo(symbol: str) -> Optional[dict]:
    """
    透過 Yahoo Finance v8 API 抓取即時報價。
    回傳包含 price, open, prev_close, volume 的 dict，失敗回傳 None。
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "interval": "1d",
        "range":    "1d",
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        meta = data["chart"]["result"][0]["meta"]

        # 優先用 regularMarketPrice，盤後用 postMarketPrice
        price = meta.get("regularMarketPrice") or meta.get("postMarketPrice")
        if not price:
            print(f"[StockScraper] {symbol} 無法取得價格")
            return None

        return {
            "price":      round(float(price), 4),
            "open":       round(float(meta.get("regularMarketOpen", price)), 4),
            "prev_close": round(float(meta.get("chartPreviousClose", price)), 4),
            "volume":     int(meta.get("regularMarketVolume", 0)),
            "currency":   meta.get("currency", "USD"),
        }

    except Exception as e:
        print(f"[StockScraper] {symbol} 抓取失敗：{e}")
        return None


def fetch_stock(symbol: str) -> Optional[dict]:
    """
    抓取單一標的報價。
    回傳格式：
    {
      "symbol":     "VOO",
      "label":      "Vanguard S&P500",
      "price":      520.34,
      "open":       518.00,
      "prev_close": 519.00,
      "change_pct": 0.26,      # 漲跌幅 %
      "volume":     1234567,
      "currency":   "USD",
      "time":       "2026-05-27 10:30:00"
    }
    """
    target = STOCK_TARGETS.get(symbol)
    if not target:
        print(f"[StockScraper] 未知標的：{symbol}")
        return None

    raw = _fetch_yahoo(target["yahoo_symbol"])
    if not raw:
        return None

    change_pct = 0.0
    if raw["prev_close"] and raw["prev_close"] != 0:
        change_pct = round(
            (raw["price"] - raw["prev_close"]) / raw["prev_close"] * 100, 2
        )

    return {
        "symbol":     symbol,
        "label":      target["label"],
        "price":      raw["price"],
        "open":       raw["open"],
        "prev_close": raw["prev_close"],
        "change_pct": change_pct,
        "volume":     raw["volume"],
        "currency":   target["currency"],
        "time":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def fetch_all_stocks() -> dict:
    """
    一次抓取所有追蹤標的。
    回傳 { "VOO": {...}, "0050": {...}, "00919": {...} }
    """
    print(f"[StockScraper] 開始抓取 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    results = {}

    for symbol in STOCK_TARGETS:
        data = fetch_stock(symbol)
        if data:
            results[symbol] = data
            print(f"  [{symbol}] {data['label']} 價格：{data['price']} ({data['change_pct']:+.2f}%)")
        else:
            print(f"  [{symbol}] ⚠️  抓取失敗")

    if not results:
        print("[StockScraper] ⚠️  全部抓取失敗")

    return results
