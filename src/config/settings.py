"""配置层：以 YAML 文件为主配置源（仓库根 etc/settings.yml），环境变量 WA_* 可覆盖。

- 配置按「域」分组：每个一级键对应一个 struct（pydantic 子模型），如
  `email` / `telegram` / `llm` / `monitor` / `auth` / `app` / `csrf` / `guest` /
  `database` / `source`。读取时即 `settings.email.smtp_host` 这种结构化访问。
- 环境变量（WA_ 前缀，或 .env）优先级高于 YAML，生产可用其覆盖敏感/环境相关项；
  嵌套字段用双下划线分隔，如 `WA_EMAIL__SMTP_HOST`、`WA_LLM__API_KEY`。
- 类内默认值仅作为 YAML 缺失时的兜底。

开发默认使用 SQLite（零配置）；生产在 YAML / 环境变量设置 database.url 为 PostgreSQL
（如 postgresql+psycopg://user:pass@host:5432/watch_anything）。
"""
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

# 仓库根 etc/settings.yml（settings.py 位于 src/config/，故向上两级到仓库根）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_YAML = PROJECT_ROOT / "etc" / "settings.yml"


# ---------------- 各域 struct（子模型） ----------------

class DatabaseSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: str = "sqlite:///./watch_anything.db"


class GuestSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    radar_limit: int = 1
    channel_limit: int = 1


class AppSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = "Watch Anything"
    cors_origins: list[str] = ["*"]
    # 对外链接基址（验证邮件/回调等拼接绝对 URL 用）
    backend_base_url: str = "http://127.0.0.1:8000"


class CsrfSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # 对写请求（POST/PUT/PATCH/DELETE）校验 Origin 与「本站 Host 源」或下列受信前端源一致，
    # 不一致返回 403。测试用 WA_CSRF__ENABLED=false 关闭。生产务必把受信源改为真实前端源。
    enabled: bool = True
    trusted_origins: list[str] = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ]


class AuthSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # 鉴权（轻量 MVP：token 即 user_id 的签名，仅用于打通流程）
    secret_key: str = "dev-insecure-secret-change-me-please-override"
    token_expire_hours: int = 24 * 30
    # Cookie 安全属性：生产必须为 True（仅 HTTPS 发送），测试环境置 False
    # 以兼容 TestClient 走 http 时不发送 secure cookie。
    cookie_secure: bool = True


class EmailSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # 邮件发送（EmailChannel）：现阶段用本地 SMTP（MailHog/Mailpit，localhost:1025）。
    # 后续可切「个人 SMTP → 云厂 SMTP 中继 → 云厂 HTTP API」，仅改此处与 EmailBackend 实现。
    # 留空（smtp_host=""）则 EmailChannel 退回 mock（不真发）。
    smtp_host: str = ""
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False     # STARTTLS
    smtp_use_ssl: bool = False     # SMTP over SSL（与 use_tls 互斥）
    from_email: str = "noreply@watch-anything.local"


class TelegramSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # Telegram 机器人：bot_token 为空则发送走 mock；bot_username 用于生成绑定连接。
    bot_token: str = ""
    bot_username: str = ""


class LlmSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # LLM：OpenAI 兼容接口（可切 Claude / 国产模型）
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""          # 留空则解析/打分自动降级（不调用外部）
    model: str = "gpt-4o-mini"
    timeout: float = 20.0      # 单次 LLM 调用超时（秒）


class MonitorSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # 相关性/重要性打分阈值：低于丢弃，高于留存并推送
    relevance_threshold: float = 0.6
    # 调度：轻量 asyncio 循环扫描间隔（秒）
    scan_interval_seconds: int = 60
    # 是否在应用启动时自动开启监控调度（测试可置 False）
    autostart: bool = True
    # 单次扫描每个数据源最多处理的原始条目数（防爆炸）
    max_items_per_source: int = 20


class SourceSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # 数据源抓取：HTTP 超时与 UA
    fetch_timeout: float = 10.0
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """从 YAML 文件读取配置作为默认值（优先级低于环境变量 WA_*）。

    每个一级键对应一个 struct 子模型；返回其下的 dict 供 pydantic 校验为子模型。
    """

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
        # 直接返回 YAML 中同名一级键（应为 dict，交由 pydantic 校验为子模型）
        return self._data.get(field_name), field_name, False

    def __call__(self) -> dict:
        return self._data


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="WA_", extra="ignore")

    database: DatabaseSettings = DatabaseSettings()
    guest: GuestSettings = GuestSettings()
    app: AppSettings = AppSettings()
    csrf: CsrfSettings = CsrfSettings()
    auth: AuthSettings = AuthSettings()
    email: EmailSettings = EmailSettings()
    telegram: TelegramSettings = TelegramSettings()
    llm: LlmSettings = LlmSettings()
    monitor: MonitorSettings = MonitorSettings()
    source: SourceSettings = SourceSettings()

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
