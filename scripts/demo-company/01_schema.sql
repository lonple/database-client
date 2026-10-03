-- IT 公司问数演示库：schema company（按业务域建表）
-- 目标库：本地 PostgreSQL / 库 postgres
-- 可重复执行：先 DROP 再建

DROP SCHEMA IF EXISTS company CASCADE;
CREATE SCHEMA company;

COMMENT ON SCHEMA company IS '智能问数测评库 company_eval_v2：模拟 IT 公司数据（故意含空值与脏数据；完整注释见仓库 metadata MD）';

-- ========== 组织人事 ==========
CREATE TABLE company.org_department (
    id              BIGSERIAL PRIMARY KEY,
    dept_code       VARCHAR(32)  NOT NULL,
    dept_name       VARCHAR(64)  NOT NULL,
    parent_id       BIGINT       REFERENCES company.org_department(id),
    manager_emp_id  BIGINT,                 -- 稍后回填，允许空
    status          SMALLINT     NOT NULL DEFAULT 1,
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_org_department_code UNIQUE (dept_code)
);

CREATE TABLE company.hr_job_level (
    id          BIGSERIAL PRIMARY KEY,
    level_code  VARCHAR(16)  NOT NULL,
    level_name  VARCHAR(32)  NOT NULL,
    rank_no     INT          NOT NULL,
    CONSTRAINT uk_hr_job_level_code UNIQUE (level_code)
);

CREATE TABLE company.hr_employee (
    id                  BIGSERIAL PRIMARY KEY,
    emp_no              VARCHAR(32)  NOT NULL,
    name                VARCHAR(64)  NOT NULL,
    gender              CHAR(1),                    -- 允许空
    dept_id             BIGINT       REFERENCES company.org_department(id),
    job_level_id        BIGINT       REFERENCES company.hr_job_level(id),
    title               VARCHAR(64),
    hire_date           DATE         NOT NULL,
    leave_date          DATE,
    employment_status   VARCHAR(16)  NOT NULL DEFAULT 'active',
    email               VARCHAR(128),
    phone               VARCHAR(32),
    base_city           VARCHAR(32),
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_hr_employee_emp_no UNIQUE (emp_no)
);

CREATE INDEX idx_hr_employee_dept ON company.hr_employee(dept_id);
CREATE INDEX idx_hr_employee_status ON company.hr_employee(employment_status);
CREATE INDEX idx_hr_employee_hire ON company.hr_employee(hire_date);

-- ========== 考勤工时 ==========
CREATE TABLE company.att_leave_type (
    id                 BIGSERIAL PRIMARY KEY,
    type_code          VARCHAR(32)  NOT NULL,
    type_name          VARCHAR(64)  NOT NULL,
    is_paid            BOOLEAN      NOT NULL DEFAULT TRUE,
    deduct_attendance  BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT uk_att_leave_type_code UNIQUE (type_code)
);

