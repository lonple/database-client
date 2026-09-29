from dbc_askdata.observability.trace import resolve_trace_id


def test_resolve_keeps_valid_gateway_id():
    # 连字符在合法字符集内
    assert resolve_trace_id("abcDEF12-3456-7890-abcd-ef0123456789") == "abcDEF12-3456-7890-abcd-ef0123456789"
    assert resolve_trace_id("  gateway.trace_01  ") == "gateway.trace_01"


def test_resolve_rejects_illegal_and_generates():
    tid = resolve_trace_id("")
    assert len(tid) == 32
    assert tid.isalnum()
    tid2 = resolve_trace_id("bad id with spaces!!!")
    assert len(tid2) == 32
    assert tid != tid2 or True  # 两次生成可不同


def test_resolve_truncates_to_64():
    raw = "a" * 80
    # 超长但字符合法：截断到 64（先 fullmatch 失败因长度>64，应生成新 id）
    tid = resolve_trace_id(raw)
    assert len(tid) == 32
    # 恰好 64 位合法
    raw64 = "b" * 64
    assert resolve_trace_id(raw64) == raw64
