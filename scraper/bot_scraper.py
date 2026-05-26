"""
scraper/bot_scraper.py
從台灣銀行官網抓取即時匯率與黃金存摺牌價。

資料來源：
  匯率 → https://rate.bot.com.tw/xrt?Lang=zh-TW
  黃金 → https://rate.bot.com.tw/gold?Lang=zh-TW
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

CURRENCY_NAME_MAP = {
    "美金 (USD)": "USD",
    "日圓 (JPY)": "JPY",
}


def _fetch_page(url: str) -> Optional[BeautifulSoup]:
    """通用頁面抓取，失敗回傳 None。"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = "utf-8"
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"[Scraper] 抓取失敗 {url}：{e}")
        return None


def fetch_exchange_rates() -> dict:
    """
    抓取 USD、JPY 即期匯率。
    回傳格式：
    {
      "USD": {"currency": "USD", "buy": 31.73, "sell": 31.85, "time": "..."},
      "JPY": { ... }
    }
    """
    url = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
    soup = _fetch_page(url)
    if not soup:
        return {}

    results = {}
    table = soup.find("table")
    if not table:
        print("[Scraper] 找不到匯率表格")
        return {}

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        currency_text = cells[0].get_text(strip=True)

        for tw_name, code in CURRENCY_NAME_MAP.items():
            if tw_name in currency_text:
                try:
                    buy  = float(cells[2].get_text(strip=True))
                    sell = float(cells[3].get_text(strip=True))
                    results[code] = {
                        "currency": code,
                        "buy": buy,
                        "sell": sell,
                        "time": now_str
                    }
                except ValueError:
                    print(f"[Scraper] {code} 匯率解析失敗")

    return results


def fetch_gold_price() -> Optional[dict]:
    """
    抓取黃金存摺牌價。
    台銀頁面結構：
      列2 cells[2] = "4,587買進"  → 銀行賣出價（你買入的價格）
      列3 cells[2] = "4,533回售"  → 銀行買進價（你賣出的價格）
    """
    url = "https://rate.bot.com.tw/gold?Lang=zh-TW"
    soup = _fetch_page(url)
    if not soup:
        return None

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        table = soup.find("table")
        if not table:
            print("[Scraper] 找不到黃金表格")
            return None

        rows = [r for r in table.find_all("tr") if r.find_all("td")]

        def extract_number(text: str) -> Optional[float]:
            """從 '4,587買進' 這類字串取出數字部分。"""
            digits = text.replace(",", "")
            result = ""
            for ch in digits:
                if ch.isdigit() or ch == ".":
                    result += ch
                elif result:
                    break
            return float(result) if result else None

        sell = extract_number(rows[0].find_all("td")[2].get_text(strip=True))  # 銀行賣出
        buy  = extract_number(rows[1].find_all("td")[2].get_text(strip=True))  # 銀行買進

        if sell and buy:
            print(f"  [GOLD] 買:{buy}  賣:{sell}")
            return {
                "currency": "GOLD",
                "buy": buy,
                "sell": sell,
                "time": now_str
            }
        else:
            print(f"[Scraper] 黃金價格解析失敗：sell={sell} buy={buy}")

    except Exception as e:
        print(f"[Scraper] 黃金解析失敗：{e}")

    return None


def fetch_all() -> dict:
    """一次抓取所有追蹤標的（USD、JPY、黃金）。"""
    print(f"[Scraper] 開始抓取 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = fetch_exchange_rates()

    gold = fetch_gold_price()
    if gold:
        results["GOLD"] = gold

    for code, data in results.items():
        print(f"  [{code}] 買:{data['buy']}  賣:{data['sell']}")

    if not results:
        print("[Scraper] ⚠️  全部抓取失敗")

    return results
