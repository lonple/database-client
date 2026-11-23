# LLM Provider Profile（多套大模型插件）

按 `DBC_ASKDATA_LLM_PROVIDER`（或 `ADA_LLM_PROVIDER`）加载整套：**模型档位 + Adapter + 提示词包**。

## 内置厂商

| id | 目录 | 说明 |
|----|------|------|
| `qwen` | `qwen/` | 通义千问 / DashScope；请求体带 `enable_thinking=false` |

## 配置

```bash
# 必选语义
export DBC_ASKDATA_LLM_PROVIDER=qwen

# 可选覆盖（空则用 profile.yaml）
# export DBC_ASKDATA_LLM_MODEL=...
# export DBC_ASKDATA_LLM_MODEL_LIGHT=...
# export DBC_ASKDATA_LLM_BASE_URL=...
# export DBC_ASKDATA_LLM_PROFILE_PATH=/path/to/custom-profile-dir
```

优先级：`显式 model 参数` > `Settings 覆盖` > `profile.models`。

旧 `DBC_ASKDATA_AGENT_BUNDLE_PATH` 仅在**显式设置**时作为 models/prompts overlay。

## 新增厂商

1. 复制 `qwen/` 为 `providers/<id>/`
2. 改 `profile.yaml` 的 `id` / `models` / `adapter` / `default_base_url`
3. 按评测改 `prompts/*.md`
4. 在 `llm/registry.py` 的 `BUILTIN_PROVIDERS` 增加 `<id>`

图编排与 Tool 面**不要**写 `if provider == ...`；厂商差异只进 Adapter / Prompt pack。

## 提示词版本

`profile.yaml` 的 `prompt_bindings` 把**模型名**映射到 **prompt_version**。`prompt_pack_version` 是当前 `prompts/` 目录的包版本。模型升级后若要换文案：新增 `prompts/vN/`，把对应模型的 `prompt_version` 改成 `N`。每次 LLM 调用的 span 会写入 `promptVersion`。未出现在映射里的模型记为 `unbound`。

## 共享策略

`llm/prompts/_policy/` 可供 `{{include:policy/xxx.md}}` 引用，避免多厂商业务规则漂移。
