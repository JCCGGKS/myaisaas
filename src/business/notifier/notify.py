"""多通道通知分发：对雷达的多个渠道循环发送，并记录防重发。

- 绑定跟随雷达：接收人直接取自 radar.notify_channels（list[dict]，含 channel_type/recipient/verified）；
- 复用 notifier/dispatch（策略 + 工厂）做实际发送；
- 发送成功写入 Notification 记录，避免同一事件重复推送。
"""
from data.engine import Session
from business.notifier.channels import PushMessage
from business.notifier.dispatch import dispatch
from dao.notification_dao import exists as notification_exists
from dao.notification_dao import record
from model.event import Event
from model.radar import Radar
from model.user import User
from utils.logging import get_logger

logger = get_logger(__name__)


async def notify_radar(event: Event, radar: Radar, user: User, db: Session | None = None) -> list[str]:
    """向 radar.notify_channels（绑定对象列表）逐个推送 event；返回成功推送的渠道列表。

    去重：已存在 Notification(event_id, channel) 则跳过（权威持久去重），
    避免监控循环重跑导致同一事件重复推送。
    """
    pushed: list[str] = []
    msg = PushMessage(title=event.title, body=event.summary or event.title, url=event.source_url)
    for binding in radar.notify_channels or []:
        if not isinstance(binding, dict):
            continue
        channel = binding.get("channel_type")
        recipient = binding.get("recipient")
        if not channel or not recipient or not binding.get("verified"):
            logger.warning("跳过推送 channel=%s：未绑定 / 未验证 / 无接收人", channel)
            continue
        if db is not None and notification_exists(db, event.id, channel):
            logger.info("去重跳过 event_id=%s channel=%s（已推送过）", event.id, channel)
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
