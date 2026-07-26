"""通知分发：与雷达解耦，由 ChannelFactory 实例化渠道并发送（带重试）。"""
import asyncio

from business.notifier.channels import PushMessage
from business.notifier.factory import ChannelFactory
from utils.logging import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 3
BASE_BACKOFF = 0.5  # 秒，指数退避：0.5, 1, 2 ...


async def dispatch(channel_type: str, recipient: str, msg: PushMessage) -> bool:
    """按渠道类型分发一条推送；返回是否最终发送成功。

    - 渠道实例化失败（未知类型等）→ 记错误，返回 False。
    - send 抛异常 → 按指数退避重试最多 MAX_RETRIES 次。
    - send 返回 False（业务失败，如接收人为空）→ 不重试，直接 False。
    外部依赖失败不应中断主流程。
    """
    try:
        channel = ChannelFactory.create(channel_type)
    except Exception as exc:
        logger.error("渠道实例化失败 channel=%s: %s", channel_type, exc)
        return False

    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            ok = await channel.send(recipient, msg)
            if ok:
                logger.info("通知分发成功 channel=%s recipient=%s", channel_type, recipient)
                return True
            # 业务失败（如空接收人）：不重试
            logger.warning("通知分发返回失败 channel=%s recipient=%s（不重试）", channel_type, recipient)
            return False
        except Exception as exc:  # 外部依赖异常：重试
            last_exc = exc
            logger.warning(
                "通知分发失败(第%d/%d次) channel=%s recipient=%s: %s",
                attempt, MAX_RETRIES, channel_type, recipient, exc,
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BASE_BACKOFF * (2 ** (attempt - 1)))
    logger.error("通知分发最终失败 channel=%s recipient=%s: %s", channel_type, recipient, last_exc)
    return False
