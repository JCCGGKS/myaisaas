"""配置层：从环境变量加载（pydantic-settings）。

开发默认使用 SQLite（零配置）；生产在 .env 设置 DATABASE_URL 为 PostgreSQL
（如 postgresql+psycopg://user:pass@host:5432/watch_anything）。
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="WA_", extra="ignore")

    # 数据库：开发用 SQLite 文件，生产切 PostgreSQL
    database_url: str = "sqlite:///./watch_anything.db"

    # 游客限额（MVP，见 AGENTS.md「游客模式与渠道绑定」）
    guest_radar_limit: int = 1
    guest_channel_limit: int = 1

    # 应用
    app_name: str = "Watch Anything"
    cors_origins: list[str] = ["*"]

    # 鉴权（轻量 MVP：token 即 user_id 的签名，仅用于打通流程）
    secret_key: str = "dev-insecure-secret-change-me"
    token_expire_hours: int = 24 * 30

    # 外部依赖（通知渠道用，未配置时渠道可绑定但发送走 Fake）
    telegram_bot_token: str = ""
    smtp_host: str = ""
    from_email: str = "noreply@watch-anything.local"


settings = Settings()
