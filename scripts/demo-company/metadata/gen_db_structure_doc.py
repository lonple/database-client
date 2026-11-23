"""从 company schema 导出交付风格的《数据库结构说明》Markdown。"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:root@127.0.0.1:5432/postgres"
OUT = Path(__file__).resolve().parent / "db-structure.md"
EXTENDED_CATALOG = Path(__file__).resolve().parent / "extended_catalog.json"

# 表中文标题（仅表用途，精简；不含字段/口径补充）
TABLE_DESC: dict[str, str] = {
    "org_department": "组织部门表",
    "hr_job_level": "职级字典表",
    "hr_employee": "员工主数据表",
    "att_leave_type": "请假类型字典",
    "att_leave": "请假单",
    "att_overtime": "加班申请记录",
    "att_daily_record": "日考勤结果",
    "att_timesheet": "项目工时填报",
    "fin_salary_period": "薪资结算期间",
    "fin_salary_slip": "工资条",
    "fin_reimburse": "报销单头表",
    "fin_reimburse_item": "报销单明细",
    "fin_activity_budget": "部门活动预算",
    "fin_activity_expense": "部门活动花费",
    "crm_customer": "客户主数据",
    "prd_product": "产品主数据",
    "prd_product_cost": "产品月度成本",
    "sal_sales_order": "销售订单头表",
    "sal_sales_order_item": "销售订单明细",
    "prj_project": "交付项目",
    "prj_project_member": "项目成员",
    "prj_project_revenue": "项目回款记录",
}

# 字段说明：table.col -> 中文说明（枚举字段须写明 key=中文含义）
COL_DESC: dict[str, str] = {
    "org_department.id": "主键",
    "org_department.dept_code": "部门编码（业务唯一）",
    "org_department.dept_name": "部门名称",
    "org_department.parent_id": "上级部门 ID，根部门为空",
    "org_department.manager_emp_id": "部门负责人员工 ID",
    "org_department.status": "部门状态：`1`=有效",
    "org_department.created_at": "创建时间",
    "org_department.updated_at": "更新时间",
    "hr_job_level.id": "主键",
    "hr_job_level.level_code": "职级编码（如 P1/P2/M1）",
    "hr_job_level.level_name": "职级名称",
    "hr_job_level.rank_no": "职级排序号，数值越大级别越高",
    "hr_employee.id": "主键",
    "hr_employee.emp_no": "工号（业务键，唯一）",
    "hr_employee.name": "姓名",
    "hr_employee.gender": "性别：`M`=男、`F`=女；允许空",
    "hr_employee.dept_id": "所属部门 ID",
    "hr_employee.job_level_id": "职级 ID，关联 hr_job_level",
    "hr_employee.title": "职位名称",
    "hr_employee.hire_date": "入职日期",
    "hr_employee.leave_date": "离职日期；在职通常为空。判断是否在岗优先看本字段，勿仅依赖 employment_status",
    "hr_employee.employment_status": "人事状态：`active`=在职、`resigned`=离职（库中存在 leave_date 非空但本字段仍为 active 的冲突行）",
    "hr_employee.email": "邮箱",
    "hr_employee.phone": "手机号",
    "hr_employee.base_city": "常驻城市",
    "hr_employee.created_at": "创建时间",
    "hr_employee.updated_at": "更新时间",
    "att_leave_type.id": "主键",
    "att_leave_type.type_code": "请假类型编码：`annual`=年假、`sick`=病假、`personal`=事假、`marriage`=婚假、`maternity`=产假、`compensatory`=调休",
    "att_leave_type.type_name": "请假类型名称",
    "att_leave_type.is_paid": "是否带薪：`true`=带薪、`false`=不带薪",
    "att_leave_type.deduct_attendance": "是否扣考勤：`true`=扣考勤、`false`=不扣",
    "att_leave.id": "主键",
    "att_leave.emp_id": "请假员工 ID",
    "att_leave.leave_type_id": "请假类型 ID，关联 att_leave_type；允许空（脏数据）",
    "att_leave.start_at": "请假开始时间",
    "att_leave.end_at": "请假结束时间",
    "att_leave.leave_days": "请假天数（可含半天）",
    "att_leave.reason": "请假事由",
    "att_leave.status": "审批状态：`draft`=草稿、`approved`=已通过、`rejected`=已驳回、`cancelled`=已取消",
    "att_leave.approved_by": "审批人员工 ID",
    "att_leave.approved_at": "审批时间",
    "att_leave.created_at": "创建时间",
    "att_overtime.id": "主键",
    "att_overtime.emp_id": "加班员工 ID",
    "att_overtime.project_id": "关联项目 ID，可空",
    "att_overtime.overtime_date": "加班日期",
    "att_overtime.start_at": "加班开始时间",
    "att_overtime.end_at": "加班结束时间",
    "att_overtime.hours": "加班小时数",
    "att_overtime.ot_type": "加班类型：`workday`=工作日加班、`weekend`=周末加班、`holiday`=节假日加班",
    "att_overtime.compensate_type": "补偿方式：`pay`=加班费、`leave`=调休",
    "att_overtime.status": "审批状态：`draft`=草稿、`approved`=已通过、`rejected`=已驳回",
    "att_overtime.created_at": "创建时间",
    "att_daily_record.id": "主键",
    "att_daily_record.emp_id": "员工 ID",
    "att_daily_record.work_date": "考勤日期",
    "att_daily_record.check_in_at": "签到时间",
    "att_daily_record.check_out_at": "签退时间",
    "att_daily_record.work_hours": "出勤工时（小时）",
    "att_daily_record.late_minutes": "迟到分钟数",
    "att_daily_record.early_leave_minutes": "早退分钟数",
    "att_daily_record.attendance_status": "当日考勤状态：`normal`=正常、`late`=迟到、`early`=早退、`leave`=请假、`absent`=缺勤",
    "att_daily_record.source": "数据来源：`device`=打卡设备、`manual`=手工补录",
    "att_daily_record.created_at": "创建时间",
    "att_timesheet.id": "主键",
    "att_timesheet.emp_id": "填报员工 ID",
    "att_timesheet.project_id": "项目 ID，可空",
    "att_timesheet.work_date": "填报日期",
    "att_timesheet.hours": "填报工时（小时）",
    "att_timesheet.work_type": "工时类型：`develop`=开发、`test`=测试、`implement`=实施、`support`=支持、`manage`=管理",
    "att_timesheet.remark": "备注",
    "att_timesheet.status": "审批状态：`draft`=草稿、`submitted`=已提交、`approved`=已通过",
    "att_timesheet.created_at": "创建时间",
    "fin_salary_period.id": "主键",
    "fin_salary_period.period_code": "薪资月编码，格式 YYYY-MM",
    "fin_salary_period.year_month": "所属年月（取月首日）",
    "fin_salary_period.pay_date": "发薪日期",
    "fin_salary_period.status": "期间状态：`open`=开放（未关账）、`closed`=已关账",
    "fin_salary_slip.id": "主键",
    "fin_salary_slip.period_id": "薪资期间 ID，关联 fin_salary_period",
    "fin_salary_slip.emp_id": "员工 ID",
    "fin_salary_slip.dept_id": "发薪时部门 ID",
    "fin_salary_slip.base_salary": "基本工资",
    "fin_salary_slip.allowance": "津贴",
    "fin_salary_slip.overtime_pay": "加班费",
    "fin_salary_slip.bonus": "奖金",
    "fin_salary_slip.social_security_personal": "个人社保扣款",
    "fin_salary_slip.housing_fund_personal": "个人公积金扣款",
    "fin_salary_slip.tax": "个人所得税",
    "fin_salary_slip.other_deduction": "其他扣款",
    "fin_salary_slip.net_pay": "实发合计",
    "fin_salary_slip.currency": "币种：`CNY`=人民币",
    "fin_salary_slip.created_at": "创建时间",
    "fin_reimburse.id": "主键",
    "fin_reimburse.claim_no": "报销单号（业务键，唯一）",
    "fin_reimburse.emp_id": "提单人员工 ID",
    "fin_reimburse.dept_id": "费用归属部门 ID",
    "fin_reimburse.project_id": "关联项目 ID，可空",
    "fin_reimburse.claim_date": "报销申请日期（统计报销时间范围用本字段，不用 paid_at）",
    "fin_reimburse.title": "报销标题",
    "fin_reimburse.total_amount": "报销头表金额（单据总额口径）",
    "fin_reimburse.status": "报销状态：`draft`=草稿、`submitted`=已提交、`approved`=已通过、`rejected`=已驳回、`paid`=已付款",
    "fin_reimburse.paid_at": "付款时间；仅 status=paid 时通常有值",
    "fin_reimburse.created_at": "创建时间",
    "fin_reimburse_item.id": "主键",
    "fin_reimburse_item.claim_id": "报销单头 ID，关联 fin_reimburse",
    "fin_reimburse_item.category": "费用类别：`travel`=差旅、`meal`=餐费、`traffic`=交通、`office`=办公、`entertainment`=招待、`training`=培训",
    "fin_reimburse_item.amount": "明细金额",
    "fin_reimburse_item.occur_date": "费用发生日",
    "fin_reimburse_item.invoice_no": "发票号",
    "fin_reimburse_item.remark": "备注",
    "fin_activity_budget.id": "主键",
    "fin_activity_budget.activity_code": "活动编码（业务唯一）",
    "fin_activity_budget.activity_name": "活动名称",
    "fin_activity_budget.dept_id": "归属部门 ID",
    "fin_activity_budget.owner_emp_id": "活动负责人员工 ID",
    "fin_activity_budget.year": "预算年度",
    "fin_activity_budget.budget_amount": "预算金额",
    "fin_activity_budget.status": "预算状态：`planned`=已规划、`ongoing`=进行中、`closed`=已关闭",
    "fin_activity_budget.created_at": "创建时间",
    "fin_activity_expense.id": "主键",
    "fin_activity_expense.budget_id": "活动预算 ID，关联 fin_activity_budget",
    "fin_activity_expense.expense_date": "花费日期",
    "fin_activity_expense.category": "花费类别：`catering`=餐饮、`venue`=场地、`gift`=礼品、`transport`=交通、`other`=其他",
    "fin_activity_expense.amount": "花费金额",
    "fin_activity_expense.payee": "收款方",
    "fin_activity_expense.remark": "备注",
    "fin_activity_expense.status": "状态：`draft`=草稿、`approved`=已通过、`paid`=已付款",
    "fin_activity_expense.created_at": "创建时间",
    "crm_customer.id": "主键",
    "crm_customer.customer_code": "客户编码（业务键，唯一）",
    "crm_customer.customer_name": "客户名称",
    "crm_customer.industry": "所属行业",
    "crm_customer.region": "区域",
    "crm_customer.customer_level": "客户等级：`A`=战略大客户、`B`=重要客户、`C`=普通客户",
    "crm_customer.owner_emp_id": "销售负责人员工 ID",
    "crm_customer.status": "客户状态：`active`=合作中、`churned`=已流失",
    "crm_customer.created_at": "创建时间",
    "prd_product.id": "主键",
    "prd_product.product_code": "产品编码（业务键，唯一）",
    "prd_product.product_name": "产品名称",
    "prd_product.product_line": "产品线",
    "prd_product.pricing_model": "计价模式：`subscription`=订阅、`license`=授权买断、`project`=项目制",
    "prd_product.list_price": "目录价",
    "prd_product.unit": "计量单位（如套/年、套、人月、场）",
    "prd_product.status": "产品状态：`on_sale`=在售、`off`=停售",
    "prd_product.created_at": "创建时间",
    "prd_product_cost.id": "主键",
    "prd_product_cost.product_id": "产品 ID，关联 prd_product",
    "prd_product_cost.year_month": "成本年月（取月首日）",
    "prd_product_cost.unit_cost": "单位成本",
    "prd_product_cost.cost_type": "成本类型：`license_cost`=授权成本、`cloud`=云资源成本、`support`=支持成本、`other`=其他",
    "prd_product_cost.remark": "备注",
    "sal_sales_order.id": "主键",
    "sal_sales_order.order_no": "订单号（业务键，唯一）",
    "sal_sales_order.customer_id": "客户 ID，关联 crm_customer",
    "sal_sales_order.owner_emp_id": "销售负责人员工 ID",
    "sal_sales_order.dept_id": "销售部门 ID",
    "sal_sales_order.order_date": "下单日期",
    "sal_sales_order.sign_date": "签约日期",
    "sal_sales_order.currency": "币种：`CNY`=人民币",
    "sal_sales_order.total_amount": "订单头金额",
    "sal_sales_order.status": "订单状态：`draft`=草稿、`signed`=已签约、`delivering`=交付中、`closed`=已关闭、`cancelled`=已取消；有效订单通常排除 cancelled/draft",
    "sal_sales_order.created_at": "创建时间",
    "sal_sales_order_item.id": "主键",
    "sal_sales_order_item.order_id": "订单头 ID，关联 sal_sales_order",
    "sal_sales_order_item.product_id": "产品 ID，关联 prd_product",
    "sal_sales_order_item.qty": "数量",
    "sal_sales_order_item.unit_price": "单价",
    "sal_sales_order_item.discount_rate": "折扣率（0~1，如 0.1 表示九折）",
    "sal_sales_order_item.amount": "行金额（折后）",
    "sal_sales_order_item.cost_amount": "行成本金额",
    "prj_project.id": "主键",
    "prj_project.project_code": "项目编号（业务键，唯一）",
    "prj_project.project_name": "项目名称",
    "prj_project.customer_id": "客户 ID，关联 crm_customer",
    "prj_project.project_type": "项目类型：`implementation`=实施交付、`custom_dev`=定制开发、`ops`=运维托管、`poc`=POC 验证",
    "prj_project.dept_id": "承接部门 ID",
    "prj_project.pm_emp_id": "项目经理员工 ID",
    "prj_project.start_date": "实际/立项开始日期",
    "prj_project.end_date": "实际结束日期；进行中可空",
    "prj_project.plan_end_date": "计划结束日期",
    "prj_project.contract_amount": "合同金额",
    "prj_project.status": "项目状态：`planning`=规划中、`active`=进行中、`closed`=已结项、`warranty`=质保中",
    "prj_project.created_at": "创建时间",
    "prj_project_member.id": "主键",
    "prj_project_member.project_id": "项目 ID，关联 prj_project",
    "prj_project_member.emp_id": "成员员工 ID",
    "prj_project_member.role": "项目角色：`pm`=项目经理、`dev`=开发、`qa`=测试、`implement`=实施、`support`=支持",
    "prj_project_member.join_date": "加入项目日期",
    "prj_project_member.leave_date": "离开项目日期；仍在项目中可空",
    "prj_project_member.allocation_pct": "投入占比（百分比，如 50 表示 50%）",
    "prj_project_revenue.id": "主键",
    "prj_project_revenue.project_id": "项目 ID，关联 prj_project",
    "prj_project_revenue.revenue_date": "回款/收入确认日期",
    "prj_project_revenue.revenue_type": "回款类型：`milestone`=里程碑款、`acceptance`=验收款、`monthly`=按月确认、`final`=尾款",
    "prj_project_revenue.amount": "应回/确认金额",
    "prj_project_revenue.received_amount": "已到账金额",
    "prj_project_revenue.invoice_no": "发票号",
    "prj_project_revenue.remark": "备注",
    "prj_project_revenue.created_at": "创建时间",
}

def _load_extended_catalog() -> None:
    """合并扩展表中文说明（由 gen_extended_schema.py 生成）。"""
    if not EXTENDED_CATALOG.is_file():
        return
    data = json.loads(EXTENDED_CATALOG.read_text(encoding="utf-8"))
    for tname, meta in (data.get("tables") or {}).items():
        if tname not in TABLE_DESC and meta.get("zh"):
            # 标题只用精简用途，去掉句号与字段向补充
            TABLE_DESC[tname] = str(meta["zh"]).strip().rstrip("。；;")
        for col, zh in (meta.get("columns") or {}).items():
            key = f"{tname}.{col}"
            if key not in COL_DESC and zh:
                COL_DESC[key] = str(zh)


_load_extended_catalog()

# 表输出顺序（按业务域；扩展表按库内字母序追加）
TABLE_ORDER = [
    "org_department",
    "hr_job_level",
    "hr_employee",
    "att_leave_type",
    "att_leave",
    "att_overtime",
    "att_daily_record",
    "att_timesheet",
    "fin_salary_period",
    "fin_salary_slip",
    "fin_reimburse",
    "fin_reimburse_item",
    "fin_activity_budget",
    "fin_activity_expense",
    "crm_customer",
    "prd_product",
    "prd_product_cost",
    "sal_sales_order",
    "sal_sales_order_item",
    "prj_project",
    "prj_project_member",
    "prj_project_revenue",
]


def _fmt_default(raw: str | None) -> str:
    if raw is None or raw == "":
        return "-"
    s = raw.strip()
    # nextval(...) 等
    if s.upper().startswith("NEXTVAL"):
        return "自增"
    if s.upper() == "CURRENT_TIMESTAMP":
        return "CURRENT_TIMESTAMP"
    if s.startswith("'") and s.endswith("'::"):
        # rare
        pass
    # 'active'::character varying → active
    if "::" in s:
        s = s.split("::", 1)[0]
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        s = s[1:-1]
    return s or "-"


def _fmt_type(data_type: str, udt: str, maxlen: int | None, prec: int | None, scale: int | None) -> str:
    dt = (data_type or "").lower()
    if dt == "character varying":
        return f"varchar({maxlen})" if maxlen else "varchar"
    if dt == "character":
        return f"char({maxlen})" if maxlen else "char"
    if dt == "numeric":
        if prec is not None and scale is not None:
            return f"numeric({prec},{scale})"
        return "numeric"
    if dt == "timestamp without time zone":
        return "timestamp"
    if dt == "timestamp with time zone":
        return "timestamptz"
    if dt in ("bigint", "integer", "smallint", "boolean", "date", "text"):
        return dt
    if udt:
        return udt
    return dt or "-"


def _guess_desc(table: str, col: str, db_comment: str | None = None) -> str:
    """优先文档字典（含枚举中文释义）；否则用库内 COMMENT；没有则留空。"""
    key = f"{table}.{col}"
    if key in COL_DESC and COL_DESC[key].strip():
        return COL_DESC[key].strip()
    if db_comment and db_comment.strip() and "???" not in db_comment and "�" not in db_comment:
        return db_comment.strip()
    # 不再用英文列名冒充「字段说明」
    return ""


def _table_title_zh(table: str, db_comment: str | None = None) -> str:
    """标题用中文用途：精简、去句号、去掉字段向补充。"""
    raw = (TABLE_DESC.get(table) or db_comment or "").strip()
    if "???" in raw or "�" in raw:
        raw = (TABLE_DESC.get(table) or "").strip()
    raw = raw.rstrip("。；;")
    # 截断分号/句号后的补充说明
    for sep in ("；", ";", "，业务", "；业务"):
        if sep in raw:
            raw = raw.split(sep, 1)[0].strip()
    return raw


def _short_field_label(desc: str) -> str:
    """一行摘要用：去掉枚举展开、括号与「关联…」等补充。"""
    s = (desc or "").strip()
    if not s or s == "-":
        return ""
    for sep in ("：", ":"):
        if sep in s:
            s = s.split(sep, 1)[0].strip()
            break
    s = re.sub(r"[（(][^）)]*[）)]", "", s).strip()
    for sep in ("，关联", ",关联", "；", ";"):
        if sep in s:
            s = s.split(sep, 1)[0].strip()
            break
    return s


def _field_summary_line(col_pairs: list[tuple[str, str, str]]) -> str:
    """字段名+类型+短说明压缩成一行：id bigint 主键|order_no varchar(32) 订单号"""
    parts: list[str] = []
    for name, typ, desc in col_pairs:
        label = _short_field_label(desc)
        bits = [name]
        typ_s = (typ or "").strip()
        if typ_s and typ_s != "-":
            bits.append(typ_s)
        if label:
            bits.append(label)
        parts.append(" ".join(bits))
    return "|".join(parts)


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        tables = [
            r["table_name"]
            for r in await conn.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'company' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
        ]
        # PK set
        pk_rows = await conn.fetch(
            """
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = 'company' AND tc.constraint_type = 'PRIMARY KEY'
            """
        )
        pks: dict[str, set[str]] = {}
        for r in pk_rows:
            pks.setdefault(r["table_name"], set()).add(r["column_name"])

        lines: list[str] = [
            "# company 库数据库结构说明",
            "",
            "> Schema：`company`（PostgreSQL）  ",
            "> 版本：company_eval_v2（含扩展表，合计约 200 张）  ",
            "> 说明：**唯一完整**交付用表结构文档。每表四段：英文标题 → 中文用途 → 字段一行摘要 → 完整字段表。",
            "> 枚举/状态类字段在「字段说明」中给出 key=中文含义；扩展表以 catalog/库注释为准。",
            "> 外键按子表分组的可读版见 [table-relations.md](./table-relations.md)。",
            "",
            "## 目录",
            "",
        ]
        ordered = [t for t in TABLE_ORDER if t in tables] + [t for t in tables if t not in TABLE_ORDER]
        for i, t in enumerate(ordered, 1):
            zh = _table_title_zh(t)
            if zh:
                lines.append(f"{i}. [{t}](#{t}) — {zh}")
            else:
                lines.append(f"{i}. [{t}](#{t})")
        lines.append("")

        # 库内表/列注释（优先）
        db_table_comments = {
            r["table_name"]: (r["comment"] or "").strip()
            for r in await conn.fetch(
                """
                SELECT c.relname AS table_name, obj_description(c.oid) AS comment
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'company' AND c.relkind = 'r'
                """
            )
        }
        db_col_comments = {
            (r["table_name"], r["column_name"]): (r["comment"] or "").strip()
            for r in await conn.fetch(
                """
                SELECT c.relname AS table_name, a.attname AS column_name,
                       col_description(c.oid, a.attnum) AS comment
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
                WHERE n.nspname = 'company' AND c.relkind = 'r'
                """
            )
        }

        for t in ordered:
            cols = await conn.fetch(
                """
                SELECT
                  column_name,
                  data_type,
                  udt_name,
                  character_maximum_length,
                  numeric_precision,
                  numeric_scale,
                  is_nullable,
                  column_default
                FROM information_schema.columns
                WHERE table_schema = 'company' AND table_name = $1
                ORDER BY ordinal_position
                """,
                t,
            )
            zh = _table_title_zh(t, db_table_comments.get(t))
            # 1) 英文标题  2) 中文用途  3) 字段一行摘要  4) 完整字段表
            lines.append(f"## {t}")
            lines.append("")
            if zh:
                lines.append(zh)
            if not cols:
                if not zh:
                    lines.append("_（无列）_")
                lines.append("")
                continue
            col_pairs: list[tuple[str, str, str]] = []
            detail_rows: list[str] = []
            for c in cols:
                name = c["column_name"]
                typ = _fmt_type(
                    c["data_type"],
                    c["udt_name"],
                    c["character_maximum_length"],
                    c["numeric_precision"],
                    c["numeric_scale"],
                )
                required = "是" if c["is_nullable"] == "NO" else "否"
                default = _fmt_default(c["column_default"])
                is_pk = "是" if name in pks.get(t, set()) else "否"
                desc = _guess_desc(t, name, db_col_comments.get((t, name)))
                col_pairs.append((name, typ, desc or ""))
                detail_rows.append(
                    f"| {name} | {desc or '-'} | `{typ}` | {required} | {default} | {is_pk} |"
                )
            lines.append(_field_summary_line(col_pairs))
            lines.append("")
            lines.append("| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |")
            lines.append("|----|----------|----------|----------|--------|----------|")
            lines.extend(detail_rows)
            lines.append("")

        fk_rows = await conn.fetch(
            """
            SELECT
              tc.table_name AS child_table,
              kcu.column_name AS child_column,
              ccu.table_name AS parent_table,
              ccu.column_name AS parent_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.table_schema = 'company'
              AND tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.table_name, kcu.column_name
            """
        )
        lines.extend(
            [
                "## 关联关系（全量外键）",
                "",
                f"> 以库内实际 FOREIGN KEY 为准，共 **{len(fk_rows)}** 条。",
                "> 按子表分组的可读版见 [table-relations.md](./table-relations.md)。",
                "",
                "| 从表.列 | 主表.列 |",
                "|---------|---------|",
            ]
        )
        for r in fk_rows:
            lines.append(
                f"| {r['child_table']}.{r['child_column']} | "
                f"{r['parent_table']}.{r['parent_column']} |"
            )
        lines.append("")

        OUT.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {OUT} tables={len(ordered)} fks={len(fk_rows)}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
