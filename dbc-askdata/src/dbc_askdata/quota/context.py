from __future__ import annotations

from contextvars import ContextVar

quota_user_id: ContextVar[int | None] = ContextVar("quota_user_id", default=None)
quota_eval_mode: ContextVar[bool] = ContextVar("quota_eval_mode", default=False)


def bind_quota(*, user_id: int | None, eval_mode: bool = False) -> None:
    quota_user_id.set(user_id)
    quota_eval_mode.set(bool(eval_mode))


def clear_quota() -> None:
    quota_user_id.set(None)
    quota_eval_mode.set(False)
