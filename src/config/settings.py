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

    # ---------- 监控 / LLM（均可通过环境变量 WA_* 覆盖，保证灵活性） ----------
    # LLM：OpenAI 兼容接口（可切 Claude / 国产模型）
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""          # 留空则解析/打分自动降级（不调用外部）
    llm_model: str = "gpt-4o-mini"
    llm_timeout: float = 20.0      # 单次 LLM 调用超时（秒）

    # 相关性/重要性打分阈值：低于丢弃，高于留存并推送
    relevance_threshold: float = 0.6

    # 调度：轻量 asyncio 循环扫描间隔（秒）
    scan_interval_seconds: int = 60
    # 是否在应用启动时自动开启监控调度（测试可置 False）
    monitor_autostart: bool = True

    # 单次扫描每个数据源最多处理的原始条目数（防爆炸）
    max_items_per_source: int = 20

    # 数据源抓取：HTTP 超时与 UA
    source_fetch_timeout: float = 10.0
    source_user_agent: str = "WatchAnything/0.1 (+https://...)"


settings = Settings()
