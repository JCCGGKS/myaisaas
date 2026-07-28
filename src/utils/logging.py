"""统一日志：所有业务日志经此获取 logger，禁止散用 print。

日志级别：DEBUG 记细节、INFO 记关键步骤、WARNING/ERROR 记异常。
注意：不得记录密钥、token 明文、用户隐私。

输出受配置（settings.log）控制：
- console_enabled：是否输出到控制台（stdout）；
- file_enabled：是否输出到文件；
- dir：日志文件根目录（相对路径基于仓库根，如 logs），写入 <dir>/watch_anything.log。
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path

from config.settings import PROJECT_ROOT, settings

_CONFIGURED = False
_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    cfg = settings.log
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # 控制台
    if cfg.console_enabled:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        root.addHandler(sh)

    # 文件（按仓库根解析目录；RotatingFileHandler 按配置做大小轮转，避免无限增长）
    if cfg.file_enabled:
        log_dir = Path(cfg.dir)
        if not log_dir.is_absolute():
            # 相对路径基于仓库根（与 etc/ 同级），保证 logs 落在项目根
            log_dir = PROJECT_ROOT / log_dir
        os.makedirs(log_dir, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_dir / "watch_anything.log",
            maxBytes=cfg.max_bytes,
            backupCount=cfg.backup_count,
            encoding="utf-8",
        )
        fh.setFormatter(formatter)
        root.addHandler(fh)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(name)
