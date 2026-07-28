"""渠道工厂（Factory）：按 channel_type 实例化策略，新增渠道零改分发代码。"""
from business.notifier.channels import (
    EmailChannel,
    FeishuChannel,
    NotificationChannel,
    TelegramChannel,
    WebhookChannel,
    WebpushChannel,
)
from utils.logging import get_logger

logger = get_logger(__name__)


class ChannelFactory:
    _registry = {
        "telegram": TelegramChannel,
        "email": EmailChannel,
        "webhook": WebhookChannel,
        "feishu": FeishuChannel,
        "webpush": WebpushChannel,
    }

    @classmethod
    def create(cls, channel_type: str, **config) -> NotificationChannel:
        if channel_type not in cls._registry:
            raise ValueError(f"unknown channel: {channel_type}")
        logger.debug("实例化渠道策略 type=%s", channel_type)
        return cls._registry[channel_type](**config)

    @classmethod
    def register(cls, name: str, klass: type) -> None:
        """扩展点：新增渠道只注册，不改分发逻辑（开闭原则）。"""
        cls._registry[name] = klass
