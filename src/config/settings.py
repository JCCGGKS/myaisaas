"""配置层：以 YAML 文件为主配置源（仓库根 etc/settings.yml），环境变量 WA_* 可覆盖。

- 主配置写在 `etc/settings.yml`，便于在不改代码的前提下调整参数；
- 环境变量（WA_ 前缀，或 .env）优先级高于 YAML，生产可用其覆盖敏感/环境相关项；
- 类内默认值仅作为 YAML 缺失时的兜底。

开发默认使用 SQLite（零配置）；生产在 YAML / 环境变量设置 database_url 为 PostgreSQL
（如 postgresql+psycopg://user:pass@host:5432/watch_anything）。
"""
from pathlib import Path

import yaml
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

# 仓库根 etc/settings.yml（settings.py 位于 src/config/，故向上两级到仓库根）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_YAML = PROJECT_ROOT / "etc" / "settings.yml"


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """从 YAML 文件读取配置作为默认值（优先级低于环境变量 WA_*）。"""

    def __init__(self, settings_cls, yaml_file: Path = CONFIG_YAML):
        super().__init__(settings_cls)
        self._data = self._load(yaml_file)

    @staticmethod
    def _load(yaml_file: Path) -> dict:
        if not yaml_file.exists():
            return {}
        with open(yaml_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def get_field_value(self, field, field_name):
        # 与 pydantic-settings 内置 JSON 源一致：直接返回已解析的值
        return self._data.get(field_name), field_name, False

    def __call__(self) -> dict:
        return self._data


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
    # 对外链接基址（验证邮件/回调等拼接绝对 URL 用）
    backend_base_url: str = "http://127.0.0.1:8000"

    # CSRF 防护（Origin 校验，呼应 01_guest.md §8 第 1 步）
    # 对写请求（POST/PUT/PATCH/DELETE）校验 Origin 与「本站 Host 源」或下列受信前端源一致，
    # 不一致返回 403。测试用 WA_CSRF_ENABLED=false 关闭。生产务必把受信源改为真实前端源。
    csrf_enabled: bool = True
    csrf_trusted_origins: list[str] = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ]

    # 鉴权（轻量 MVP：token 即 user_id 的签名，仅用于打通流程）
    secret_key: str = "dev-insecure-secret-change-me-please-override"
    token_expire_hours: int = 24 * 30

    # Cookie 安全属性：生产必须为 True（仅 HTTPS 发送），测试环境置 False
    # 以兼容 TestClient 走 http 时不发送 secure cookie。
    cookie_secure: bool = True

    # 外部依赖（通知渠道用，未配置时渠道可绑定但发送走 Fake）
    telegram_bot_token: str = ""

    # 邮件发送（EmailChannel）：现阶段用本地 SMTP（MailHog/Mailpit，localhost:1025）。
    # 后续可切「个人 SMTP → 云厂 SMTP 中继 → 云厂 HTTP API」，仅改此处与 EmailBackend 实现。
    smtp_host: str = "localhost"   # 留空则 EmailChannel 退回 mock（不真发）
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False     # STARTTLS
    smtp_use_ssl: bool = False     # SMTP over SSL（与 use_tls 互斥）
    from_email: str = "noreply@watch-anything.local"

    # ---------- 监控 / LLM ----------
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
    source_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # 优先级：环境变量(WA_*) > YAML 文件 > 初始化值 > .env 文件 > 密钥文件
        return (
            env_settings,
            YamlConfigSettingsSource(settings_cls),
            init_settings,
            dotenv_settings,
            file_secret_settings,
        )


settings = Settings()
