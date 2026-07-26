"""鉴权业务（MVP 轻量）：注册/登录本质是把「当前游客」升级为真实账号。

- 游客达到限额后，前端引导注册/登录；
- 注册/登录时把 cookie 对应的游客数据（雷达 + 渠道绑定）合并进账号，
  并置 is_guest=False，从而解除限额；
- 返回签名 token，写入同一 wa_uid cookie。
"""
from sqlalchemy import update

from data.engine import Session
from dao.user_dao import get_by_email, get_by_id
from model.radar import Radar
from model.user import User
from utils.exceptions import AppError
from utils.logging import get_logger
from utils.security import hash_password, issue_token, verify_password

logger = get_logger(__name__)


def _merge_guest_into(db: Session, guest: User, target: User) -> None:
    """把 guest 的雷达与渠道绑定合并进 target，并删除 guest。"""
    db.execute(update(Radar).where(Radar.owner_id == guest.id).values(owner_id=target.id))
    merged = list(target.channel_bindings or [])
    for b in guest.channel_bindings or []:
        if not any(x.get("channel_type") == b.get("channel_type") for x in merged):
            merged.append(b)
    target.channel_bindings = merged
    db.delete(guest)
    db.flush()
    logger.info("游客数据合并 guest=%s -> user=%s", guest.id, target.id)


def upgrade_current_guest(
    db: Session, guest: User, email: str, password: str, require_existing: bool = False
) -> tuple[User, str]:
    email = (email or "").strip().lower()
    if not email or not password:
        raise AppError("email 与 password 必填", status_code=422)

    existing = get_by_email(db, email)
    if require_existing and (existing is None or existing.is_guest):
        raise AppError("账号不存在，请先注册", status_code=404)

    if existing is not None and existing.id == guest.id:
        # cookie 已对应此账号（已是登录态）：直接续期 token，不改动密码，
        # 避免登录态用户在登录页重提交时误把密码覆盖成输入值（含输错场景）。
        user = existing
    elif existing is not None:
        # 邮箱属于另一个真实账号：注册需校验密码一致（防冒用），登录需校验密码
        if not verify_password(password, existing.password):
            if require_existing:
                raise AppError("密码错误", status_code=401)
            raise AppError("该邮箱已注册，请用密码登录", status_code=409)
        _merge_guest_into(db, guest, existing)
        user = existing
    else:
        guest.email = email
        guest.password = hash_password(password)  # 哈希存储，不存明文
        user = guest

    user.is_guest = False
    db.add(user)
    db.commit()
    db.refresh(user)
    token = issue_token(user.id)
    logger.info("游客升级为账号 user_id=%s email=%s", user.id, email)
    return user, token


def get_user_by_token(db: Session, token: str) -> User | None:
    from utils.security import verify_token

    uid = verify_token(token)
    if uid is None:
        return None
    return get_by_id(db, uid)
