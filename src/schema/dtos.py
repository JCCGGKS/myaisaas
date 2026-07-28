"""接口契约层：Pydantic 请求/响应 DTO。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RadarCreate(BaseModel):
    raw_query: str
    # 多通道：每个元素为绑定对象 {channel_type, recipient, verified, ...}（绑定跟随雷达）
    notify_channels: list[dict] = []


class RadarChannelsIn(BaseModel):
    # 雷达级绑定列表（元素为绑定对象，而非仅类型字符串）
    notify_channels: list[dict]


class RadarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_query: str
    # 绑定跟随雷达：list[dict]，每个元素含 channel_type/recipient/verified
    notify_channels: list[dict]
    status: str
    active: bool
    keywords: list
    sources: list
    filters: dict
    last_scan_at: datetime | None
    created_at: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_url: str | None
    relevance_score: float | None
    summary: str | None
    pushed_channels: list[str]
    created_at: datetime


class ChannelOut(BaseModel):
    type: str
    bound: bool
    verified: bool
    recipient: str | None = None  # 仅在该雷达已绑定时返回接收人


class ChannelBind(BaseModel):
    # channel_type 来自 URL 路径；recipient 为渠道接收人（webhook / 邮箱）
    # radar_id 必填：绑定跟随雷达，写入对应雷达的 notify_channels
    channel_type: str = ""
    recipient: str = ""
    radar_id: int | None = None


class AuthIn(BaseModel):
    email: str
    password: str
    name: str = ""


class AuthOut(BaseModel):
    token: str
    user_id: int
    is_guest: bool


class AuthMeOut(BaseModel):
    user_id: int
    email: str | None
    name: str | None
    is_guest: bool
