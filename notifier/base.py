"""
notifier/base.py
通知模組的抽象介面。
新增通知管道只需繼承這個 class。
"""
from abc import ABC, abstractmethod


class BaseNotifier(ABC):

    @abstractmethod
    def send(self, message: str) -> bool:
        """
        發送通知。
        回傳 True 表示成功，False 表示失敗。
        """
        ...

    def send_alerts(self, alerts: list[dict]) -> bool:
        """接收 alert_engine 回傳的 list，組合成一則訊息發送。"""
        if not alerts:
            return True

        lines = ["🔔 匯率提醒\n" + "─" * 20]
        for a in alerts:
            lines.append(a["message"])
        message = "\n\n".join(lines)

        return self.send(message)
