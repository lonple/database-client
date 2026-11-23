"""生成 company schema 扩展表（合计约 200 张）+ 元数据目录 + 表关系说明。

不灌数。核心 22 张仍由 01_schema.sql + seed_company.py 维护；
本脚本只产出 02_schema_extended.sql 与 metadata 附属文件。
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_SQL = HERE / "02_schema_extended.sql"
OUT_CATALOG = HERE / "metadata" / "extended_catalog.json"
# 全量外键关系由 metadata/export_table_relations.py 从库导出，勿在此覆盖

CORE_TABLES = {
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
}


def T(
    name: str,
    zh: str,
    cols: list[tuple[str, str, str]],
    fks: list[tuple[str, str]] | None = None,
    uniq: list[str] | None = None,
) -> dict:
    """cols: (col, sql_type, zh_comment)"""
    return {
        "name": name,
        "zh": zh,
        "cols": cols,
        "fks": fks or [],
        "uniq": uniq or [],
    }


def std_audit() -> list[tuple[str, str, str]]:
    return [
        ("status", "VARCHAR(16) NOT NULL DEFAULT 'active'", "状态"),
        ("remark", "VARCHAR(256)", "备注"),
        ("created_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP", "创建时间"),
        ("updated_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP", "更新时间"),
    ]


def code_name(prefix: str, code_zh: str = "编码", name_zh: str = "名称") -> list[tuple[str, str, str]]:
    return [
        (f"{prefix}_code", "VARCHAR(32) NOT NULL", code_zh),
        (f"{prefix}_name", "VARCHAR(128) NOT NULL", name_zh),
    ]


def build_tables() -> list[dict]:
    tables: list[dict] = []

    # ----- 组织扩展 -----
    tables += [
        T("org_company", "法人公司", code_name("company", "公司编码", "公司名称") + [("legal_name", "VARCHAR(256)", "法定名称"), ("tax_no", "VARCHAR(64)", "税号")] + std_audit(), uniq=["company_code"]),
        T("org_office", "办公职场", code_name("office", "职场编码", "职场名称") + [("city", "VARCHAR(32)", "城市"), ("address", "VARCHAR(256)", "地址"), ("company_id", "BIGINT", "所属公司 ID")] + std_audit(), fks=[("company_id", "org_company")], uniq=["office_code"]),
        T("org_cost_center", "成本中心", code_name("cc", "成本中心编码", "成本中心名称") + [("dept_id", "BIGINT", "关联部门 ID"), ("owner_emp_id", "BIGINT", "负责人员工 ID")] + std_audit(), fks=[("dept_id", "org_department"), ("owner_emp_id", "hr_employee")], uniq=["cc_code"]),
        T("org_position", "岗位编制", code_name("pos", "岗位编码", "岗位名称") + [("dept_id", "BIGINT", "所属部门 ID"), ("job_level_id", "BIGINT", "对应职级 ID"), ("headcount", "INT", "编制人数")] + std_audit(), fks=[("dept_id", "org_department"), ("job_level_id", "hr_job_level")], uniq=["pos_code"]),
        T("org_biz_unit", "业务单元", code_name("bu", "业务单元编码", "业务单元名称") + [("leader_emp_id", "BIGINT", "负责人员工 ID")] + std_audit(), fks=[("leader_emp_id", "hr_employee")], uniq=["bu_code"]),
        T("org_location", "地理区位", code_name("loc", "区位编码", "区位名称") + [("region", "VARCHAR(32)", "大区"), ("country", "VARCHAR(32)", "国家地区")] + std_audit(), uniq=["loc_code"]),
        T("org_dept_closure", "部门闭包表（祖先-后代）", [("ancestor_id", "BIGINT NOT NULL", "祖先部门 ID"), ("descendant_id", "BIGINT NOT NULL", "后代部门 ID"), ("depth", "INT NOT NULL", "层级深度")], fks=[("ancestor_id", "org_department"), ("descendant_id", "org_department")], uniq=["ancestor_id", "descendant_id"]),
        T("org_dept_change", "部门变更记录", [("dept_id", "BIGINT NOT NULL", "部门 ID"), ("change_type", "VARCHAR(32)", "变更类型"), ("old_parent_id", "BIGINT", "原上级部门 ID"), ("new_parent_id", "BIGINT", "新上级部门 ID"), ("effective_date", "DATE", "生效日期"), ("operator_emp_id", "BIGINT", "操作人员工 ID")] + std_audit(), fks=[("dept_id", "org_department"), ("operator_emp_id", "hr_employee")]),
        T("org_seal", "公司印章台账", code_name("seal", "印章编码", "印章名称") + [("company_id", "BIGINT", "所属公司 ID"), ("keeper_emp_id", "BIGINT", "保管人员工 ID")] + std_audit(), fks=[("company_id", "org_company"), ("keeper_emp_id", "hr_employee")], uniq=["seal_code"]),
        T("org_announcement", "内部公告", [("title", "VARCHAR(256) NOT NULL", "标题"), ("content", "TEXT", "正文"), ("publisher_emp_id", "BIGINT", "发布人员工 ID"), ("publish_at", "TIMESTAMP", "发布时间"), ("scope", "VARCHAR(32)", "发布范围")] + std_audit(), fks=[("publisher_emp_id", "hr_employee")]),
    ]

    # ----- 人事扩展 -----
    hr_extra = [
        ("hr_contract", "劳动合同", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("contract_no", "VARCHAR(64)", "合同编号"), ("contract_type", "VARCHAR(32)", "合同类型"), ("start_date", "DATE", "开始日期"), ("end_date", "DATE", "结束日期"), ("sign_company_id", "BIGINT", "签约公司 ID")], [("emp_id", "hr_employee"), ("sign_company_id", "org_company")]),
        ("hr_probation", "试用期考核", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("plan_end_date", "DATE", "计划转正日"), ("actual_end_date", "DATE", "实际转正日"), ("result", "VARCHAR(32)", "考核结果"), ("mentor_emp_id", "BIGINT", "导师员工 ID")], [("emp_id", "hr_employee"), ("mentor_emp_id", "hr_employee")]),
        ("hr_transfer", "人事调动", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("from_dept_id", "BIGINT", "调出部门 ID"), ("to_dept_id", "BIGINT", "调入部门 ID"), ("effective_date", "DATE", "生效日期"), ("transfer_type", "VARCHAR(32)", "调动类型")], [("emp_id", "hr_employee"), ("from_dept_id", "org_department"), ("to_dept_id", "org_department")]),
        ("hr_promotion", "晋升记录", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("from_level_id", "BIGINT", "原职级 ID"), ("to_level_id", "BIGINT", "新职级 ID"), ("effective_date", "DATE", "生效日期")], [("emp_id", "hr_employee"), ("from_level_id", "hr_job_level"), ("to_level_id", "hr_job_level")]),
        ("hr_resignation", "离职办理", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("apply_date", "DATE", "申请日期"), ("last_work_date", "DATE", "最后工作日"), ("reason_type", "VARCHAR(32)", "离职原因类型"), ("exit_interview", "TEXT", "离职面谈纪要")], [("emp_id", "hr_employee")]),
        ("hr_onboarding", "入职办理单", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("checklist_status", "VARCHAR(32)", "清单状态"), ("it_ready", "BOOLEAN", "IT 是否就绪"), ("badge_no", "VARCHAR(32)", "工牌号")], [("emp_id", "hr_employee")]),
        ("hr_bank_account", "员工薪酬账户", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("bank_name", "VARCHAR(64)", "开户行"), ("account_no", "VARCHAR(64)", "账号"), ("is_primary", "BOOLEAN", "是否主账户")], [("emp_id", "hr_employee")]),
        ("hr_emergency_contact", "紧急联系人", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("contact_name", "VARCHAR(64)", "联系人姓名"), ("relation", "VARCHAR(32)", "关系"), ("phone", "VARCHAR(32)", "电话")], [("emp_id", "hr_employee")]),
        ("hr_education", "教育经历", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("school", "VARCHAR(128)", "学校"), ("degree", "VARCHAR(32)", "学历"), ("major", "VARCHAR(64)", "专业"), ("graduate_date", "DATE", "毕业日期")], [("emp_id", "hr_employee")]),
        ("hr_work_history", "入职前工作经历", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("employer", "VARCHAR(128)", "原单位"), ("title", "VARCHAR(64)", "职位"), ("start_date", "DATE", "开始日期"), ("end_date", "DATE", "结束日期")], [("emp_id", "hr_employee")]),
        ("hr_performance_cycle", "绩效考核周期", code_name("cycle", "周期编码", "周期名称") + [("start_date", "DATE", "开始日期"), ("end_date", "DATE", "结束日期")], []),
        ("hr_performance_goal", "绩效目标", [("cycle_id", "BIGINT NOT NULL", "周期 ID"), ("emp_id", "BIGINT NOT NULL", "员工 ID"), ("goal_text", "TEXT", "目标描述"), ("weight_pct", "NUMERIC(6,2)", "权重百分比")], [("cycle_id", "hr_performance_cycle"), ("emp_id", "hr_employee")]),
        ("hr_performance_review", "绩效评估结果", [("cycle_id", "BIGINT NOT NULL", "周期 ID"), ("emp_id", "BIGINT NOT NULL", "员工 ID"), ("score", "NUMERIC(6,2)", "得分"), ("grade", "VARCHAR(16)", "等级"), ("reviewer_emp_id", "BIGINT", "评估人员工 ID")], [("cycle_id", "hr_performance_cycle"), ("emp_id", "hr_employee"), ("reviewer_emp_id", "hr_employee")]),
        ("hr_training_course", "培训课程", code_name("course", "课程编码", "课程名称") + [("hours", "NUMERIC(6,2)", "课时"), ("vendor", "VARCHAR(128)", "培训供应商")], []),
        ("hr_training_session", "培训场次", [("course_id", "BIGINT NOT NULL", "课程 ID"), ("start_at", "TIMESTAMP", "开始时间"), ("end_at", "TIMESTAMP", "结束时间"), ("location", "VARCHAR(128)", "地点"), ("trainer", "VARCHAR(64)", "讲师")], [("course_id", "hr_training_course")]),
        ("hr_training_enroll", "培训报名", [("session_id", "BIGINT NOT NULL", "场次 ID"), ("emp_id", "BIGINT NOT NULL", "员工 ID"), ("attend_status", "VARCHAR(32)", "出勤状态")], [("session_id", "hr_training_session"), ("emp_id", "hr_employee")]),
        ("hr_recruit_req", "招聘需求", code_name("req", "需求编码", "需求名称") + [("dept_id", "BIGINT", "需求部门 ID"), ("headcount", "INT", "需求人数"), ("job_level_id", "BIGINT", "目标职级 ID"), ("owner_emp_id", "BIGINT", "招聘负责人员工 ID")], [("dept_id", "org_department"), ("job_level_id", "hr_job_level"), ("owner_emp_id", "hr_employee")]),
        ("hr_candidate", "候选人", code_name("cand", "候选人编码", "候选人姓名") + [("phone", "VARCHAR(32)", "电话"), ("email", "VARCHAR(128)", "邮箱"), ("source", "VARCHAR(32)", "来源渠道")], []),
        ("hr_interview", "面试记录", [("candidate_id", "BIGINT NOT NULL", "候选人 ID"), ("req_id", "BIGINT", "招聘需求 ID"), ("interviewer_emp_id", "BIGINT", "面试官员工 ID"), ("interview_at", "TIMESTAMP", "面试时间"), ("result", "VARCHAR(32)", "结果")], [("candidate_id", "hr_candidate"), ("req_id", "hr_recruit_req"), ("interviewer_emp_id", "hr_employee")]),
        ("hr_offer", "录用 Offer", [("candidate_id", "BIGINT NOT NULL", "候选人 ID"), ("req_id", "BIGINT", "招聘需求 ID"), ("offer_amount", "NUMERIC(14,2)", "offer 年薪/月薪金额"), ("accept_status", "VARCHAR(32)", "接受状态"), ("join_date", "DATE", "预计入职日")], [("candidate_id", "hr_candidate"), ("req_id", "hr_recruit_req")]),
        ("hr_award", "奖惩记录", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("award_type", "VARCHAR(32)", "奖惩类型"), ("amount", "NUMERIC(12,2)", "金额"), ("occur_date", "DATE", "发生日期"), ("reason", "VARCHAR(256)", "事由")], [("emp_id", "hr_employee")]),
        ("hr_certificate", "员工证书资质", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("cert_name", "VARCHAR(128)", "证书名称"), ("cert_no", "VARCHAR(64)", "证书编号"), ("expire_date", "DATE", "到期日")], [("emp_id", "hr_employee")]),
        ("hr_family_member", "员工家属信息", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("member_name", "VARCHAR(64)", "家属姓名"), ("relation", "VARCHAR(32)", "关系"), ("birthday", "DATE", "生日")], [("emp_id", "hr_employee")]),
        ("hr_work_calendar", "工作日历", [("cal_date", "DATE NOT NULL", "日期"), ("day_type", "VARCHAR(16)", "日类型：work/weekend/holiday"), ("holiday_name", "VARCHAR(64)", "节假日名称")], []),
        ("hr_headcount_plan", "编制计划", [("dept_id", "BIGINT NOT NULL", "部门 ID"), ("year_month", "VARCHAR(7)", "年月 YYYY-MM"), ("plan_hc", "INT", "计划编制"), ("actual_hc", "INT", "实际在岗")], [("dept_id", "org_department")]),
    ]
    for name, zh, cols, fks in hr_extra:
        uniq = []
        if any(c[0].endswith("_code") for c in cols):
            code_col = next(c[0] for c in cols if c[0].endswith("_code"))
            uniq = [code_col]
        tables.append(T(name, zh, cols + std_audit(), fks=fks, uniq=uniq))

    # ----- 考勤扩展 -----
    att_extra = [
        ("att_shift", "班次定义", code_name("shift", "班次编码", "班次名称") + [("start_time", "TIME", "上班时间"), ("end_time", "TIME", "下班时间"), ("break_minutes", "INT", "休息分钟")], []),
        ("att_shift_assign", "班次排班", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("shift_id", "BIGINT NOT NULL", "班次 ID"), ("work_date", "DATE NOT NULL", "日期")], [("emp_id", "hr_employee"), ("shift_id", "att_shift")]),
        ("att_punch", "打卡流水", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("punch_at", "TIMESTAMP NOT NULL", "打卡时间"), ("punch_type", "VARCHAR(16)", "打卡类型"), ("device_no", "VARCHAR(64)", "设备号"), ("office_id", "BIGINT", "职场 ID")], [("emp_id", "hr_employee"), ("office_id", "org_office")]),
        ("att_travel", "出差申请", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("start_date", "DATE", "开始日期"), ("end_date", "DATE", "结束日期"), ("destination", "VARCHAR(128)", "目的地"), ("project_id", "BIGINT", "关联项目 ID")], [("emp_id", "hr_employee"), ("project_id", "prj_project")]),
        ("att_remote_work", "居家办公申请", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("work_date", "DATE", "日期"), ("reason", "VARCHAR(256)", "事由")], [("emp_id", "hr_employee")]),
        ("att_makeup_card", "补卡申请", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("work_date", "DATE", "日期"), ("punch_type", "VARCHAR(16)", "补卡类型"), ("reason", "VARCHAR(256)", "事由")], [("emp_id", "hr_employee")]),
        ("att_leave_balance", "假期余额", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("leave_type_id", "BIGINT NOT NULL", "请假类型 ID"), ("year", "INT", "年度"), ("balance_days", "NUMERIC(8,2)", "剩余天数")], [("emp_id", "hr_employee"), ("leave_type_id", "att_leave_type")]),
        ("att_ot_rule", "加班规则", code_name("rule", "规则编码", "规则名称") + [("weekday_rate", "NUMERIC(6,2)", "工作日倍率"), ("weekend_rate", "NUMERIC(6,2)", "周末倍率"), ("holiday_rate", "NUMERIC(6,2)", "节假日倍率")], []),
        ("att_monthly_summary", "月考勤汇总", [("emp_id", "BIGINT NOT NULL", "员工 ID"), ("year_month", "VARCHAR(7)", "年月"), ("work_days", "NUMERIC(8,2)", "出勤天"), ("leave_days", "NUMERIC(8,2)", "请假天"), ("ot_hours", "NUMERIC(8,2)", "加班小时")], [("emp_id", "hr_employee")]),
        ("att_device", "考勤设备", code_name("device", "设备编码", "设备名称") + [("office_id", "BIGINT", "职场 ID"), ("ip_addr", "VARCHAR(64)", "IP")], [("office_id", "org_office")]),
    ]
    for name, zh, cols, fks in att_extra:
        uniq = [c[0] for c in cols if c[0].endswith("_code")][:1]
        tables.append(T(name, zh, cols + std_audit(), fks=fks, uniq=uniq))

    # ----- 财务扩展 -----
    fin_extra = [
        ("fin_vendor", "供应商主数据", code_name("vendor", "供应商编码", "供应商名称") + [("tax_no", "VARCHAR(64)", "税号"), ("contact", "VARCHAR(64)", "联系人"), ("phone", "VARCHAR(32)", "电话")], []),
        ("fin_invoice", "进销项发票", [("invoice_no", "VARCHAR(64) NOT NULL", "发票号"), ("invoice_type", "VARCHAR(32)", "发票类型"), ("vendor_id", "BIGINT", "供应商 ID"), ("customer_id", "BIGINT", "客户 ID"), ("amount", "NUMERIC(14,2)", "含税金额"), ("tax_amount", "NUMERIC(14,2)", "税额"), ("invoice_date", "DATE", "开票日期")], [("vendor_id", "fin_vendor"), ("customer_id", "crm_customer")]),
        ("fin_payment", "付款单", [("payment_no", "VARCHAR(64) NOT NULL", "付款单号"), ("vendor_id", "BIGINT", "供应商 ID"), ("amount", "NUMERIC(14,2)", "付款金额"), ("pay_date", "DATE", "付款日期"), ("method", "VARCHAR(32)", "支付方式"), ("applicant_emp_id", "BIGINT", "申请人员工 ID")], [("vendor_id", "fin_vendor"), ("applicant_emp_id", "hr_employee")]),
        ("fin_receipt", "收款单", [("receipt_no", "VARCHAR(64) NOT NULL", "收款单号"), ("customer_id", "BIGINT", "客户 ID"), ("amount", "NUMERIC(14,2)", "收款金额"), ("receipt_date", "DATE", "收款日期"), ("project_id", "BIGINT", "项目 ID")], [("customer_id", "crm_customer"), ("project_id", "prj_project")]),
        ("fin_budget_year", "年度预算", [("year", "INT NOT NULL", "年度"), ("dept_id", "BIGINT", "部门 ID"), ("budget_amount", "NUMERIC(14,2)", "预算金额"), ("used_amount", "NUMERIC(14,2)", "已用金额")], [("dept_id", "org_department")]),
        ("fin_budget_line", "预算明细行", [("budget_id", "BIGINT NOT NULL", "年度预算 ID"), ("subject_code", "VARCHAR(32)", "科目编码"), ("subject_name", "VARCHAR(64)", "科目名称"), ("amount", "NUMERIC(14,2)", "金额")], [("budget_id", "fin_budget_year")]),
        ("fin_fixed_asset", "固定资产", code_name("asset", "资产编码", "资产名称") + [("category", "VARCHAR(32)", "资产类别"), ("purchase_date", "DATE", "购置日期"), ("original_value", "NUMERIC(14,2)", "原值"), ("custodian_emp_id", "BIGINT", "保管人员工 ID"), ("dept_id", "BIGINT", "使用部门 ID")], [("custodian_emp_id", "hr_employee"), ("dept_id", "org_department")]),
        ("fin_asset_depr", "资产折旧明细", [("asset_id", "BIGINT NOT NULL", "资产 ID"), ("year_month", "VARCHAR(7)", "年月"), ("depr_amount", "NUMERIC(14,2)", "折旧额")], [("asset_id", "fin_fixed_asset")]),
        ("fin_loan", "对公借款", [("loan_no", "VARCHAR(64)", "借款单号"), ("emp_id", "BIGINT NOT NULL", "借款人员工 ID"), ("amount", "NUMERIC(14,2)", "借款金额"), ("loan_date", "DATE", "借款日期"), ("due_date", "DATE", "应还日期")], [("emp_id", "hr_employee")]),
        ("fin_loan_repay", "借款核销", [("loan_id", "BIGINT NOT NULL", "借款 ID"), ("repay_amount", "NUMERIC(14,2)", "核销金额"), ("repay_date", "DATE", "核销日期"), ("reimburse_id", "BIGINT", "关联报销单 ID")], [("loan_id", "fin_loan"), ("reimburse_id", "fin_reimburse")]),
        ("fin_tax_period", "税务申报期间", [("year_month", "VARCHAR(7) NOT NULL", "年月"), ("tax_type", "VARCHAR(32)", "税种"), ("payable_amount", "NUMERIC(14,2)", "应纳税额"), ("paid_amount", "NUMERIC(14,2)", "已缴税额")], []),
        ("fin_bank_account", "公司银行账户", code_name("acct", "账户编码", "账户名称") + [("bank_name", "VARCHAR(64)", "开户行"), ("account_no", "VARCHAR(64)", "账号"), ("company_id", "BIGINT", "所属公司 ID")], [("company_id", "org_company")]),
        ("fin_bank_txn", "银行流水", [("acct_id", "BIGINT NOT NULL", "账户 ID"), ("txn_date", "DATE", "交易日期"), ("direction", "VARCHAR(8)", "收支方向"), ("amount", "NUMERIC(14,2)", "金额"), ("counterpart", "VARCHAR(128)", "对方户名"), ("ref_no", "VARCHAR(64)", "银行参考号")], [("acct_id", "fin_bank_account")]),
        ("fin_cost_allocation", "费用分摊", [("year_month", "VARCHAR(7)", "年月"), ("from_dept_id", "BIGINT", "分出部门 ID"), ("to_dept_id", "BIGINT", "分入部门 ID"), ("amount", "NUMERIC(14,2)", "分摊金额"), ("subject_code", "VARCHAR(32)", "科目编码")], [("from_dept_id", "org_department"), ("to_dept_id", "org_department")]),
        ("fin_gl_account", "会计科目", code_name("acct", "科目编码", "科目名称") + [("acct_type", "VARCHAR(32)", "科目类型"), ("parent_code", "VARCHAR(32)", "上级科目编码")], []),
        ("fin_journal", "会计凭证头", [("voucher_no", "VARCHAR(64) NOT NULL", "凭证号"), ("voucher_date", "DATE", "凭证日期"), ("period", "VARCHAR(7)", "会计期间"), ("created_by", "BIGINT", "制单人员工 ID")], [("created_by", "hr_employee")]),
        ("fin_journal_line", "会计凭证分录", [("journal_id", "BIGINT NOT NULL", "凭证头 ID"), ("acct_id", "BIGINT NOT NULL", "科目 ID"), ("debit", "NUMERIC(14,2)", "借方"), ("credit", "NUMERIC(14,2)", "贷方"), ("summary", "VARCHAR(256)", "摘要")], [("journal_id", "fin_journal"), ("acct_id", "fin_gl_account")]),
        ("fin_exchange_rate", "汇率", [("currency", "VARCHAR(8) NOT NULL", "币种"), ("rate_date", "DATE NOT NULL", "汇率日期"), ("rate", "NUMERIC(18,8)", "对人民币汇率")], []),
        ("fin_petty_cash", "备用金账户", [("dept_id", "BIGINT", "部门 ID"), ("keeper_emp_id", "BIGINT", "保管人员工 ID"), ("balance", "NUMERIC(14,2)", "余额")], [("dept_id", "org_department"), ("keeper_emp_id", "hr_employee")]),
        ("fin_petty_cash_txn", "备用金收支", [("petty_id", "BIGINT NOT NULL", "备用金账户 ID"), ("txn_date", "DATE", "日期"), ("direction", "VARCHAR(8)", "收支"), ("amount", "NUMERIC(14,2)", "金额"), ("reason", "VARCHAR(256)", "事由")], [("petty_id", "fin_petty_cash")]),
    ]
    for name, zh, cols, fks in fin_extra:
        uniq = []
        for c in cols:
            if c[0].endswith("_no") or c[0].endswith("_code"):
                uniq = [c[0]]
                break
        tables.append(T(name, zh, cols + std_audit(), fks=fks, uniq=uniq))

    # ----- CRM / 销售扩展 -----
    crm_sal = [
        ("crm_contact", "客户联系人", [("customer_id", "BIGINT NOT NULL", "客户 ID"), ("contact_name", "VARCHAR(64)", "联系人姓名"), ("title", "VARCHAR(64)", "职务"), ("phone", "VARCHAR(32)", "电话"), ("email", "VARCHAR(128)", "邮箱"), ("is_primary", "BOOLEAN", "是否主联系人")], [("customer_id", "crm_customer")]),
        ("crm_lead", "销售线索", code_name("lead", "线索编码", "线索名称") + [("source", "VARCHAR(32)", "来源"), ("owner_emp_id", "BIGINT", "负责销售员工 ID"), ("customer_id", "BIGINT", "转化客户 ID")], [("owner_emp_id", "hr_employee"), ("customer_id", "crm_customer")]),
        ("crm_opportunity", "商机", code_name("opp", "商机编码", "商机名称") + [("customer_id", "BIGINT", "客户 ID"), ("owner_emp_id", "BIGINT", "负责销售员工 ID"), ("amount", "NUMERIC(14,2)", "预计金额"), ("stage", "VARCHAR(32)", "阶段"), ("close_date", "DATE", "预计成交日")], [("customer_id", "crm_customer"), ("owner_emp_id", "hr_employee")]),
        ("crm_activity", "客户跟进活动", [("customer_id", "BIGINT", "客户 ID"), ("opp_id", "BIGINT", "商机 ID"), ("emp_id", "BIGINT", "跟进人员工 ID"), ("activity_type", "VARCHAR(32)", "活动类型"), ("activity_at", "TIMESTAMP", "活动时间"), ("content", "TEXT", "内容")], [("customer_id", "crm_customer"), ("opp_id", "crm_opportunity"), ("emp_id", "hr_employee")]),
        ("crm_visit", "客户拜访", [("customer_id", "BIGINT NOT NULL", "客户 ID"), ("emp_id", "BIGINT", "拜访人员工 ID"), ("visit_date", "DATE", "拜访日期"), ("purpose", "VARCHAR(256)", "目的"), ("result", "VARCHAR(256)", "结果")], [("customer_id", "crm_customer"), ("emp_id", "hr_employee")]),
        ("crm_complaint", "客户投诉", [("customer_id", "BIGINT NOT NULL", "客户 ID"), ("project_id", "BIGINT", "项目 ID"), ("title", "VARCHAR(256)", "标题"), ("severity_level", "VARCHAR(16)", "严重级别"), ("handler_emp_id", "BIGINT", "处理人员工 ID")], [("customer_id", "crm_customer"), ("project_id", "prj_project"), ("handler_emp_id", "hr_employee")]),
        ("crm_sla", "客户服务等级协议", [("customer_id", "BIGINT NOT NULL", "客户 ID"), ("sla_level", "VARCHAR(16)", "SLA 等级"), ("response_hours", "INT", "响应时限小时"), ("resolve_hours", "INT", "解决时限小时")], [("customer_id", "crm_customer")]),
        ("sal_quote", "销售报价单", code_name("quote", "报价单号", "报价名称") + [("customer_id", "BIGINT", "客户 ID"), ("owner_emp_id", "BIGINT", "销售员工 ID"), ("total_amount", "NUMERIC(14,2)", "总金额"), ("valid_until", "DATE", "有效期至")], [("customer_id", "crm_customer"), ("owner_emp_id", "hr_employee")]),
        ("sal_quote_item", "报价明细", [("quote_id", "BIGINT NOT NULL", "报价单 ID"), ("product_id", "BIGINT", "产品 ID"), ("qty", "NUMERIC(12,2)", "数量"), ("unit_price", "NUMERIC(14,2)", "单价"), ("amount", "NUMERIC(14,2)", "金额")], [("quote_id", "sal_quote"), ("product_id", "prd_product")]),
        ("sal_contract", "销售合同", code_name("contract", "合同编号", "合同名称") + [("customer_id", "BIGINT", "客户 ID"), ("order_id", "BIGINT", "关联订单 ID"), ("sign_date", "DATE", "签订日期"), ("amount", "NUMERIC(14,2)", "合同金额"), ("owner_emp_id", "BIGINT", "负责销售员工 ID")], [("customer_id", "crm_customer"), ("order_id", "sal_sales_order"), ("owner_emp_id", "hr_employee")]),
        ("sal_contract_milestone", "合同里程碑收款", [("contract_id", "BIGINT NOT NULL", "合同 ID"), ("milestone_name", "VARCHAR(128)", "里程碑名称"), ("due_date", "DATE", "应收日期"), ("amount", "NUMERIC(14,2)", "应收金额"), ("received_amount", "NUMERIC(14,2)", "已收金额")], [("contract_id", "sal_contract")]),
        ("sal_delivery", "发货/交付单", code_name("delivery", "交付单号", "交付说明") + [("order_id", "BIGINT", "订单 ID"), ("delivery_date", "DATE", "交付日期"), ("receiver", "VARCHAR(64)", "收货人")], [("order_id", "sal_sales_order")]),
        ("sal_delivery_item", "交付明细", [("delivery_id", "BIGINT NOT NULL", "交付单 ID"), ("product_id", "BIGINT", "产品 ID"), ("qty", "NUMERIC(12,2)", "数量")], [("delivery_id", "sal_delivery"), ("product_id", "prd_product")]),
        ("sal_return", "退货单", code_name("return", "退货单号", "退货说明") + [("order_id", "BIGINT", "订单 ID"), ("return_date", "DATE", "退货日期"), ("reason", "VARCHAR(256)", "原因")], [("order_id", "sal_sales_order")]),
        ("sal_commission_rule", "销售提成规则", code_name("rule", "规则编码", "规则名称") + [("rate_pct", "NUMERIC(6,2)", "提成比例"), ("product_id", "BIGINT", "适用产品 ID")], [("product_id", "prd_product")]),
        ("sal_commission", "销售提成明细", [("emp_id", "BIGINT NOT NULL", "销售员工 ID"), ("order_id", "BIGINT", "订单 ID"), ("year_month", "VARCHAR(7)", "年月"), ("amount", "NUMERIC(14,2)", "提成金额")], [("emp_id", "hr_employee"), ("order_id", "sal_sales_order")]),
        ("sal_price_list", "价格表", code_name("plist", "价格表编码", "价格表名称") + [("currency", "VARCHAR(8)", "币种"), ("effective_from", "DATE", "生效起"), ("effective_to", "DATE", "生效止")], []),
        ("sal_price_list_item", "价格表明细", [("plist_id", "BIGINT NOT NULL", "价格表 ID"), ("product_id", "BIGINT NOT NULL", "产品 ID"), ("unit_price", "NUMERIC(14,2)", "单价")], [("plist_id", "sal_price_list"), ("product_id", "prd_product")]),
        ("sal_target", "销售目标", [("emp_id", "BIGINT", "销售员工 ID"), ("dept_id", "BIGINT", "部门 ID"), ("year_month", "VARCHAR(7)", "年月"), ("target_amount", "NUMERIC(14,2)", "目标金额"), ("actual_amount", "NUMERIC(14,2)", "实际金额")], [("emp_id", "hr_employee"), ("dept_id", "org_department")]),
        ("sal_channel", "销售渠道", code_name("channel", "渠道编码", "渠道名称") + [("channel_type", "VARCHAR(32)", "渠道类型")], []),
    ]
    for name, zh, cols, fks in crm_sal:
        uniq = [c[0] for c in cols if c[0].endswith("_code") or c[0].endswith("_no")][:1]
        tables.append(T(name, zh, cols + std_audit(), fks=fks, uniq=uniq))

    # ----- 产品 / 项目扩展 -----
    prd_prj = [
        ("prd_product_line", "产品线", code_name("line", "产品线编码", "产品线名称") + [("owner_emp_id", "BIGINT", "负责人员工 ID")], [("owner_emp_id", "hr_employee")]),
        ("prd_product_version", "产品版本", [("product_id", "BIGINT NOT NULL", "产品 ID"), ("version_no", "VARCHAR(32)", "版本号"), ("release_date", "DATE", "发布日期"), ("changelog", "TEXT", "变更说明")], [("product_id", "prd_product")]),
        ("prd_feature", "产品功能点", [("product_id", "BIGINT NOT NULL", "产品 ID"), ("feature_code", "VARCHAR(32)", "功能编码"), ("feature_name", "VARCHAR(128)", "功能名称")], [("product_id", "prd_product")]),
        ("prd_license", "产品授权许可", [("product_id", "BIGINT NOT NULL", "产品 ID"), ("customer_id", "BIGINT", "客户 ID"), ("license_key", "VARCHAR(128)", "许可密钥"), ("seat_count", "INT", "席位数"), ("expire_date", "DATE", "到期日")], [("product_id", "prd_product"), ("customer_id", "crm_customer")]),
        ("prd_roadmap", "产品路线图项", [("product_id", "BIGINT NOT NULL", "产品 ID"), ("item_name", "VARCHAR(128)", "事项名称"), ("target_quarter", "VARCHAR(8)", "目标季度"), ("priority", "VARCHAR(16)", "优先级")], [("product_id", "prd_product")]),
        ("prj_milestone", "项目里程碑", [("project_id", "BIGINT NOT NULL", "项目 ID"), ("milestone_name", "VARCHAR(128)", "里程碑名称"), ("plan_date", "DATE", "计划日期"), ("actual_date", "DATE", "实际日期")], [("project_id", "prj_project")]),
        ("prj_task", "项目任务", [("project_id", "BIGINT NOT NULL", "项目 ID"), ("task_name", "VARCHAR(128)", "任务名称"), ("assignee_emp_id", "BIGINT", "负责人员工 ID"), ("plan_start", "DATE", "计划开始"), ("plan_end", "DATE", "计划结束"), ("progress_pct", "NUMERIC(6,2)", "进度百分比")], [("project_id", "prj_project"), ("assignee_emp_id", "hr_employee")]),
        ("prj_risk", "项目风险", [("project_id", "BIGINT NOT NULL", "项目 ID"), ("risk_title", "VARCHAR(256)", "风险标题"), ("level", "VARCHAR(16)", "风险等级"), ("owner_emp_id", "BIGINT", "责任人员工 ID"), ("mitigation", "TEXT", "缓解措施")], [("project_id", "prj_project"), ("owner_emp_id", "hr_employee")]),
        ("prj_issue", "项目问题单", [("project_id", "BIGINT NOT NULL", "项目 ID"), ("title", "VARCHAR(256)", "标题"), ("severity", "VARCHAR(16)", "严重级别"), ("reporter_emp_id", "BIGINT", "报告人员工 ID"), ("assignee_emp_id", "BIGINT", "处理人员工 ID")], [("project_id", "prj_project"), ("reporter_emp_id", "hr_employee"), ("assignee_emp_id", "hr_employee")]),
        ("prj_change_request", "项目变更申请", [("project_id", "BIGINT NOT NULL", "项目 ID"), ("title", "VARCHAR(256)", "变更标题"), ("impact", "TEXT", "影响说明"), ("requester_emp_id", "BIGINT", "申请人员工 ID")], [("project_id", "prj_project"), ("requester_emp_id", "hr_employee")]),
        ("prj_document", "项目文档索引", [("project_id", "BIGINT NOT NULL", "项目 ID"), ("doc_name", "VARCHAR(256)", "文档名称"), ("doc_type", "VARCHAR(32)", "文档类型"), ("url", "VARCHAR(512)", "链接"), ("uploader_emp_id", "BIGINT", "上传人员工 ID")], [("project_id", "prj_project"), ("uploader_emp_id", "hr_employee")]),
        ("prj_stakeholder", "项目干系人", [("project_id", "BIGINT NOT NULL", "项目 ID"), ("emp_id", "BIGINT", "内部员工 ID"), ("external_name", "VARCHAR(64)", "外部干系人姓名"), ("role", "VARCHAR(64)", "角色")], [("project_id", "prj_project"), ("emp_id", "hr_employee")]),
        ("prj_weekly_report", "项目周报", [("project_id", "BIGINT NOT NULL", "项目 ID"), ("week_start", "DATE", "周起始日"), ("author_emp_id", "BIGINT", "填写人员工 ID"), ("content", "TEXT", "周报内容")], [("project_id", "prj_project"), ("author_emp_id", "hr_employee")]),
        ("prj_acceptance", "项目验收", [("project_id", "BIGINT NOT NULL", "项目 ID"), ("accept_date", "DATE", "验收日期"), ("result", "VARCHAR(32)", "验收结果"), ("customer_signer", "VARCHAR(64)", "客户签字人")], [("project_id", "prj_project")]),
        ("prj_warranty", "项目质保", [("project_id", "BIGINT NOT NULL", "项目 ID"), ("start_date", "DATE", "质保开始"), ("end_date", "DATE", "质保结束"), ("terms", "TEXT", "质保条款")], [("project_id", "prj_project")]),
    ]
    for name, zh, cols, fks in prd_prj:
        uniq = [c[0] for c in cols if c[0].endswith("_code")][:1]
        tables.append(T(name, zh, cols + std_audit(), fks=fks, uniq=uniq))

    # ----- 采购供应链 -----
    scm = [
        ("scm_purchase_req", "采购申请", code_name("req", "申请单号", "申请标题") + [("applicant_emp_id", "BIGINT", "申请人员工 ID"), ("dept_id", "BIGINT", "申请部门 ID"), ("total_amount", "NUMERIC(14,2)", "预估金额")], [("applicant_emp_id", "hr_employee"), ("dept_id", "org_department")]),
        ("scm_purchase_req_item", "采购申请明细", [("req_id", "BIGINT NOT NULL", "申请单 ID"), ("item_name", "VARCHAR(128)", "物资名称"), ("qty", "NUMERIC(12,2)", "数量"), ("unit_price", "NUMERIC(14,2)", "预估单价")], [("req_id", "scm_purchase_req")]),
        ("scm_purchase_order", "采购订单", code_name("po", "采购订单号", "订单说明") + [("vendor_id", "BIGINT", "供应商 ID"), ("req_id", "BIGINT", "来源申请 ID"), ("total_amount", "NUMERIC(14,2)", "订单金额"), ("buyer_emp_id", "BIGINT", "采购员员工 ID")], [("vendor_id", "fin_vendor"), ("req_id", "scm_purchase_req"), ("buyer_emp_id", "hr_employee")]),
        ("scm_purchase_order_item", "采购订单明细", [("po_id", "BIGINT NOT NULL", "采购订单 ID"), ("item_name", "VARCHAR(128)", "物资名称"), ("qty", "NUMERIC(12,2)", "数量"), ("unit_price", "NUMERIC(14,2)", "单价"), ("amount", "NUMERIC(14,2)", "金额")], [("po_id", "scm_purchase_order")]),
        ("scm_warehouse", "仓库", code_name("wh", "仓库编码", "仓库名称") + [("office_id", "BIGINT", "职场 ID")], [("office_id", "org_office")]),
        ("scm_receipt", "采购入库单", code_name("grn", "入库单号", "说明") + [("po_id", "BIGINT", "采购订单 ID"), ("receipt_date", "DATE", "入库日期"), ("warehouse_id", "BIGINT", "仓库 ID")], [("po_id", "scm_purchase_order"), ("warehouse_id", "scm_warehouse")]),
        ("scm_inventory", "库存台账", [("warehouse_id", "BIGINT NOT NULL", "仓库 ID"), ("sku_code", "VARCHAR(64)", "SKU 编码"), ("sku_name", "VARCHAR(128)", "SKU 名称"), ("qty_on_hand", "NUMERIC(14,2)", "在库数量")], [("warehouse_id", "scm_warehouse")]),
        ("scm_inventory_txn", "库存流水", [("warehouse_id", "BIGINT NOT NULL", "仓库 ID"), ("sku_code", "VARCHAR(64)", "SKU"), ("txn_type", "VARCHAR(16)", "出入库类型"), ("qty", "NUMERIC(14,2)", "数量"), ("txn_date", "DATE", "日期"), ("ref_no", "VARCHAR(64)", "来源单号")], [("warehouse_id", "scm_warehouse")]),
        ("scm_material", "物料主数据", code_name("mat", "物料编码", "物料名称") + [("uom", "VARCHAR(16)", "计量单位"), ("category", "VARCHAR(32)", "物料类别")], []),
        ("scm_vendor_eval", "供应商评价", [("vendor_id", "BIGINT NOT NULL", "供应商 ID"), ("year_month", "VARCHAR(7)", "年月"), ("score", "NUMERIC(6,2)", "得分"), ("evaluator_emp_id", "BIGINT", "评价人员工 ID")], [("vendor_id", "fin_vendor"), ("evaluator_emp_id", "hr_employee")]),
    ]
    for name, zh, cols, fks in scm:
        uniq = [c[0] for c in cols if c[0].endswith("_code") or c[0].endswith("_no")][:1]
        tables.append(T(name, zh, cols + std_audit(), fks=fks, uniq=uniq))

    # ----- IT / 运维 / 安全 -----
    itm = [
        ("itm_asset", "IT 资产", code_name("asset", "资产编码", "资产名称") + [("asset_type", "VARCHAR(32)", "资产类型"), ("sn", "VARCHAR(64)", "序列号"), ("assignee_emp_id", "BIGINT", "领用人员工 ID"), ("office_id", "BIGINT", "职场 ID")], [("assignee_emp_id", "hr_employee"), ("office_id", "org_office")]),
        ("itm_asset_assign", "IT 资产领用归还", [("asset_id", "BIGINT NOT NULL", "资产 ID"), ("emp_id", "BIGINT NOT NULL", "员工 ID"), ("assign_date", "DATE", "领用日期"), ("return_date", "DATE", "归还日期")], [("asset_id", "itm_asset"), ("emp_id", "hr_employee")]),
        ("itm_ticket", "IT 服务工单", code_name("ticket", "工单号", "工单标题") + [("requester_emp_id", "BIGINT", "提单人员工 ID"), ("assignee_emp_id", "BIGINT", "处理人员工 ID"), ("category", "VARCHAR(32)", "分类"), ("priority", "VARCHAR(16)", "优先级")], [("requester_emp_id", "hr_employee"), ("assignee_emp_id", "hr_employee")]),
        ("itm_ticket_comment", "工单评论", [("ticket_id", "BIGINT NOT NULL", "工单 ID"), ("author_emp_id", "BIGINT", "评论人员工 ID"), ("content", "TEXT", "内容"), ("commented_at", "TIMESTAMP", "评论时间")], [("ticket_id", "itm_ticket"), ("author_emp_id", "hr_employee")]),
        ("itm_system", "业务系统台账", code_name("sys", "系统编码", "系统名称") + [("owner_emp_id", "BIGINT", "系统负责人员工 ID"), ("env", "VARCHAR(32)", "环境"), ("url", "VARCHAR(256)", "访问地址")], [("owner_emp_id", "hr_employee")]),
        ("itm_deploy", "发布部署记录", [("system_id", "BIGINT NOT NULL", "系统 ID"), ("version_no", "VARCHAR(32)", "版本号"), ("deploy_at", "TIMESTAMP", "发布时间"), ("operator_emp_id", "BIGINT", "操作人员工 ID"), ("result", "VARCHAR(32)", "结果")], [("system_id", "itm_system"), ("operator_emp_id", "hr_employee")]),
        ("itm_incident", "生产故障", code_name("inc", "故障单号", "故障标题") + [("system_id", "BIGINT", "系统 ID"), ("severity", "VARCHAR(16)", "严重级别"), ("started_at", "TIMESTAMP", "开始时间"), ("resolved_at", "TIMESTAMP", "恢复时间"), ("commander_emp_id", "BIGINT", "指挥人员工 ID")], [("system_id", "itm_system"), ("commander_emp_id", "hr_employee")]),
        ("itm_change", "变更单", code_name("chg", "变更单号", "变更标题") + [("system_id", "BIGINT", "系统 ID"), ("planned_at", "TIMESTAMP", "计划时间"), ("risk_level", "VARCHAR(16)", "风险等级"), ("applicant_emp_id", "BIGINT", "申请人员工 ID")], [("system_id", "itm_system"), ("applicant_emp_id", "hr_employee")]),
        ("itm_account", "系统账号", [("system_id", "BIGINT NOT NULL", "系统 ID"), ("emp_id", "BIGINT", "员工 ID"), ("login_name", "VARCHAR(64)", "登录名"), ("role_name", "VARCHAR(64)", "角色")], [("system_id", "itm_system"), ("emp_id", "hr_employee")]),
        ("itm_access_request", "权限申请", [("system_id", "BIGINT NOT NULL", "系统 ID"), ("emp_id", "BIGINT NOT NULL", "申请人员工 ID"), ("role_name", "VARCHAR(64)", "申请角色"), ("reason", "VARCHAR(256)", "事由")], [("system_id", "itm_system"), ("emp_id", "hr_employee")]),
        ("sec_policy", "安全策略", code_name("pol", "策略编码", "策略名称") + [("policy_type", "VARCHAR(32)", "策略类型"), ("content", "TEXT", "策略内容")], []),
        ("sec_vulnerability", "漏洞台账", code_name("vuln", "漏洞编号", "漏洞标题") + [("system_id", "BIGINT", "系统 ID"), ("severity", "VARCHAR(16)", "严重级别"), ("discovered_at", "DATE", "发现日期"), ("fixed_at", "DATE", "修复日期")], [("system_id", "itm_system")]),
        ("sec_audit_log", "安全审计日志", [("system_id", "BIGINT", "系统 ID"), ("emp_id", "BIGINT", "操作人员工 ID"), ("action", "VARCHAR(64)", "动作"), ("acted_at", "TIMESTAMP", "操作时间"), ("ip_addr", "VARCHAR(64)", "IP")], [("system_id", "itm_system"), ("emp_id", "hr_employee")]),
        ("sec_data_class", "数据分级分类", code_name("class", "分类编码", "分类名称") + [("level_no", "INT", "密级序号")], []),
    ]
    for name, zh, cols, fks in itm:
        uniq = [c[0] for c in cols if c[0].endswith("_code") or c[0].endswith("_no")][:1]
        tables.append(T(name, zh, cols + std_audit(), fks=fks, uniq=uniq))

    # ----- 市场 / 行政 / 法务 / 质量 -----
    misc = [
        ("mkt_campaign", "市场活动", code_name("camp", "活动编码", "活动名称") + [("start_date", "DATE", "开始日期"), ("end_date", "DATE", "结束日期"), ("budget", "NUMERIC(14,2)", "预算"), ("owner_emp_id", "BIGINT", "负责人员工 ID")], [("owner_emp_id", "hr_employee")]),
        ("mkt_campaign_lead", "活动获客线索", [("camp_id", "BIGINT NOT NULL", "活动 ID"), ("lead_id", "BIGINT", "线索 ID"), ("channel", "VARCHAR(32)", "渠道")], [("camp_id", "mkt_campaign"), ("lead_id", "crm_lead")]),
        ("mkt_content", "内容素材", code_name("content", "素材编码", "素材标题") + [("content_type", "VARCHAR(32)", "类型"), ("url", "VARCHAR(512)", "链接"), ("author_emp_id", "BIGINT", "作者员工 ID")], [("author_emp_id", "hr_employee")]),
        ("mkt_event_reg", "活动报名", [("camp_id", "BIGINT NOT NULL", "活动 ID"), ("reg_name", "VARCHAR(64)", "报名人"), ("company_name", "VARCHAR(128)", "单位"), ("phone", "VARCHAR(32)", "电话")], [("camp_id", "mkt_campaign")]),
        ("adm_meeting_room", "会议室", code_name("room", "会议室编码", "会议室名称") + [("office_id", "BIGINT", "职场 ID"), ("capacity", "INT", "可容纳人数")], [("office_id", "org_office")]),
        ("adm_meeting_booking", "会议室预订", [("room_id", "BIGINT NOT NULL", "会议室 ID"), ("organizer_emp_id", "BIGINT", "组织者员工 ID"), ("start_at", "TIMESTAMP", "开始时间"), ("end_at", "TIMESTAMP", "结束时间"), ("title", "VARCHAR(256)", "会议主题")], [("room_id", "adm_meeting_room"), ("organizer_emp_id", "hr_employee")]),
        ("adm_visitor", "访客登记", [("visitor_name", "VARCHAR(64)", "访客姓名"), ("host_emp_id", "BIGINT", "接待员工 ID"), ("visit_date", "DATE", "来访日期"), ("purpose", "VARCHAR(256)", "事由"), ("office_id", "BIGINT", "职场 ID")], [("host_emp_id", "hr_employee"), ("office_id", "org_office")]),
        ("adm_supply", "办公用品", code_name("supply", "用品编码", "用品名称") + [("uom", "VARCHAR(16)", "单位"), ("unit_cost", "NUMERIC(12,2)", "单价")], []),
        ("adm_supply_request", "办公用品领用", [("supply_id", "BIGINT NOT NULL", "用品 ID"), ("emp_id", "BIGINT NOT NULL", "领用人员工 ID"), ("qty", "NUMERIC(12,2)", "数量"), ("request_date", "DATE", "领用日期")], [("supply_id", "adm_supply"), ("emp_id", "hr_employee")]),
        ("adm_vehicle", "公务车", code_name("vehicle", "车牌/编码", "车辆名称") + [("plate_no", "VARCHAR(16)", "车牌号"), ("seat_count", "INT", "座位数")], []),
        ("adm_vehicle_trip", "用车记录", [("vehicle_id", "BIGINT NOT NULL", "车辆 ID"), ("driver_emp_id", "BIGINT", "驾驶人员工 ID"), ("start_at", "TIMESTAMP", "出车时间"), ("end_at", "TIMESTAMP", "收车时间"), ("destination", "VARCHAR(128)", "目的地")], [("vehicle_id", "adm_vehicle"), ("driver_emp_id", "hr_employee")]),
        ("legal_contract", "法务合同台账", code_name("lcontract", "合同编号", "合同名称") + [("counterparty", "VARCHAR(128)", "相对方"), ("sign_date", "DATE", "签订日期"), ("amount", "NUMERIC(14,2)", "金额"), ("owner_emp_id", "BIGINT", "业务负责人员工 ID"), ("customer_id", "BIGINT", "关联客户 ID"), ("vendor_id", "BIGINT", "关联供应商 ID")], [("owner_emp_id", "hr_employee"), ("customer_id", "crm_customer"), ("vendor_id", "fin_vendor")]),
        ("legal_contract_clause", "合同关键条款", [("contract_id", "BIGINT NOT NULL", "合同 ID"), ("clause_title", "VARCHAR(128)", "条款标题"), ("clause_text", "TEXT", "条款正文")], [("contract_id", "legal_contract")]),
        ("legal_dispute", "诉讼/争议案件", code_name("case", "案件编号", "案件名称") + [("contract_id", "BIGINT", "关联合同 ID"), ("counterpart", "VARCHAR(128)", "对方当事人"), ("opened_at", "DATE", "立案日期"), ("lawyer", "VARCHAR(64)", "承办律师")], [("contract_id", "legal_contract")]),
        ("legal_compliance_check", "合规检查", code_name("chk", "检查编码", "检查名称") + [("check_date", "DATE", "检查日期"), ("result", "VARCHAR(32)", "结果"), ("owner_emp_id", "BIGINT", "负责人员工 ID")], [("owner_emp_id", "hr_employee")]),
        ("qa_test_plan", "测试计划", code_name("plan", "计划编码", "计划名称") + [("project_id", "BIGINT", "项目 ID"), ("product_id", "BIGINT", "产品 ID"), ("owner_emp_id", "BIGINT", "测试负责人员工 ID")], [("project_id", "prj_project"), ("product_id", "prd_product"), ("owner_emp_id", "hr_employee")]),
        ("qa_test_case", "测试用例", [("plan_id", "BIGINT NOT NULL", "计划 ID"), ("case_code", "VARCHAR(32)", "用例编码"), ("case_name", "VARCHAR(256)", "用例名称"), ("priority", "VARCHAR(16)", "优先级")], [("plan_id", "qa_test_plan")]),
        ("qa_defect", "缺陷", code_name("bug", "缺陷编号", "缺陷标题") + [("project_id", "BIGINT", "项目 ID"), ("product_id", "BIGINT", "产品 ID"), ("severity", "VARCHAR(16)", "严重级别"), ("reporter_emp_id", "BIGINT", "报告人员工 ID"), ("assignee_emp_id", "BIGINT", "修复人员工 ID")], [("project_id", "prj_project"), ("product_id", "prd_product"), ("reporter_emp_id", "hr_employee"), ("assignee_emp_id", "hr_employee")]),
        ("qa_release_gate", "发布门禁检查", [("system_id", "BIGINT", "系统 ID"), ("version_no", "VARCHAR(32)", "版本"), ("gate_name", "VARCHAR(64)", "门禁项"), ("passed", "BOOLEAN", "是否通过"), ("checked_by", "BIGINT", "检查人员工 ID")], [("system_id", "itm_system"), ("checked_by", "hr_employee")]),
        ("kb_article", "内部知识文章", code_name("article", "文章编码", "标题") + [("category", "VARCHAR(64)", "分类"), ("author_emp_id", "BIGINT", "作者员工 ID"), ("body", "TEXT", "正文")], [("author_emp_id", "hr_employee")]),
        ("kb_article_tag", "知识标签", [("tag_code", "VARCHAR(32) NOT NULL", "标签编码"), ("tag_name", "VARCHAR(64) NOT NULL", "标签名"), ("color", "VARCHAR(16)", "展示色"), ("sort_no", "INT", "排序号")], []),
        ("kb_article_tag_rel", "文章标签关系", [("article_id", "BIGINT NOT NULL", "文章 ID"), ("tag_id", "BIGINT NOT NULL", "标签 ID"), ("tagged_by", "BIGINT", "打标人员工 ID"), ("tagged_at", "TIMESTAMP", "打标时间")], [("article_id", "kb_article"), ("tag_id", "kb_article_tag"), ("tagged_by", "hr_employee")]),
        ("ops_duty_roster", "值班排班", [("emp_id", "BIGINT NOT NULL", "值班员工 ID"), ("duty_date", "DATE NOT NULL", "日期"), ("shift_name", "VARCHAR(32)", "班次名"), ("system_id", "BIGINT", "值守系统 ID")], [("emp_id", "hr_employee"), ("system_id", "itm_system")]),
        ("ops_runbook", "运维手册", code_name("rb", "手册编码", "手册名称") + [("system_id", "BIGINT", "系统 ID"), ("content", "TEXT", "正文"), ("owner_emp_id", "BIGINT", "维护人员工 ID")], [("system_id", "itm_system"), ("owner_emp_id", "hr_employee")]),
        ("ops_backup_job", "备份任务", code_name("bak", "任务编码", "任务名称") + [("system_id", "BIGINT", "系统 ID"), ("cron_expr", "VARCHAR(64)", "调度表达式"), ("last_run_at", "TIMESTAMP", "上次执行时间"), ("last_result", "VARCHAR(32)", "上次结果")], [("system_id", "itm_system")]),
        ("ops_monitor_alert", "监控告警", [("system_id", "BIGINT", "系统 ID"), ("alert_name", "VARCHAR(128)", "告警名"), ("severity", "VARCHAR(16)", "级别"), ("fired_at", "TIMESTAMP", "触发时间"), ("acked_by", "BIGINT", "确认人员工 ID")], [("system_id", "itm_system"), ("acked_by", "hr_employee")]),
    ]
    for name, zh, cols, fks in misc:
        uniq = [c[0] for c in cols if c[0].endswith("_code") or c[0].endswith("_no")][:1]
        tables.append(T(name, zh, cols + std_audit(), fks=fks, uniq=uniq))

    # Pad to reach ~178 extended (~200 total) with domain "dictionary / dim" style tables if short
    return tables


def topological_sort(tables: list[dict]) -> list[dict]:
    by_name = {t["name"]: t for t in tables}
    pending = set(by_name)
    done: set[str] = set(CORE_TABLES)
    ordered: list[dict] = []
    while pending:
        progress = False
        for name in sorted(pending):
            t = by_name[name]
            deps = {ref for _, ref in t["fks"]}
            if deps <= (done | (pending - {name})) and all(
                d in done or d == name for d in deps if d in CORE_TABLES or d in by_name
            ):
                # allow if all deps are core or already ordered
                if all(d in done for d in deps):
                    ordered.append(t)
                    pending.remove(name)
                    done.add(name)
                    progress = True
        if not progress:
            # break cycles: emit remaining sorted
            for name in sorted(pending):
                ordered.append(by_name[name])
            break
    return ordered


# 真实库常见：表有中文注释；关键业务列有注释；审计/次要列常无注释
_SKIP_COL_COMMENT = frozenset(
    {"status", "remark", "created_at", "updated_at", "currency", "sort_no", "color"}
)


def _should_comment_column(col: str, idx: int) -> bool:
    """主键与业务关键列写 COMMENT；审计列与部分次要列故意留空。"""
    if col == "id":
        return True
    if col in _SKIP_COL_COMMENT:
        return False
    # 约每 3 个非审计列跳过 1 个，模拟注释不全
    if idx % 3 == 2 and col.endswith(("_at", "_date", "phone", "email", "url", "ip_addr")):
        return False
    return True


def emit_sql(tables: list[dict]) -> str:
    tables = topological_sort(tables)
    lines = [
        "-- company schema 扩展表（无灌数）",
        "-- 依赖 01_schema.sql 已创建的核心表；可重复执行：先删扩展表再建模",
        "-- COMMENT：表必有中文；列注释刻意不全（模拟真实库）",
        "",
        "SET client_encoding TO 'UTF8';",
        "SET search_path TO company, public;",
        "",
        "-- 删除扩展表（逆序，尽量照顾 FK）",
    ]
    for t in reversed(tables):
        lines.append(f"DROP TABLE IF EXISTS company.{t['name']} CASCADE;")
    lines.append("")
    lines.append(f"-- 共 {len(tables)} 张扩展表")
    lines.append("")

    for t in tables:
        lines.append(f"-- {t['zh']}")
        lines.append(f"CREATE TABLE company.{t['name']} (")
        col_defs = ["    id BIGSERIAL PRIMARY KEY"]
        for col, typ, _zh in t["cols"]:
            col_defs.append(f"    {col} {typ}")
        if t["uniq"]:
            uk = ", ".join(t["uniq"])
            col_defs.append(f"    CONSTRAINT uk_{t['name']} UNIQUE ({uk})")
        lines.append(",\n".join(col_defs))
        lines.append(");")
        lines.append(f"COMMENT ON TABLE company.{t['name']} IS '{t['zh'].replace(chr(39), chr(39)+chr(39))}';")
        # id
        lines.append(f"COMMENT ON COLUMN company.{t['name']}.id IS '主键';")
        for idx, (col, _typ, zh) in enumerate(t["cols"]):
            if not _should_comment_column(col, idx):
                continue
            lines.append(
                f"COMMENT ON COLUMN company.{t['name']}.{col} IS '{zh.replace(chr(39), chr(39)+chr(39))}';"
            )
        for col, ref in t["fks"]:
            cname = f"fk_{t['name']}_{col}"[:63]
            lines.append(
                f"ALTER TABLE company.{t['name']} ADD CONSTRAINT {cname} "
                f"FOREIGN KEY ({col}) REFERENCES company.{ref}(id);"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


# 核心表外键（与 01_schema.sql 对齐，供关系文档）
CORE_FKS: list[tuple[str, str, str, str]] = [
    ("org_department", "parent_id", "org_department", "上级部门"),
    ("hr_employee", "dept_id", "org_department", "所属部门"),
    ("hr_employee", "job_level_id", "hr_job_level", "职级"),
    ("att_leave", "emp_id", "hr_employee", "请假员工"),
    ("att_leave", "leave_type_id", "att_leave_type", "请假类型"),
    ("att_leave", "approved_by", "hr_employee", "审批人"),
    ("att_overtime", "emp_id", "hr_employee", "加班员工"),
    ("att_daily_record", "emp_id", "hr_employee", "考勤员工"),
    ("att_timesheet", "emp_id", "hr_employee", "填报员工"),
    ("att_timesheet", "project_id", "prj_project", "所属项目"),
    ("fin_salary_slip", "period_id", "fin_salary_period", "薪资期间"),
    ("fin_salary_slip", "emp_id", "hr_employee", "员工"),
    ("fin_salary_slip", "dept_id", "org_department", "部门"),
    ("fin_reimburse", "emp_id", "hr_employee", "报销人"),
    ("fin_reimburse", "dept_id", "org_department", "部门"),
    ("fin_reimburse_item", "claim_id", "fin_reimburse", "报销单"),
    ("fin_activity_budget", "dept_id", "org_department", "部门"),
    ("fin_activity_budget", "owner_emp_id", "hr_employee", "负责人"),
    ("fin_activity_expense", "budget_id", "fin_activity_budget", "预算"),
    ("prd_product", "owner_emp_id", "hr_employee", "产品负责人"),
    ("prd_product_cost", "product_id", "prd_product", "产品"),
    ("sal_sales_order", "customer_id", "crm_customer", "客户"),
    ("sal_sales_order", "owner_emp_id", "hr_employee", "销售负责人"),
    ("sal_sales_order", "dept_id", "org_department", "销售部门"),
    ("sal_sales_order_item", "order_id", "sal_sales_order", "订单"),
    ("sal_sales_order_item", "product_id", "prd_product", "产品"),
    ("prj_project", "customer_id", "crm_customer", "客户"),
    ("prj_project", "dept_id", "org_department", "承接部门"),
    ("prj_project", "pm_emp_id", "hr_employee", "项目经理"),
    ("prj_project_member", "project_id", "prj_project", "项目"),
    ("prj_project_member", "emp_id", "hr_employee", "成员"),
    ("prj_project_revenue", "project_id", "prj_project", "项目"),
]


def emit_relations_md(tables: list[dict], core_count: int) -> str:
    lines = [
        "# company 库表关系说明",
        "",
        f"> 核心表 {core_count} 张（`01_schema.sql`）+ 扩展表 {len(tables)} 张（`02_schema_extended.sql`）≈ **{core_count + len(tables)}** 张。",
        "> 扩展表无灌数；外键指向核心表或其它扩展表。",
        "",
        "## 核心表",
        "",
    ]
    for n in sorted(CORE_TABLES):
        lines.append(f"- `{n}`")
    lines.extend(
        [
            "",
            "## 核心表外键关系",
            "",
            "| 子表 | 列 | 父表 | 业务含义 |",
            "|---|---|---|---|",
        ]
    )
    for child, col, parent, meaning in CORE_FKS:
        lines.append(f"| `{child}` | `{col}` | `{parent}` | {meaning} |")
    lines.extend(["", "## 扩展表外键关系", "", "| 子表 | 列 | 父表 | 业务含义 |", "|---|---|---|---|"])
    for t in tables:
        for col, ref in t["fks"]:
            lines.append(f"| `{t['name']}` | `{col}` | `{ref}` | {t['zh']} → 关联 `{ref}` |")
    lines.extend(
        [
            "",
            "## 业务域一览",
            "",
            "| 前缀 | 域 |",
            "|---|---|",
            "| org_ | 组织/公司/职场/成本中心 |",
            "| hr_ | 人事/绩效/招聘/培训 |",
            "| att_ | 考勤/排班/打卡 |",
            "| fin_ | 财务/发票/预算/总账 |",
            "| crm_/sal_ | 客户/商机/合同/交付 |",
            "| prd_/prj_ | 产品/项目交付 |",
            "| scm_ | 采购/库存 |",
            "| itm_/sec_/ops_ | IT/安全/运维 |",
            "| mkt_/adm_/legal_/qa_/kb_ | 市场/行政/法务/质量/知识 |",
            "| dim_ | 通用字典填充表 |",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    tables = build_tables()
    # Ensure we have enough tables: target extended = 200 - 22 = 178
    target_ext = 178
    if len(tables) < target_ext:
        # pad with dim_ dictionaries
        i = 1
        while len(tables) < target_ext:
            name = f"dim_lookup_{i:03d}"
            tables.append(
                T(
                    name,
                    f"通用字典项 {i:03d}",
                    [
                        ("dict_code", "VARCHAR(32) NOT NULL", "字典编码"),
                        ("dict_name", "VARCHAR(128) NOT NULL", "字典名称"),
                        ("dict_group", "VARCHAR(64)", "字典分组"),
                        ("sort_no", "INT", "排序号"),
                    ]
                    + std_audit(),
                    uniq=["dict_code"],
                )
            )
            i += 1
    elif len(tables) > target_ext:
        tables = tables[:target_ext]

    OUT_SQL.write_text(emit_sql(tables), encoding="utf-8")
    catalog = {
        "extended_count": len(tables),
        "core_count": len(CORE_TABLES),
        "total": len(tables) + len(CORE_TABLES),
        "tables": {
            t["name"]: {
                "zh": t["zh"],
                "columns": {c[0]: c[2] for c in t["cols"]},
                "fks": [{"column": c, "ref": r} for c, r in t["fks"]],
            }
            for t in tables
        },
    }
    OUT_CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT_SQL} tables={len(tables)} total≈{len(tables)+len(CORE_TABLES)}")
    print(f"wrote {OUT_CATALOG}")
    print("note: table-relations.md → run metadata/export_table_relations.py after apply")


if __name__ == "__main__":
    main()
