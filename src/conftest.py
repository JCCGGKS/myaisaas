"""pytest 引导：把 src 加入路径，并为测试指定独立 SQLite 库。

必须在 import 任何应用模块之前设置 WA_DATABASE_URL（config.settings 在导入时读取）。
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# 测试使用独立配置（etc/settings.test.yml）：mock SMTP、监控不自启、保守默认值。
# 必须在导入任何应用模块之前设置，否则会误读 settings.local.yml。
os.environ["APP_ENV"] = "test"

_TMP = tempfile.mkdtemp(prefix="wa_test_")
os.environ["WA_DATABASE_URL"] = f"sqlite:///{_TMP}/watch_anything_test.db"
# 测试环境关闭网络依赖，渠道发送走 mock / Fake
os.environ["WA_TELEGRAM_BOT_TOKEN"] = ""
os.environ["WA_SMTP_HOST"] = ""
# 测试保持「需验证」语义（不自动验证），验证流程由 test_channel_bind 覆盖
os.environ["WA_EMAIL__AUTO_VERIFY"] = "false"
# TestClient 走 http，关闭 cookie 的 Secure 属性以便 cookie 能回传
os.environ["WA_COOKIE_SECURE"] = "false"
# 测试环境关闭 CSRF Origin 校验（TestClient 不发 Origin 头）；CSRF 本身由 test_csrf.py 单独覆盖
os.environ["WA_CSRF_ENABLED"] = "false"
