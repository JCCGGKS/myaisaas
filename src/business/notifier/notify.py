"""多通道通知分发：对雷达的多个渠道循环发送，并记录防重发。

- 渠道接收人从 user.channel_bindings 中按 channel_type 解析；
- 复用 notifier/dispatch（策略 + 工厂）做实际发送；
- 发送成功写入 Notification 记录，避免同一事件重复推送。
"""
from data.engine import Session
from business.notifier.channels import PushMessage
from business.notifier.dispatch import dispatch
from dao.notification_dao import record
from model.event import Event
from model.radar import Radar
from model.user import User
from utils.logging import get_logger

logger = get_logger(__name__)


def _resolve_recipient(user: User, channel_type: str) -> str | None:
    for b in user.channel_bindings or []:
        if b.get("channel_type") == channel_type and b.get("verified") and b.get("recipient"):
            return b["recipient"]
    return None


async def notify_radar(event: Event, radar: Radar, user: User, db: Session | None = None) -> list[str]:
    """向 radar.notify_channels 逐个推送 event；返回成功推送的渠道列表。"""
    pushed: list[str] = []
    msg = PushMessage(title=event.title, body=event.summary or event.title, url=event.source_url)
    for channel in radar.notify_channels or []:
        recipient = _resolve_recipient(user, channel)
        if not recipient:
            logger.warning("跳过推送 channel=%s：未找到已验证接收人", channel)
            continue
        ok = await dispatch(channel, recipient, msg)
        if ok:
            pushed.append(channel)
            if db is not None:
                record(db, event.id, channel, recipient)
            logger.info("事件推送成功 event_id=%s channel=%s", event.id, channel)
    # 同步事件已推送渠道（即便无 db 传入也尽量更新内存对象）
    if pushed:
        event.pushed_channels = list(set((event.pushed_channels or []) + pushed))
    return pushed
