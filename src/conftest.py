"""pytest 引导：把 src 加入路径，并为测试指定独立 SQLite 库。

必须在 import 任何应用模块之前设置 WA_DATABASE_URL（config.settings 在导入时读取）。
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

_TMP = tempfile.mkdtemp(prefix="wa_test_")
os.environ["WA_DATABASE_URL"] = f"sqlite:///{_TMP}/watch_anything_test.db"
# 测试环境关闭网络依赖，渠道发送走 mock / Fake
os.environ["WA_TELEGRAM_BOT_TOKEN"] = ""
os.environ["WA_SMTP_HOST"] = ""
# TestClient 走 http，关闭 cookie 的 Secure 属性以便 cookie 能回传
os.environ["WA_COOKIE_SECURE"] = "false"
