-- company schema 扩展表（无灌数）
-- 依赖 01_schema.sql 已创建的核心表；可重复执行：先删扩展表再建模
-- COMMENT：表必有中文；列注释刻意不全（模拟真实库）

SET client_encoding TO 'UTF8';
SET search_path TO company, public;

-- 删除扩展表（逆序，尽量照顾 FK）
DROP TABLE IF EXISTS company.adm_meeting_booking CASCADE;
DROP TABLE IF EXISTS company.scm_receipt CASCADE;
DROP TABLE IF EXISTS company.scm_purchase_order_item CASCADE;
DROP TABLE IF EXISTS company.scm_purchase_order CASCADE;
DROP TABLE IF EXISTS company.scm_inventory_txn CASCADE;
DROP TABLE IF EXISTS company.scm_inventory CASCADE;
DROP TABLE IF EXISTS company.qa_test_case CASCADE;
DROP TABLE IF EXISTS company.itm_incident CASCADE;
DROP TABLE IF EXISTS company.itm_deploy CASCADE;
DROP TABLE IF EXISTS company.itm_change CASCADE;
DROP TABLE IF EXISTS company.itm_asset_assign CASCADE;
DROP TABLE IF EXISTS company.itm_asset CASCADE;
DROP TABLE IF EXISTS company.itm_account CASCADE;
DROP TABLE IF EXISTS company.itm_access_request CASCADE;
DROP TABLE IF EXISTS company.hr_training_enroll CASCADE;
DROP TABLE IF EXISTS company.hr_offer CASCADE;
DROP TABLE IF EXISTS company.hr_interview CASCADE;
DROP TABLE IF EXISTS company.hr_contract CASCADE;
DROP TABLE IF EXISTS company.fin_payment CASCADE;
DROP TABLE IF EXISTS company.fin_invoice CASCADE;
DROP TABLE IF EXISTS company.fin_budget_line CASCADE;
DROP TABLE IF EXISTS company.fin_bank_txn CASCADE;
DROP TABLE IF EXISTS company.fin_bank_account CASCADE;
DROP TABLE IF EXISTS company.fin_asset_depr CASCADE;
DROP TABLE IF EXISTS company.crm_activity CASCADE;
DROP TABLE IF EXISTS company.att_punch CASCADE;
DROP TABLE IF EXISTS company.att_device CASCADE;
DROP TABLE IF EXISTS company.adm_visitor CASCADE;
DROP TABLE IF EXISTS company.adm_meeting_room CASCADE;
DROP TABLE IF EXISTS company.sec_vulnerability CASCADE;
DROP TABLE IF EXISTS company.sec_policy CASCADE;
DROP TABLE IF EXISTS company.sec_data_class CASCADE;
DROP TABLE IF EXISTS company.sec_audit_log CASCADE;
DROP TABLE IF EXISTS company.scm_warehouse CASCADE;
DROP TABLE IF EXISTS company.scm_vendor_eval CASCADE;
DROP TABLE IF EXISTS company.scm_purchase_req_item CASCADE;
DROP TABLE IF EXISTS company.scm_purchase_req CASCADE;
DROP TABLE IF EXISTS company.scm_material CASCADE;
DROP TABLE IF EXISTS company.sal_target CASCADE;
DROP TABLE IF EXISTS company.sal_return CASCADE;
DROP TABLE IF EXISTS company.sal_quote_item CASCADE;
DROP TABLE IF EXISTS company.sal_quote CASCADE;
DROP TABLE IF EXISTS company.sal_price_list_item CASCADE;
DROP TABLE IF EXISTS company.sal_price_list CASCADE;
DROP TABLE IF EXISTS company.sal_delivery_item CASCADE;
DROP TABLE IF EXISTS company.sal_delivery CASCADE;
DROP TABLE IF EXISTS company.sal_contract_milestone CASCADE;
DROP TABLE IF EXISTS company.sal_contract CASCADE;
DROP TABLE IF EXISTS company.sal_commission_rule CASCADE;
DROP TABLE IF EXISTS company.sal_commission CASCADE;
DROP TABLE IF EXISTS company.sal_channel CASCADE;
DROP TABLE IF EXISTS company.qa_test_plan CASCADE;
DROP TABLE IF EXISTS company.qa_release_gate CASCADE;
DROP TABLE IF EXISTS company.qa_defect CASCADE;
DROP TABLE IF EXISTS company.prj_weekly_report CASCADE;
DROP TABLE IF EXISTS company.prj_warranty CASCADE;
DROP TABLE IF EXISTS company.prj_task CASCADE;
DROP TABLE IF EXISTS company.prj_stakeholder CASCADE;
DROP TABLE IF EXISTS company.prj_risk CASCADE;
DROP TABLE IF EXISTS company.prj_milestone CASCADE;
DROP TABLE IF EXISTS company.prj_issue CASCADE;
DROP TABLE IF EXISTS company.prj_document CASCADE;
DROP TABLE IF EXISTS company.prj_change_request CASCADE;
DROP TABLE IF EXISTS company.prj_acceptance CASCADE;
DROP TABLE IF EXISTS company.prd_roadmap CASCADE;
DROP TABLE IF EXISTS company.prd_product_version CASCADE;
DROP TABLE IF EXISTS company.prd_product_line CASCADE;
DROP TABLE IF EXISTS company.prd_license CASCADE;
DROP TABLE IF EXISTS company.prd_feature CASCADE;
DROP TABLE IF EXISTS company.org_seal CASCADE;
DROP TABLE IF EXISTS company.org_position CASCADE;
DROP TABLE IF EXISTS company.org_office CASCADE;
DROP TABLE IF EXISTS company.org_location CASCADE;
DROP TABLE IF EXISTS company.org_dept_closure CASCADE;
DROP TABLE IF EXISTS company.org_dept_change CASCADE;
DROP TABLE IF EXISTS company.org_cost_center CASCADE;
DROP TABLE IF EXISTS company.org_company CASCADE;
DROP TABLE IF EXISTS company.org_biz_unit CASCADE;
DROP TABLE IF EXISTS company.org_announcement CASCADE;
DROP TABLE IF EXISTS company.ops_runbook CASCADE;
DROP TABLE IF EXISTS company.ops_monitor_alert CASCADE;
DROP TABLE IF EXISTS company.ops_duty_roster CASCADE;
DROP TABLE IF EXISTS company.ops_backup_job CASCADE;
DROP TABLE IF EXISTS company.mkt_event_reg CASCADE;
DROP TABLE IF EXISTS company.mkt_content CASCADE;
DROP TABLE IF EXISTS company.mkt_campaign_lead CASCADE;
DROP TABLE IF EXISTS company.mkt_campaign CASCADE;
DROP TABLE IF EXISTS company.legal_dispute CASCADE;
DROP TABLE IF EXISTS company.legal_contract_clause CASCADE;
DROP TABLE IF EXISTS company.legal_contract CASCADE;
DROP TABLE IF EXISTS company.legal_compliance_check CASCADE;
DROP TABLE IF EXISTS company.kb_article_tag_rel CASCADE;
DROP TABLE IF EXISTS company.kb_article_tag CASCADE;
DROP TABLE IF EXISTS company.kb_article CASCADE;
DROP TABLE IF EXISTS company.itm_ticket_comment CASCADE;
DROP TABLE IF EXISTS company.itm_ticket CASCADE;
DROP TABLE IF EXISTS company.itm_system CASCADE;
DROP TABLE IF EXISTS company.hr_work_history CASCADE;
DROP TABLE IF EXISTS company.hr_work_calendar CASCADE;
DROP TABLE IF EXISTS company.hr_transfer CASCADE;
DROP TABLE IF EXISTS company.hr_training_session CASCADE;
DROP TABLE IF EXISTS company.hr_training_course CASCADE;
DROP TABLE IF EXISTS company.hr_resignation CASCADE;
DROP TABLE IF EXISTS company.hr_recruit_req CASCADE;
DROP TABLE IF EXISTS company.hr_promotion CASCADE;
DROP TABLE IF EXISTS company.hr_probation CASCADE;
DROP TABLE IF EXISTS company.hr_performance_review CASCADE;
DROP TABLE IF EXISTS company.hr_performance_goal CASCADE;
DROP TABLE IF EXISTS company.hr_performance_cycle CASCADE;
DROP TABLE IF EXISTS company.hr_onboarding CASCADE;
DROP TABLE IF EXISTS company.hr_headcount_plan CASCADE;
DROP TABLE IF EXISTS company.hr_family_member CASCADE;
DROP TABLE IF EXISTS company.hr_emergency_contact CASCADE;
DROP TABLE IF EXISTS company.hr_education CASCADE;
DROP TABLE IF EXISTS company.hr_certificate CASCADE;
DROP TABLE IF EXISTS company.hr_candidate CASCADE;
DROP TABLE IF EXISTS company.hr_bank_account CASCADE;
DROP TABLE IF EXISTS company.hr_award CASCADE;
DROP TABLE IF EXISTS company.fin_vendor CASCADE;
DROP TABLE IF EXISTS company.fin_tax_period CASCADE;
DROP TABLE IF EXISTS company.fin_receipt CASCADE;
DROP TABLE IF EXISTS company.fin_petty_cash_txn CASCADE;
DROP TABLE IF EXISTS company.fin_petty_cash CASCADE;
DROP TABLE IF EXISTS company.fin_loan_repay CASCADE;
DROP TABLE IF EXISTS company.fin_loan CASCADE;
DROP TABLE IF EXISTS company.fin_journal_line CASCADE;
DROP TABLE IF EXISTS company.fin_journal CASCADE;
DROP TABLE IF EXISTS company.fin_gl_account CASCADE;
DROP TABLE IF EXISTS company.fin_fixed_asset CASCADE;
DROP TABLE IF EXISTS company.fin_exchange_rate CASCADE;
DROP TABLE IF EXISTS company.fin_cost_allocation CASCADE;
DROP TABLE IF EXISTS company.fin_budget_year CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_028 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_027 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_026 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_025 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_024 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_023 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_022 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_021 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_020 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_019 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_018 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_017 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_016 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_015 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_014 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_013 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_012 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_011 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_010 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_009 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_008 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_007 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_006 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_005 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_004 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_003 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_002 CASCADE;
DROP TABLE IF EXISTS company.dim_lookup_001 CASCADE;
DROP TABLE IF EXISTS company.crm_visit CASCADE;
DROP TABLE IF EXISTS company.crm_sla CASCADE;
DROP TABLE IF EXISTS company.crm_opportunity CASCADE;
DROP TABLE IF EXISTS company.crm_lead CASCADE;
DROP TABLE IF EXISTS company.crm_contact CASCADE;
DROP TABLE IF EXISTS company.crm_complaint CASCADE;
DROP TABLE IF EXISTS company.att_travel CASCADE;
DROP TABLE IF EXISTS company.att_shift_assign CASCADE;
DROP TABLE IF EXISTS company.att_shift CASCADE;
DROP TABLE IF EXISTS company.att_remote_work CASCADE;
DROP TABLE IF EXISTS company.att_ot_rule CASCADE;
DROP TABLE IF EXISTS company.att_monthly_summary CASCADE;
DROP TABLE IF EXISTS company.att_makeup_card CASCADE;
DROP TABLE IF EXISTS company.att_leave_balance CASCADE;
DROP TABLE IF EXISTS company.adm_vehicle_trip CASCADE;
DROP TABLE IF EXISTS company.adm_vehicle CASCADE;
DROP TABLE IF EXISTS company.adm_supply_request CASCADE;
DROP TABLE IF EXISTS company.adm_supply CASCADE;

-- 共 178 张扩展表

