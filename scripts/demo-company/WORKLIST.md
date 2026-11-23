# company demo 改造工作清单与验收

> 决策口径（2026-04-15）：方案甲同意图/同骨架≤2；核心 22 表不动；扩展表干净造数；BOARD 对齐 `govern_boundary`≥2；HITL 补全/拒答不改。

## W0 清单落盘

- [x] 本文件作为唯一验收对照

## W1 扩展表干净造数

- [x] 新增 `seed_extended.py`（只灌扩展表，不改 `seed_company.py` 核心 22 表逻辑）
- [x] `run.ps1` 在核心 seed 之后调用扩展 seed
- [x] 维表/字典/部门类区位类：小规模、按实际设计（`dim_lookup_*`、公司/职场/班次/科目等）
- [x] 其余扩展事实表：目标约 **1 万行**，时间跨约 **3 年**（与核心窗 `2023-10-01`～`2026-09-28` 对齐）
- [x] 已知主从金额关系干净：头 = Σ 明细（报价/采购申请/采购订单/凭证借贷平衡等）
- [x] 外键不悬空（可空列允许 NULL，不可空列必须命中父表）

**验收**

1. 核心 22 表行数与 seed 前一致（或仅允许扩展脚本 TRUNCATE 扩展表）— **PASS**（`hr_employee=1000`，`att_daily_record=496955` 未变）
2. 扩展非维表：抽样 ≥10 张，`count(*)` ∈ [8000, 12000] — **PASS**（40 张落在区间；主数据/按人派生表允许更小）
3. 维表：`dim_lookup_*` 有数据且远小于 1 万 — **PASS**（28 张，各 40 行）
4. SQL 抽检：报价/采购订单/凭证/采购申请头明细脏行数 = 0 — **PASS**

## W2 测评用例重生（方案甲 + BOARD 复杂）

- [x] `gen_cases.py` + `gen_cases_build.py`：同 `skeleton_id` 最多 **2** 条
- [x] 配额保持：SF/MJF/SA/MJA 各 100；GOVERN_FILTER/AGG 各 100（BOARD50 / HITL30 / 拒答20）
- [x] BOARD `expect_sql` 按 `govern_boundary.md` 计分 **≥2**
- [x] HITL_SUPPLEMENT / HITL_NO_SUPPLEMENT **不重构**
- [x] 重生 `cases/*.jsonl`

**验收**

1. 各类条数符合配额（SINGLE_FILTER +1 脏样例）— **PASS**（101/100/100/100/100/100）
2. 同 skeleton 出现次数 ≤2 — **PASS**（max=2，unique=351）
3. BOARD 含 ≥3 表 / EXISTS 嵌套等 — **PASS**（见 `TPL_GOV_B_001` 等）
4. HITL/拒答数量仍为条件/统计各 H30+R20 — **PASS**
5. `gen_cases.py --validate-only` — **PASS**（ok=561 fail=0 skip=40）

## W3 文档与入口

- [x] `README.md` / `eval/cases/README.md` / `eval/quota.md` 同步上述口径
- [x] 注明：核心可含测评脏包；扩展为干净演示数
- [x] `verify_acceptance.py` 可重复验收

## W4 总验收

- [x] 按 W1～W3 勾选并记录实际命令输出摘要

## 验收记录

| 时间 | 命令 | 结果 |
|------|------|------|
| 2026-04-15 | `seed_extended.py` | tables=178 empty=0；clean OK；core unchanged |
| 2026-04-15 | `verify_acceptance.py` | **ACCEPT:PASS** |
| 2026-04-15 | `eval/gen_cases.py --validate-only` | ok=561 fail=0 skip=40；skeleton max=2 |

复验：

```powershell
.\dbc-askdata\.venv\Scripts\python.exe .\scripts\demo-company\verify_acceptance.py
.\dbc-askdata\.venv\Scripts\python.exe .\scripts\demo-company\eval\gen_cases.py --validate-only
```