CREATE TABLE company.att_leave (
    id              BIGSERIAL PRIMARY KEY,
    emp_id          BIGINT       NOT NULL REFERENCES company.hr_employee(id),
    leave_type_id   BIGINT       REFERENCES company.att_leave_type(id), -- 允许空：脏数据
    start_at        TIMESTAMP    NOT NULL,
    end_at          TIMESTAMP    NOT NULL,
    leave_days      NUMERIC(6,2),
    reason          VARCHAR(256),
    status          VARCHAR(16)  NOT NULL DEFAULT 'approved',
    approved_by     BIGINT       REFERENCES company.hr_employee(id),
    approved_at     TIMESTAMP,
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_att_leave_emp ON company.att_leave(emp_id);
CREATE INDEX idx_att_leave_start ON company.att_leave(start_at);

CREATE TABLE company.att_overtime (
    id               BIGSERIAL PRIMARY KEY,
    emp_id           BIGINT       NOT NULL REFERENCES company.hr_employee(id),
    project_id       BIGINT,                    -- 可空；FK 在项目表创建后加可选
    overtime_date    DATE         NOT NULL,
    start_at         TIMESTAMP,
    end_at           TIMESTAMP,
    hours            NUMERIC(6,2),
    ot_type          VARCHAR(16),               -- workday/weekend/holiday
    compensate_type  VARCHAR(16),               -- pay/leave
    status           VARCHAR(16)  NOT NULL DEFAULT 'approved',
    created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_att_overtime_emp ON company.att_overtime(emp_id);
CREATE INDEX idx_att_overtime_date ON company.att_overtime(overtime_date);

CREATE TABLE company.att_daily_record (
    id                  BIGSERIAL PRIMARY KEY,
    emp_id              BIGINT       NOT NULL REFERENCES company.hr_employee(id),
    work_date           DATE         NOT NULL,
    check_in_at         TIMESTAMP,
    check_out_at        TIMESTAMP,
    work_hours          NUMERIC(6,2),
    late_minutes        INT,
    early_leave_minutes INT,
    attendance_status   VARCHAR(16),            -- normal/late/early/absent/leave/holiday
    source              VARCHAR(16),            -- device/manual
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_att_daily_emp_date UNIQUE (emp_id, work_date)
);

CREATE INDEX idx_att_daily_date ON company.att_daily_record(work_date);
CREATE INDEX idx_att_daily_status ON company.att_daily_record(attendance_status);

CREATE TABLE company.att_timesheet (
    id          BIGSERIAL PRIMARY KEY,
    emp_id      BIGINT       NOT NULL REFERENCES company.hr_employee(id),
    project_id  BIGINT,                         -- 允许空脏数据
    work_date   DATE         NOT NULL,
    hours       NUMERIC(6,2) NOT NULL,
    work_type   VARCHAR(16),                    -- develop/test/implement/support/manage
    remark      VARCHAR(256),
    status      VARCHAR(16)  NOT NULL DEFAULT 'approved',
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_att_timesheet_emp ON company.att_timesheet(emp_id);
CREATE INDEX idx_att_timesheet_project ON company.att_timesheet(project_id);
CREATE INDEX idx_att_timesheet_date ON company.att_timesheet(work_date);

-- ========== 财务 ==========
CREATE TABLE company.fin_salary_period (
    id           BIGSERIAL PRIMARY KEY,
    period_code  VARCHAR(16)  NOT NULL,
    year_month   DATE         NOT NULL,
    pay_date     DATE,
    status       VARCHAR(16)  NOT NULL DEFAULT 'closed',
    CONSTRAINT uk_fin_salary_period_code UNIQUE (period_code)
);

CREATE TABLE company.fin_salary_slip (
    id                         BIGSERIAL PRIMARY KEY,
    period_id                  BIGINT       NOT NULL REFERENCES company.fin_salary_period(id),
    emp_id                     BIGINT       NOT NULL REFERENCES company.hr_employee(id),
    dept_id                    BIGINT       REFERENCES company.org_department(id),
    base_salary                NUMERIC(12,2),
    allowance                  NUMERIC(12,2),
    overtime_pay               NUMERIC(12,2),
    bonus                      NUMERIC(12,2),
    social_security_personal   NUMERIC(12,2),
    housing_fund_personal      NUMERIC(12,2),
    tax                        NUMERIC(12,2),
    other_deduction            NUMERIC(12,2),
    net_pay                    NUMERIC(12,2),
    currency                   VARCHAR(8)   DEFAULT 'CNY',
    created_at                 TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_salary_slip UNIQUE (period_id, emp_id)
);

CREATE INDEX idx_fin_salary_slip_emp ON company.fin_salary_slip(emp_id);

CREATE TABLE company.fin_reimburse (
    id           BIGSERIAL PRIMARY KEY,
    claim_no     VARCHAR(32)  NOT NULL,
    emp_id       BIGINT       NOT NULL REFERENCES company.hr_employee(id),
    dept_id      BIGINT       REFERENCES company.org_department(id),
    project_id   BIGINT,
    claim_date   DATE         NOT NULL,
    title        VARCHAR(128),
    total_amount NUMERIC(12,2),
    status       VARCHAR(16)  NOT NULL DEFAULT 'approved',
    paid_at      TIMESTAMP,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_reimburse_claim_no UNIQUE (claim_no)
);

CREATE INDEX idx_fin_reimburse_emp ON company.fin_reimburse(emp_id);
CREATE INDEX idx_fin_reimburse_date ON company.fin_reimburse(claim_date);

CREATE TABLE company.fin_reimburse_item (
    id          BIGSERIAL PRIMARY KEY,
    claim_id    BIGINT       NOT NULL REFERENCES company.fin_reimburse(id),
    category    VARCHAR(32),
    amount      NUMERIC(12,2),
    occur_date  DATE,
    invoice_no  VARCHAR(64),
    remark      VARCHAR(256)
);

CREATE INDEX idx_fin_reimburse_item_claim ON company.fin_reimburse_item(claim_id);

CREATE TABLE company.fin_activity_budget (
    id             BIGSERIAL PRIMARY KEY,
    activity_code  VARCHAR(32)  NOT NULL,
    activity_name  VARCHAR(128) NOT NULL,
    dept_id        BIGINT       REFERENCES company.org_department(id),
    owner_emp_id   BIGINT       REFERENCES company.hr_employee(id),
    year           INT          NOT NULL,
    budget_amount  NUMERIC(12,2),
    status         VARCHAR(16)  NOT NULL DEFAULT 'ongoing',
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_fin_activity_budget_code UNIQUE (activity_code)
);

CREATE TABLE company.fin_activity_expense (
    id            BIGSERIAL PRIMARY KEY,
    budget_id     BIGINT       NOT NULL REFERENCES company.fin_activity_budget(id),
    expense_date  DATE         NOT NULL,
    category      VARCHAR(32),
    amount        NUMERIC(12,2),
    payee         VARCHAR(128),
    remark        VARCHAR(256),
    status        VARCHAR(16)  NOT NULL DEFAULT 'paid',
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fin_activity_expense_budget ON company.fin_activity_expense(budget_id);

-- ========== 客户 / 产品 / 销售 / 项目 ==========
CREATE TABLE company.crm_customer (
    id              BIGSERIAL PRIMARY KEY,
    customer_code   VARCHAR(32)  NOT NULL,
    customer_name   VARCHAR(128) NOT NULL,
    industry        VARCHAR(64),
    region          VARCHAR(32),
    customer_level  VARCHAR(8),
    owner_emp_id    BIGINT       REFERENCES company.hr_employee(id),
    status          VARCHAR(16)  NOT NULL DEFAULT 'active',
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_crm_customer_code UNIQUE (customer_code)
);

CREATE TABLE company.prd_product (
    id             BIGSERIAL PRIMARY KEY,
    product_code   VARCHAR(32)  NOT NULL,
    product_name   VARCHAR(128) NOT NULL,
    product_line   VARCHAR(64),
    pricing_model  VARCHAR(32),
    list_price     NUMERIC(12,2),
    unit           VARCHAR(16),
    status         VARCHAR(16)  NOT NULL DEFAULT 'on_sale',
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_prd_product_code UNIQUE (product_code)
);

CREATE TABLE company.prd_product_cost (
    id          BIGSERIAL PRIMARY KEY,
    product_id  BIGINT       NOT NULL REFERENCES company.prd_product(id),
    year_month  DATE         NOT NULL,
    unit_cost   NUMERIC(12,2),
    cost_type   VARCHAR(32),
    remark      VARCHAR(256),
    CONSTRAINT uk_prd_product_cost UNIQUE (product_id, year_month, cost_type)
);

CREATE TABLE company.sal_sales_order (
    id             BIGSERIAL PRIMARY KEY,
    order_no       VARCHAR(32)  NOT NULL,
    customer_id    BIGINT       REFERENCES company.crm_customer(id),
    owner_emp_id   BIGINT       REFERENCES company.hr_employee(id),
    dept_id        BIGINT       REFERENCES company.org_department(id),
    order_date     DATE,
    sign_date      DATE,
    currency       VARCHAR(8)   DEFAULT 'CNY',
    total_amount   NUMERIC(14,2),
    status         VARCHAR(16)  NOT NULL DEFAULT 'signed',
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_sal_sales_order_no UNIQUE (order_no)
);

CREATE INDEX idx_sal_order_date ON company.sal_sales_order(order_date);
CREATE INDEX idx_sal_order_customer ON company.sal_sales_order(customer_id);

CREATE TABLE company.sal_sales_order_item (
    id            BIGSERIAL PRIMARY KEY,
    order_id      BIGINT       NOT NULL REFERENCES company.sal_sales_order(id),
    product_id    BIGINT       REFERENCES company.prd_product(id),
    qty           NUMERIC(12,2),
    unit_price    NUMERIC(12,2),
    discount_rate NUMERIC(6,4),
    amount        NUMERIC(14,2),
    cost_amount   NUMERIC(14,2)
);

CREATE INDEX idx_sal_order_item_order ON company.sal_sales_order_item(order_id);

CREATE TABLE company.prj_project (
    id               BIGSERIAL PRIMARY KEY,
    project_code     VARCHAR(32)  NOT NULL,
    project_name     VARCHAR(128) NOT NULL,
    customer_id      BIGINT       REFERENCES company.crm_customer(id),
    project_type     VARCHAR(32),
    dept_id          BIGINT       REFERENCES company.org_department(id),
    pm_emp_id        BIGINT       REFERENCES company.hr_employee(id),
    start_date       DATE,
    end_date         DATE,
    plan_end_date    DATE,
    contract_amount  NUMERIC(14,2),
    status           VARCHAR(16)  NOT NULL DEFAULT 'active',
    created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_prj_project_code UNIQUE (project_code)
);

CREATE INDEX idx_prj_project_status ON company.prj_project(status);

CREATE TABLE company.prj_project_member (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT       NOT NULL REFERENCES company.prj_project(id),
    emp_id          BIGINT       NOT NULL REFERENCES company.hr_employee(id),
    role            VARCHAR(32),
    join_date       DATE,
    leave_date      DATE,
    allocation_pct  NUMERIC(6,2),
    CONSTRAINT uk_prj_member UNIQUE (project_id, emp_id)
);

CREATE TABLE company.prj_project_revenue (
    id               BIGSERIAL PRIMARY KEY,
    project_id       BIGINT       NOT NULL REFERENCES company.prj_project(id),
    revenue_date     DATE         NOT NULL,
    revenue_type     VARCHAR(32),
    amount           NUMERIC(14,2),
    received_amount  NUMERIC(14,2),
    invoice_no       VARCHAR(64),
    remark           VARCHAR(256),
    created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_prj_revenue_project ON company.prj_project_revenue(project_id);
CREATE INDEX idx_prj_revenue_date ON company.prj_project_revenue(revenue_date);

-- 可选外键（项目相关字段）
ALTER TABLE company.att_overtime
    ADD CONSTRAINT fk_att_overtime_project
    FOREIGN KEY (project_id) REFERENCES company.prj_project(id);

ALTER TABLE company.att_timesheet
    ADD CONSTRAINT fk_att_timesheet_project
    FOREIGN KEY (project_id) REFERENCES company.prj_project(id);

ALTER TABLE company.fin_reimburse
    ADD CONSTRAINT fk_fin_reimburse_project
    FOREIGN KEY (project_id) REFERENCES company.prj_project(id);
