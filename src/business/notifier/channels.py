"""通知渠道策略（Strategy）。

每个渠道实现 `send(recipient, msg) -> bool`：
- recipient 由各渠道解释：telegram=chat_id, email=address, webhook=url
- MVP 未配置真实凭证时，仅记日志并返回 True（流程不中断）；测试注入 FakeChannel。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from config.settings import settings
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PushMessage:
    title: str
    body: str
    url: str | None = None


class NotificationChannel(ABC):
    @abstractmethod
    async def send(self, recipient: str, msg: PushMessage) -> bool:
        ...


class TelegramChannel(NotificationChannel):
    def __init__(self, token: str | None = None):
        self.token = token or settings.telegram_bot_token

    async def send(self, chat_id: str, msg: PushMessage) -> bool:
        if not chat_id:
            logger.warning("Telegram 发送跳过：chat_id 为空")
            return False
        # 未配置 token 时仅模拟（MVP 打通流程，不真正调用 Telegram API）
        if not self.token:
            logger.info("[mock] Telegram -> chat_id=%s : %s", chat_id, msg.title)
            return True
        logger.info("Telegram 发送 chat_id=%s", chat_id)
        # TODO: 真实调用 Telegram Bot API（sendMessage）
        return True


class EmailChannel(NotificationChannel):
    def __init__(self, smtp_host: str | None = None):
        self.smtp_host = smtp_host or settings.smtp_host

    async def send(self, address: str, msg: PushMessage) -> bool:
        if not address:
            logger.warning("Email 发送跳过：address 为空")
            return False
        if not self.smtp_host:
            logger.info("[mock] Email -> %s : %s", address, msg.title)
            return True
        logger.info("Email 发送 %s", address)
        # TODO: 真实 SMTP 发送
        return True


class WebhookChannel(NotificationChannel):
    async def send(self, url: str, msg: PushMessage) -> bool:
        if not url:
            logger.warning("Webhook 发送跳过：url 为空")
            return False
        logger.info("[mock] Webhook -> %s : %s", url, msg.title)
        # TODO: 真实 POST JSON 到 url
        return True


class FakeChannel(NotificationChannel):
    """测试用：记录发送调用，不真正发送。"""

    def __init__(self) -> None:
        self.sent: list[tuple[str, PushMessage]] = []

    async def send(self, recipient: str, msg: PushMessage) -> bool:
        self.sent.append((recipient, msg))
        return True
