"""
notifier/email_notify.py
Email 備用通知（Gmail SMTP）。
LINE 掛掉或未設定時自動降級到 Email。

Gmail 設定步驟：
  1. 開啟「兩步驟驗證」
  2. 前往 Google 帳號 > 安全性 > 應用程式密碼
  3. 產生一組 16 碼應用程式密碼
  4. 填入 .env 的 EMAIL_PASSWORD
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from notifier.base import BaseNotifier
from config import config


class EmailNotifier(BaseNotifier):

    def __init__(self):
        self.sender   = config.EMAIL_SENDER
        self.password = config.EMAIL_PASSWORD
        self.receiver = config.EMAIL_RECEIVER
        self.enabled  = config.EMAIL_ENABLED

    def _is_configured(self) -> bool:
        return self.enabled and bool(self.sender and self.password and self.receiver)

    def send(self, message: str) -> bool:
        if not self._is_configured():
            print("[Email] ⚠️  Email 未啟用或未設定")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"]    = self.sender
            msg["To"]      = self.receiver
            msg["Subject"] = "🔔 匯率追蹤提醒"
            msg.attach(MIMEText(message, "plain", "utf-8"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender, self.password)
                server.sendmail(self.sender, self.receiver, msg.as_string())

            print("[Email] ✅ 通知發送成功")
            return True

        except Exception as e:
            print(f"[Email] ❌ 發送失敗：{e}")
            return False
