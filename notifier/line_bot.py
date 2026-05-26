"""
notifier/line_bot.py
使用 LINE Messaging API 發送推播通知。

設定步驟（一次性）：
  1. 前往 https://developers.line.biz/ 建立 Provider
  2. 建立 Messaging API Channel
  3. 取得 Channel access token（長期憑證）
  4. 用 LINE app 加入你的 Bot 為好友
  5. 取得你自己的 LINE User ID
  6. 把 token 和 user_id 填入 .env
"""
import requests
from notifier.base import BaseNotifier
from config import config


class LineNotifier(BaseNotifier):

    def __init__(self):
        self.token   = config.LINE_CHANNEL_ACCESS_TOKEN
        self.user_id = config.LINE_USER_ID
        self.api_url = "https://api.line.me/v2/bot/message/push"

    def _is_configured(self) -> bool:
        return bool(self.token and self.user_id)

    def send(self, message: str) -> bool:
        if not self._is_configured():
            print("[LINE] ⚠️  LINE 尚未設定（請填寫 .env 的 LINE_* 欄位）")
            return False

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        payload = {
            "to": self.user_id,
            "messages": [{"type": "text", "text": message}]
        }

        try:
            resp = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                print("[LINE] ✅ 通知發送成功")
                return True
            else:
                print(f"[LINE] ❌ 發送失敗 {resp.status_code}：{resp.text}")
                return False
        except Exception as e:
            print(f"[LINE] ❌ 連線錯誤：{e}")
            return False
