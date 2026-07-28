"""通知渠道策略（Strategy）。

每个渠道实现 `send(recipient, msg) -> bool`：
- recipient 由各渠道解释：telegram=chat_id, email=address, webhook=url
- email 现阶段走本地 SMTP（MailHog 兼容），未配置 host 时退回 mock；测试注入 FakeChannel。
"""
import asyncio
import base64
import hashlib
import hmac
import json
import smtplib
import time
from dataclasses import dataclass

import httpx
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from abc import ABC, abstractmethod
from pywebpush import WebPushException, webpush

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
        self.token = token or settings.telegram.bot_token

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


class FeishuChannel(NotificationChannel):
    """飞书（Lark）群机器人：向绑定提供的 webhook URL 推送 interactive 卡片。

    recipient = 群机器人 webhook 地址（https://open.feishu.cn/open-apis/bot/v2/hook/xxx）。
    机器人开启「签名校验」时，需在 settings.feishu.sign_secret 配置对应密钥（与 webhook 同源）。
    """

    def __init__(
        self,
        webhook_url: str | None = None,
        sign_secret: str | None = None,
        timeout: float | None = None,
    ):
        self.webhook_url = webhook_url
        self.sign_secret = sign_secret if sign_secret is not None else settings.feishu.sign_secret
        self.timeout = timeout if timeout is not None else settings.feishu.timeout

    @staticmethod
    def _gen_sign(secret: str, timestamp: str) -> str:
        # 飞书签名：HMAC-SHA256(string_to_sign=时间戳+"\n"+密钥)，再做 base64
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

    def _build_payload(self, msg: PushMessage) -> dict:
        payload: dict = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "blue",
                    "title": {"tag": "plain_text", "content": msg.title},
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": msg.body}},
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "查看详情"},
                                "type": "primary",
                                "url": msg.url or "#",
                            }
                        ],
                    },
                ],
            },
        }
        # 开启签名校验则附加 timestamp + sign（与飞书服务端校验一致）
        if self.sign_secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = self._gen_sign(self.sign_secret, timestamp)
        return payload

    def _post(self, url: str, payload: dict) -> None:
        # 同步 HTTP，交由 dispatch 在线程池执行，避免阻塞事件循环
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code >= 400:
                resp.raise_for_status()
            try:
                data = resp.json()
            except Exception:
                return
            # 飞书：HTTP 200 但业务失败（code != 0），如 invalid webhook / sign
            if isinstance(data, dict) and data.get("code", 0) != 0:
                raise RuntimeError(f"feishu bot error: {data}")

    async def send(self, webhook_url: str, msg: PushMessage) -> bool:
        url = webhook_url or self.webhook_url
        if not url:
            logger.warning("Feishu 发送跳过：webhook url 为空")
            return False
        payload = self._build_payload(msg)
        try:
            await asyncio.to_thread(self._post, url, payload)
            logger.info("Feishu 发送成功 url=%s title=%s", url, msg.title)
            return True
        except Exception as exc:  # 外部依赖失败不应中断主流程
            logger.error("Feishu 发送失败 url=%s : %s", url, exc)
            return False


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
        self.host = smtp_host or settings.email.smtp_host
        self.port = smtp_port or settings.email.smtp_port
        self.user = smtp_user or settings.email.smtp_user
        self.password = smtp_password or settings.email.smtp_password
        self.use_tls = settings.email.smtp_use_tls if use_tls is None else use_tls
        self.use_ssl = settings.email.smtp_use_ssl if use_ssl is None else use_ssl
        self.from_email = from_email or settings.email.from_email

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


class WebpushChannel(NotificationChannel):
    """浏览器原生 Web Push：recipient 为 PushSubscription 的 JSON 字符串。

    用 VAPID 私钥经 pywebpush 推送到浏览器 endpoint。
    未配置 VAPID 私钥时降级为 mock（不真发，便于无密钥跑通流程）。
    """

    def __init__(
        self,
        vapid_private_key: str | None = None,
        subject: str | None = None,
        timeout: float | None = None,
    ):
        self.vapid_private_key = vapid_private_key or settings.webpush.vapid_private_key
        self.subject = subject or settings.webpush.subject
        self.timeout = settings.webpush.timeout if timeout is None else timeout

    async def send(self, subscription_json: str, msg: PushMessage) -> bool:
        if not subscription_json:
            logger.warning("WebPush 发送跳过：subscription 为空")
            return False
        # 开发降级：未配置 VAPID 私钥不真发，流程不中断
        if not self.vapid_private_key:
            logger.info("[mock] WebPush -> %s : %s", subscription_json[:40], msg.title)
            return True
        try:
            sub = json.loads(subscription_json)
        except Exception:
            logger.error("WebPush 发送失败：subscription 非合法 JSON")
            return False
        payload = json.dumps(
            {"title": msg.title, "body": msg.body, "url": msg.url or ""}
        ).encode("utf-8")
        endpoint = (sub.get("endpoint") or "")[:60]
        try:
            await asyncio.to_thread(
                webpush,
                subscription_info=sub,
                data=payload,
                vapid_private_key=self.vapid_private_key,
                vapid_claims={"sub": self.subject},
                timeout=self.timeout,
            )
            logger.info("WebPush 发送成功 endpoint=%s title=%s", endpoint, msg.title)
            return True
        except WebPushException as exc:
            # 404/410：订阅已失效（退订/轮换），调用方可据此移除
            if exc.response is not None and exc.response.status_code in (404, 410):
                logger.warning("WebPush 订阅失效(endpoint gone) endpoint=%s", endpoint)
                return False
            logger.error("WebPush 发送失败 endpoint=%s : %s", endpoint, exc)
            return False
        except Exception as exc:  # 外部依赖失败不应中断主流程
            logger.error("WebPush 发送失败 endpoint=%s : %s", endpoint, exc)
            return False


class FakeChannel(NotificationChannel):
    """测试用：记录发送调用，不真正发送。"""

    def __init__(self) -> None:
        self.sent: list[tuple[str, PushMessage]] = []

    async def send(self, recipient: str, msg: PushMessage) -> bool:
        self.sent.append((recipient, msg))
        return True