-- 办公用品
CREATE TABLE company.adm_supply (
    id BIGSERIAL PRIMARY KEY,
    supply_code VARCHAR(32) NOT NULL,
    supply_name VARCHAR(128) NOT NULL,
    uom VARCHAR(16),
    unit_cost NUMERIC(12,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_adm_supply UNIQUE (supply_code)
);
COMMENT ON TABLE company.adm_supply IS '办公用品';
COMMENT ON COLUMN company.adm_supply.id IS '主键';
COMMENT ON COLUMN company.adm_supply.supply_code IS '用品编码';
COMMENT ON COLUMN company.adm_supply.supply_name IS '用品名称';
COMMENT ON COLUMN company.adm_supply.uom IS '单位';
COMMENT ON COLUMN company.adm_supply.unit_cost IS '单价';

-- 办公用品领用
CREATE TABLE company.adm_supply_request (
    id BIGSERIAL PRIMARY KEY,
    supply_id BIGINT NOT NULL,
    emp_id BIGINT NOT NULL,
    qty NUMERIC(12,2),
    request_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.adm_supply_request IS '办公用品领用';
COMMENT ON COLUMN company.adm_supply_request.id IS '主键';
COMMENT ON COLUMN company.adm_supply_request.supply_id IS '用品 ID';
COMMENT ON COLUMN company.adm_supply_request.emp_id IS '领用人员工 ID';
COMMENT ON COLUMN company.adm_supply_request.qty IS '数量';
COMMENT ON COLUMN company.adm_supply_request.request_date IS '领用日期';
ALTER TABLE company.adm_supply_request ADD CONSTRAINT fk_adm_supply_request_supply_id FOREIGN KEY (supply_id) REFERENCES company.adm_supply(id);
ALTER TABLE company.adm_supply_request ADD CONSTRAINT fk_adm_supply_request_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 公务车
CREATE TABLE company.adm_vehicle (
    id BIGSERIAL PRIMARY KEY,
    vehicle_code VARCHAR(32) NOT NULL,
    vehicle_name VARCHAR(128) NOT NULL,
    plate_no VARCHAR(16),
    seat_count INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_adm_vehicle UNIQUE (vehicle_code)
);
COMMENT ON TABLE company.adm_vehicle IS '公务车';
COMMENT ON COLUMN company.adm_vehicle.id IS '主键';
COMMENT ON COLUMN company.adm_vehicle.vehicle_code IS '车牌/编码';
COMMENT ON COLUMN company.adm_vehicle.vehicle_name IS '车辆名称';
COMMENT ON COLUMN company.adm_vehicle.plate_no IS '车牌号';
COMMENT ON COLUMN company.adm_vehicle.seat_count IS '座位数';

-- 用车记录
CREATE TABLE company.adm_vehicle_trip (
    id BIGSERIAL PRIMARY KEY,
    vehicle_id BIGINT NOT NULL,
    driver_emp_id BIGINT,
    start_at TIMESTAMP,
    end_at TIMESTAMP,
    destination VARCHAR(128),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.adm_vehicle_trip IS '用车记录';
COMMENT ON COLUMN company.adm_vehicle_trip.id IS '主键';
COMMENT ON COLUMN company.adm_vehicle_trip.vehicle_id IS '车辆 ID';
COMMENT ON COLUMN company.adm_vehicle_trip.driver_emp_id IS '驾驶人员工 ID';
COMMENT ON COLUMN company.adm_vehicle_trip.end_at IS '收车时间';
COMMENT ON COLUMN company.adm_vehicle_trip.destination IS '目的地';
ALTER TABLE company.adm_vehicle_trip ADD CONSTRAINT fk_adm_vehicle_trip_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES company.adm_vehicle(id);
ALTER TABLE company.adm_vehicle_trip ADD CONSTRAINT fk_adm_vehicle_trip_driver_emp_id FOREIGN KEY (driver_emp_id) REFERENCES company.hr_employee(id);

-- 假期余额
CREATE TABLE company.att_leave_balance (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    leave_type_id BIGINT NOT NULL,
    year INT,
    balance_days NUMERIC(8,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.att_leave_balance IS '假期余额';
COMMENT ON COLUMN company.att_leave_balance.id IS '主键';
COMMENT ON COLUMN company.att_leave_balance.emp_id IS '员工 ID';
COMMENT ON COLUMN company.att_leave_balance.leave_type_id IS '请假类型 ID';
COMMENT ON COLUMN company.att_leave_balance.year IS '年度';
COMMENT ON COLUMN company.att_leave_balance.balance_days IS '剩余天数';
ALTER TABLE company.att_leave_balance ADD CONSTRAINT fk_att_leave_balance_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.att_leave_balance ADD CONSTRAINT fk_att_leave_balance_leave_type_id FOREIGN KEY (leave_type_id) REFERENCES company.att_leave_type(id);

-- 补卡申请
CREATE TABLE company.att_makeup_card (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    work_date DATE,
    punch_type VARCHAR(16),
    reason VARCHAR(256),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.att_makeup_card IS '补卡申请';
COMMENT ON COLUMN company.att_makeup_card.id IS '主键';
COMMENT ON COLUMN company.att_makeup_card.emp_id IS '员工 ID';
COMMENT ON COLUMN company.att_makeup_card.work_date IS '日期';
COMMENT ON COLUMN company.att_makeup_card.punch_type IS '补卡类型';
COMMENT ON COLUMN company.att_makeup_card.reason IS '事由';
ALTER TABLE company.att_makeup_card ADD CONSTRAINT fk_att_makeup_card_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 月考勤汇总
CREATE TABLE company.att_monthly_summary (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    year_month VARCHAR(7),
    work_days NUMERIC(8,2),
    leave_days NUMERIC(8,2),
    ot_hours NUMERIC(8,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.att_monthly_summary IS '月考勤汇总';
COMMENT ON COLUMN company.att_monthly_summary.id IS '主键';
COMMENT ON COLUMN company.att_monthly_summary.emp_id IS '员工 ID';
COMMENT ON COLUMN company.att_monthly_summary.year_month IS '年月';
COMMENT ON COLUMN company.att_monthly_summary.work_days IS '出勤天';
COMMENT ON COLUMN company.att_monthly_summary.leave_days IS '请假天';
COMMENT ON COLUMN company.att_monthly_summary.ot_hours IS '加班小时';
ALTER TABLE company.att_monthly_summary ADD CONSTRAINT fk_att_monthly_summary_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 加班规则
CREATE TABLE company.att_ot_rule (
    id BIGSERIAL PRIMARY KEY,
    rule_code VARCHAR(32) NOT NULL,
    rule_name VARCHAR(128) NOT NULL,
    weekday_rate NUMERIC(6,2),
    weekend_rate NUMERIC(6,2),
    holiday_rate NUMERIC(6,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_att_ot_rule UNIQUE (rule_code)
);
COMMENT ON TABLE company.att_ot_rule IS '加班规则';
COMMENT ON COLUMN company.att_ot_rule.id IS '主键';
COMMENT ON COLUMN company.att_ot_rule.rule_code IS '规则编码';
COMMENT ON COLUMN company.att_ot_rule.rule_name IS '规则名称';
COMMENT ON COLUMN company.att_ot_rule.weekday_rate IS '工作日倍率';
COMMENT ON COLUMN company.att_ot_rule.weekend_rate IS '周末倍率';
COMMENT ON COLUMN company.att_ot_rule.holiday_rate IS '节假日倍率';

-- 居家办公申请
CREATE TABLE company.att_remote_work (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    work_date DATE,
    reason VARCHAR(256),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.att_remote_work IS '居家办公申请';
COMMENT ON COLUMN company.att_remote_work.id IS '主键';
COMMENT ON COLUMN company.att_remote_work.emp_id IS '员工 ID';
COMMENT ON COLUMN company.att_remote_work.work_date IS '日期';
COMMENT ON COLUMN company.att_remote_work.reason IS '事由';
ALTER TABLE company.att_remote_work ADD CONSTRAINT fk_att_remote_work_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 班次定义
CREATE TABLE company.att_shift (
    id BIGSERIAL PRIMARY KEY,
    shift_code VARCHAR(32) NOT NULL,
    shift_name VARCHAR(128) NOT NULL,
    start_time TIME,
    end_time TIME,
    break_minutes INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_att_shift UNIQUE (shift_code)
);
COMMENT ON TABLE company.att_shift IS '班次定义';
COMMENT ON COLUMN company.att_shift.id IS '主键';
COMMENT ON COLUMN company.att_shift.shift_code IS '班次编码';
COMMENT ON COLUMN company.att_shift.shift_name IS '班次名称';
COMMENT ON COLUMN company.att_shift.start_time IS '上班时间';
COMMENT ON COLUMN company.att_shift.end_time IS '下班时间';
COMMENT ON COLUMN company.att_shift.break_minutes IS '休息分钟';

-- 班次排班
CREATE TABLE company.att_shift_assign (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    shift_id BIGINT NOT NULL,
    work_date DATE NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.att_shift_assign IS '班次排班';
COMMENT ON COLUMN company.att_shift_assign.id IS '主键';
COMMENT ON COLUMN company.att_shift_assign.emp_id IS '员工 ID';
COMMENT ON COLUMN company.att_shift_assign.shift_id IS '班次 ID';
ALTER TABLE company.att_shift_assign ADD CONSTRAINT fk_att_shift_assign_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.att_shift_assign ADD CONSTRAINT fk_att_shift_assign_shift_id FOREIGN KEY (shift_id) REFERENCES company.att_shift(id);

-- 出差申请
CREATE TABLE company.att_travel (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    start_date DATE,
    end_date DATE,
    destination VARCHAR(128),
    project_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.att_travel IS '出差申请';
COMMENT ON COLUMN company.att_travel.id IS '主键';
COMMENT ON COLUMN company.att_travel.emp_id IS '员工 ID';
COMMENT ON COLUMN company.att_travel.start_date IS '开始日期';
COMMENT ON COLUMN company.att_travel.destination IS '目的地';
COMMENT ON COLUMN company.att_travel.project_id IS '关联项目 ID';
ALTER TABLE company.att_travel ADD CONSTRAINT fk_att_travel_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.att_travel ADD CONSTRAINT fk_att_travel_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);

-- 客户投诉
CREATE TABLE company.crm_complaint (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    project_id BIGINT,
    title VARCHAR(256),
    severity_level VARCHAR(16),
    handler_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.crm_complaint IS '客户投诉';
COMMENT ON COLUMN company.crm_complaint.id IS '主键';
COMMENT ON COLUMN company.crm_complaint.customer_id IS '客户 ID';
COMMENT ON COLUMN company.crm_complaint.project_id IS '项目 ID';
COMMENT ON COLUMN company.crm_complaint.title IS '标题';
COMMENT ON COLUMN company.crm_complaint.severity_level IS '严重级别';
COMMENT ON COLUMN company.crm_complaint.handler_emp_id IS '处理人员工 ID';
ALTER TABLE company.crm_complaint ADD CONSTRAINT fk_crm_complaint_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);
ALTER TABLE company.crm_complaint ADD CONSTRAINT fk_crm_complaint_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);
ALTER TABLE company.crm_complaint ADD CONSTRAINT fk_crm_complaint_handler_emp_id FOREIGN KEY (handler_emp_id) REFERENCES company.hr_employee(id);

-- 客户联系人
CREATE TABLE company.crm_contact (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    contact_name VARCHAR(64),
    title VARCHAR(64),
    phone VARCHAR(32),
    email VARCHAR(128),
    is_primary BOOLEAN,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.crm_contact IS '客户联系人';
COMMENT ON COLUMN company.crm_contact.id IS '主键';
COMMENT ON COLUMN company.crm_contact.customer_id IS '客户 ID';
COMMENT ON COLUMN company.crm_contact.contact_name IS '联系人姓名';
COMMENT ON COLUMN company.crm_contact.title IS '职务';
COMMENT ON COLUMN company.crm_contact.phone IS '电话';
COMMENT ON COLUMN company.crm_contact.email IS '邮箱';
COMMENT ON COLUMN company.crm_contact.is_primary IS '是否主联系人';
ALTER TABLE company.crm_contact ADD CONSTRAINT fk_crm_contact_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);

-- 销售线索
CREATE TABLE company.crm_lead (
    id BIGSERIAL PRIMARY KEY,
    lead_code VARCHAR(32) NOT NULL,
    lead_name VARCHAR(128) NOT NULL,
    source VARCHAR(32),
    owner_emp_id BIGINT,
    customer_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_crm_lead UNIQUE (lead_code)
);
COMMENT ON TABLE company.crm_lead IS '销售线索';
COMMENT ON COLUMN company.crm_lead.id IS '主键';
COMMENT ON COLUMN company.crm_lead.lead_code IS '线索编码';
COMMENT ON COLUMN company.crm_lead.lead_name IS '线索名称';
COMMENT ON COLUMN company.crm_lead.source IS '来源';
COMMENT ON COLUMN company.crm_lead.owner_emp_id IS '负责销售员工 ID';
COMMENT ON COLUMN company.crm_lead.customer_id IS '转化客户 ID';
ALTER TABLE company.crm_lead ADD CONSTRAINT fk_crm_lead_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.crm_lead ADD CONSTRAINT fk_crm_lead_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);

-- 商机
CREATE TABLE company.crm_opportunity (
    id BIGSERIAL PRIMARY KEY,
    opp_code VARCHAR(32) NOT NULL,
    opp_name VARCHAR(128) NOT NULL,
    customer_id BIGINT,
    owner_emp_id BIGINT,
    amount NUMERIC(14,2),
    stage VARCHAR(32),
    close_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_crm_opportunity UNIQUE (opp_code)
);
COMMENT ON TABLE company.crm_opportunity IS '商机';
COMMENT ON COLUMN company.crm_opportunity.id IS '主键';
COMMENT ON COLUMN company.crm_opportunity.opp_code IS '商机编码';
COMMENT ON COLUMN company.crm_opportunity.opp_name IS '商机名称';
COMMENT ON COLUMN company.crm_opportunity.customer_id IS '客户 ID';
COMMENT ON COLUMN company.crm_opportunity.owner_emp_id IS '负责销售员工 ID';
COMMENT ON COLUMN company.crm_opportunity.amount IS '预计金额';
COMMENT ON COLUMN company.crm_opportunity.stage IS '阶段';
COMMENT ON COLUMN company.crm_opportunity.close_date IS '预计成交日';
ALTER TABLE company.crm_opportunity ADD CONSTRAINT fk_crm_opportunity_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);
ALTER TABLE company.crm_opportunity ADD CONSTRAINT fk_crm_opportunity_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);

-- 客户服务等级协议
CREATE TABLE company.crm_sla (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    sla_level VARCHAR(16),
    response_hours INT,
    resolve_hours INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.crm_sla IS '客户服务等级协议';
COMMENT ON COLUMN company.crm_sla.id IS '主键';
COMMENT ON COLUMN company.crm_sla.customer_id IS '客户 ID';
COMMENT ON COLUMN company.crm_sla.sla_level IS 'SLA 等级';
COMMENT ON COLUMN company.crm_sla.response_hours IS '响应时限小时';
COMMENT ON COLUMN company.crm_sla.resolve_hours IS '解决时限小时';
ALTER TABLE company.crm_sla ADD CONSTRAINT fk_crm_sla_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);

-- 客户拜访
CREATE TABLE company.crm_visit (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    emp_id BIGINT,
    visit_date DATE,
    purpose VARCHAR(256),
    result VARCHAR(256),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.crm_visit IS '客户拜访';
COMMENT ON COLUMN company.crm_visit.id IS '主键';
COMMENT ON COLUMN company.crm_visit.customer_id IS '客户 ID';
COMMENT ON COLUMN company.crm_visit.emp_id IS '拜访人员工 ID';
COMMENT ON COLUMN company.crm_visit.purpose IS '目的';
COMMENT ON COLUMN company.crm_visit.result IS '结果';
ALTER TABLE company.crm_visit ADD CONSTRAINT fk_crm_visit_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);
ALTER TABLE company.crm_visit ADD CONSTRAINT fk_crm_visit_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 通用字典项 001
CREATE TABLE company.dim_lookup_001 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_001 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_001 IS '通用字典项 001';
COMMENT ON COLUMN company.dim_lookup_001.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_001.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_001.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_001.dict_group IS '字典分组';

-- 通用字典项 002
CREATE TABLE company.dim_lookup_002 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_002 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_002 IS '通用字典项 002';
COMMENT ON COLUMN company.dim_lookup_002.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_002.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_002.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_002.dict_group IS '字典分组';

-- 通用字典项 003
CREATE TABLE company.dim_lookup_003 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_003 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_003 IS '通用字典项 003';
COMMENT ON COLUMN company.dim_lookup_003.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_003.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_003.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_003.dict_group IS '字典分组';

-- 通用字典项 004
CREATE TABLE company.dim_lookup_004 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_004 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_004 IS '通用字典项 004';
COMMENT ON COLUMN company.dim_lookup_004.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_004.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_004.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_004.dict_group IS '字典分组';

-- 通用字典项 005
CREATE TABLE company.dim_lookup_005 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_005 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_005 IS '通用字典项 005';
COMMENT ON COLUMN company.dim_lookup_005.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_005.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_005.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_005.dict_group IS '字典分组';

-- 通用字典项 006
CREATE TABLE company.dim_lookup_006 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_006 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_006 IS '通用字典项 006';
COMMENT ON COLUMN company.dim_lookup_006.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_006.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_006.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_006.dict_group IS '字典分组';

-- 通用字典项 007
CREATE TABLE company.dim_lookup_007 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_007 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_007 IS '通用字典项 007';
COMMENT ON COLUMN company.dim_lookup_007.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_007.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_007.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_007.dict_group IS '字典分组';

-- 通用字典项 008
CREATE TABLE company.dim_lookup_008 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_008 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_008 IS '通用字典项 008';
COMMENT ON COLUMN company.dim_lookup_008.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_008.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_008.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_008.dict_group IS '字典分组';

-- 通用字典项 009
CREATE TABLE company.dim_lookup_009 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_009 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_009 IS '通用字典项 009';
COMMENT ON COLUMN company.dim_lookup_009.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_009.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_009.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_009.dict_group IS '字典分组';

-- 通用字典项 010
CREATE TABLE company.dim_lookup_010 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_010 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_010 IS '通用字典项 010';
COMMENT ON COLUMN company.dim_lookup_010.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_010.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_010.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_010.dict_group IS '字典分组';

-- 通用字典项 011
CREATE TABLE company.dim_lookup_011 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_011 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_011 IS '通用字典项 011';
COMMENT ON COLUMN company.dim_lookup_011.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_011.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_011.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_011.dict_group IS '字典分组';

-- 通用字典项 012
CREATE TABLE company.dim_lookup_012 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_012 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_012 IS '通用字典项 012';
COMMENT ON COLUMN company.dim_lookup_012.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_012.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_012.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_012.dict_group IS '字典分组';

-- 通用字典项 013
CREATE TABLE company.dim_lookup_013 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_013 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_013 IS '通用字典项 013';
COMMENT ON COLUMN company.dim_lookup_013.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_013.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_013.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_013.dict_group IS '字典分组';

-- 通用字典项 014
CREATE TABLE company.dim_lookup_014 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_014 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_014 IS '通用字典项 014';
COMMENT ON COLUMN company.dim_lookup_014.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_014.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_014.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_014.dict_group IS '字典分组';

-- 通用字典项 015
CREATE TABLE company.dim_lookup_015 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_015 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_015 IS '通用字典项 015';
COMMENT ON COLUMN company.dim_lookup_015.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_015.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_015.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_015.dict_group IS '字典分组';

-- 通用字典项 016
CREATE TABLE company.dim_lookup_016 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_016 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_016 IS '通用字典项 016';
COMMENT ON COLUMN company.dim_lookup_016.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_016.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_016.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_016.dict_group IS '字典分组';

-- 通用字典项 017
CREATE TABLE company.dim_lookup_017 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_017 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_017 IS '通用字典项 017';
COMMENT ON COLUMN company.dim_lookup_017.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_017.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_017.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_017.dict_group IS '字典分组';

-- 通用字典项 018
CREATE TABLE company.dim_lookup_018 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_018 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_018 IS '通用字典项 018';
COMMENT ON COLUMN company.dim_lookup_018.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_018.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_018.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_018.dict_group IS '字典分组';

-- 通用字典项 019
CREATE TABLE company.dim_lookup_019 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_019 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_019 IS '通用字典项 019';
COMMENT ON COLUMN company.dim_lookup_019.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_019.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_019.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_019.dict_group IS '字典分组';

-- 通用字典项 020
CREATE TABLE company.dim_lookup_020 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_020 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_020 IS '通用字典项 020';
COMMENT ON COLUMN company.dim_lookup_020.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_020.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_020.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_020.dict_group IS '字典分组';

-- 通用字典项 021
CREATE TABLE company.dim_lookup_021 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_021 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_021 IS '通用字典项 021';
COMMENT ON COLUMN company.dim_lookup_021.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_021.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_021.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_021.dict_group IS '字典分组';

-- 通用字典项 022
CREATE TABLE company.dim_lookup_022 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_022 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_022 IS '通用字典项 022';
COMMENT ON COLUMN company.dim_lookup_022.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_022.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_022.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_022.dict_group IS '字典分组';

-- 通用字典项 023
CREATE TABLE company.dim_lookup_023 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_023 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_023 IS '通用字典项 023';
COMMENT ON COLUMN company.dim_lookup_023.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_023.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_023.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_023.dict_group IS '字典分组';

-- 通用字典项 024
CREATE TABLE company.dim_lookup_024 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_024 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_024 IS '通用字典项 024';
COMMENT ON COLUMN company.dim_lookup_024.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_024.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_024.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_024.dict_group IS '字典分组';

-- 通用字典项 025
CREATE TABLE company.dim_lookup_025 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_025 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_025 IS '通用字典项 025';
COMMENT ON COLUMN company.dim_lookup_025.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_025.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_025.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_025.dict_group IS '字典分组';

-- 通用字典项 026
CREATE TABLE company.dim_lookup_026 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_026 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_026 IS '通用字典项 026';
COMMENT ON COLUMN company.dim_lookup_026.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_026.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_026.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_026.dict_group IS '字典分组';

-- 通用字典项 027
CREATE TABLE company.dim_lookup_027 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_027 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_027 IS '通用字典项 027';
COMMENT ON COLUMN company.dim_lookup_027.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_027.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_027.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_027.dict_group IS '字典分组';

-- 通用字典项 028
CREATE TABLE company.dim_lookup_028 (
    id BIGSERIAL PRIMARY KEY,
    dict_code VARCHAR(32) NOT NULL,
    dict_name VARCHAR(128) NOT NULL,
    dict_group VARCHAR(64),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_dim_lookup_028 UNIQUE (dict_code)
);
COMMENT ON TABLE company.dim_lookup_028 IS '通用字典项 028';
COMMENT ON COLUMN company.dim_lookup_028.id IS '主键';
COMMENT ON COLUMN company.dim_lookup_028.dict_code IS '字典编码';
COMMENT ON COLUMN company.dim_lookup_028.dict_name IS '字典名称';
COMMENT ON COLUMN company.dim_lookup_028.dict_group IS '字典分组';

-- 年度预算
CREATE TABLE company.fin_budget_year (
    id BIGSERIAL PRIMARY KEY,
    year INT NOT NULL,
    dept_id BIGINT,
    budget_amount NUMERIC(14,2),
    used_amount NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.fin_budget_year IS '年度预算';
COMMENT ON COLUMN company.fin_budget_year.id IS '主键';
COMMENT ON COLUMN company.fin_budget_year.year IS '年度';
COMMENT ON COLUMN company.fin_budget_year.dept_id IS '部门 ID';
COMMENT ON COLUMN company.fin_budget_year.budget_amount IS '预算金额';
COMMENT ON COLUMN company.fin_budget_year.used_amount IS '已用金额';
ALTER TABLE company.fin_budget_year ADD CONSTRAINT fk_fin_budget_year_dept_id FOREIGN KEY (dept_id) REFERENCES company.org_department(id);

-- 费用分摊
CREATE TABLE company.fin_cost_allocation (
    id BIGSERIAL PRIMARY KEY,
    year_month VARCHAR(7),
    from_dept_id BIGINT,
    to_dept_id BIGINT,
    amount NUMERIC(14,2),
    subject_code VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_cost_allocation UNIQUE (subject_code)
);
COMMENT ON TABLE company.fin_cost_allocation IS '费用分摊';
COMMENT ON COLUMN company.fin_cost_allocation.id IS '主键';
COMMENT ON COLUMN company.fin_cost_allocation.year_month IS '年月';
COMMENT ON COLUMN company.fin_cost_allocation.from_dept_id IS '分出部门 ID';
COMMENT ON COLUMN company.fin_cost_allocation.to_dept_id IS '分入部门 ID';
COMMENT ON COLUMN company.fin_cost_allocation.amount IS '分摊金额';
COMMENT ON COLUMN company.fin_cost_allocation.subject_code IS '科目编码';
ALTER TABLE company.fin_cost_allocation ADD CONSTRAINT fk_fin_cost_allocation_from_dept_id FOREIGN KEY (from_dept_id) REFERENCES company.org_department(id);
ALTER TABLE company.fin_cost_allocation ADD CONSTRAINT fk_fin_cost_allocation_to_dept_id FOREIGN KEY (to_dept_id) REFERENCES company.org_department(id);

-- 汇率
CREATE TABLE company.fin_exchange_rate (
    id BIGSERIAL PRIMARY KEY,
    currency VARCHAR(8) NOT NULL,
    rate_date DATE NOT NULL,
    rate NUMERIC(18,8),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.fin_exchange_rate IS '汇率';
COMMENT ON COLUMN company.fin_exchange_rate.id IS '主键';
COMMENT ON COLUMN company.fin_exchange_rate.rate_date IS '汇率日期';
COMMENT ON COLUMN company.fin_exchange_rate.rate IS '对人民币汇率';

-- 固定资产
CREATE TABLE company.fin_fixed_asset (
    id BIGSERIAL PRIMARY KEY,
    asset_code VARCHAR(32) NOT NULL,
    asset_name VARCHAR(128) NOT NULL,
    category VARCHAR(32),
    purchase_date DATE,
    original_value NUMERIC(14,2),
    custodian_emp_id BIGINT,
    dept_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_fixed_asset UNIQUE (asset_code)
);
COMMENT ON TABLE company.fin_fixed_asset IS '固定资产';
COMMENT ON COLUMN company.fin_fixed_asset.id IS '主键';
COMMENT ON COLUMN company.fin_fixed_asset.asset_code IS '资产编码';
COMMENT ON COLUMN company.fin_fixed_asset.asset_name IS '资产名称';
COMMENT ON COLUMN company.fin_fixed_asset.category IS '资产类别';
COMMENT ON COLUMN company.fin_fixed_asset.purchase_date IS '购置日期';
COMMENT ON COLUMN company.fin_fixed_asset.original_value IS '原值';
COMMENT ON COLUMN company.fin_fixed_asset.custodian_emp_id IS '保管人员工 ID';
COMMENT ON COLUMN company.fin_fixed_asset.dept_id IS '使用部门 ID';
ALTER TABLE company.fin_fixed_asset ADD CONSTRAINT fk_fin_fixed_asset_custodian_emp_id FOREIGN KEY (custodian_emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.fin_fixed_asset ADD CONSTRAINT fk_fin_fixed_asset_dept_id FOREIGN KEY (dept_id) REFERENCES company.org_department(id);

-- 会计科目
CREATE TABLE company.fin_gl_account (
    id BIGSERIAL PRIMARY KEY,
    acct_code VARCHAR(32) NOT NULL,
    acct_name VARCHAR(128) NOT NULL,
    acct_type VARCHAR(32),
    parent_code VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_gl_account UNIQUE (acct_code)
);
COMMENT ON TABLE company.fin_gl_account IS '会计科目';
COMMENT ON COLUMN company.fin_gl_account.id IS '主键';
COMMENT ON COLUMN company.fin_gl_account.acct_code IS '科目编码';
COMMENT ON COLUMN company.fin_gl_account.acct_name IS '科目名称';
COMMENT ON COLUMN company.fin_gl_account.acct_type IS '科目类型';
COMMENT ON COLUMN company.fin_gl_account.parent_code IS '上级科目编码';

-- 会计凭证头
CREATE TABLE company.fin_journal (
    id BIGSERIAL PRIMARY KEY,
    voucher_no VARCHAR(64) NOT NULL,
    voucher_date DATE,
    period VARCHAR(7),
    created_by BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_journal UNIQUE (voucher_no)
);
COMMENT ON TABLE company.fin_journal IS '会计凭证头';
COMMENT ON COLUMN company.fin_journal.id IS '主键';
COMMENT ON COLUMN company.fin_journal.voucher_no IS '凭证号';
COMMENT ON COLUMN company.fin_journal.voucher_date IS '凭证日期';
COMMENT ON COLUMN company.fin_journal.period IS '会计期间';
COMMENT ON COLUMN company.fin_journal.created_by IS '制单人员工 ID';
ALTER TABLE company.fin_journal ADD CONSTRAINT fk_fin_journal_created_by FOREIGN KEY (created_by) REFERENCES company.hr_employee(id);

-- 会计凭证分录
CREATE TABLE company.fin_journal_line (
    id BIGSERIAL PRIMARY KEY,
    journal_id BIGINT NOT NULL,
    acct_id BIGINT NOT NULL,
    debit NUMERIC(14,2),
    credit NUMERIC(14,2),
    summary VARCHAR(256),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.fin_journal_line IS '会计凭证分录';
COMMENT ON COLUMN company.fin_journal_line.id IS '主键';
COMMENT ON COLUMN company.fin_journal_line.journal_id IS '凭证头 ID';
COMMENT ON COLUMN company.fin_journal_line.acct_id IS '科目 ID';
COMMENT ON COLUMN company.fin_journal_line.debit IS '借方';
COMMENT ON COLUMN company.fin_journal_line.credit IS '贷方';
COMMENT ON COLUMN company.fin_journal_line.summary IS '摘要';
ALTER TABLE company.fin_journal_line ADD CONSTRAINT fk_fin_journal_line_journal_id FOREIGN KEY (journal_id) REFERENCES company.fin_journal(id);
ALTER TABLE company.fin_journal_line ADD CONSTRAINT fk_fin_journal_line_acct_id FOREIGN KEY (acct_id) REFERENCES company.fin_gl_account(id);

-- 对公借款
CREATE TABLE company.fin_loan (
    id BIGSERIAL PRIMARY KEY,
    loan_no VARCHAR(64),
    emp_id BIGINT NOT NULL,
    amount NUMERIC(14,2),
    loan_date DATE,
    due_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_loan UNIQUE (loan_no)
);
COMMENT ON TABLE company.fin_loan IS '对公借款';
COMMENT ON COLUMN company.fin_loan.id IS '主键';
COMMENT ON COLUMN company.fin_loan.loan_no IS '借款单号';
COMMENT ON COLUMN company.fin_loan.emp_id IS '借款人员工 ID';
COMMENT ON COLUMN company.fin_loan.amount IS '借款金额';
COMMENT ON COLUMN company.fin_loan.loan_date IS '借款日期';
COMMENT ON COLUMN company.fin_loan.due_date IS '应还日期';
ALTER TABLE company.fin_loan ADD CONSTRAINT fk_fin_loan_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 借款核销
CREATE TABLE company.fin_loan_repay (
    id BIGSERIAL PRIMARY KEY,
    loan_id BIGINT NOT NULL,
    repay_amount NUMERIC(14,2),
    repay_date DATE,
    reimburse_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.fin_loan_repay IS '借款核销';
COMMENT ON COLUMN company.fin_loan_repay.id IS '主键';
COMMENT ON COLUMN company.fin_loan_repay.loan_id IS '借款 ID';
COMMENT ON COLUMN company.fin_loan_repay.repay_amount IS '核销金额';
COMMENT ON COLUMN company.fin_loan_repay.reimburse_id IS '关联报销单 ID';
ALTER TABLE company.fin_loan_repay ADD CONSTRAINT fk_fin_loan_repay_loan_id FOREIGN KEY (loan_id) REFERENCES company.fin_loan(id);
ALTER TABLE company.fin_loan_repay ADD CONSTRAINT fk_fin_loan_repay_reimburse_id FOREIGN KEY (reimburse_id) REFERENCES company.fin_reimburse(id);

-- 备用金账户
CREATE TABLE company.fin_petty_cash (
    id BIGSERIAL PRIMARY KEY,
    dept_id BIGINT,
    keeper_emp_id BIGINT,
    balance NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.fin_petty_cash IS '备用金账户';
COMMENT ON COLUMN company.fin_petty_cash.id IS '主键';
COMMENT ON COLUMN company.fin_petty_cash.dept_id IS '部门 ID';
COMMENT ON COLUMN company.fin_petty_cash.keeper_emp_id IS '保管人员工 ID';
COMMENT ON COLUMN company.fin_petty_cash.balance IS '余额';
ALTER TABLE company.fin_petty_cash ADD CONSTRAINT fk_fin_petty_cash_dept_id FOREIGN KEY (dept_id) REFERENCES company.org_department(id);
ALTER TABLE company.fin_petty_cash ADD CONSTRAINT fk_fin_petty_cash_keeper_emp_id FOREIGN KEY (keeper_emp_id) REFERENCES company.hr_employee(id);

-- 备用金收支
CREATE TABLE company.fin_petty_cash_txn (
    id BIGSERIAL PRIMARY KEY,
    petty_id BIGINT NOT NULL,
    txn_date DATE,
    direction VARCHAR(8),
    amount NUMERIC(14,2),
    reason VARCHAR(256),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.fin_petty_cash_txn IS '备用金收支';
COMMENT ON COLUMN company.fin_petty_cash_txn.id IS '主键';
COMMENT ON COLUMN company.fin_petty_cash_txn.petty_id IS '备用金账户 ID';
COMMENT ON COLUMN company.fin_petty_cash_txn.txn_date IS '日期';
COMMENT ON COLUMN company.fin_petty_cash_txn.direction IS '收支';
COMMENT ON COLUMN company.fin_petty_cash_txn.amount IS '金额';
COMMENT ON COLUMN company.fin_petty_cash_txn.reason IS '事由';
ALTER TABLE company.fin_petty_cash_txn ADD CONSTRAINT fk_fin_petty_cash_txn_petty_id FOREIGN KEY (petty_id) REFERENCES company.fin_petty_cash(id);

-- 收款单
CREATE TABLE company.fin_receipt (
    id BIGSERIAL PRIMARY KEY,
    receipt_no VARCHAR(64) NOT NULL,
    customer_id BIGINT,
    amount NUMERIC(14,2),
    receipt_date DATE,
    project_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_receipt UNIQUE (receipt_no)
);
COMMENT ON TABLE company.fin_receipt IS '收款单';
COMMENT ON COLUMN company.fin_receipt.id IS '主键';
COMMENT ON COLUMN company.fin_receipt.receipt_no IS '收款单号';
COMMENT ON COLUMN company.fin_receipt.customer_id IS '客户 ID';
COMMENT ON COLUMN company.fin_receipt.amount IS '收款金额';
COMMENT ON COLUMN company.fin_receipt.receipt_date IS '收款日期';
COMMENT ON COLUMN company.fin_receipt.project_id IS '项目 ID';
ALTER TABLE company.fin_receipt ADD CONSTRAINT fk_fin_receipt_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);
ALTER TABLE company.fin_receipt ADD CONSTRAINT fk_fin_receipt_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);

-- 税务申报期间
CREATE TABLE company.fin_tax_period (
    id BIGSERIAL PRIMARY KEY,
    year_month VARCHAR(7) NOT NULL,
    tax_type VARCHAR(32),
    payable_amount NUMERIC(14,2),
    paid_amount NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.fin_tax_period IS '税务申报期间';
COMMENT ON COLUMN company.fin_tax_period.id IS '主键';
COMMENT ON COLUMN company.fin_tax_period.year_month IS '年月';
COMMENT ON COLUMN company.fin_tax_period.tax_type IS '税种';
COMMENT ON COLUMN company.fin_tax_period.payable_amount IS '应纳税额';
COMMENT ON COLUMN company.fin_tax_period.paid_amount IS '已缴税额';

-- 供应商主数据
CREATE TABLE company.fin_vendor (
    id BIGSERIAL PRIMARY KEY,
    vendor_code VARCHAR(32) NOT NULL,
    vendor_name VARCHAR(128) NOT NULL,
    tax_no VARCHAR(64),
    contact VARCHAR(64),
    phone VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_vendor UNIQUE (vendor_code)
);
COMMENT ON TABLE company.fin_vendor IS '供应商主数据';
COMMENT ON COLUMN company.fin_vendor.id IS '主键';
COMMENT ON COLUMN company.fin_vendor.vendor_code IS '供应商编码';
COMMENT ON COLUMN company.fin_vendor.vendor_name IS '供应商名称';
COMMENT ON COLUMN company.fin_vendor.tax_no IS '税号';
COMMENT ON COLUMN company.fin_vendor.contact IS '联系人';
COMMENT ON COLUMN company.fin_vendor.phone IS '电话';

-- 奖惩记录
CREATE TABLE company.hr_award (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    award_type VARCHAR(32),
    amount NUMERIC(12,2),
    occur_date DATE,
    reason VARCHAR(256),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_award IS '奖惩记录';
COMMENT ON COLUMN company.hr_award.id IS '主键';
COMMENT ON COLUMN company.hr_award.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_award.award_type IS '奖惩类型';
COMMENT ON COLUMN company.hr_award.amount IS '金额';
COMMENT ON COLUMN company.hr_award.occur_date IS '发生日期';
COMMENT ON COLUMN company.hr_award.reason IS '事由';
ALTER TABLE company.hr_award ADD CONSTRAINT fk_hr_award_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 员工薪酬账户
CREATE TABLE company.hr_bank_account (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    bank_name VARCHAR(64),
    account_no VARCHAR(64),
    is_primary BOOLEAN,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_bank_account IS '员工薪酬账户';
COMMENT ON COLUMN company.hr_bank_account.id IS '主键';
COMMENT ON COLUMN company.hr_bank_account.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_bank_account.bank_name IS '开户行';
COMMENT ON COLUMN company.hr_bank_account.account_no IS '账号';
COMMENT ON COLUMN company.hr_bank_account.is_primary IS '是否主账户';
ALTER TABLE company.hr_bank_account ADD CONSTRAINT fk_hr_bank_account_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 候选人
CREATE TABLE company.hr_candidate (
    id BIGSERIAL PRIMARY KEY,
    cand_code VARCHAR(32) NOT NULL,
    cand_name VARCHAR(128) NOT NULL,
    phone VARCHAR(32),
    email VARCHAR(128),
    source VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_hr_candidate UNIQUE (cand_code)
);
COMMENT ON TABLE company.hr_candidate IS '候选人';
COMMENT ON COLUMN company.hr_candidate.id IS '主键';
COMMENT ON COLUMN company.hr_candidate.cand_code IS '候选人编码';
COMMENT ON COLUMN company.hr_candidate.cand_name IS '候选人姓名';
COMMENT ON COLUMN company.hr_candidate.email IS '邮箱';
COMMENT ON COLUMN company.hr_candidate.source IS '来源渠道';

-- 员工证书资质
CREATE TABLE company.hr_certificate (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    cert_name VARCHAR(128),
    cert_no VARCHAR(64),
    expire_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_certificate IS '员工证书资质';
COMMENT ON COLUMN company.hr_certificate.id IS '主键';
COMMENT ON COLUMN company.hr_certificate.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_certificate.cert_name IS '证书名称';
COMMENT ON COLUMN company.hr_certificate.cert_no IS '证书编号';
COMMENT ON COLUMN company.hr_certificate.expire_date IS '到期日';
ALTER TABLE company.hr_certificate ADD CONSTRAINT fk_hr_certificate_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 教育经历
CREATE TABLE company.hr_education (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    school VARCHAR(128),
    degree VARCHAR(32),
    major VARCHAR(64),
    graduate_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_education IS '教育经历';
COMMENT ON COLUMN company.hr_education.id IS '主键';
COMMENT ON COLUMN company.hr_education.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_education.school IS '学校';
COMMENT ON COLUMN company.hr_education.degree IS '学历';
COMMENT ON COLUMN company.hr_education.major IS '专业';
COMMENT ON COLUMN company.hr_education.graduate_date IS '毕业日期';
ALTER TABLE company.hr_education ADD CONSTRAINT fk_hr_education_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 紧急联系人
CREATE TABLE company.hr_emergency_contact (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    contact_name VARCHAR(64),
    relation VARCHAR(32),
    phone VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_emergency_contact IS '紧急联系人';
COMMENT ON COLUMN company.hr_emergency_contact.id IS '主键';
COMMENT ON COLUMN company.hr_emergency_contact.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_emergency_contact.contact_name IS '联系人姓名';
COMMENT ON COLUMN company.hr_emergency_contact.relation IS '关系';
COMMENT ON COLUMN company.hr_emergency_contact.phone IS '电话';
ALTER TABLE company.hr_emergency_contact ADD CONSTRAINT fk_hr_emergency_contact_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 员工家属信息
CREATE TABLE company.hr_family_member (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    member_name VARCHAR(64),
    relation VARCHAR(32),
    birthday DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_family_member IS '员工家属信息';
COMMENT ON COLUMN company.hr_family_member.id IS '主键';
COMMENT ON COLUMN company.hr_family_member.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_family_member.member_name IS '家属姓名';
COMMENT ON COLUMN company.hr_family_member.relation IS '关系';
COMMENT ON COLUMN company.hr_family_member.birthday IS '生日';
ALTER TABLE company.hr_family_member ADD CONSTRAINT fk_hr_family_member_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 编制计划
CREATE TABLE company.hr_headcount_plan (
    id BIGSERIAL PRIMARY KEY,
    dept_id BIGINT NOT NULL,
    year_month VARCHAR(7),
    plan_hc INT,
    actual_hc INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_headcount_plan IS '编制计划';
COMMENT ON COLUMN company.hr_headcount_plan.id IS '主键';
COMMENT ON COLUMN company.hr_headcount_plan.dept_id IS '部门 ID';
COMMENT ON COLUMN company.hr_headcount_plan.year_month IS '年月 YYYY-MM';
COMMENT ON COLUMN company.hr_headcount_plan.plan_hc IS '计划编制';
COMMENT ON COLUMN company.hr_headcount_plan.actual_hc IS '实际在岗';
ALTER TABLE company.hr_headcount_plan ADD CONSTRAINT fk_hr_headcount_plan_dept_id FOREIGN KEY (dept_id) REFERENCES company.org_department(id);

-- 入职办理单
CREATE TABLE company.hr_onboarding (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    checklist_status VARCHAR(32),
    it_ready BOOLEAN,
    badge_no VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_onboarding IS '入职办理单';
COMMENT ON COLUMN company.hr_onboarding.id IS '主键';
COMMENT ON COLUMN company.hr_onboarding.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_onboarding.checklist_status IS '清单状态';
COMMENT ON COLUMN company.hr_onboarding.it_ready IS 'IT 是否就绪';
COMMENT ON COLUMN company.hr_onboarding.badge_no IS '工牌号';
ALTER TABLE company.hr_onboarding ADD CONSTRAINT fk_hr_onboarding_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 绩效考核周期
CREATE TABLE company.hr_performance_cycle (
    id BIGSERIAL PRIMARY KEY,
    cycle_code VARCHAR(32) NOT NULL,
    cycle_name VARCHAR(128) NOT NULL,
    start_date DATE,
    end_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_hr_performance_cycle UNIQUE (cycle_code)
);
COMMENT ON TABLE company.hr_performance_cycle IS '绩效考核周期';
COMMENT ON COLUMN company.hr_performance_cycle.id IS '主键';
COMMENT ON COLUMN company.hr_performance_cycle.cycle_code IS '周期编码';
COMMENT ON COLUMN company.hr_performance_cycle.cycle_name IS '周期名称';
COMMENT ON COLUMN company.hr_performance_cycle.end_date IS '结束日期';

-- 绩效目标
CREATE TABLE company.hr_performance_goal (
    id BIGSERIAL PRIMARY KEY,
    cycle_id BIGINT NOT NULL,
    emp_id BIGINT NOT NULL,
    goal_text TEXT,
    weight_pct NUMERIC(6,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_performance_goal IS '绩效目标';
COMMENT ON COLUMN company.hr_performance_goal.id IS '主键';
COMMENT ON COLUMN company.hr_performance_goal.cycle_id IS '周期 ID';
COMMENT ON COLUMN company.hr_performance_goal.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_performance_goal.goal_text IS '目标描述';
COMMENT ON COLUMN company.hr_performance_goal.weight_pct IS '权重百分比';
ALTER TABLE company.hr_performance_goal ADD CONSTRAINT fk_hr_performance_goal_cycle_id FOREIGN KEY (cycle_id) REFERENCES company.hr_performance_cycle(id);
ALTER TABLE company.hr_performance_goal ADD CONSTRAINT fk_hr_performance_goal_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 绩效评估结果
CREATE TABLE company.hr_performance_review (
    id BIGSERIAL PRIMARY KEY,
    cycle_id BIGINT NOT NULL,
    emp_id BIGINT NOT NULL,
    score NUMERIC(6,2),
    grade VARCHAR(16),
    reviewer_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_performance_review IS '绩效评估结果';
COMMENT ON COLUMN company.hr_performance_review.id IS '主键';
COMMENT ON COLUMN company.hr_performance_review.cycle_id IS '周期 ID';
COMMENT ON COLUMN company.hr_performance_review.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_performance_review.score IS '得分';
COMMENT ON COLUMN company.hr_performance_review.grade IS '等级';
COMMENT ON COLUMN company.hr_performance_review.reviewer_emp_id IS '评估人员工 ID';
ALTER TABLE company.hr_performance_review ADD CONSTRAINT fk_hr_performance_review_cycle_id FOREIGN KEY (cycle_id) REFERENCES company.hr_performance_cycle(id);
ALTER TABLE company.hr_performance_review ADD CONSTRAINT fk_hr_performance_review_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.hr_performance_review ADD CONSTRAINT fk_hr_performance_review_reviewer_emp_id FOREIGN KEY (reviewer_emp_id) REFERENCES company.hr_employee(id);

-- 试用期考核
CREATE TABLE company.hr_probation (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    plan_end_date DATE,
    actual_end_date DATE,
    result VARCHAR(32),
    mentor_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_probation IS '试用期考核';
COMMENT ON COLUMN company.hr_probation.id IS '主键';
COMMENT ON COLUMN company.hr_probation.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_probation.plan_end_date IS '计划转正日';
COMMENT ON COLUMN company.hr_probation.result IS '考核结果';
COMMENT ON COLUMN company.hr_probation.mentor_emp_id IS '导师员工 ID';
ALTER TABLE company.hr_probation ADD CONSTRAINT fk_hr_probation_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.hr_probation ADD CONSTRAINT fk_hr_probation_mentor_emp_id FOREIGN KEY (mentor_emp_id) REFERENCES company.hr_employee(id);

-- 晋升记录
CREATE TABLE company.hr_promotion (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    from_level_id BIGINT,
    to_level_id BIGINT,
    effective_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_promotion IS '晋升记录';
COMMENT ON COLUMN company.hr_promotion.id IS '主键';
COMMENT ON COLUMN company.hr_promotion.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_promotion.from_level_id IS '原职级 ID';
COMMENT ON COLUMN company.hr_promotion.to_level_id IS '新职级 ID';
COMMENT ON COLUMN company.hr_promotion.effective_date IS '生效日期';
ALTER TABLE company.hr_promotion ADD CONSTRAINT fk_hr_promotion_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.hr_promotion ADD CONSTRAINT fk_hr_promotion_from_level_id FOREIGN KEY (from_level_id) REFERENCES company.hr_job_level(id);
ALTER TABLE company.hr_promotion ADD CONSTRAINT fk_hr_promotion_to_level_id FOREIGN KEY (to_level_id) REFERENCES company.hr_job_level(id);

-- 招聘需求
CREATE TABLE company.hr_recruit_req (
    id BIGSERIAL PRIMARY KEY,
    req_code VARCHAR(32) NOT NULL,
    req_name VARCHAR(128) NOT NULL,
    dept_id BIGINT,
    headcount INT,
    job_level_id BIGINT,
    owner_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_hr_recruit_req UNIQUE (req_code)
);
COMMENT ON TABLE company.hr_recruit_req IS '招聘需求';
COMMENT ON COLUMN company.hr_recruit_req.id IS '主键';
COMMENT ON COLUMN company.hr_recruit_req.req_code IS '需求编码';
COMMENT ON COLUMN company.hr_recruit_req.req_name IS '需求名称';
COMMENT ON COLUMN company.hr_recruit_req.dept_id IS '需求部门 ID';
COMMENT ON COLUMN company.hr_recruit_req.headcount IS '需求人数';
COMMENT ON COLUMN company.hr_recruit_req.job_level_id IS '目标职级 ID';
COMMENT ON COLUMN company.hr_recruit_req.owner_emp_id IS '招聘负责人员工 ID';
ALTER TABLE company.hr_recruit_req ADD CONSTRAINT fk_hr_recruit_req_dept_id FOREIGN KEY (dept_id) REFERENCES company.org_department(id);
ALTER TABLE company.hr_recruit_req ADD CONSTRAINT fk_hr_recruit_req_job_level_id FOREIGN KEY (job_level_id) REFERENCES company.hr_job_level(id);
ALTER TABLE company.hr_recruit_req ADD CONSTRAINT fk_hr_recruit_req_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);

-- 离职办理
CREATE TABLE company.hr_resignation (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    apply_date DATE,
    last_work_date DATE,
    reason_type VARCHAR(32),
    exit_interview TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_resignation IS '离职办理';
COMMENT ON COLUMN company.hr_resignation.id IS '主键';
COMMENT ON COLUMN company.hr_resignation.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_resignation.apply_date IS '申请日期';
COMMENT ON COLUMN company.hr_resignation.reason_type IS '离职原因类型';
COMMENT ON COLUMN company.hr_resignation.exit_interview IS '离职面谈纪要';
ALTER TABLE company.hr_resignation ADD CONSTRAINT fk_hr_resignation_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 培训课程
CREATE TABLE company.hr_training_course (
    id BIGSERIAL PRIMARY KEY,
    course_code VARCHAR(32) NOT NULL,
    course_name VARCHAR(128) NOT NULL,
    hours NUMERIC(6,2),
    vendor VARCHAR(128),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_hr_training_course UNIQUE (course_code)
);
COMMENT ON TABLE company.hr_training_course IS '培训课程';
COMMENT ON COLUMN company.hr_training_course.id IS '主键';
COMMENT ON COLUMN company.hr_training_course.course_code IS '课程编码';
COMMENT ON COLUMN company.hr_training_course.course_name IS '课程名称';
COMMENT ON COLUMN company.hr_training_course.hours IS '课时';
COMMENT ON COLUMN company.hr_training_course.vendor IS '培训供应商';

-- 培训场次
CREATE TABLE company.hr_training_session (
    id BIGSERIAL PRIMARY KEY,
    course_id BIGINT NOT NULL,
    start_at TIMESTAMP,
    end_at TIMESTAMP,
    location VARCHAR(128),
    trainer VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_training_session IS '培训场次';
COMMENT ON COLUMN company.hr_training_session.id IS '主键';
COMMENT ON COLUMN company.hr_training_session.course_id IS '课程 ID';
COMMENT ON COLUMN company.hr_training_session.start_at IS '开始时间';
COMMENT ON COLUMN company.hr_training_session.location IS '地点';
COMMENT ON COLUMN company.hr_training_session.trainer IS '讲师';
ALTER TABLE company.hr_training_session ADD CONSTRAINT fk_hr_training_session_course_id FOREIGN KEY (course_id) REFERENCES company.hr_training_course(id);

-- 人事调动
CREATE TABLE company.hr_transfer (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    from_dept_id BIGINT,
    to_dept_id BIGINT,
    effective_date DATE,
    transfer_type VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_transfer IS '人事调动';
COMMENT ON COLUMN company.hr_transfer.id IS '主键';
COMMENT ON COLUMN company.hr_transfer.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_transfer.from_dept_id IS '调出部门 ID';
COMMENT ON COLUMN company.hr_transfer.to_dept_id IS '调入部门 ID';
COMMENT ON COLUMN company.hr_transfer.effective_date IS '生效日期';
COMMENT ON COLUMN company.hr_transfer.transfer_type IS '调动类型';
ALTER TABLE company.hr_transfer ADD CONSTRAINT fk_hr_transfer_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.hr_transfer ADD CONSTRAINT fk_hr_transfer_from_dept_id FOREIGN KEY (from_dept_id) REFERENCES company.org_department(id);
ALTER TABLE company.hr_transfer ADD CONSTRAINT fk_hr_transfer_to_dept_id FOREIGN KEY (to_dept_id) REFERENCES company.org_department(id);

-- 工作日历
CREATE TABLE company.hr_work_calendar (
    id BIGSERIAL PRIMARY KEY,
    cal_date DATE NOT NULL,
    day_type VARCHAR(16),
    holiday_name VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_work_calendar IS '工作日历';
COMMENT ON COLUMN company.hr_work_calendar.id IS '主键';
COMMENT ON COLUMN company.hr_work_calendar.cal_date IS '日期';
COMMENT ON COLUMN company.hr_work_calendar.day_type IS '日类型：work/weekend/holiday';
COMMENT ON COLUMN company.hr_work_calendar.holiday_name IS '节假日名称';

-- 入职前工作经历
CREATE TABLE company.hr_work_history (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    employer VARCHAR(128),
    title VARCHAR(64),
    start_date DATE,
    end_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_work_history IS '入职前工作经历';
COMMENT ON COLUMN company.hr_work_history.id IS '主键';
COMMENT ON COLUMN company.hr_work_history.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_work_history.employer IS '原单位';
COMMENT ON COLUMN company.hr_work_history.title IS '职位';
COMMENT ON COLUMN company.hr_work_history.start_date IS '开始日期';
COMMENT ON COLUMN company.hr_work_history.end_date IS '结束日期';
ALTER TABLE company.hr_work_history ADD CONSTRAINT fk_hr_work_history_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 业务系统台账
CREATE TABLE company.itm_system (
    id BIGSERIAL PRIMARY KEY,
    sys_code VARCHAR(32) NOT NULL,
    sys_name VARCHAR(128) NOT NULL,
    owner_emp_id BIGINT,
    env VARCHAR(32),
    url VARCHAR(256),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_itm_system UNIQUE (sys_code)
);
COMMENT ON TABLE company.itm_system IS '业务系统台账';
COMMENT ON COLUMN company.itm_system.id IS '主键';
COMMENT ON COLUMN company.itm_system.sys_code IS '系统编码';
COMMENT ON COLUMN company.itm_system.sys_name IS '系统名称';
COMMENT ON COLUMN company.itm_system.owner_emp_id IS '系统负责人员工 ID';
COMMENT ON COLUMN company.itm_system.env IS '环境';
COMMENT ON COLUMN company.itm_system.url IS '访问地址';
ALTER TABLE company.itm_system ADD CONSTRAINT fk_itm_system_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);

-- IT 服务工单
CREATE TABLE company.itm_ticket (
    id BIGSERIAL PRIMARY KEY,
    ticket_code VARCHAR(32) NOT NULL,
    ticket_name VARCHAR(128) NOT NULL,
    requester_emp_id BIGINT,
    assignee_emp_id BIGINT,
    category VARCHAR(32),
    priority VARCHAR(16),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_itm_ticket UNIQUE (ticket_code)
);
COMMENT ON TABLE company.itm_ticket IS 'IT 服务工单';
COMMENT ON COLUMN company.itm_ticket.id IS '主键';
COMMENT ON COLUMN company.itm_ticket.ticket_code IS '工单号';
COMMENT ON COLUMN company.itm_ticket.ticket_name IS '工单标题';
COMMENT ON COLUMN company.itm_ticket.requester_emp_id IS '提单人员工 ID';
COMMENT ON COLUMN company.itm_ticket.assignee_emp_id IS '处理人员工 ID';
COMMENT ON COLUMN company.itm_ticket.category IS '分类';
COMMENT ON COLUMN company.itm_ticket.priority IS '优先级';
ALTER TABLE company.itm_ticket ADD CONSTRAINT fk_itm_ticket_requester_emp_id FOREIGN KEY (requester_emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.itm_ticket ADD CONSTRAINT fk_itm_ticket_assignee_emp_id FOREIGN KEY (assignee_emp_id) REFERENCES company.hr_employee(id);

-- 工单评论
CREATE TABLE company.itm_ticket_comment (
    id BIGSERIAL PRIMARY KEY,
    ticket_id BIGINT NOT NULL,
    author_emp_id BIGINT,
    content TEXT,
    commented_at TIMESTAMP,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.itm_ticket_comment IS '工单评论';
COMMENT ON COLUMN company.itm_ticket_comment.id IS '主键';
COMMENT ON COLUMN company.itm_ticket_comment.ticket_id IS '工单 ID';
COMMENT ON COLUMN company.itm_ticket_comment.author_emp_id IS '评论人员工 ID';
COMMENT ON COLUMN company.itm_ticket_comment.content IS '内容';
COMMENT ON COLUMN company.itm_ticket_comment.commented_at IS '评论时间';
ALTER TABLE company.itm_ticket_comment ADD CONSTRAINT fk_itm_ticket_comment_ticket_id FOREIGN KEY (ticket_id) REFERENCES company.itm_ticket(id);
ALTER TABLE company.itm_ticket_comment ADD CONSTRAINT fk_itm_ticket_comment_author_emp_id FOREIGN KEY (author_emp_id) REFERENCES company.hr_employee(id);

-- 内部知识文章
CREATE TABLE company.kb_article (
    id BIGSERIAL PRIMARY KEY,
    article_code VARCHAR(32) NOT NULL,
    article_name VARCHAR(128) NOT NULL,
    category VARCHAR(64),
    author_emp_id BIGINT,
    body TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_kb_article UNIQUE (article_code)
);
COMMENT ON TABLE company.kb_article IS '内部知识文章';
COMMENT ON COLUMN company.kb_article.id IS '主键';
COMMENT ON COLUMN company.kb_article.article_code IS '文章编码';
COMMENT ON COLUMN company.kb_article.article_name IS '标题';
COMMENT ON COLUMN company.kb_article.category IS '分类';
COMMENT ON COLUMN company.kb_article.author_emp_id IS '作者员工 ID';
COMMENT ON COLUMN company.kb_article.body IS '正文';
ALTER TABLE company.kb_article ADD CONSTRAINT fk_kb_article_author_emp_id FOREIGN KEY (author_emp_id) REFERENCES company.hr_employee(id);

-- 知识标签
CREATE TABLE company.kb_article_tag (
    id BIGSERIAL PRIMARY KEY,
    tag_code VARCHAR(32) NOT NULL,
    tag_name VARCHAR(64) NOT NULL,
    color VARCHAR(16),
    sort_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_kb_article_tag UNIQUE (tag_code)
);
COMMENT ON TABLE company.kb_article_tag IS '知识标签';
COMMENT ON COLUMN company.kb_article_tag.id IS '主键';
COMMENT ON COLUMN company.kb_article_tag.tag_code IS '标签编码';
COMMENT ON COLUMN company.kb_article_tag.tag_name IS '标签名';

-- 文章标签关系
CREATE TABLE company.kb_article_tag_rel (
    id BIGSERIAL PRIMARY KEY,
    article_id BIGINT NOT NULL,
    tag_id BIGINT NOT NULL,
    tagged_by BIGINT,
    tagged_at TIMESTAMP,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.kb_article_tag_rel IS '文章标签关系';
COMMENT ON COLUMN company.kb_article_tag_rel.id IS '主键';
COMMENT ON COLUMN company.kb_article_tag_rel.article_id IS '文章 ID';
COMMENT ON COLUMN company.kb_article_tag_rel.tag_id IS '标签 ID';
COMMENT ON COLUMN company.kb_article_tag_rel.tagged_by IS '打标人员工 ID';
COMMENT ON COLUMN company.kb_article_tag_rel.tagged_at IS '打标时间';
ALTER TABLE company.kb_article_tag_rel ADD CONSTRAINT fk_kb_article_tag_rel_article_id FOREIGN KEY (article_id) REFERENCES company.kb_article(id);
ALTER TABLE company.kb_article_tag_rel ADD CONSTRAINT fk_kb_article_tag_rel_tag_id FOREIGN KEY (tag_id) REFERENCES company.kb_article_tag(id);
ALTER TABLE company.kb_article_tag_rel ADD CONSTRAINT fk_kb_article_tag_rel_tagged_by FOREIGN KEY (tagged_by) REFERENCES company.hr_employee(id);

-- 合规检查
CREATE TABLE company.legal_compliance_check (
    id BIGSERIAL PRIMARY KEY,
    chk_code VARCHAR(32) NOT NULL,
    chk_name VARCHAR(128) NOT NULL,
    check_date DATE,
    result VARCHAR(32),
    owner_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_legal_compliance_check UNIQUE (chk_code)
);
COMMENT ON TABLE company.legal_compliance_check IS '合规检查';
COMMENT ON COLUMN company.legal_compliance_check.id IS '主键';
COMMENT ON COLUMN company.legal_compliance_check.chk_code IS '检查编码';
COMMENT ON COLUMN company.legal_compliance_check.chk_name IS '检查名称';
COMMENT ON COLUMN company.legal_compliance_check.result IS '结果';
COMMENT ON COLUMN company.legal_compliance_check.owner_emp_id IS '负责人员工 ID';
ALTER TABLE company.legal_compliance_check ADD CONSTRAINT fk_legal_compliance_check_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);

-- 法务合同台账
CREATE TABLE company.legal_contract (
    id BIGSERIAL PRIMARY KEY,
    lcontract_code VARCHAR(32) NOT NULL,
    lcontract_name VARCHAR(128) NOT NULL,
    counterparty VARCHAR(128),
    sign_date DATE,
    amount NUMERIC(14,2),
    owner_emp_id BIGINT,
    customer_id BIGINT,
    vendor_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_legal_contract UNIQUE (lcontract_code)
);
COMMENT ON TABLE company.legal_contract IS '法务合同台账';
COMMENT ON COLUMN company.legal_contract.id IS '主键';
COMMENT ON COLUMN company.legal_contract.lcontract_code IS '合同编号';
COMMENT ON COLUMN company.legal_contract.lcontract_name IS '合同名称';
COMMENT ON COLUMN company.legal_contract.counterparty IS '相对方';
COMMENT ON COLUMN company.legal_contract.sign_date IS '签订日期';
COMMENT ON COLUMN company.legal_contract.amount IS '金额';
COMMENT ON COLUMN company.legal_contract.owner_emp_id IS '业务负责人员工 ID';
COMMENT ON COLUMN company.legal_contract.customer_id IS '关联客户 ID';
COMMENT ON COLUMN company.legal_contract.vendor_id IS '关联供应商 ID';
ALTER TABLE company.legal_contract ADD CONSTRAINT fk_legal_contract_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.legal_contract ADD CONSTRAINT fk_legal_contract_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);
ALTER TABLE company.legal_contract ADD CONSTRAINT fk_legal_contract_vendor_id FOREIGN KEY (vendor_id) REFERENCES company.fin_vendor(id);

-- 合同关键条款
CREATE TABLE company.legal_contract_clause (
    id BIGSERIAL PRIMARY KEY,
    contract_id BIGINT NOT NULL,
    clause_title VARCHAR(128),
    clause_text TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.legal_contract_clause IS '合同关键条款';
COMMENT ON COLUMN company.legal_contract_clause.id IS '主键';
COMMENT ON COLUMN company.legal_contract_clause.contract_id IS '合同 ID';
COMMENT ON COLUMN company.legal_contract_clause.clause_title IS '条款标题';
COMMENT ON COLUMN company.legal_contract_clause.clause_text IS '条款正文';
ALTER TABLE company.legal_contract_clause ADD CONSTRAINT fk_legal_contract_clause_contract_id FOREIGN KEY (contract_id) REFERENCES company.legal_contract(id);

-- 诉讼/争议案件
CREATE TABLE company.legal_dispute (
    id BIGSERIAL PRIMARY KEY,
    case_code VARCHAR(32) NOT NULL,
    case_name VARCHAR(128) NOT NULL,
    contract_id BIGINT,
    counterpart VARCHAR(128),
    opened_at DATE,
    lawyer VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_legal_dispute UNIQUE (case_code)
);
COMMENT ON TABLE company.legal_dispute IS '诉讼/争议案件';
COMMENT ON COLUMN company.legal_dispute.id IS '主键';
COMMENT ON COLUMN company.legal_dispute.case_code IS '案件编号';
COMMENT ON COLUMN company.legal_dispute.case_name IS '案件名称';
COMMENT ON COLUMN company.legal_dispute.contract_id IS '关联合同 ID';
COMMENT ON COLUMN company.legal_dispute.counterpart IS '对方当事人';
COMMENT ON COLUMN company.legal_dispute.opened_at IS '立案日期';
COMMENT ON COLUMN company.legal_dispute.lawyer IS '承办律师';
ALTER TABLE company.legal_dispute ADD CONSTRAINT fk_legal_dispute_contract_id FOREIGN KEY (contract_id) REFERENCES company.legal_contract(id);

-- 市场活动
CREATE TABLE company.mkt_campaign (
    id BIGSERIAL PRIMARY KEY,
    camp_code VARCHAR(32) NOT NULL,
    camp_name VARCHAR(128) NOT NULL,
    start_date DATE,
    end_date DATE,
    budget NUMERIC(14,2),
    owner_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_mkt_campaign UNIQUE (camp_code)
);
COMMENT ON TABLE company.mkt_campaign IS '市场活动';
COMMENT ON COLUMN company.mkt_campaign.id IS '主键';
COMMENT ON COLUMN company.mkt_campaign.camp_code IS '活动编码';
COMMENT ON COLUMN company.mkt_campaign.camp_name IS '活动名称';
COMMENT ON COLUMN company.mkt_campaign.end_date IS '结束日期';
COMMENT ON COLUMN company.mkt_campaign.budget IS '预算';
COMMENT ON COLUMN company.mkt_campaign.owner_emp_id IS '负责人员工 ID';
ALTER TABLE company.mkt_campaign ADD CONSTRAINT fk_mkt_campaign_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);

-- 活动获客线索
CREATE TABLE company.mkt_campaign_lead (
    id BIGSERIAL PRIMARY KEY,
    camp_id BIGINT NOT NULL,
    lead_id BIGINT,
    channel VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.mkt_campaign_lead IS '活动获客线索';
COMMENT ON COLUMN company.mkt_campaign_lead.id IS '主键';
COMMENT ON COLUMN company.mkt_campaign_lead.camp_id IS '活动 ID';
COMMENT ON COLUMN company.mkt_campaign_lead.lead_id IS '线索 ID';
COMMENT ON COLUMN company.mkt_campaign_lead.channel IS '渠道';
ALTER TABLE company.mkt_campaign_lead ADD CONSTRAINT fk_mkt_campaign_lead_camp_id FOREIGN KEY (camp_id) REFERENCES company.mkt_campaign(id);
ALTER TABLE company.mkt_campaign_lead ADD CONSTRAINT fk_mkt_campaign_lead_lead_id FOREIGN KEY (lead_id) REFERENCES company.crm_lead(id);

-- 内容素材
CREATE TABLE company.mkt_content (
    id BIGSERIAL PRIMARY KEY,
    content_code VARCHAR(32) NOT NULL,
    content_name VARCHAR(128) NOT NULL,
    content_type VARCHAR(32),
    url VARCHAR(512),
    author_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_mkt_content UNIQUE (content_code)
);
COMMENT ON TABLE company.mkt_content IS '内容素材';
COMMENT ON COLUMN company.mkt_content.id IS '主键';
COMMENT ON COLUMN company.mkt_content.content_code IS '素材编码';
COMMENT ON COLUMN company.mkt_content.content_name IS '素材标题';
COMMENT ON COLUMN company.mkt_content.content_type IS '类型';
COMMENT ON COLUMN company.mkt_content.url IS '链接';
COMMENT ON COLUMN company.mkt_content.author_emp_id IS '作者员工 ID';
ALTER TABLE company.mkt_content ADD CONSTRAINT fk_mkt_content_author_emp_id FOREIGN KEY (author_emp_id) REFERENCES company.hr_employee(id);

-- 活动报名
CREATE TABLE company.mkt_event_reg (
    id BIGSERIAL PRIMARY KEY,
    camp_id BIGINT NOT NULL,
    reg_name VARCHAR(64),
    company_name VARCHAR(128),
    phone VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.mkt_event_reg IS '活动报名';
COMMENT ON COLUMN company.mkt_event_reg.id IS '主键';
COMMENT ON COLUMN company.mkt_event_reg.camp_id IS '活动 ID';
COMMENT ON COLUMN company.mkt_event_reg.reg_name IS '报名人';
COMMENT ON COLUMN company.mkt_event_reg.company_name IS '单位';
COMMENT ON COLUMN company.mkt_event_reg.phone IS '电话';
ALTER TABLE company.mkt_event_reg ADD CONSTRAINT fk_mkt_event_reg_camp_id FOREIGN KEY (camp_id) REFERENCES company.mkt_campaign(id);

-- 备份任务
CREATE TABLE company.ops_backup_job (
    id BIGSERIAL PRIMARY KEY,
    bak_code VARCHAR(32) NOT NULL,
    bak_name VARCHAR(128) NOT NULL,
    system_id BIGINT,
    cron_expr VARCHAR(64),
    last_run_at TIMESTAMP,
    last_result VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_ops_backup_job UNIQUE (bak_code)
);
COMMENT ON TABLE company.ops_backup_job IS '备份任务';
COMMENT ON COLUMN company.ops_backup_job.id IS '主键';
COMMENT ON COLUMN company.ops_backup_job.bak_code IS '任务编码';
COMMENT ON COLUMN company.ops_backup_job.bak_name IS '任务名称';
COMMENT ON COLUMN company.ops_backup_job.system_id IS '系统 ID';
COMMENT ON COLUMN company.ops_backup_job.cron_expr IS '调度表达式';
COMMENT ON COLUMN company.ops_backup_job.last_run_at IS '上次执行时间';
COMMENT ON COLUMN company.ops_backup_job.last_result IS '上次结果';
ALTER TABLE company.ops_backup_job ADD CONSTRAINT fk_ops_backup_job_system_id FOREIGN KEY (system_id) REFERENCES company.itm_system(id);

-- 值班排班
CREATE TABLE company.ops_duty_roster (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    duty_date DATE NOT NULL,
    shift_name VARCHAR(32),
    system_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.ops_duty_roster IS '值班排班';
COMMENT ON COLUMN company.ops_duty_roster.id IS '主键';
COMMENT ON COLUMN company.ops_duty_roster.emp_id IS '值班员工 ID';
COMMENT ON COLUMN company.ops_duty_roster.duty_date IS '日期';
COMMENT ON COLUMN company.ops_duty_roster.shift_name IS '班次名';
COMMENT ON COLUMN company.ops_duty_roster.system_id IS '值守系统 ID';
ALTER TABLE company.ops_duty_roster ADD CONSTRAINT fk_ops_duty_roster_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.ops_duty_roster ADD CONSTRAINT fk_ops_duty_roster_system_id FOREIGN KEY (system_id) REFERENCES company.itm_system(id);

-- 监控告警
CREATE TABLE company.ops_monitor_alert (
    id BIGSERIAL PRIMARY KEY,
    system_id BIGINT,
    alert_name VARCHAR(128),
    severity VARCHAR(16),
    fired_at TIMESTAMP,
    acked_by BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.ops_monitor_alert IS '监控告警';
COMMENT ON COLUMN company.ops_monitor_alert.id IS '主键';
COMMENT ON COLUMN company.ops_monitor_alert.system_id IS '系统 ID';
COMMENT ON COLUMN company.ops_monitor_alert.alert_name IS '告警名';
COMMENT ON COLUMN company.ops_monitor_alert.severity IS '级别';
COMMENT ON COLUMN company.ops_monitor_alert.fired_at IS '触发时间';
COMMENT ON COLUMN company.ops_monitor_alert.acked_by IS '确认人员工 ID';
ALTER TABLE company.ops_monitor_alert ADD CONSTRAINT fk_ops_monitor_alert_system_id FOREIGN KEY (system_id) REFERENCES company.itm_system(id);
ALTER TABLE company.ops_monitor_alert ADD CONSTRAINT fk_ops_monitor_alert_acked_by FOREIGN KEY (acked_by) REFERENCES company.hr_employee(id);

-- 运维手册
CREATE TABLE company.ops_runbook (
    id BIGSERIAL PRIMARY KEY,
    rb_code VARCHAR(32) NOT NULL,
    rb_name VARCHAR(128) NOT NULL,
    system_id BIGINT,
    content TEXT,
    owner_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_ops_runbook UNIQUE (rb_code)
);
COMMENT ON TABLE company.ops_runbook IS '运维手册';
COMMENT ON COLUMN company.ops_runbook.id IS '主键';
COMMENT ON COLUMN company.ops_runbook.rb_code IS '手册编码';
COMMENT ON COLUMN company.ops_runbook.rb_name IS '手册名称';
COMMENT ON COLUMN company.ops_runbook.system_id IS '系统 ID';
COMMENT ON COLUMN company.ops_runbook.content IS '正文';
COMMENT ON COLUMN company.ops_runbook.owner_emp_id IS '维护人员工 ID';
ALTER TABLE company.ops_runbook ADD CONSTRAINT fk_ops_runbook_system_id FOREIGN KEY (system_id) REFERENCES company.itm_system(id);
ALTER TABLE company.ops_runbook ADD CONSTRAINT fk_ops_runbook_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);

-- 内部公告
CREATE TABLE company.org_announcement (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(256) NOT NULL,
    content TEXT,
    publisher_emp_id BIGINT,
    publish_at TIMESTAMP,
    scope VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.org_announcement IS '内部公告';
COMMENT ON COLUMN company.org_announcement.id IS '主键';
COMMENT ON COLUMN company.org_announcement.title IS '标题';
COMMENT ON COLUMN company.org_announcement.content IS '正文';
COMMENT ON COLUMN company.org_announcement.publisher_emp_id IS '发布人员工 ID';
COMMENT ON COLUMN company.org_announcement.publish_at IS '发布时间';
COMMENT ON COLUMN company.org_announcement.scope IS '发布范围';
ALTER TABLE company.org_announcement ADD CONSTRAINT fk_org_announcement_publisher_emp_id FOREIGN KEY (publisher_emp_id) REFERENCES company.hr_employee(id);

-- 业务单元
CREATE TABLE company.org_biz_unit (
    id BIGSERIAL PRIMARY KEY,
    bu_code VARCHAR(32) NOT NULL,
    bu_name VARCHAR(128) NOT NULL,
    leader_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_org_biz_unit UNIQUE (bu_code)
);
COMMENT ON TABLE company.org_biz_unit IS '业务单元';
COMMENT ON COLUMN company.org_biz_unit.id IS '主键';
COMMENT ON COLUMN company.org_biz_unit.bu_code IS '业务单元编码';
COMMENT ON COLUMN company.org_biz_unit.bu_name IS '业务单元名称';
COMMENT ON COLUMN company.org_biz_unit.leader_emp_id IS '负责人员工 ID';
ALTER TABLE company.org_biz_unit ADD CONSTRAINT fk_org_biz_unit_leader_emp_id FOREIGN KEY (leader_emp_id) REFERENCES company.hr_employee(id);

-- 法人公司
CREATE TABLE company.org_company (
    id BIGSERIAL PRIMARY KEY,
    company_code VARCHAR(32) NOT NULL,
    company_name VARCHAR(128) NOT NULL,
    legal_name VARCHAR(256),
    tax_no VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_org_company UNIQUE (company_code)
);
COMMENT ON TABLE company.org_company IS '法人公司';
COMMENT ON COLUMN company.org_company.id IS '主键';
COMMENT ON COLUMN company.org_company.company_code IS '公司编码';
COMMENT ON COLUMN company.org_company.company_name IS '公司名称';
COMMENT ON COLUMN company.org_company.legal_name IS '法定名称';
COMMENT ON COLUMN company.org_company.tax_no IS '税号';

-- 成本中心
CREATE TABLE company.org_cost_center (
    id BIGSERIAL PRIMARY KEY,
    cc_code VARCHAR(32) NOT NULL,
    cc_name VARCHAR(128) NOT NULL,
    dept_id BIGINT,
    owner_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_org_cost_center UNIQUE (cc_code)
);
COMMENT ON TABLE company.org_cost_center IS '成本中心';
COMMENT ON COLUMN company.org_cost_center.id IS '主键';
COMMENT ON COLUMN company.org_cost_center.cc_code IS '成本中心编码';
COMMENT ON COLUMN company.org_cost_center.cc_name IS '成本中心名称';
COMMENT ON COLUMN company.org_cost_center.dept_id IS '关联部门 ID';
COMMENT ON COLUMN company.org_cost_center.owner_emp_id IS '负责人员工 ID';
ALTER TABLE company.org_cost_center ADD CONSTRAINT fk_org_cost_center_dept_id FOREIGN KEY (dept_id) REFERENCES company.org_department(id);
ALTER TABLE company.org_cost_center ADD CONSTRAINT fk_org_cost_center_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);

-- 部门变更记录
CREATE TABLE company.org_dept_change (
    id BIGSERIAL PRIMARY KEY,
    dept_id BIGINT NOT NULL,
    change_type VARCHAR(32),
    old_parent_id BIGINT,
    new_parent_id BIGINT,
    effective_date DATE,
    operator_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.org_dept_change IS '部门变更记录';
COMMENT ON COLUMN company.org_dept_change.id IS '主键';
COMMENT ON COLUMN company.org_dept_change.dept_id IS '部门 ID';
COMMENT ON COLUMN company.org_dept_change.change_type IS '变更类型';
COMMENT ON COLUMN company.org_dept_change.old_parent_id IS '原上级部门 ID';
COMMENT ON COLUMN company.org_dept_change.new_parent_id IS '新上级部门 ID';
COMMENT ON COLUMN company.org_dept_change.effective_date IS '生效日期';
COMMENT ON COLUMN company.org_dept_change.operator_emp_id IS '操作人员工 ID';
ALTER TABLE company.org_dept_change ADD CONSTRAINT fk_org_dept_change_dept_id FOREIGN KEY (dept_id) REFERENCES company.org_department(id);
ALTER TABLE company.org_dept_change ADD CONSTRAINT fk_org_dept_change_operator_emp_id FOREIGN KEY (operator_emp_id) REFERENCES company.hr_employee(id);

-- 部门闭包表（祖先-后代）
CREATE TABLE company.org_dept_closure (
    id BIGSERIAL PRIMARY KEY,
    ancestor_id BIGINT NOT NULL,
    descendant_id BIGINT NOT NULL,
    depth INT NOT NULL,
    CONSTRAINT uk_org_dept_closure UNIQUE (ancestor_id, descendant_id)
);
COMMENT ON TABLE company.org_dept_closure IS '部门闭包表（祖先-后代）';
COMMENT ON COLUMN company.org_dept_closure.id IS '主键';
COMMENT ON COLUMN company.org_dept_closure.ancestor_id IS '祖先部门 ID';
COMMENT ON COLUMN company.org_dept_closure.descendant_id IS '后代部门 ID';
COMMENT ON COLUMN company.org_dept_closure.depth IS '层级深度';
ALTER TABLE company.org_dept_closure ADD CONSTRAINT fk_org_dept_closure_ancestor_id FOREIGN KEY (ancestor_id) REFERENCES company.org_department(id);
ALTER TABLE company.org_dept_closure ADD CONSTRAINT fk_org_dept_closure_descendant_id FOREIGN KEY (descendant_id) REFERENCES company.org_department(id);

-- 地理区位
CREATE TABLE company.org_location (
    id BIGSERIAL PRIMARY KEY,
    loc_code VARCHAR(32) NOT NULL,
    loc_name VARCHAR(128) NOT NULL,
    region VARCHAR(32),
    country VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_org_location UNIQUE (loc_code)
);
COMMENT ON TABLE company.org_location IS '地理区位';
COMMENT ON COLUMN company.org_location.id IS '主键';
COMMENT ON COLUMN company.org_location.loc_code IS '区位编码';
COMMENT ON COLUMN company.org_location.loc_name IS '区位名称';
COMMENT ON COLUMN company.org_location.region IS '大区';
COMMENT ON COLUMN company.org_location.country IS '国家地区';

-- 办公职场
CREATE TABLE company.org_office (
    id BIGSERIAL PRIMARY KEY,
    office_code VARCHAR(32) NOT NULL,
    office_name VARCHAR(128) NOT NULL,
    city VARCHAR(32),
    address VARCHAR(256),
    company_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_org_office UNIQUE (office_code)
);
COMMENT ON TABLE company.org_office IS '办公职场';
COMMENT ON COLUMN company.org_office.id IS '主键';
COMMENT ON COLUMN company.org_office.office_code IS '职场编码';
COMMENT ON COLUMN company.org_office.office_name IS '职场名称';
COMMENT ON COLUMN company.org_office.city IS '城市';
COMMENT ON COLUMN company.org_office.address IS '地址';
COMMENT ON COLUMN company.org_office.company_id IS '所属公司 ID';
ALTER TABLE company.org_office ADD CONSTRAINT fk_org_office_company_id FOREIGN KEY (company_id) REFERENCES company.org_company(id);

-- 岗位编制
CREATE TABLE company.org_position (
    id BIGSERIAL PRIMARY KEY,
    pos_code VARCHAR(32) NOT NULL,
    pos_name VARCHAR(128) NOT NULL,
    dept_id BIGINT,
    job_level_id BIGINT,
    headcount INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_org_position UNIQUE (pos_code)
);
COMMENT ON TABLE company.org_position IS '岗位编制';
COMMENT ON COLUMN company.org_position.id IS '主键';
COMMENT ON COLUMN company.org_position.pos_code IS '岗位编码';
COMMENT ON COLUMN company.org_position.pos_name IS '岗位名称';
COMMENT ON COLUMN company.org_position.dept_id IS '所属部门 ID';
COMMENT ON COLUMN company.org_position.job_level_id IS '对应职级 ID';
COMMENT ON COLUMN company.org_position.headcount IS '编制人数';
ALTER TABLE company.org_position ADD CONSTRAINT fk_org_position_dept_id FOREIGN KEY (dept_id) REFERENCES company.org_department(id);
ALTER TABLE company.org_position ADD CONSTRAINT fk_org_position_job_level_id FOREIGN KEY (job_level_id) REFERENCES company.hr_job_level(id);

-- 公司印章台账
CREATE TABLE company.org_seal (
    id BIGSERIAL PRIMARY KEY,
    seal_code VARCHAR(32) NOT NULL,
    seal_name VARCHAR(128) NOT NULL,
    company_id BIGINT,
    keeper_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_org_seal UNIQUE (seal_code)
);
COMMENT ON TABLE company.org_seal IS '公司印章台账';
COMMENT ON COLUMN company.org_seal.id IS '主键';
COMMENT ON COLUMN company.org_seal.seal_code IS '印章编码';
COMMENT ON COLUMN company.org_seal.seal_name IS '印章名称';
COMMENT ON COLUMN company.org_seal.company_id IS '所属公司 ID';
COMMENT ON COLUMN company.org_seal.keeper_emp_id IS '保管人员工 ID';
ALTER TABLE company.org_seal ADD CONSTRAINT fk_org_seal_company_id FOREIGN KEY (company_id) REFERENCES company.org_company(id);
ALTER TABLE company.org_seal ADD CONSTRAINT fk_org_seal_keeper_emp_id FOREIGN KEY (keeper_emp_id) REFERENCES company.hr_employee(id);

-- 产品功能点
CREATE TABLE company.prd_feature (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    feature_code VARCHAR(32),
    feature_name VARCHAR(128),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_prd_feature UNIQUE (feature_code)
);
COMMENT ON TABLE company.prd_feature IS '产品功能点';
COMMENT ON COLUMN company.prd_feature.id IS '主键';
COMMENT ON COLUMN company.prd_feature.product_id IS '产品 ID';
COMMENT ON COLUMN company.prd_feature.feature_code IS '功能编码';
COMMENT ON COLUMN company.prd_feature.feature_name IS '功能名称';
ALTER TABLE company.prd_feature ADD CONSTRAINT fk_prd_feature_product_id FOREIGN KEY (product_id) REFERENCES company.prd_product(id);

-- 产品授权许可
CREATE TABLE company.prd_license (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    customer_id BIGINT,
    license_key VARCHAR(128),
    seat_count INT,
    expire_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prd_license IS '产品授权许可';
COMMENT ON COLUMN company.prd_license.id IS '主键';
COMMENT ON COLUMN company.prd_license.product_id IS '产品 ID';
COMMENT ON COLUMN company.prd_license.customer_id IS '客户 ID';
COMMENT ON COLUMN company.prd_license.license_key IS '许可密钥';
COMMENT ON COLUMN company.prd_license.seat_count IS '席位数';
COMMENT ON COLUMN company.prd_license.expire_date IS '到期日';
ALTER TABLE company.prd_license ADD CONSTRAINT fk_prd_license_product_id FOREIGN KEY (product_id) REFERENCES company.prd_product(id);
ALTER TABLE company.prd_license ADD CONSTRAINT fk_prd_license_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);

-- 产品线
CREATE TABLE company.prd_product_line (
    id BIGSERIAL PRIMARY KEY,
    line_code VARCHAR(32) NOT NULL,
    line_name VARCHAR(128) NOT NULL,
    owner_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_prd_product_line UNIQUE (line_code)
);
COMMENT ON TABLE company.prd_product_line IS '产品线';
COMMENT ON COLUMN company.prd_product_line.id IS '主键';
COMMENT ON COLUMN company.prd_product_line.line_code IS '产品线编码';
COMMENT ON COLUMN company.prd_product_line.line_name IS '产品线名称';
COMMENT ON COLUMN company.prd_product_line.owner_emp_id IS '负责人员工 ID';
ALTER TABLE company.prd_product_line ADD CONSTRAINT fk_prd_product_line_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);

-- 产品版本
CREATE TABLE company.prd_product_version (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    version_no VARCHAR(32),
    release_date DATE,
    changelog TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prd_product_version IS '产品版本';
COMMENT ON COLUMN company.prd_product_version.id IS '主键';
COMMENT ON COLUMN company.prd_product_version.product_id IS '产品 ID';
COMMENT ON COLUMN company.prd_product_version.version_no IS '版本号';
COMMENT ON COLUMN company.prd_product_version.changelog IS '变更说明';
ALTER TABLE company.prd_product_version ADD CONSTRAINT fk_prd_product_version_product_id FOREIGN KEY (product_id) REFERENCES company.prd_product(id);

-- 产品路线图项
CREATE TABLE company.prd_roadmap (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    item_name VARCHAR(128),
    target_quarter VARCHAR(8),
    priority VARCHAR(16),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prd_roadmap IS '产品路线图项';
COMMENT ON COLUMN company.prd_roadmap.id IS '主键';
COMMENT ON COLUMN company.prd_roadmap.product_id IS '产品 ID';
COMMENT ON COLUMN company.prd_roadmap.item_name IS '事项名称';
COMMENT ON COLUMN company.prd_roadmap.target_quarter IS '目标季度';
COMMENT ON COLUMN company.prd_roadmap.priority IS '优先级';
ALTER TABLE company.prd_roadmap ADD CONSTRAINT fk_prd_roadmap_product_id FOREIGN KEY (product_id) REFERENCES company.prd_product(id);

-- 项目验收
CREATE TABLE company.prj_acceptance (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL,
    accept_date DATE,
    result VARCHAR(32),
    customer_signer VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prj_acceptance IS '项目验收';
COMMENT ON COLUMN company.prj_acceptance.id IS '主键';
COMMENT ON COLUMN company.prj_acceptance.project_id IS '项目 ID';
COMMENT ON COLUMN company.prj_acceptance.accept_date IS '验收日期';
COMMENT ON COLUMN company.prj_acceptance.result IS '验收结果';
COMMENT ON COLUMN company.prj_acceptance.customer_signer IS '客户签字人';
ALTER TABLE company.prj_acceptance ADD CONSTRAINT fk_prj_acceptance_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);

-- 项目变更申请
CREATE TABLE company.prj_change_request (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL,
    title VARCHAR(256),
    impact TEXT,
    requester_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prj_change_request IS '项目变更申请';
COMMENT ON COLUMN company.prj_change_request.id IS '主键';
COMMENT ON COLUMN company.prj_change_request.project_id IS '项目 ID';
COMMENT ON COLUMN company.prj_change_request.title IS '变更标题';
COMMENT ON COLUMN company.prj_change_request.impact IS '影响说明';
COMMENT ON COLUMN company.prj_change_request.requester_emp_id IS '申请人员工 ID';
ALTER TABLE company.prj_change_request ADD CONSTRAINT fk_prj_change_request_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);
ALTER TABLE company.prj_change_request ADD CONSTRAINT fk_prj_change_request_requester_emp_id FOREIGN KEY (requester_emp_id) REFERENCES company.hr_employee(id);

-- 项目文档索引
CREATE TABLE company.prj_document (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL,
    doc_name VARCHAR(256),
    doc_type VARCHAR(32),
    url VARCHAR(512),
    uploader_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prj_document IS '项目文档索引';
COMMENT ON COLUMN company.prj_document.id IS '主键';
COMMENT ON COLUMN company.prj_document.project_id IS '项目 ID';
COMMENT ON COLUMN company.prj_document.doc_name IS '文档名称';
COMMENT ON COLUMN company.prj_document.doc_type IS '文档类型';
COMMENT ON COLUMN company.prj_document.url IS '链接';
COMMENT ON COLUMN company.prj_document.uploader_emp_id IS '上传人员工 ID';
ALTER TABLE company.prj_document ADD CONSTRAINT fk_prj_document_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);
ALTER TABLE company.prj_document ADD CONSTRAINT fk_prj_document_uploader_emp_id FOREIGN KEY (uploader_emp_id) REFERENCES company.hr_employee(id);

-- 项目问题单
CREATE TABLE company.prj_issue (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL,
    title VARCHAR(256),
    severity VARCHAR(16),
    reporter_emp_id BIGINT,
    assignee_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prj_issue IS '项目问题单';
COMMENT ON COLUMN company.prj_issue.id IS '主键';
COMMENT ON COLUMN company.prj_issue.project_id IS '项目 ID';
COMMENT ON COLUMN company.prj_issue.title IS '标题';
COMMENT ON COLUMN company.prj_issue.severity IS '严重级别';
COMMENT ON COLUMN company.prj_issue.reporter_emp_id IS '报告人员工 ID';
COMMENT ON COLUMN company.prj_issue.assignee_emp_id IS '处理人员工 ID';
ALTER TABLE company.prj_issue ADD CONSTRAINT fk_prj_issue_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);
ALTER TABLE company.prj_issue ADD CONSTRAINT fk_prj_issue_reporter_emp_id FOREIGN KEY (reporter_emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.prj_issue ADD CONSTRAINT fk_prj_issue_assignee_emp_id FOREIGN KEY (assignee_emp_id) REFERENCES company.hr_employee(id);

-- 项目里程碑
CREATE TABLE company.prj_milestone (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL,
    milestone_name VARCHAR(128),
    plan_date DATE,
    actual_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prj_milestone IS '项目里程碑';
COMMENT ON COLUMN company.prj_milestone.id IS '主键';
COMMENT ON COLUMN company.prj_milestone.project_id IS '项目 ID';
COMMENT ON COLUMN company.prj_milestone.milestone_name IS '里程碑名称';
COMMENT ON COLUMN company.prj_milestone.actual_date IS '实际日期';
ALTER TABLE company.prj_milestone ADD CONSTRAINT fk_prj_milestone_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);

-- 项目风险
CREATE TABLE company.prj_risk (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL,
    risk_title VARCHAR(256),
    level VARCHAR(16),
    owner_emp_id BIGINT,
    mitigation TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prj_risk IS '项目风险';
COMMENT ON COLUMN company.prj_risk.id IS '主键';
COMMENT ON COLUMN company.prj_risk.project_id IS '项目 ID';
COMMENT ON COLUMN company.prj_risk.risk_title IS '风险标题';
COMMENT ON COLUMN company.prj_risk.level IS '风险等级';
COMMENT ON COLUMN company.prj_risk.owner_emp_id IS '责任人员工 ID';
COMMENT ON COLUMN company.prj_risk.mitigation IS '缓解措施';
ALTER TABLE company.prj_risk ADD CONSTRAINT fk_prj_risk_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);
ALTER TABLE company.prj_risk ADD CONSTRAINT fk_prj_risk_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);

-- 项目干系人
CREATE TABLE company.prj_stakeholder (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL,
    emp_id BIGINT,
    external_name VARCHAR(64),
    role VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prj_stakeholder IS '项目干系人';
COMMENT ON COLUMN company.prj_stakeholder.id IS '主键';
COMMENT ON COLUMN company.prj_stakeholder.project_id IS '项目 ID';
COMMENT ON COLUMN company.prj_stakeholder.emp_id IS '内部员工 ID';
COMMENT ON COLUMN company.prj_stakeholder.external_name IS '外部干系人姓名';
COMMENT ON COLUMN company.prj_stakeholder.role IS '角色';
ALTER TABLE company.prj_stakeholder ADD CONSTRAINT fk_prj_stakeholder_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);
ALTER TABLE company.prj_stakeholder ADD CONSTRAINT fk_prj_stakeholder_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 项目任务
CREATE TABLE company.prj_task (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL,
    task_name VARCHAR(128),
    assignee_emp_id BIGINT,
    plan_start DATE,
    plan_end DATE,
    progress_pct NUMERIC(6,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prj_task IS '项目任务';
COMMENT ON COLUMN company.prj_task.id IS '主键';
COMMENT ON COLUMN company.prj_task.project_id IS '项目 ID';
COMMENT ON COLUMN company.prj_task.task_name IS '任务名称';
COMMENT ON COLUMN company.prj_task.assignee_emp_id IS '负责人员工 ID';
COMMENT ON COLUMN company.prj_task.plan_start IS '计划开始';
COMMENT ON COLUMN company.prj_task.plan_end IS '计划结束';
COMMENT ON COLUMN company.prj_task.progress_pct IS '进度百分比';
ALTER TABLE company.prj_task ADD CONSTRAINT fk_prj_task_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);
ALTER TABLE company.prj_task ADD CONSTRAINT fk_prj_task_assignee_emp_id FOREIGN KEY (assignee_emp_id) REFERENCES company.hr_employee(id);

-- 项目质保
CREATE TABLE company.prj_warranty (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL,
    start_date DATE,
    end_date DATE,
    terms TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prj_warranty IS '项目质保';
COMMENT ON COLUMN company.prj_warranty.id IS '主键';
COMMENT ON COLUMN company.prj_warranty.project_id IS '项目 ID';
COMMENT ON COLUMN company.prj_warranty.start_date IS '质保开始';
COMMENT ON COLUMN company.prj_warranty.terms IS '质保条款';
ALTER TABLE company.prj_warranty ADD CONSTRAINT fk_prj_warranty_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);

-- 项目周报
CREATE TABLE company.prj_weekly_report (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL,
    week_start DATE,
    author_emp_id BIGINT,
    content TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.prj_weekly_report IS '项目周报';
COMMENT ON COLUMN company.prj_weekly_report.id IS '主键';
COMMENT ON COLUMN company.prj_weekly_report.project_id IS '项目 ID';
COMMENT ON COLUMN company.prj_weekly_report.week_start IS '周起始日';
COMMENT ON COLUMN company.prj_weekly_report.author_emp_id IS '填写人员工 ID';
COMMENT ON COLUMN company.prj_weekly_report.content IS '周报内容';
ALTER TABLE company.prj_weekly_report ADD CONSTRAINT fk_prj_weekly_report_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);
ALTER TABLE company.prj_weekly_report ADD CONSTRAINT fk_prj_weekly_report_author_emp_id FOREIGN KEY (author_emp_id) REFERENCES company.hr_employee(id);

-- 缺陷
CREATE TABLE company.qa_defect (
    id BIGSERIAL PRIMARY KEY,
    bug_code VARCHAR(32) NOT NULL,
    bug_name VARCHAR(128) NOT NULL,
    project_id BIGINT,
    product_id BIGINT,
    severity VARCHAR(16),
    reporter_emp_id BIGINT,
    assignee_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_qa_defect UNIQUE (bug_code)
);
COMMENT ON TABLE company.qa_defect IS '缺陷';
COMMENT ON COLUMN company.qa_defect.id IS '主键';
COMMENT ON COLUMN company.qa_defect.bug_code IS '缺陷编号';
COMMENT ON COLUMN company.qa_defect.bug_name IS '缺陷标题';
COMMENT ON COLUMN company.qa_defect.project_id IS '项目 ID';
COMMENT ON COLUMN company.qa_defect.product_id IS '产品 ID';
COMMENT ON COLUMN company.qa_defect.severity IS '严重级别';
COMMENT ON COLUMN company.qa_defect.reporter_emp_id IS '报告人员工 ID';
COMMENT ON COLUMN company.qa_defect.assignee_emp_id IS '修复人员工 ID';
ALTER TABLE company.qa_defect ADD CONSTRAINT fk_qa_defect_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);
ALTER TABLE company.qa_defect ADD CONSTRAINT fk_qa_defect_product_id FOREIGN KEY (product_id) REFERENCES company.prd_product(id);
ALTER TABLE company.qa_defect ADD CONSTRAINT fk_qa_defect_reporter_emp_id FOREIGN KEY (reporter_emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.qa_defect ADD CONSTRAINT fk_qa_defect_assignee_emp_id FOREIGN KEY (assignee_emp_id) REFERENCES company.hr_employee(id);

-- 发布门禁检查
CREATE TABLE company.qa_release_gate (
    id BIGSERIAL PRIMARY KEY,
    system_id BIGINT,
    version_no VARCHAR(32),
    gate_name VARCHAR(64),
    passed BOOLEAN,
    checked_by BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_qa_release_gate UNIQUE (version_no)
);
COMMENT ON TABLE company.qa_release_gate IS '发布门禁检查';
COMMENT ON COLUMN company.qa_release_gate.id IS '主键';
COMMENT ON COLUMN company.qa_release_gate.system_id IS '系统 ID';
COMMENT ON COLUMN company.qa_release_gate.version_no IS '版本';
COMMENT ON COLUMN company.qa_release_gate.gate_name IS '门禁项';
COMMENT ON COLUMN company.qa_release_gate.passed IS '是否通过';
COMMENT ON COLUMN company.qa_release_gate.checked_by IS '检查人员工 ID';
ALTER TABLE company.qa_release_gate ADD CONSTRAINT fk_qa_release_gate_system_id FOREIGN KEY (system_id) REFERENCES company.itm_system(id);
ALTER TABLE company.qa_release_gate ADD CONSTRAINT fk_qa_release_gate_checked_by FOREIGN KEY (checked_by) REFERENCES company.hr_employee(id);

-- 测试计划
CREATE TABLE company.qa_test_plan (
    id BIGSERIAL PRIMARY KEY,
    plan_code VARCHAR(32) NOT NULL,
    plan_name VARCHAR(128) NOT NULL,
    project_id BIGINT,
    product_id BIGINT,
    owner_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_qa_test_plan UNIQUE (plan_code)
);
COMMENT ON TABLE company.qa_test_plan IS '测试计划';
COMMENT ON COLUMN company.qa_test_plan.id IS '主键';
COMMENT ON COLUMN company.qa_test_plan.plan_code IS '计划编码';
COMMENT ON COLUMN company.qa_test_plan.plan_name IS '计划名称';
COMMENT ON COLUMN company.qa_test_plan.project_id IS '项目 ID';
COMMENT ON COLUMN company.qa_test_plan.product_id IS '产品 ID';
COMMENT ON COLUMN company.qa_test_plan.owner_emp_id IS '测试负责人员工 ID';
ALTER TABLE company.qa_test_plan ADD CONSTRAINT fk_qa_test_plan_project_id FOREIGN KEY (project_id) REFERENCES company.prj_project(id);
ALTER TABLE company.qa_test_plan ADD CONSTRAINT fk_qa_test_plan_product_id FOREIGN KEY (product_id) REFERENCES company.prd_product(id);
ALTER TABLE company.qa_test_plan ADD CONSTRAINT fk_qa_test_plan_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);

-- 销售渠道
CREATE TABLE company.sal_channel (
    id BIGSERIAL PRIMARY KEY,
    channel_code VARCHAR(32) NOT NULL,
    channel_name VARCHAR(128) NOT NULL,
    channel_type VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_sal_channel UNIQUE (channel_code)
);
COMMENT ON TABLE company.sal_channel IS '销售渠道';
COMMENT ON COLUMN company.sal_channel.id IS '主键';
COMMENT ON COLUMN company.sal_channel.channel_code IS '渠道编码';
COMMENT ON COLUMN company.sal_channel.channel_name IS '渠道名称';
COMMENT ON COLUMN company.sal_channel.channel_type IS '渠道类型';

-- 销售提成明细
CREATE TABLE company.sal_commission (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    order_id BIGINT,
    year_month VARCHAR(7),
    amount NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.sal_commission IS '销售提成明细';
COMMENT ON COLUMN company.sal_commission.id IS '主键';
COMMENT ON COLUMN company.sal_commission.emp_id IS '销售员工 ID';
COMMENT ON COLUMN company.sal_commission.order_id IS '订单 ID';
COMMENT ON COLUMN company.sal_commission.year_month IS '年月';
COMMENT ON COLUMN company.sal_commission.amount IS '提成金额';
ALTER TABLE company.sal_commission ADD CONSTRAINT fk_sal_commission_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.sal_commission ADD CONSTRAINT fk_sal_commission_order_id FOREIGN KEY (order_id) REFERENCES company.sal_sales_order(id);

-- 销售提成规则
CREATE TABLE company.sal_commission_rule (
    id BIGSERIAL PRIMARY KEY,
    rule_code VARCHAR(32) NOT NULL,
    rule_name VARCHAR(128) NOT NULL,
    rate_pct NUMERIC(6,2),
    product_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_sal_commission_rule UNIQUE (rule_code)
);
COMMENT ON TABLE company.sal_commission_rule IS '销售提成规则';
COMMENT ON COLUMN company.sal_commission_rule.id IS '主键';
COMMENT ON COLUMN company.sal_commission_rule.rule_code IS '规则编码';
COMMENT ON COLUMN company.sal_commission_rule.rule_name IS '规则名称';
COMMENT ON COLUMN company.sal_commission_rule.rate_pct IS '提成比例';
COMMENT ON COLUMN company.sal_commission_rule.product_id IS '适用产品 ID';
ALTER TABLE company.sal_commission_rule ADD CONSTRAINT fk_sal_commission_rule_product_id FOREIGN KEY (product_id) REFERENCES company.prd_product(id);

-- 销售合同
CREATE TABLE company.sal_contract (
    id BIGSERIAL PRIMARY KEY,
    contract_code VARCHAR(32) NOT NULL,
    contract_name VARCHAR(128) NOT NULL,
    customer_id BIGINT,
    order_id BIGINT,
    sign_date DATE,
    amount NUMERIC(14,2),
    owner_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_sal_contract UNIQUE (contract_code)
);
COMMENT ON TABLE company.sal_contract IS '销售合同';
COMMENT ON COLUMN company.sal_contract.id IS '主键';
COMMENT ON COLUMN company.sal_contract.contract_code IS '合同编号';
COMMENT ON COLUMN company.sal_contract.contract_name IS '合同名称';
COMMENT ON COLUMN company.sal_contract.customer_id IS '客户 ID';
COMMENT ON COLUMN company.sal_contract.order_id IS '关联订单 ID';
COMMENT ON COLUMN company.sal_contract.sign_date IS '签订日期';
COMMENT ON COLUMN company.sal_contract.amount IS '合同金额';
COMMENT ON COLUMN company.sal_contract.owner_emp_id IS '负责销售员工 ID';
ALTER TABLE company.sal_contract ADD CONSTRAINT fk_sal_contract_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);
ALTER TABLE company.sal_contract ADD CONSTRAINT fk_sal_contract_order_id FOREIGN KEY (order_id) REFERENCES company.sal_sales_order(id);
ALTER TABLE company.sal_contract ADD CONSTRAINT fk_sal_contract_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);

-- 合同里程碑收款
CREATE TABLE company.sal_contract_milestone (
    id BIGSERIAL PRIMARY KEY,
    contract_id BIGINT NOT NULL,
    milestone_name VARCHAR(128),
    due_date DATE,
    amount NUMERIC(14,2),
    received_amount NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.sal_contract_milestone IS '合同里程碑收款';
COMMENT ON COLUMN company.sal_contract_milestone.id IS '主键';
COMMENT ON COLUMN company.sal_contract_milestone.contract_id IS '合同 ID';
COMMENT ON COLUMN company.sal_contract_milestone.milestone_name IS '里程碑名称';
COMMENT ON COLUMN company.sal_contract_milestone.amount IS '应收金额';
COMMENT ON COLUMN company.sal_contract_milestone.received_amount IS '已收金额';
ALTER TABLE company.sal_contract_milestone ADD CONSTRAINT fk_sal_contract_milestone_contract_id FOREIGN KEY (contract_id) REFERENCES company.sal_contract(id);

-- 发货/交付单
CREATE TABLE company.sal_delivery (
    id BIGSERIAL PRIMARY KEY,
    delivery_code VARCHAR(32) NOT NULL,
    delivery_name VARCHAR(128) NOT NULL,
    order_id BIGINT,
    delivery_date DATE,
    receiver VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_sal_delivery UNIQUE (delivery_code)
);
COMMENT ON TABLE company.sal_delivery IS '发货/交付单';
COMMENT ON COLUMN company.sal_delivery.id IS '主键';
COMMENT ON COLUMN company.sal_delivery.delivery_code IS '交付单号';
COMMENT ON COLUMN company.sal_delivery.delivery_name IS '交付说明';
COMMENT ON COLUMN company.sal_delivery.order_id IS '订单 ID';
COMMENT ON COLUMN company.sal_delivery.delivery_date IS '交付日期';
COMMENT ON COLUMN company.sal_delivery.receiver IS '收货人';
ALTER TABLE company.sal_delivery ADD CONSTRAINT fk_sal_delivery_order_id FOREIGN KEY (order_id) REFERENCES company.sal_sales_order(id);

-- 交付明细
CREATE TABLE company.sal_delivery_item (
    id BIGSERIAL PRIMARY KEY,
    delivery_id BIGINT NOT NULL,
    product_id BIGINT,
    qty NUMERIC(12,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.sal_delivery_item IS '交付明细';
COMMENT ON COLUMN company.sal_delivery_item.id IS '主键';
COMMENT ON COLUMN company.sal_delivery_item.delivery_id IS '交付单 ID';
COMMENT ON COLUMN company.sal_delivery_item.product_id IS '产品 ID';
COMMENT ON COLUMN company.sal_delivery_item.qty IS '数量';
ALTER TABLE company.sal_delivery_item ADD CONSTRAINT fk_sal_delivery_item_delivery_id FOREIGN KEY (delivery_id) REFERENCES company.sal_delivery(id);
ALTER TABLE company.sal_delivery_item ADD CONSTRAINT fk_sal_delivery_item_product_id FOREIGN KEY (product_id) REFERENCES company.prd_product(id);

-- 价格表
CREATE TABLE company.sal_price_list (
    id BIGSERIAL PRIMARY KEY,
    plist_code VARCHAR(32) NOT NULL,
    plist_name VARCHAR(128) NOT NULL,
    currency VARCHAR(8),
    effective_from DATE,
    effective_to DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_sal_price_list UNIQUE (plist_code)
);
COMMENT ON TABLE company.sal_price_list IS '价格表';
COMMENT ON COLUMN company.sal_price_list.id IS '主键';
COMMENT ON COLUMN company.sal_price_list.plist_code IS '价格表编码';
COMMENT ON COLUMN company.sal_price_list.plist_name IS '价格表名称';
COMMENT ON COLUMN company.sal_price_list.effective_from IS '生效起';
COMMENT ON COLUMN company.sal_price_list.effective_to IS '生效止';

-- 价格表明细
CREATE TABLE company.sal_price_list_item (
    id BIGSERIAL PRIMARY KEY,
    plist_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    unit_price NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.sal_price_list_item IS '价格表明细';
COMMENT ON COLUMN company.sal_price_list_item.id IS '主键';
COMMENT ON COLUMN company.sal_price_list_item.plist_id IS '价格表 ID';
COMMENT ON COLUMN company.sal_price_list_item.product_id IS '产品 ID';
COMMENT ON COLUMN company.sal_price_list_item.unit_price IS '单价';
ALTER TABLE company.sal_price_list_item ADD CONSTRAINT fk_sal_price_list_item_plist_id FOREIGN KEY (plist_id) REFERENCES company.sal_price_list(id);
ALTER TABLE company.sal_price_list_item ADD CONSTRAINT fk_sal_price_list_item_product_id FOREIGN KEY (product_id) REFERENCES company.prd_product(id);

-- 销售报价单
CREATE TABLE company.sal_quote (
    id BIGSERIAL PRIMARY KEY,
    quote_code VARCHAR(32) NOT NULL,
    quote_name VARCHAR(128) NOT NULL,
    customer_id BIGINT,
    owner_emp_id BIGINT,
    total_amount NUMERIC(14,2),
    valid_until DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_sal_quote UNIQUE (quote_code)
);
COMMENT ON TABLE company.sal_quote IS '销售报价单';
COMMENT ON COLUMN company.sal_quote.id IS '主键';
COMMENT ON COLUMN company.sal_quote.quote_code IS '报价单号';
COMMENT ON COLUMN company.sal_quote.quote_name IS '报价名称';
COMMENT ON COLUMN company.sal_quote.customer_id IS '客户 ID';
COMMENT ON COLUMN company.sal_quote.owner_emp_id IS '销售员工 ID';
COMMENT ON COLUMN company.sal_quote.total_amount IS '总金额';
COMMENT ON COLUMN company.sal_quote.valid_until IS '有效期至';
ALTER TABLE company.sal_quote ADD CONSTRAINT fk_sal_quote_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);
ALTER TABLE company.sal_quote ADD CONSTRAINT fk_sal_quote_owner_emp_id FOREIGN KEY (owner_emp_id) REFERENCES company.hr_employee(id);

-- 报价明细
CREATE TABLE company.sal_quote_item (
    id BIGSERIAL PRIMARY KEY,
    quote_id BIGINT NOT NULL,
    product_id BIGINT,
    qty NUMERIC(12,2),
    unit_price NUMERIC(14,2),
    amount NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.sal_quote_item IS '报价明细';
COMMENT ON COLUMN company.sal_quote_item.id IS '主键';
COMMENT ON COLUMN company.sal_quote_item.quote_id IS '报价单 ID';
COMMENT ON COLUMN company.sal_quote_item.product_id IS '产品 ID';
COMMENT ON COLUMN company.sal_quote_item.qty IS '数量';
COMMENT ON COLUMN company.sal_quote_item.unit_price IS '单价';
COMMENT ON COLUMN company.sal_quote_item.amount IS '金额';
ALTER TABLE company.sal_quote_item ADD CONSTRAINT fk_sal_quote_item_quote_id FOREIGN KEY (quote_id) REFERENCES company.sal_quote(id);
ALTER TABLE company.sal_quote_item ADD CONSTRAINT fk_sal_quote_item_product_id FOREIGN KEY (product_id) REFERENCES company.prd_product(id);

-- 退货单
CREATE TABLE company.sal_return (
    id BIGSERIAL PRIMARY KEY,
    return_code VARCHAR(32) NOT NULL,
    return_name VARCHAR(128) NOT NULL,
    order_id BIGINT,
    return_date DATE,
    reason VARCHAR(256),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_sal_return UNIQUE (return_code)
);
COMMENT ON TABLE company.sal_return IS '退货单';
COMMENT ON COLUMN company.sal_return.id IS '主键';
COMMENT ON COLUMN company.sal_return.return_code IS '退货单号';
COMMENT ON COLUMN company.sal_return.return_name IS '退货说明';
COMMENT ON COLUMN company.sal_return.order_id IS '订单 ID';
COMMENT ON COLUMN company.sal_return.return_date IS '退货日期';
COMMENT ON COLUMN company.sal_return.reason IS '原因';
ALTER TABLE company.sal_return ADD CONSTRAINT fk_sal_return_order_id FOREIGN KEY (order_id) REFERENCES company.sal_sales_order(id);

-- 销售目标
CREATE TABLE company.sal_target (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT,
    dept_id BIGINT,
    year_month VARCHAR(7),
    target_amount NUMERIC(14,2),
    actual_amount NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.sal_target IS '销售目标';
COMMENT ON COLUMN company.sal_target.id IS '主键';
COMMENT ON COLUMN company.sal_target.emp_id IS '销售员工 ID';
COMMENT ON COLUMN company.sal_target.dept_id IS '部门 ID';
COMMENT ON COLUMN company.sal_target.year_month IS '年月';
COMMENT ON COLUMN company.sal_target.target_amount IS '目标金额';
COMMENT ON COLUMN company.sal_target.actual_amount IS '实际金额';
ALTER TABLE company.sal_target ADD CONSTRAINT fk_sal_target_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.sal_target ADD CONSTRAINT fk_sal_target_dept_id FOREIGN KEY (dept_id) REFERENCES company.org_department(id);

-- 物料主数据
CREATE TABLE company.scm_material (
    id BIGSERIAL PRIMARY KEY,
    mat_code VARCHAR(32) NOT NULL,
    mat_name VARCHAR(128) NOT NULL,
    uom VARCHAR(16),
    category VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_scm_material UNIQUE (mat_code)
);
COMMENT ON TABLE company.scm_material IS '物料主数据';
COMMENT ON COLUMN company.scm_material.id IS '主键';
COMMENT ON COLUMN company.scm_material.mat_code IS '物料编码';
COMMENT ON COLUMN company.scm_material.mat_name IS '物料名称';
COMMENT ON COLUMN company.scm_material.uom IS '计量单位';
COMMENT ON COLUMN company.scm_material.category IS '物料类别';

-- 采购申请
CREATE TABLE company.scm_purchase_req (
    id BIGSERIAL PRIMARY KEY,
    req_code VARCHAR(32) NOT NULL,
    req_name VARCHAR(128) NOT NULL,
    applicant_emp_id BIGINT,
    dept_id BIGINT,
    total_amount NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_scm_purchase_req UNIQUE (req_code)
);
COMMENT ON TABLE company.scm_purchase_req IS '采购申请';
COMMENT ON COLUMN company.scm_purchase_req.id IS '主键';
COMMENT ON COLUMN company.scm_purchase_req.req_code IS '申请单号';
COMMENT ON COLUMN company.scm_purchase_req.req_name IS '申请标题';
COMMENT ON COLUMN company.scm_purchase_req.applicant_emp_id IS '申请人员工 ID';
COMMENT ON COLUMN company.scm_purchase_req.dept_id IS '申请部门 ID';
COMMENT ON COLUMN company.scm_purchase_req.total_amount IS '预估金额';
ALTER TABLE company.scm_purchase_req ADD CONSTRAINT fk_scm_purchase_req_applicant_emp_id FOREIGN KEY (applicant_emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.scm_purchase_req ADD CONSTRAINT fk_scm_purchase_req_dept_id FOREIGN KEY (dept_id) REFERENCES company.org_department(id);

-- 采购申请明细
CREATE TABLE company.scm_purchase_req_item (
    id BIGSERIAL PRIMARY KEY,
    req_id BIGINT NOT NULL,
    item_name VARCHAR(128),
    qty NUMERIC(12,2),
    unit_price NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.scm_purchase_req_item IS '采购申请明细';
COMMENT ON COLUMN company.scm_purchase_req_item.id IS '主键';
COMMENT ON COLUMN company.scm_purchase_req_item.req_id IS '申请单 ID';
COMMENT ON COLUMN company.scm_purchase_req_item.item_name IS '物资名称';
COMMENT ON COLUMN company.scm_purchase_req_item.qty IS '数量';
COMMENT ON COLUMN company.scm_purchase_req_item.unit_price IS '预估单价';
ALTER TABLE company.scm_purchase_req_item ADD CONSTRAINT fk_scm_purchase_req_item_req_id FOREIGN KEY (req_id) REFERENCES company.scm_purchase_req(id);

-- 供应商评价
CREATE TABLE company.scm_vendor_eval (
    id BIGSERIAL PRIMARY KEY,
    vendor_id BIGINT NOT NULL,
    year_month VARCHAR(7),
    score NUMERIC(6,2),
    evaluator_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.scm_vendor_eval IS '供应商评价';
COMMENT ON COLUMN company.scm_vendor_eval.id IS '主键';
COMMENT ON COLUMN company.scm_vendor_eval.vendor_id IS '供应商 ID';
COMMENT ON COLUMN company.scm_vendor_eval.year_month IS '年月';
COMMENT ON COLUMN company.scm_vendor_eval.score IS '得分';
COMMENT ON COLUMN company.scm_vendor_eval.evaluator_emp_id IS '评价人员工 ID';
ALTER TABLE company.scm_vendor_eval ADD CONSTRAINT fk_scm_vendor_eval_vendor_id FOREIGN KEY (vendor_id) REFERENCES company.fin_vendor(id);
ALTER TABLE company.scm_vendor_eval ADD CONSTRAINT fk_scm_vendor_eval_evaluator_emp_id FOREIGN KEY (evaluator_emp_id) REFERENCES company.hr_employee(id);

-- 仓库
CREATE TABLE company.scm_warehouse (
    id BIGSERIAL PRIMARY KEY,
    wh_code VARCHAR(32) NOT NULL,
    wh_name VARCHAR(128) NOT NULL,
    office_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_scm_warehouse UNIQUE (wh_code)
);
COMMENT ON TABLE company.scm_warehouse IS '仓库';
COMMENT ON COLUMN company.scm_warehouse.id IS '主键';
COMMENT ON COLUMN company.scm_warehouse.wh_code IS '仓库编码';
COMMENT ON COLUMN company.scm_warehouse.wh_name IS '仓库名称';
COMMENT ON COLUMN company.scm_warehouse.office_id IS '职场 ID';
ALTER TABLE company.scm_warehouse ADD CONSTRAINT fk_scm_warehouse_office_id FOREIGN KEY (office_id) REFERENCES company.org_office(id);

-- 安全审计日志
CREATE TABLE company.sec_audit_log (
    id BIGSERIAL PRIMARY KEY,
    system_id BIGINT,
    emp_id BIGINT,
    action VARCHAR(64),
    acted_at TIMESTAMP,
    ip_addr VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.sec_audit_log IS '安全审计日志';
COMMENT ON COLUMN company.sec_audit_log.id IS '主键';
COMMENT ON COLUMN company.sec_audit_log.system_id IS '系统 ID';
COMMENT ON COLUMN company.sec_audit_log.emp_id IS '操作人员工 ID';
COMMENT ON COLUMN company.sec_audit_log.action IS '动作';
COMMENT ON COLUMN company.sec_audit_log.acted_at IS '操作时间';
COMMENT ON COLUMN company.sec_audit_log.ip_addr IS 'IP';
ALTER TABLE company.sec_audit_log ADD CONSTRAINT fk_sec_audit_log_system_id FOREIGN KEY (system_id) REFERENCES company.itm_system(id);
ALTER TABLE company.sec_audit_log ADD CONSTRAINT fk_sec_audit_log_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 数据分级分类
CREATE TABLE company.sec_data_class (
    id BIGSERIAL PRIMARY KEY,
    class_code VARCHAR(32) NOT NULL,
    class_name VARCHAR(128) NOT NULL,
    level_no INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_sec_data_class UNIQUE (class_code)
);
COMMENT ON TABLE company.sec_data_class IS '数据分级分类';
COMMENT ON COLUMN company.sec_data_class.id IS '主键';
COMMENT ON COLUMN company.sec_data_class.class_code IS '分类编码';
COMMENT ON COLUMN company.sec_data_class.class_name IS '分类名称';
COMMENT ON COLUMN company.sec_data_class.level_no IS '密级序号';

-- 安全策略
CREATE TABLE company.sec_policy (
    id BIGSERIAL PRIMARY KEY,
    pol_code VARCHAR(32) NOT NULL,
    pol_name VARCHAR(128) NOT NULL,
    policy_type VARCHAR(32),
    content TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_sec_policy UNIQUE (pol_code)
);
COMMENT ON TABLE company.sec_policy IS '安全策略';
COMMENT ON COLUMN company.sec_policy.id IS '主键';
COMMENT ON COLUMN company.sec_policy.pol_code IS '策略编码';
COMMENT ON COLUMN company.sec_policy.pol_name IS '策略名称';
COMMENT ON COLUMN company.sec_policy.policy_type IS '策略类型';
COMMENT ON COLUMN company.sec_policy.content IS '策略内容';

-- 漏洞台账
CREATE TABLE company.sec_vulnerability (
    id BIGSERIAL PRIMARY KEY,
    vuln_code VARCHAR(32) NOT NULL,
    vuln_name VARCHAR(128) NOT NULL,
    system_id BIGINT,
    severity VARCHAR(16),
    discovered_at DATE,
    fixed_at DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_sec_vulnerability UNIQUE (vuln_code)
);
COMMENT ON TABLE company.sec_vulnerability IS '漏洞台账';
COMMENT ON COLUMN company.sec_vulnerability.id IS '主键';
COMMENT ON COLUMN company.sec_vulnerability.vuln_code IS '漏洞编号';
COMMENT ON COLUMN company.sec_vulnerability.vuln_name IS '漏洞标题';
COMMENT ON COLUMN company.sec_vulnerability.system_id IS '系统 ID';
COMMENT ON COLUMN company.sec_vulnerability.severity IS '严重级别';
COMMENT ON COLUMN company.sec_vulnerability.discovered_at IS '发现日期';
ALTER TABLE company.sec_vulnerability ADD CONSTRAINT fk_sec_vulnerability_system_id FOREIGN KEY (system_id) REFERENCES company.itm_system(id);

-- 会议室
CREATE TABLE company.adm_meeting_room (
    id BIGSERIAL PRIMARY KEY,
    room_code VARCHAR(32) NOT NULL,
    room_name VARCHAR(128) NOT NULL,
    office_id BIGINT,
    capacity INT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_adm_meeting_room UNIQUE (room_code)
);
COMMENT ON TABLE company.adm_meeting_room IS '会议室';
COMMENT ON COLUMN company.adm_meeting_room.id IS '主键';
COMMENT ON COLUMN company.adm_meeting_room.room_code IS '会议室编码';
COMMENT ON COLUMN company.adm_meeting_room.room_name IS '会议室名称';
COMMENT ON COLUMN company.adm_meeting_room.office_id IS '职场 ID';
COMMENT ON COLUMN company.adm_meeting_room.capacity IS '可容纳人数';
ALTER TABLE company.adm_meeting_room ADD CONSTRAINT fk_adm_meeting_room_office_id FOREIGN KEY (office_id) REFERENCES company.org_office(id);

-- 访客登记
CREATE TABLE company.adm_visitor (
    id BIGSERIAL PRIMARY KEY,
    visitor_name VARCHAR(64),
    host_emp_id BIGINT,
    visit_date DATE,
    purpose VARCHAR(256),
    office_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.adm_visitor IS '访客登记';
COMMENT ON COLUMN company.adm_visitor.id IS '主键';
COMMENT ON COLUMN company.adm_visitor.visitor_name IS '访客姓名';
COMMENT ON COLUMN company.adm_visitor.host_emp_id IS '接待员工 ID';
COMMENT ON COLUMN company.adm_visitor.purpose IS '事由';
COMMENT ON COLUMN company.adm_visitor.office_id IS '职场 ID';
ALTER TABLE company.adm_visitor ADD CONSTRAINT fk_adm_visitor_host_emp_id FOREIGN KEY (host_emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.adm_visitor ADD CONSTRAINT fk_adm_visitor_office_id FOREIGN KEY (office_id) REFERENCES company.org_office(id);

-- 考勤设备
CREATE TABLE company.att_device (
    id BIGSERIAL PRIMARY KEY,
    device_code VARCHAR(32) NOT NULL,
    device_name VARCHAR(128) NOT NULL,
    office_id BIGINT,
    ip_addr VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_att_device UNIQUE (device_code)
);
COMMENT ON TABLE company.att_device IS '考勤设备';
COMMENT ON COLUMN company.att_device.id IS '主键';
COMMENT ON COLUMN company.att_device.device_code IS '设备编码';
COMMENT ON COLUMN company.att_device.device_name IS '设备名称';
COMMENT ON COLUMN company.att_device.office_id IS '职场 ID';
COMMENT ON COLUMN company.att_device.ip_addr IS 'IP';
ALTER TABLE company.att_device ADD CONSTRAINT fk_att_device_office_id FOREIGN KEY (office_id) REFERENCES company.org_office(id);

-- 打卡流水
CREATE TABLE company.att_punch (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    punch_at TIMESTAMP NOT NULL,
    punch_type VARCHAR(16),
    device_no VARCHAR(64),
    office_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.att_punch IS '打卡流水';
COMMENT ON COLUMN company.att_punch.id IS '主键';
COMMENT ON COLUMN company.att_punch.emp_id IS '员工 ID';
COMMENT ON COLUMN company.att_punch.punch_at IS '打卡时间';
COMMENT ON COLUMN company.att_punch.punch_type IS '打卡类型';
COMMENT ON COLUMN company.att_punch.device_no IS '设备号';
COMMENT ON COLUMN company.att_punch.office_id IS '职场 ID';
ALTER TABLE company.att_punch ADD CONSTRAINT fk_att_punch_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.att_punch ADD CONSTRAINT fk_att_punch_office_id FOREIGN KEY (office_id) REFERENCES company.org_office(id);

-- 客户跟进活动
CREATE TABLE company.crm_activity (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT,
    opp_id BIGINT,
    emp_id BIGINT,
    activity_type VARCHAR(32),
    activity_at TIMESTAMP,
    content TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.crm_activity IS '客户跟进活动';
COMMENT ON COLUMN company.crm_activity.id IS '主键';
COMMENT ON COLUMN company.crm_activity.customer_id IS '客户 ID';
COMMENT ON COLUMN company.crm_activity.opp_id IS '商机 ID';
COMMENT ON COLUMN company.crm_activity.emp_id IS '跟进人员工 ID';
COMMENT ON COLUMN company.crm_activity.activity_type IS '活动类型';
COMMENT ON COLUMN company.crm_activity.activity_at IS '活动时间';
COMMENT ON COLUMN company.crm_activity.content IS '内容';
ALTER TABLE company.crm_activity ADD CONSTRAINT fk_crm_activity_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);
ALTER TABLE company.crm_activity ADD CONSTRAINT fk_crm_activity_opp_id FOREIGN KEY (opp_id) REFERENCES company.crm_opportunity(id);
ALTER TABLE company.crm_activity ADD CONSTRAINT fk_crm_activity_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 资产折旧明细
CREATE TABLE company.fin_asset_depr (
    id BIGSERIAL PRIMARY KEY,
    asset_id BIGINT NOT NULL,
    year_month VARCHAR(7),
    depr_amount NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.fin_asset_depr IS '资产折旧明细';
COMMENT ON COLUMN company.fin_asset_depr.id IS '主键';
COMMENT ON COLUMN company.fin_asset_depr.asset_id IS '资产 ID';
COMMENT ON COLUMN company.fin_asset_depr.year_month IS '年月';
COMMENT ON COLUMN company.fin_asset_depr.depr_amount IS '折旧额';
ALTER TABLE company.fin_asset_depr ADD CONSTRAINT fk_fin_asset_depr_asset_id FOREIGN KEY (asset_id) REFERENCES company.fin_fixed_asset(id);

-- 公司银行账户
CREATE TABLE company.fin_bank_account (
    id BIGSERIAL PRIMARY KEY,
    acct_code VARCHAR(32) NOT NULL,
    acct_name VARCHAR(128) NOT NULL,
    bank_name VARCHAR(64),
    account_no VARCHAR(64),
    company_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_bank_account UNIQUE (acct_code)
);
COMMENT ON TABLE company.fin_bank_account IS '公司银行账户';
COMMENT ON COLUMN company.fin_bank_account.id IS '主键';
COMMENT ON COLUMN company.fin_bank_account.acct_code IS '账户编码';
COMMENT ON COLUMN company.fin_bank_account.acct_name IS '账户名称';
COMMENT ON COLUMN company.fin_bank_account.bank_name IS '开户行';
COMMENT ON COLUMN company.fin_bank_account.account_no IS '账号';
COMMENT ON COLUMN company.fin_bank_account.company_id IS '所属公司 ID';
ALTER TABLE company.fin_bank_account ADD CONSTRAINT fk_fin_bank_account_company_id FOREIGN KEY (company_id) REFERENCES company.org_company(id);

-- 银行流水
CREATE TABLE company.fin_bank_txn (
    id BIGSERIAL PRIMARY KEY,
    acct_id BIGINT NOT NULL,
    txn_date DATE,
    direction VARCHAR(8),
    amount NUMERIC(14,2),
    counterpart VARCHAR(128),
    ref_no VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_bank_txn UNIQUE (ref_no)
);
COMMENT ON TABLE company.fin_bank_txn IS '银行流水';
COMMENT ON COLUMN company.fin_bank_txn.id IS '主键';
COMMENT ON COLUMN company.fin_bank_txn.acct_id IS '账户 ID';
COMMENT ON COLUMN company.fin_bank_txn.txn_date IS '交易日期';
COMMENT ON COLUMN company.fin_bank_txn.direction IS '收支方向';
COMMENT ON COLUMN company.fin_bank_txn.amount IS '金额';
COMMENT ON COLUMN company.fin_bank_txn.counterpart IS '对方户名';
COMMENT ON COLUMN company.fin_bank_txn.ref_no IS '银行参考号';
ALTER TABLE company.fin_bank_txn ADD CONSTRAINT fk_fin_bank_txn_acct_id FOREIGN KEY (acct_id) REFERENCES company.fin_bank_account(id);

-- 预算明细行
CREATE TABLE company.fin_budget_line (
    id BIGSERIAL PRIMARY KEY,
    budget_id BIGINT NOT NULL,
    subject_code VARCHAR(32),
    subject_name VARCHAR(64),
    amount NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_budget_line UNIQUE (subject_code)
);
COMMENT ON TABLE company.fin_budget_line IS '预算明细行';
COMMENT ON COLUMN company.fin_budget_line.id IS '主键';
COMMENT ON COLUMN company.fin_budget_line.budget_id IS '年度预算 ID';
COMMENT ON COLUMN company.fin_budget_line.subject_code IS '科目编码';
COMMENT ON COLUMN company.fin_budget_line.subject_name IS '科目名称';
COMMENT ON COLUMN company.fin_budget_line.amount IS '金额';
ALTER TABLE company.fin_budget_line ADD CONSTRAINT fk_fin_budget_line_budget_id FOREIGN KEY (budget_id) REFERENCES company.fin_budget_year(id);

-- 进销项发票
CREATE TABLE company.fin_invoice (
    id BIGSERIAL PRIMARY KEY,
    invoice_no VARCHAR(64) NOT NULL,
    invoice_type VARCHAR(32),
    vendor_id BIGINT,
    customer_id BIGINT,
    amount NUMERIC(14,2),
    tax_amount NUMERIC(14,2),
    invoice_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_invoice UNIQUE (invoice_no)
);
COMMENT ON TABLE company.fin_invoice IS '进销项发票';
COMMENT ON COLUMN company.fin_invoice.id IS '主键';
COMMENT ON COLUMN company.fin_invoice.invoice_no IS '发票号';
COMMENT ON COLUMN company.fin_invoice.invoice_type IS '发票类型';
COMMENT ON COLUMN company.fin_invoice.vendor_id IS '供应商 ID';
COMMENT ON COLUMN company.fin_invoice.customer_id IS '客户 ID';
COMMENT ON COLUMN company.fin_invoice.amount IS '含税金额';
COMMENT ON COLUMN company.fin_invoice.tax_amount IS '税额';
COMMENT ON COLUMN company.fin_invoice.invoice_date IS '开票日期';
ALTER TABLE company.fin_invoice ADD CONSTRAINT fk_fin_invoice_vendor_id FOREIGN KEY (vendor_id) REFERENCES company.fin_vendor(id);
ALTER TABLE company.fin_invoice ADD CONSTRAINT fk_fin_invoice_customer_id FOREIGN KEY (customer_id) REFERENCES company.crm_customer(id);

-- 付款单
CREATE TABLE company.fin_payment (
    id BIGSERIAL PRIMARY KEY,
    payment_no VARCHAR(64) NOT NULL,
    vendor_id BIGINT,
    amount NUMERIC(14,2),
    pay_date DATE,
    method VARCHAR(32),
    applicant_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_payment UNIQUE (payment_no)
);
COMMENT ON TABLE company.fin_payment IS '付款单';
COMMENT ON COLUMN company.fin_payment.id IS '主键';
COMMENT ON COLUMN company.fin_payment.payment_no IS '付款单号';
COMMENT ON COLUMN company.fin_payment.vendor_id IS '供应商 ID';
COMMENT ON COLUMN company.fin_payment.amount IS '付款金额';
COMMENT ON COLUMN company.fin_payment.pay_date IS '付款日期';
COMMENT ON COLUMN company.fin_payment.method IS '支付方式';
COMMENT ON COLUMN company.fin_payment.applicant_emp_id IS '申请人员工 ID';
ALTER TABLE company.fin_payment ADD CONSTRAINT fk_fin_payment_vendor_id FOREIGN KEY (vendor_id) REFERENCES company.fin_vendor(id);
ALTER TABLE company.fin_payment ADD CONSTRAINT fk_fin_payment_applicant_emp_id FOREIGN KEY (applicant_emp_id) REFERENCES company.hr_employee(id);

-- 劳动合同
CREATE TABLE company.hr_contract (
    id BIGSERIAL PRIMARY KEY,
    emp_id BIGINT NOT NULL,
    contract_no VARCHAR(64),
    contract_type VARCHAR(32),
    start_date DATE,
    end_date DATE,
    sign_company_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_contract IS '劳动合同';
COMMENT ON COLUMN company.hr_contract.id IS '主键';
COMMENT ON COLUMN company.hr_contract.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_contract.contract_no IS '合同编号';
COMMENT ON COLUMN company.hr_contract.contract_type IS '合同类型';
COMMENT ON COLUMN company.hr_contract.start_date IS '开始日期';
COMMENT ON COLUMN company.hr_contract.end_date IS '结束日期';
COMMENT ON COLUMN company.hr_contract.sign_company_id IS '签约公司 ID';
ALTER TABLE company.hr_contract ADD CONSTRAINT fk_hr_contract_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.hr_contract ADD CONSTRAINT fk_hr_contract_sign_company_id FOREIGN KEY (sign_company_id) REFERENCES company.org_company(id);

-- 面试记录
CREATE TABLE company.hr_interview (
    id BIGSERIAL PRIMARY KEY,
    candidate_id BIGINT NOT NULL,
    req_id BIGINT,
    interviewer_emp_id BIGINT,
    interview_at TIMESTAMP,
    result VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_interview IS '面试记录';
COMMENT ON COLUMN company.hr_interview.id IS '主键';
COMMENT ON COLUMN company.hr_interview.candidate_id IS '候选人 ID';
COMMENT ON COLUMN company.hr_interview.req_id IS '招聘需求 ID';
COMMENT ON COLUMN company.hr_interview.interviewer_emp_id IS '面试官员工 ID';
COMMENT ON COLUMN company.hr_interview.interview_at IS '面试时间';
COMMENT ON COLUMN company.hr_interview.result IS '结果';
ALTER TABLE company.hr_interview ADD CONSTRAINT fk_hr_interview_candidate_id FOREIGN KEY (candidate_id) REFERENCES company.hr_candidate(id);
ALTER TABLE company.hr_interview ADD CONSTRAINT fk_hr_interview_req_id FOREIGN KEY (req_id) REFERENCES company.hr_recruit_req(id);
ALTER TABLE company.hr_interview ADD CONSTRAINT fk_hr_interview_interviewer_emp_id FOREIGN KEY (interviewer_emp_id) REFERENCES company.hr_employee(id);

-- 录用 Offer
CREATE TABLE company.hr_offer (
    id BIGSERIAL PRIMARY KEY,
    candidate_id BIGINT NOT NULL,
    req_id BIGINT,
    offer_amount NUMERIC(14,2),
    accept_status VARCHAR(32),
    join_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_offer IS '录用 Offer';
COMMENT ON COLUMN company.hr_offer.id IS '主键';
COMMENT ON COLUMN company.hr_offer.candidate_id IS '候选人 ID';
COMMENT ON COLUMN company.hr_offer.req_id IS '招聘需求 ID';
COMMENT ON COLUMN company.hr_offer.offer_amount IS 'offer 年薪/月薪金额';
COMMENT ON COLUMN company.hr_offer.accept_status IS '接受状态';
COMMENT ON COLUMN company.hr_offer.join_date IS '预计入职日';
ALTER TABLE company.hr_offer ADD CONSTRAINT fk_hr_offer_candidate_id FOREIGN KEY (candidate_id) REFERENCES company.hr_candidate(id);
ALTER TABLE company.hr_offer ADD CONSTRAINT fk_hr_offer_req_id FOREIGN KEY (req_id) REFERENCES company.hr_recruit_req(id);

-- 培训报名
CREATE TABLE company.hr_training_enroll (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL,
    emp_id BIGINT NOT NULL,
    attend_status VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.hr_training_enroll IS '培训报名';
COMMENT ON COLUMN company.hr_training_enroll.id IS '主键';
COMMENT ON COLUMN company.hr_training_enroll.session_id IS '场次 ID';
COMMENT ON COLUMN company.hr_training_enroll.emp_id IS '员工 ID';
COMMENT ON COLUMN company.hr_training_enroll.attend_status IS '出勤状态';
ALTER TABLE company.hr_training_enroll ADD CONSTRAINT fk_hr_training_enroll_session_id FOREIGN KEY (session_id) REFERENCES company.hr_training_session(id);
ALTER TABLE company.hr_training_enroll ADD CONSTRAINT fk_hr_training_enroll_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 权限申请
CREATE TABLE company.itm_access_request (
    id BIGSERIAL PRIMARY KEY,
    system_id BIGINT NOT NULL,
    emp_id BIGINT NOT NULL,
    role_name VARCHAR(64),
    reason VARCHAR(256),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.itm_access_request IS '权限申请';
COMMENT ON COLUMN company.itm_access_request.id IS '主键';
COMMENT ON COLUMN company.itm_access_request.system_id IS '系统 ID';
COMMENT ON COLUMN company.itm_access_request.emp_id IS '申请人员工 ID';
COMMENT ON COLUMN company.itm_access_request.role_name IS '申请角色';
COMMENT ON COLUMN company.itm_access_request.reason IS '事由';
ALTER TABLE company.itm_access_request ADD CONSTRAINT fk_itm_access_request_system_id FOREIGN KEY (system_id) REFERENCES company.itm_system(id);
ALTER TABLE company.itm_access_request ADD CONSTRAINT fk_itm_access_request_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 系统账号
CREATE TABLE company.itm_account (
    id BIGSERIAL PRIMARY KEY,
    system_id BIGINT NOT NULL,
    emp_id BIGINT,
    login_name VARCHAR(64),
    role_name VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.itm_account IS '系统账号';
COMMENT ON COLUMN company.itm_account.id IS '主键';
COMMENT ON COLUMN company.itm_account.system_id IS '系统 ID';
COMMENT ON COLUMN company.itm_account.emp_id IS '员工 ID';
COMMENT ON COLUMN company.itm_account.login_name IS '登录名';
COMMENT ON COLUMN company.itm_account.role_name IS '角色';
ALTER TABLE company.itm_account ADD CONSTRAINT fk_itm_account_system_id FOREIGN KEY (system_id) REFERENCES company.itm_system(id);
ALTER TABLE company.itm_account ADD CONSTRAINT fk_itm_account_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- IT 资产
CREATE TABLE company.itm_asset (
    id BIGSERIAL PRIMARY KEY,
    asset_code VARCHAR(32) NOT NULL,
    asset_name VARCHAR(128) NOT NULL,
    asset_type VARCHAR(32),
    sn VARCHAR(64),
    assignee_emp_id BIGINT,
    office_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_itm_asset UNIQUE (asset_code)
);
COMMENT ON TABLE company.itm_asset IS 'IT 资产';
COMMENT ON COLUMN company.itm_asset.id IS '主键';
COMMENT ON COLUMN company.itm_asset.asset_code IS '资产编码';
COMMENT ON COLUMN company.itm_asset.asset_name IS '资产名称';
COMMENT ON COLUMN company.itm_asset.asset_type IS '资产类型';
COMMENT ON COLUMN company.itm_asset.sn IS '序列号';
COMMENT ON COLUMN company.itm_asset.assignee_emp_id IS '领用人员工 ID';
COMMENT ON COLUMN company.itm_asset.office_id IS '职场 ID';
ALTER TABLE company.itm_asset ADD CONSTRAINT fk_itm_asset_assignee_emp_id FOREIGN KEY (assignee_emp_id) REFERENCES company.hr_employee(id);
ALTER TABLE company.itm_asset ADD CONSTRAINT fk_itm_asset_office_id FOREIGN KEY (office_id) REFERENCES company.org_office(id);

-- IT 资产领用归还
CREATE TABLE company.itm_asset_assign (
    id BIGSERIAL PRIMARY KEY,
    asset_id BIGINT NOT NULL,
    emp_id BIGINT NOT NULL,
    assign_date DATE,
    return_date DATE,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.itm_asset_assign IS 'IT 资产领用归还';
COMMENT ON COLUMN company.itm_asset_assign.id IS '主键';
COMMENT ON COLUMN company.itm_asset_assign.asset_id IS '资产 ID';
COMMENT ON COLUMN company.itm_asset_assign.emp_id IS '员工 ID';
COMMENT ON COLUMN company.itm_asset_assign.return_date IS '归还日期';
ALTER TABLE company.itm_asset_assign ADD CONSTRAINT fk_itm_asset_assign_asset_id FOREIGN KEY (asset_id) REFERENCES company.itm_asset(id);
ALTER TABLE company.itm_asset_assign ADD CONSTRAINT fk_itm_asset_assign_emp_id FOREIGN KEY (emp_id) REFERENCES company.hr_employee(id);

-- 变更单
CREATE TABLE company.itm_change (
    id BIGSERIAL PRIMARY KEY,
    chg_code VARCHAR(32) NOT NULL,
    chg_name VARCHAR(128) NOT NULL,
    system_id BIGINT,
    planned_at TIMESTAMP,
    risk_level VARCHAR(16),
    applicant_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_itm_change UNIQUE (chg_code)
);
COMMENT ON TABLE company.itm_change IS '变更单';
COMMENT ON COLUMN company.itm_change.id IS '主键';
COMMENT ON COLUMN company.itm_change.chg_code IS '变更单号';
COMMENT ON COLUMN company.itm_change.chg_name IS '变更标题';
COMMENT ON COLUMN company.itm_change.system_id IS '系统 ID';
COMMENT ON COLUMN company.itm_change.planned_at IS '计划时间';
COMMENT ON COLUMN company.itm_change.risk_level IS '风险等级';
COMMENT ON COLUMN company.itm_change.applicant_emp_id IS '申请人员工 ID';
ALTER TABLE company.itm_change ADD CONSTRAINT fk_itm_change_system_id FOREIGN KEY (system_id) REFERENCES company.itm_system(id);
ALTER TABLE company.itm_change ADD CONSTRAINT fk_itm_change_applicant_emp_id FOREIGN KEY (applicant_emp_id) REFERENCES company.hr_employee(id);

-- 发布部署记录
CREATE TABLE company.itm_deploy (
    id BIGSERIAL PRIMARY KEY,
    system_id BIGINT NOT NULL,
    version_no VARCHAR(32),
    deploy_at TIMESTAMP,
    operator_emp_id BIGINT,
    result VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_itm_deploy UNIQUE (version_no)
);
COMMENT ON TABLE company.itm_deploy IS '发布部署记录';
COMMENT ON COLUMN company.itm_deploy.id IS '主键';
COMMENT ON COLUMN company.itm_deploy.system_id IS '系统 ID';
COMMENT ON COLUMN company.itm_deploy.version_no IS '版本号';
COMMENT ON COLUMN company.itm_deploy.operator_emp_id IS '操作人员工 ID';
COMMENT ON COLUMN company.itm_deploy.result IS '结果';
ALTER TABLE company.itm_deploy ADD CONSTRAINT fk_itm_deploy_system_id FOREIGN KEY (system_id) REFERENCES company.itm_system(id);
ALTER TABLE company.itm_deploy ADD CONSTRAINT fk_itm_deploy_operator_emp_id FOREIGN KEY (operator_emp_id) REFERENCES company.hr_employee(id);

-- 生产故障
CREATE TABLE company.itm_incident (
    id BIGSERIAL PRIMARY KEY,
    inc_code VARCHAR(32) NOT NULL,
    inc_name VARCHAR(128) NOT NULL,
    system_id BIGINT,
    severity VARCHAR(16),
    started_at TIMESTAMP,
    resolved_at TIMESTAMP,
    commander_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_itm_incident UNIQUE (inc_code)
);
COMMENT ON TABLE company.itm_incident IS '生产故障';
COMMENT ON COLUMN company.itm_incident.id IS '主键';
COMMENT ON COLUMN company.itm_incident.inc_code IS '故障单号';
COMMENT ON COLUMN company.itm_incident.inc_name IS '故障标题';
COMMENT ON COLUMN company.itm_incident.system_id IS '系统 ID';
COMMENT ON COLUMN company.itm_incident.severity IS '严重级别';
COMMENT ON COLUMN company.itm_incident.started_at IS '开始时间';
COMMENT ON COLUMN company.itm_incident.commander_emp_id IS '指挥人员工 ID';
ALTER TABLE company.itm_incident ADD CONSTRAINT fk_itm_incident_system_id FOREIGN KEY (system_id) REFERENCES company.itm_system(id);
ALTER TABLE company.itm_incident ADD CONSTRAINT fk_itm_incident_commander_emp_id FOREIGN KEY (commander_emp_id) REFERENCES company.hr_employee(id);

-- 测试用例
CREATE TABLE company.qa_test_case (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL,
    case_code VARCHAR(32),
    case_name VARCHAR(256),
    priority VARCHAR(16),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_qa_test_case UNIQUE (case_code)
);
COMMENT ON TABLE company.qa_test_case IS '测试用例';
COMMENT ON COLUMN company.qa_test_case.id IS '主键';
COMMENT ON COLUMN company.qa_test_case.plan_id IS '计划 ID';
COMMENT ON COLUMN company.qa_test_case.case_code IS '用例编码';
COMMENT ON COLUMN company.qa_test_case.case_name IS '用例名称';
COMMENT ON COLUMN company.qa_test_case.priority IS '优先级';
ALTER TABLE company.qa_test_case ADD CONSTRAINT fk_qa_test_case_plan_id FOREIGN KEY (plan_id) REFERENCES company.qa_test_plan(id);

-- 库存台账
CREATE TABLE company.scm_inventory (
    id BIGSERIAL PRIMARY KEY,
    warehouse_id BIGINT NOT NULL,
    sku_code VARCHAR(64),
    sku_name VARCHAR(128),
    qty_on_hand NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_scm_inventory UNIQUE (sku_code)
);
COMMENT ON TABLE company.scm_inventory IS '库存台账';
COMMENT ON COLUMN company.scm_inventory.id IS '主键';
COMMENT ON COLUMN company.scm_inventory.warehouse_id IS '仓库 ID';
COMMENT ON COLUMN company.scm_inventory.sku_code IS 'SKU 编码';
COMMENT ON COLUMN company.scm_inventory.sku_name IS 'SKU 名称';
COMMENT ON COLUMN company.scm_inventory.qty_on_hand IS '在库数量';
ALTER TABLE company.scm_inventory ADD CONSTRAINT fk_scm_inventory_warehouse_id FOREIGN KEY (warehouse_id) REFERENCES company.scm_warehouse(id);

-- 库存流水
CREATE TABLE company.scm_inventory_txn (
    id BIGSERIAL PRIMARY KEY,
    warehouse_id BIGINT NOT NULL,
    sku_code VARCHAR(64),
    txn_type VARCHAR(16),
    qty NUMERIC(14,2),
    txn_date DATE,
    ref_no VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_scm_inventory_txn UNIQUE (sku_code)
);
COMMENT ON TABLE company.scm_inventory_txn IS '库存流水';
COMMENT ON COLUMN company.scm_inventory_txn.id IS '主键';
COMMENT ON COLUMN company.scm_inventory_txn.warehouse_id IS '仓库 ID';
COMMENT ON COLUMN company.scm_inventory_txn.sku_code IS 'SKU';
COMMENT ON COLUMN company.scm_inventory_txn.txn_type IS '出入库类型';
COMMENT ON COLUMN company.scm_inventory_txn.qty IS '数量';
COMMENT ON COLUMN company.scm_inventory_txn.txn_date IS '日期';
COMMENT ON COLUMN company.scm_inventory_txn.ref_no IS '来源单号';
ALTER TABLE company.scm_inventory_txn ADD CONSTRAINT fk_scm_inventory_txn_warehouse_id FOREIGN KEY (warehouse_id) REFERENCES company.scm_warehouse(id);

-- 采购订单
CREATE TABLE company.scm_purchase_order (
    id BIGSERIAL PRIMARY KEY,
    po_code VARCHAR(32) NOT NULL,
    po_name VARCHAR(128) NOT NULL,
    vendor_id BIGINT,
    req_id BIGINT,
    total_amount NUMERIC(14,2),
    buyer_emp_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_scm_purchase_order UNIQUE (po_code)
);
COMMENT ON TABLE company.scm_purchase_order IS '采购订单';
COMMENT ON COLUMN company.scm_purchase_order.id IS '主键';
COMMENT ON COLUMN company.scm_purchase_order.po_code IS '采购订单号';
COMMENT ON COLUMN company.scm_purchase_order.po_name IS '订单说明';
COMMENT ON COLUMN company.scm_purchase_order.vendor_id IS '供应商 ID';
COMMENT ON COLUMN company.scm_purchase_order.req_id IS '来源申请 ID';
COMMENT ON COLUMN company.scm_purchase_order.total_amount IS '订单金额';
COMMENT ON COLUMN company.scm_purchase_order.buyer_emp_id IS '采购员员工 ID';
ALTER TABLE company.scm_purchase_order ADD CONSTRAINT fk_scm_purchase_order_vendor_id FOREIGN KEY (vendor_id) REFERENCES company.fin_vendor(id);
ALTER TABLE company.scm_purchase_order ADD CONSTRAINT fk_scm_purchase_order_req_id FOREIGN KEY (req_id) REFERENCES company.scm_purchase_req(id);
ALTER TABLE company.scm_purchase_order ADD CONSTRAINT fk_scm_purchase_order_buyer_emp_id FOREIGN KEY (buyer_emp_id) REFERENCES company.hr_employee(id);

-- 采购订单明细
CREATE TABLE company.scm_purchase_order_item (
    id BIGSERIAL PRIMARY KEY,
    po_id BIGINT NOT NULL,
    item_name VARCHAR(128),
    qty NUMERIC(12,2),
    unit_price NUMERIC(14,2),
    amount NUMERIC(14,2),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.scm_purchase_order_item IS '采购订单明细';
COMMENT ON COLUMN company.scm_purchase_order_item.id IS '主键';
COMMENT ON COLUMN company.scm_purchase_order_item.po_id IS '采购订单 ID';
COMMENT ON COLUMN company.scm_purchase_order_item.item_name IS '物资名称';
COMMENT ON COLUMN company.scm_purchase_order_item.qty IS '数量';
COMMENT ON COLUMN company.scm_purchase_order_item.unit_price IS '单价';
COMMENT ON COLUMN company.scm_purchase_order_item.amount IS '金额';
ALTER TABLE company.scm_purchase_order_item ADD CONSTRAINT fk_scm_purchase_order_item_po_id FOREIGN KEY (po_id) REFERENCES company.scm_purchase_order(id);

-- 采购入库单
CREATE TABLE company.scm_receipt (
    id BIGSERIAL PRIMARY KEY,
    grn_code VARCHAR(32) NOT NULL,
    grn_name VARCHAR(128) NOT NULL,
    po_id BIGINT,
    receipt_date DATE,
    warehouse_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_scm_receipt UNIQUE (grn_code)
);
COMMENT ON TABLE company.scm_receipt IS '采购入库单';
COMMENT ON COLUMN company.scm_receipt.id IS '主键';
COMMENT ON COLUMN company.scm_receipt.grn_code IS '入库单号';
COMMENT ON COLUMN company.scm_receipt.grn_name IS '说明';
COMMENT ON COLUMN company.scm_receipt.po_id IS '采购订单 ID';
COMMENT ON COLUMN company.scm_receipt.receipt_date IS '入库日期';
COMMENT ON COLUMN company.scm_receipt.warehouse_id IS '仓库 ID';
ALTER TABLE company.scm_receipt ADD CONSTRAINT fk_scm_receipt_po_id FOREIGN KEY (po_id) REFERENCES company.scm_purchase_order(id);
ALTER TABLE company.scm_receipt ADD CONSTRAINT fk_scm_receipt_warehouse_id FOREIGN KEY (warehouse_id) REFERENCES company.scm_warehouse(id);

-- 会议室预订
CREATE TABLE company.adm_meeting_booking (
    id BIGSERIAL PRIMARY KEY,
    room_id BIGINT NOT NULL,
    organizer_emp_id BIGINT,
    start_at TIMESTAMP,
    end_at TIMESTAMP,
    title VARCHAR(256),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    remark VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE company.adm_meeting_booking IS '会议室预订';
COMMENT ON COLUMN company.adm_meeting_booking.id IS '主键';
COMMENT ON COLUMN company.adm_meeting_booking.room_id IS '会议室 ID';
COMMENT ON COLUMN company.adm_meeting_booking.organizer_emp_id IS '组织者员工 ID';
COMMENT ON COLUMN company.adm_meeting_booking.end_at IS '结束时间';
COMMENT ON COLUMN company.adm_meeting_booking.title IS '会议主题';
ALTER TABLE company.adm_meeting_booking ADD CONSTRAINT fk_adm_meeting_booking_room_id FOREIGN KEY (room_id) REFERENCES company.adm_meeting_room(id);
ALTER TABLE company.adm_meeting_booking ADD CONSTRAINT fk_adm_meeting_booking_organizer_emp_id FOREIGN KEY (organizer_emp_id) REFERENCES company.hr_employee(id);

