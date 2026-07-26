"""通知渠道策略（Strategy）。

每个渠道实现 `send(recipient, msg) -> bool`：
- recipient 由各渠道解释：telegram=chat_id, email=address, webhook=url
- email 现阶段走本地 SMTP（MailHog 兼容），未配置 host 时退回 mock；测试注入 FakeChannel。
"""
import asyncio
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from abc import ABC, abstractmethod

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
    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        use_tls: bool | None = None,
        use_ssl: bool | None = None,
        from_email: str | None = None,
    ):
        self.host = smtp_host or settings.smtp_host
        self.port = smtp_port or settings.smtp_port
        self.user = smtp_user or settings.smtp_user
        self.password = smtp_password or settings.smtp_password
        self.use_tls = settings.smtp_use_tls if use_tls is None else use_tls
        self.use_ssl = settings.smtp_use_ssl if use_ssl is None else use_ssl
        self.from_email = from_email or settings.from_email

    def _build_message(self, address: str, msg: PushMessage) -> MIMEMultipart:
        m = MIMEMultipart("alternative")
        m["Subject"] = msg.title
        m["From"] = formataddr(("Watch Anything", self.from_email))
        m["To"] = address
        text = f"{msg.body}\n\n{msg.url or ''}"
        m.attach(MIMEText(text, "plain", "utf-8"))
        m.attach(MIMEText(self._render_html(msg), "html", "utf-8"))
        return m

    @staticmethod
    def _render_html(msg: PushMessage) -> str:
        url = msg.url or "#"
        return (
            '<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:480px">'
            f'<h3 style="margin:0 0 8px;color:#111">{msg.title}</h3>'
            f'<p style="color:#333;line-height:1.6">{msg.body}</p>'
            f'<p><a href="{url}" style="display:inline-block;padding:8px 14px;'
            'background:#2f6df6;color:#fff;border-radius:6px;text-decoration:none">查看详情</a></p>'
            "</div>"
        )

    def _smtp_send(self, message: MIMEMultipart) -> None:
        if self.use_ssl:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=10) as smtp:
                self._login_if_needed(smtp)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                self._login_if_needed(smtp)
                if self.use_tls:
                    smtp.starttls()
                smtp.send_message(message)

    def _login_if_needed(self, smtp: smtplib.SMTP) -> None:
        if self.user and self.password:
            smtp.login(self.user, self.password)

    async def send(self, address: str, msg: PushMessage) -> bool:
        if not address:
            logger.warning("Email 发送跳过：address 为空")
            return False
        # 未配置 SMTP host：退回 mock（流程不中断），便于无邮件服务时跑通
        if not self.host:
            logger.info("[mock] Email -> %s : %s", address, msg.title)
            return True
        message = self._build_message(address, msg)
        try:
            await asyncio.to_thread(self._smtp_send, message)
            logger.info("Email 发送成功 address=%s title=%s", address, msg.title)
            return True
        except Exception as exc:  # 发送失败不应中断主流程
            logger.error("Email 发送失败 address=%s : %s", address, exc)
            return False


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
