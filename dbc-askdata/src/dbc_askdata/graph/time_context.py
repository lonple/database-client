from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_TZ = ZoneInfo("Asia/Shanghai")
_WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def business_now() -> datetime:
    return datetime.now(_TZ)


def current_time_context() -> dict[str, str | int]:
    """注入 LLM 的业务当前时间（上海时区），避免模型按训练截止年臆测「今年」。"""
    now = business_now()
    return {
        "timezone": "Asia/Shanghai",
        "today": now.strftime("%Y-%m-%d"),
        "now": now.strftime("%Y-%m-%d %H:%M:%S"),
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "weekday": _WEEKDAYS[now.weekday()],
        "instruction": (
            f"当前业务时区为 Asia/Shanghai，今天是 {now.strftime('%Y-%m-%d')}（{_WEEKDAYS[now.weekday()]}），"
            f"今年是 {now.year} 年。"
            "解释「今天/昨天/本周/本月/今年/近N天」等相对时间时必须以此为准，禁止使用训练记忆中的旧年份。"
        ),
    }


def current_time_system_suffix() -> str:
    ctx = current_time_context()
    return str(ctx["instruction"])
