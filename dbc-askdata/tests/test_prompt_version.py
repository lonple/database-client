from dbc_askdata.llm.profile import load_profile_from_dir, providers_root
from dbc_askdata.llm.prompt_version import bind_prompt_version
from dbc_askdata.observability.llm_exchange import build_llm_rounds_meta


def test_qwen_bindings_map_model_to_prompt_version() -> None:
    profile = load_profile_from_dir(providers_root() / "qwen")
    assert profile.prompt_version_for("qwen-max") == "1"
    assert profile.prompt_version_for("qwen3.6-flash") == "1"
    assert profile.prompt_version_for("unknown-model") == "unbound"
    assert "治理计分" in profile.get_prompt("build_system")
    assert "治理计分" in profile.get_prompt("build_system", model="qwen-max")


def test_llm_round_log_carries_prompt_version() -> None:
    bind_prompt_version("1")
    meta = build_llm_rounds_meta(
        messages=[{"role": "user", "content": "hi"}],
        response={"role": "assistant", "content": "ok"},
        role="chat_reply",
    )
    assert meta["promptVersion"] == "1"
    assert meta["llmRounds"][0]["promptVersion"] == "1"

    explicit = build_llm_rounds_meta(
        messages=[{"role": "user", "content": "hi"}],
        response={"role": "assistant", "content": "ok"},
        prompt_version="2",
    )
    assert explicit["promptVersion"] == "2"
