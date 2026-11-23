# 出题人口径（不对模型 / Tool 开放）

用于编写期望 SQL 与比对规则，避免测评金标自相矛盾。

## 在职员工

默认金标定义（除非用例显式另写）：

```text
leave_date IS NULL
OR leave_date > :as_of_date
```

**不要**仅用 `employment_status = 'active'`（库中存在 leave_date 非空但 status 仍为 active 的冲突行）。

若问题说「状态是在职/active」——才按 `employment_status` 过滤（用于测脏口径）。

## 报销金额

- 问「报销单金额 / 单据总额」→ 用头表 `fin_reimburse.total_amount`
- 造数保证：每单至少一行明细，且 `total_amount = Σ fin_reimburse_item.amount`（无头空/头≠明细/无明细）
- 问「明细合计」→ 对 `fin_reimburse_item` 聚合，结果应与头表一致
- 已付款：`status = 'paid'`（若题面写「已报销且已付款」则同时要求 paid）

## 销售订单有效

默认排除：`status IN ('cancelled', 'draft')` 之外视为有效，除非题面只要「已签约」等更窄集合。

## 时间

- 「上月 / 本季度 / 2025 年」按自然历，连接时区 Asia/Shanghai（日期列按 DATE 字面量）。
- 日考勤只含已生成工作日抽样，**不是**全员全工作日全覆盖。

## 中断不补全

期望：不产生有效业务结果集，或保持 HITL/拒答。  
`expect_sql` 可留空；`compare_mode = empty_or_refuse`。

## 维度汇总：同等唯一键补全

金标 SQL 只选业务侧唯一键（如 `dept_name`）。比对器按目标库维护同等唯一键家族；若问数返回 `dept_id`/`dept_code` 等，先查表补全到金标键再比对，勿在期望 SQL 里堆叠多列唯一键。
