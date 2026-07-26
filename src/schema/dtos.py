"""接口契约层：Pydantic 请求/响应 DTO。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RadarCreate(BaseModel):
    raw_query: str
    notify_channel: str = ""


class RadarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    raw_query: str
    notify_channel: str
    active: bool
    keywords: list
    sources: list
    created_at: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    source_url: str | None
    relevance_score: float | None
    created_at: datetime


class ChannelOut(BaseModel):
    type: str
    bound: bool
    verified: bool


class ChannelBind(BaseModel):
    # channel_type 来自 URL 路径，body 只需 recipient；这里允许缺省以兼容仅传 recipient
    channel_type: str = ""
    recipient: str = ""


class AuthIn(BaseModel):
    email: str
    password: str


class AuthOut(BaseModel):
    token: str
    user_id: int
    is_guest: bool
