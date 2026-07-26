"""通知分发：与雷达解耦，由 ChannelFactory 实例化渠道并发送。"""
from business.notifier.channels import PushMessage
from business.notifier.factory import ChannelFactory
from utils.logging import get_logger

logger = get_logger(__name__)


async def dispatch(channel_type: str, recipient: str, msg: PushMessage) -> bool:
    """按渠道类型分发一条推送；返回是否发送成功。

    注：记录 Notification（防重发）属于监控循环/事件命中后的上层编排，
    这里只负责「选渠道 + 发送」，保持通知子系统的单一职责。
    """
    try:
        channel = ChannelFactory.create(channel_type)
        ok = await channel.send(recipient, msg)
        logger.info("通知分发 channel=%s recipient=%s result=%s", channel_type, recipient, ok)
        return ok
    except Exception as exc:  # 外部依赖失败不应中断主流程
        logger.error("通知分发失败 channel=%s recipient=%s: %s", channel_type, recipient, exc)
        return False
