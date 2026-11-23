# company 库表关系说明

> 以库内实际 FOREIGN KEY 为准（自动导出）。
> 核心表 22 张 + 扩展表 178 张 ≈ **200** 张；外键共 **253** 条。
> 扩展表无灌数；外键可指向核心表或其它扩展表。

## 核心表

- `att_daily_record`
- `att_leave`
- `att_leave_type`
- `att_overtime`
- `att_timesheet`
- `crm_customer`
- `fin_activity_budget`
- `fin_activity_expense`
- `fin_reimburse`
- `fin_reimburse_item`
- `fin_salary_period`
- `fin_salary_slip`
- `hr_employee`
- `hr_job_level`
- `org_department`
- `prd_product`
- `prd_product_cost`
- `prj_project`
- `prj_project_member`
- `prj_project_revenue`
- `sal_sales_order`
- `sal_sales_order_item`

## 核心表外键关系（34）

| 子表 | 列 | 父表 | 父列 | 子表说明 |
|---|---|---|---|---|
| `att_daily_record` | `emp_id` | `hr_employee` | `id` | - |
| `att_leave` | `approved_by` | `hr_employee` | `id` | - |
| `att_leave` | `emp_id` | `hr_employee` | `id` | - |
| `att_leave` | `leave_type_id` | `att_leave_type` | `id` | - |
| `att_overtime` | `emp_id` | `hr_employee` | `id` | - |
| `att_overtime` | `project_id` | `prj_project` | `id` | - |
| `att_timesheet` | `emp_id` | `hr_employee` | `id` | - |
| `att_timesheet` | `project_id` | `prj_project` | `id` | - |
| `crm_customer` | `owner_emp_id` | `hr_employee` | `id` | - |
| `fin_activity_budget` | `dept_id` | `org_department` | `id` | - |
| `fin_activity_budget` | `owner_emp_id` | `hr_employee` | `id` | - |
| `fin_activity_expense` | `budget_id` | `fin_activity_budget` | `id` | - |
| `fin_reimburse` | `dept_id` | `org_department` | `id` | - |
| `fin_reimburse` | `emp_id` | `hr_employee` | `id` | - |
| `fin_reimburse` | `project_id` | `prj_project` | `id` | - |
| `fin_reimburse_item` | `claim_id` | `fin_reimburse` | `id` | - |
| `fin_salary_slip` | `dept_id` | `org_department` | `id` | - |
| `fin_salary_slip` | `emp_id` | `hr_employee` | `id` | - |
| `fin_salary_slip` | `period_id` | `fin_salary_period` | `id` | - |
| `hr_employee` | `dept_id` | `org_department` | `id` | - |
| `hr_employee` | `job_level_id` | `hr_job_level` | `id` | - |
| `org_department` | `parent_id` | `org_department` | `id` | - |
| `prd_product_cost` | `product_id` | `prd_product` | `id` | - |
| `prj_project` | `customer_id` | `crm_customer` | `id` | - |
| `prj_project` | `dept_id` | `org_department` | `id` | - |
| `prj_project` | `pm_emp_id` | `hr_employee` | `id` | - |
| `prj_project_member` | `emp_id` | `hr_employee` | `id` | - |
| `prj_project_member` | `project_id` | `prj_project` | `id` | - |
| `prj_project_revenue` | `project_id` | `prj_project` | `id` | - |
| `sal_sales_order` | `customer_id` | `crm_customer` | `id` | - |
| `sal_sales_order` | `dept_id` | `org_department` | `id` | - |
| `sal_sales_order` | `owner_emp_id` | `hr_employee` | `id` | - |
| `sal_sales_order_item` | `order_id` | `sal_sales_order` | `id` | - |
| `sal_sales_order_item` | `product_id` | `prd_product` | `id` | - |

## 扩展表外键关系（219）

| 子表 | 列 | 父表 | 父列 | 子表说明 |
|---|---|---|---|---|
| `adm_meeting_booking` | `organizer_emp_id` | `hr_employee` | `id` | 会议室预订 |
| `adm_meeting_booking` | `room_id` | `adm_meeting_room` | `id` | 会议室预订 |
| `adm_meeting_room` | `office_id` | `org_office` | `id` | 会议室 |
| `adm_supply_request` | `emp_id` | `hr_employee` | `id` | 办公用品领用 |
| `adm_supply_request` | `supply_id` | `adm_supply` | `id` | 办公用品领用 |
| `adm_vehicle_trip` | `driver_emp_id` | `hr_employee` | `id` | 用车记录 |
| `adm_vehicle_trip` | `vehicle_id` | `adm_vehicle` | `id` | 用车记录 |
| `adm_visitor` | `host_emp_id` | `hr_employee` | `id` | 访客登记 |
| `adm_visitor` | `office_id` | `org_office` | `id` | 访客登记 |
| `att_device` | `office_id` | `org_office` | `id` | 考勤设备 |
| `att_leave_balance` | `emp_id` | `hr_employee` | `id` | 假期余额 |
| `att_leave_balance` | `leave_type_id` | `att_leave_type` | `id` | 假期余额 |
| `att_makeup_card` | `emp_id` | `hr_employee` | `id` | 补卡申请 |
| `att_monthly_summary` | `emp_id` | `hr_employee` | `id` | 月考勤汇总 |
| `att_punch` | `emp_id` | `hr_employee` | `id` | 打卡流水 |
| `att_punch` | `office_id` | `org_office` | `id` | 打卡流水 |
| `att_remote_work` | `emp_id` | `hr_employee` | `id` | 居家办公申请 |
| `att_shift_assign` | `emp_id` | `hr_employee` | `id` | 班次排班 |
| `att_shift_assign` | `shift_id` | `att_shift` | `id` | 班次排班 |
| `att_travel` | `emp_id` | `hr_employee` | `id` | 出差申请 |
| `att_travel` | `project_id` | `prj_project` | `id` | 出差申请 |
| `crm_activity` | `customer_id` | `crm_customer` | `id` | 客户跟进活动 |
| `crm_activity` | `emp_id` | `hr_employee` | `id` | 客户跟进活动 |
| `crm_activity` | `opp_id` | `crm_opportunity` | `id` | 客户跟进活动 |
| `crm_complaint` | `customer_id` | `crm_customer` | `id` | 客户投诉 |
| `crm_complaint` | `handler_emp_id` | `hr_employee` | `id` | 客户投诉 |
| `crm_complaint` | `project_id` | `prj_project` | `id` | 客户投诉 |
| `crm_contact` | `customer_id` | `crm_customer` | `id` | 客户联系人 |
| `crm_lead` | `customer_id` | `crm_customer` | `id` | 销售线索 |
| `crm_lead` | `owner_emp_id` | `hr_employee` | `id` | 销售线索 |
| `crm_opportunity` | `customer_id` | `crm_customer` | `id` | 商机 |
| `crm_opportunity` | `owner_emp_id` | `hr_employee` | `id` | 商机 |
| `crm_sla` | `customer_id` | `crm_customer` | `id` | 客户服务等级协议 |
| `crm_visit` | `customer_id` | `crm_customer` | `id` | 客户拜访 |
| `crm_visit` | `emp_id` | `hr_employee` | `id` | 客户拜访 |
| `fin_asset_depr` | `asset_id` | `fin_fixed_asset` | `id` | 资产折旧明细 |
| `fin_bank_account` | `company_id` | `org_company` | `id` | 公司银行账户 |
| `fin_bank_txn` | `acct_id` | `fin_bank_account` | `id` | 银行流水 |
| `fin_budget_line` | `budget_id` | `fin_budget_year` | `id` | 预算明细行 |
| `fin_budget_year` | `dept_id` | `org_department` | `id` | 年度预算 |
| `fin_cost_allocation` | `from_dept_id` | `org_department` | `id` | 费用分摊 |
| `fin_cost_allocation` | `to_dept_id` | `org_department` | `id` | 费用分摊 |
| `fin_fixed_asset` | `custodian_emp_id` | `hr_employee` | `id` | 固定资产 |
| `fin_fixed_asset` | `dept_id` | `org_department` | `id` | 固定资产 |
| `fin_invoice` | `customer_id` | `crm_customer` | `id` | 进销项发票 |
| `fin_invoice` | `vendor_id` | `fin_vendor` | `id` | 进销项发票 |
| `fin_journal` | `created_by` | `hr_employee` | `id` | 会计凭证头 |
| `fin_journal_line` | `acct_id` | `fin_gl_account` | `id` | 会计凭证分录 |
| `fin_journal_line` | `journal_id` | `fin_journal` | `id` | 会计凭证分录 |
| `fin_loan` | `emp_id` | `hr_employee` | `id` | 对公借款 |
| `fin_loan_repay` | `loan_id` | `fin_loan` | `id` | 借款核销 |
| `fin_loan_repay` | `reimburse_id` | `fin_reimburse` | `id` | 借款核销 |
| `fin_payment` | `applicant_emp_id` | `hr_employee` | `id` | 付款单 |
| `fin_payment` | `vendor_id` | `fin_vendor` | `id` | 付款单 |
| `fin_petty_cash` | `dept_id` | `org_department` | `id` | 备用金账户 |
| `fin_petty_cash` | `keeper_emp_id` | `hr_employee` | `id` | 备用金账户 |
| `fin_petty_cash_txn` | `petty_id` | `fin_petty_cash` | `id` | 备用金收支 |
| `fin_receipt` | `customer_id` | `crm_customer` | `id` | 收款单 |
| `fin_receipt` | `project_id` | `prj_project` | `id` | 收款单 |
| `hr_award` | `emp_id` | `hr_employee` | `id` | 奖惩记录 |
| `hr_bank_account` | `emp_id` | `hr_employee` | `id` | 员工薪酬账户 |
| `hr_certificate` | `emp_id` | `hr_employee` | `id` | 员工证书资质 |
| `hr_contract` | `emp_id` | `hr_employee` | `id` | 劳动合同 |
| `hr_contract` | `sign_company_id` | `org_company` | `id` | 劳动合同 |
| `hr_education` | `emp_id` | `hr_employee` | `id` | 教育经历 |
| `hr_emergency_contact` | `emp_id` | `hr_employee` | `id` | 紧急联系人 |
| `hr_family_member` | `emp_id` | `hr_employee` | `id` | 员工家属信息 |
| `hr_headcount_plan` | `dept_id` | `org_department` | `id` | 编制计划 |
| `hr_interview` | `candidate_id` | `hr_candidate` | `id` | 面试记录 |
| `hr_interview` | `interviewer_emp_id` | `hr_employee` | `id` | 面试记录 |
| `hr_interview` | `req_id` | `hr_recruit_req` | `id` | 面试记录 |
| `hr_offer` | `candidate_id` | `hr_candidate` | `id` | 录用 Offer |
| `hr_offer` | `req_id` | `hr_recruit_req` | `id` | 录用 Offer |
| `hr_onboarding` | `emp_id` | `hr_employee` | `id` | 入职办理单 |
| `hr_performance_goal` | `cycle_id` | `hr_performance_cycle` | `id` | 绩效目标 |
| `hr_performance_goal` | `emp_id` | `hr_employee` | `id` | 绩效目标 |
| `hr_performance_review` | `cycle_id` | `hr_performance_cycle` | `id` | 绩效评估结果 |
| `hr_performance_review` | `emp_id` | `hr_employee` | `id` | 绩效评估结果 |
| `hr_performance_review` | `reviewer_emp_id` | `hr_employee` | `id` | 绩效评估结果 |
| `hr_probation` | `emp_id` | `hr_employee` | `id` | 试用期考核 |
| `hr_probation` | `mentor_emp_id` | `hr_employee` | `id` | 试用期考核 |
| `hr_promotion` | `emp_id` | `hr_employee` | `id` | 晋升记录 |
| `hr_promotion` | `from_level_id` | `hr_job_level` | `id` | 晋升记录 |
| `hr_promotion` | `to_level_id` | `hr_job_level` | `id` | 晋升记录 |
| `hr_recruit_req` | `dept_id` | `org_department` | `id` | 招聘需求 |
| `hr_recruit_req` | `job_level_id` | `hr_job_level` | `id` | 招聘需求 |
| `hr_recruit_req` | `owner_emp_id` | `hr_employee` | `id` | 招聘需求 |
| `hr_resignation` | `emp_id` | `hr_employee` | `id` | 离职办理 |
| `hr_training_enroll` | `emp_id` | `hr_employee` | `id` | 培训报名 |
| `hr_training_enroll` | `session_id` | `hr_training_session` | `id` | 培训报名 |
| `hr_training_session` | `course_id` | `hr_training_course` | `id` | 培训场次 |
| `hr_transfer` | `emp_id` | `hr_employee` | `id` | 人事调动 |
| `hr_transfer` | `from_dept_id` | `org_department` | `id` | 人事调动 |
| `hr_transfer` | `to_dept_id` | `org_department` | `id` | 人事调动 |
| `hr_work_history` | `emp_id` | `hr_employee` | `id` | 入职前工作经历 |
| `itm_access_request` | `emp_id` | `hr_employee` | `id` | 权限申请 |
| `itm_access_request` | `system_id` | `itm_system` | `id` | 权限申请 |
| `itm_account` | `emp_id` | `hr_employee` | `id` | 系统账号 |
| `itm_account` | `system_id` | `itm_system` | `id` | 系统账号 |
| `itm_asset` | `assignee_emp_id` | `hr_employee` | `id` | IT 资产 |
| `itm_asset` | `office_id` | `org_office` | `id` | IT 资产 |
| `itm_asset_assign` | `asset_id` | `itm_asset` | `id` | IT 资产领用归还 |
| `itm_asset_assign` | `emp_id` | `hr_employee` | `id` | IT 资产领用归还 |
| `itm_change` | `applicant_emp_id` | `hr_employee` | `id` | 变更单 |
| `itm_change` | `system_id` | `itm_system` | `id` | 变更单 |
| `itm_deploy` | `operator_emp_id` | `hr_employee` | `id` | 发布部署记录 |
| `itm_deploy` | `system_id` | `itm_system` | `id` | 发布部署记录 |
| `itm_incident` | `commander_emp_id` | `hr_employee` | `id` | 生产故障 |
| `itm_incident` | `system_id` | `itm_system` | `id` | 生产故障 |
| `itm_system` | `owner_emp_id` | `hr_employee` | `id` | 业务系统台账 |
| `itm_ticket` | `assignee_emp_id` | `hr_employee` | `id` | IT 服务工单 |
| `itm_ticket` | `requester_emp_id` | `hr_employee` | `id` | IT 服务工单 |
| `itm_ticket_comment` | `author_emp_id` | `hr_employee` | `id` | 工单评论 |
| `itm_ticket_comment` | `ticket_id` | `itm_ticket` | `id` | 工单评论 |
| `kb_article` | `author_emp_id` | `hr_employee` | `id` | 内部知识文章 |
| `kb_article_tag_rel` | `article_id` | `kb_article` | `id` | 文章标签关系 |
| `kb_article_tag_rel` | `tag_id` | `kb_article_tag` | `id` | 文章标签关系 |
| `kb_article_tag_rel` | `tagged_by` | `hr_employee` | `id` | 文章标签关系 |
| `legal_compliance_check` | `owner_emp_id` | `hr_employee` | `id` | 合规检查 |
| `legal_contract` | `customer_id` | `crm_customer` | `id` | 法务合同台账 |
| `legal_contract` | `owner_emp_id` | `hr_employee` | `id` | 法务合同台账 |
| `legal_contract` | `vendor_id` | `fin_vendor` | `id` | 法务合同台账 |
| `legal_contract_clause` | `contract_id` | `legal_contract` | `id` | 合同关键条款 |
| `legal_dispute` | `contract_id` | `legal_contract` | `id` | 诉讼/争议案件 |
| `mkt_campaign` | `owner_emp_id` | `hr_employee` | `id` | 市场活动 |
| `mkt_campaign_lead` | `camp_id` | `mkt_campaign` | `id` | 活动获客线索 |
| `mkt_campaign_lead` | `lead_id` | `crm_lead` | `id` | 活动获客线索 |
| `mkt_content` | `author_emp_id` | `hr_employee` | `id` | 内容素材 |
| `mkt_event_reg` | `camp_id` | `mkt_campaign` | `id` | 活动报名 |
| `ops_backup_job` | `system_id` | `itm_system` | `id` | 备份任务 |
| `ops_duty_roster` | `emp_id` | `hr_employee` | `id` | 值班排班 |
| `ops_duty_roster` | `system_id` | `itm_system` | `id` | 值班排班 |
| `ops_monitor_alert` | `acked_by` | `hr_employee` | `id` | 监控告警 |
| `ops_monitor_alert` | `system_id` | `itm_system` | `id` | 监控告警 |
| `ops_runbook` | `owner_emp_id` | `hr_employee` | `id` | 运维手册 |
| `ops_runbook` | `system_id` | `itm_system` | `id` | 运维手册 |
| `org_announcement` | `publisher_emp_id` | `hr_employee` | `id` | 内部公告 |
| `org_biz_unit` | `leader_emp_id` | `hr_employee` | `id` | 业务单元 |
| `org_cost_center` | `dept_id` | `org_department` | `id` | 成本中心 |
| `org_cost_center` | `owner_emp_id` | `hr_employee` | `id` | 成本中心 |
| `org_dept_change` | `dept_id` | `org_department` | `id` | 部门变更记录 |
| `org_dept_change` | `operator_emp_id` | `hr_employee` | `id` | 部门变更记录 |
| `org_dept_closure` | `ancestor_id` | `org_department` | `id` | 部门闭包表（祖先-后代） |
| `org_dept_closure` | `descendant_id` | `org_department` | `id` | 部门闭包表（祖先-后代） |
| `org_office` | `company_id` | `org_company` | `id` | 办公职场 |
| `org_position` | `dept_id` | `org_department` | `id` | 岗位编制 |
| `org_position` | `job_level_id` | `hr_job_level` | `id` | 岗位编制 |
| `org_seal` | `company_id` | `org_company` | `id` | 公司印章台账 |
| `org_seal` | `keeper_emp_id` | `hr_employee` | `id` | 公司印章台账 |
| `prd_feature` | `product_id` | `prd_product` | `id` | 产品功能点 |
| `prd_license` | `customer_id` | `crm_customer` | `id` | 产品授权许可 |
| `prd_license` | `product_id` | `prd_product` | `id` | 产品授权许可 |
| `prd_product_line` | `owner_emp_id` | `hr_employee` | `id` | 产品线 |
| `prd_product_version` | `product_id` | `prd_product` | `id` | 产品版本 |
| `prd_roadmap` | `product_id` | `prd_product` | `id` | 产品路线图项 |
| `prj_acceptance` | `project_id` | `prj_project` | `id` | 项目验收 |
| `prj_change_request` | `project_id` | `prj_project` | `id` | 项目变更申请 |
| `prj_change_request` | `requester_emp_id` | `hr_employee` | `id` | 项目变更申请 |
| `prj_document` | `project_id` | `prj_project` | `id` | 项目文档索引 |
| `prj_document` | `uploader_emp_id` | `hr_employee` | `id` | 项目文档索引 |
| `prj_issue` | `assignee_emp_id` | `hr_employee` | `id` | 项目问题单 |
| `prj_issue` | `project_id` | `prj_project` | `id` | 项目问题单 |
| `prj_issue` | `reporter_emp_id` | `hr_employee` | `id` | 项目问题单 |
| `prj_milestone` | `project_id` | `prj_project` | `id` | 项目里程碑 |
| `prj_risk` | `owner_emp_id` | `hr_employee` | `id` | 项目风险 |
| `prj_risk` | `project_id` | `prj_project` | `id` | 项目风险 |
| `prj_stakeholder` | `emp_id` | `hr_employee` | `id` | 项目干系人 |
| `prj_stakeholder` | `project_id` | `prj_project` | `id` | 项目干系人 |
| `prj_task` | `assignee_emp_id` | `hr_employee` | `id` | 项目任务 |
| `prj_task` | `project_id` | `prj_project` | `id` | 项目任务 |
| `prj_warranty` | `project_id` | `prj_project` | `id` | 项目质保 |
| `prj_weekly_report` | `author_emp_id` | `hr_employee` | `id` | 项目周报 |
| `prj_weekly_report` | `project_id` | `prj_project` | `id` | 项目周报 |
| `qa_defect` | `assignee_emp_id` | `hr_employee` | `id` | 缺陷 |
| `qa_defect` | `product_id` | `prd_product` | `id` | 缺陷 |
| `qa_defect` | `project_id` | `prj_project` | `id` | 缺陷 |
| `qa_defect` | `reporter_emp_id` | `hr_employee` | `id` | 缺陷 |
| `qa_release_gate` | `checked_by` | `hr_employee` | `id` | 发布门禁检查 |
| `qa_release_gate` | `system_id` | `itm_system` | `id` | 发布门禁检查 |
| `qa_test_case` | `plan_id` | `qa_test_plan` | `id` | 测试用例 |
| `qa_test_plan` | `owner_emp_id` | `hr_employee` | `id` | 测试计划 |
| `qa_test_plan` | `product_id` | `prd_product` | `id` | 测试计划 |
| `qa_test_plan` | `project_id` | `prj_project` | `id` | 测试计划 |
| `sal_commission` | `emp_id` | `hr_employee` | `id` | 销售提成明细 |
| `sal_commission` | `order_id` | `sal_sales_order` | `id` | 销售提成明细 |
| `sal_commission_rule` | `product_id` | `prd_product` | `id` | 销售提成规则 |
| `sal_contract` | `customer_id` | `crm_customer` | `id` | 销售合同 |
| `sal_contract` | `order_id` | `sal_sales_order` | `id` | 销售合同 |
| `sal_contract` | `owner_emp_id` | `hr_employee` | `id` | 销售合同 |
| `sal_contract_milestone` | `contract_id` | `sal_contract` | `id` | 合同里程碑收款 |
| `sal_delivery` | `order_id` | `sal_sales_order` | `id` | 发货/交付单 |
| `sal_delivery_item` | `delivery_id` | `sal_delivery` | `id` | 交付明细 |
| `sal_delivery_item` | `product_id` | `prd_product` | `id` | 交付明细 |
| `sal_price_list_item` | `plist_id` | `sal_price_list` | `id` | 价格表明细 |
| `sal_price_list_item` | `product_id` | `prd_product` | `id` | 价格表明细 |
| `sal_quote` | `customer_id` | `crm_customer` | `id` | 销售报价单 |
| `sal_quote` | `owner_emp_id` | `hr_employee` | `id` | 销售报价单 |
| `sal_quote_item` | `product_id` | `prd_product` | `id` | 报价明细 |
| `sal_quote_item` | `quote_id` | `sal_quote` | `id` | 报价明细 |
| `sal_return` | `order_id` | `sal_sales_order` | `id` | 退货单 |
| `sal_target` | `dept_id` | `org_department` | `id` | 销售目标 |
| `sal_target` | `emp_id` | `hr_employee` | `id` | 销售目标 |
| `scm_inventory` | `warehouse_id` | `scm_warehouse` | `id` | 库存台账 |
| `scm_inventory_txn` | `warehouse_id` | `scm_warehouse` | `id` | 库存流水 |
| `scm_purchase_order` | `buyer_emp_id` | `hr_employee` | `id` | 采购订单 |
| `scm_purchase_order` | `req_id` | `scm_purchase_req` | `id` | 采购订单 |
| `scm_purchase_order` | `vendor_id` | `fin_vendor` | `id` | 采购订单 |
| `scm_purchase_order_item` | `po_id` | `scm_purchase_order` | `id` | 采购订单明细 |
| `scm_purchase_req` | `applicant_emp_id` | `hr_employee` | `id` | 采购申请 |
| `scm_purchase_req` | `dept_id` | `org_department` | `id` | 采购申请 |
| `scm_purchase_req_item` | `req_id` | `scm_purchase_req` | `id` | 采购申请明细 |
| `scm_receipt` | `po_id` | `scm_purchase_order` | `id` | 采购入库单 |
| `scm_receipt` | `warehouse_id` | `scm_warehouse` | `id` | 采购入库单 |
| `scm_vendor_eval` | `evaluator_emp_id` | `hr_employee` | `id` | 供应商评价 |
| `scm_vendor_eval` | `vendor_id` | `fin_vendor` | `id` | 供应商评价 |
| `scm_warehouse` | `office_id` | `org_office` | `id` | 仓库 |
| `sec_audit_log` | `emp_id` | `hr_employee` | `id` | 安全审计日志 |
| `sec_audit_log` | `system_id` | `itm_system` | `id` | 安全审计日志 |
| `sec_vulnerability` | `system_id` | `itm_system` | `id` | 漏洞台账 |

## 全量外键（按子表）

### `adm_meeting_booking`（扩展 · 会议室预订）

- `organizer_emp_id` → `hr_employee.id`
- `room_id` → `adm_meeting_room.id`

### `adm_meeting_room`（扩展 · 会议室）

- `office_id` → `org_office.id`

### `adm_supply_request`（扩展 · 办公用品领用）

- `emp_id` → `hr_employee.id`
- `supply_id` → `adm_supply.id`

### `adm_vehicle_trip`（扩展 · 用车记录）

- `driver_emp_id` → `hr_employee.id`
- `vehicle_id` → `adm_vehicle.id`

### `adm_visitor`（扩展 · 访客登记）

- `host_emp_id` → `hr_employee.id`
- `office_id` → `org_office.id`

### `att_daily_record`（核心）

- `emp_id` → `hr_employee.id`

### `att_device`（扩展 · 考勤设备）

- `office_id` → `org_office.id`

### `att_leave`（核心）

- `approved_by` → `hr_employee.id`
- `emp_id` → `hr_employee.id`
- `leave_type_id` → `att_leave_type.id`

### `att_leave_balance`（扩展 · 假期余额）

- `emp_id` → `hr_employee.id`
- `leave_type_id` → `att_leave_type.id`

### `att_makeup_card`（扩展 · 补卡申请）

- `emp_id` → `hr_employee.id`

### `att_monthly_summary`（扩展 · 月考勤汇总）

- `emp_id` → `hr_employee.id`

### `att_overtime`（核心）

- `emp_id` → `hr_employee.id`
- `project_id` → `prj_project.id`

### `att_punch`（扩展 · 打卡流水）

- `emp_id` → `hr_employee.id`
- `office_id` → `org_office.id`

### `att_remote_work`（扩展 · 居家办公申请）

- `emp_id` → `hr_employee.id`

### `att_shift_assign`（扩展 · 班次排班）

- `emp_id` → `hr_employee.id`
- `shift_id` → `att_shift.id`

### `att_timesheet`（核心）

- `emp_id` → `hr_employee.id`
- `project_id` → `prj_project.id`

### `att_travel`（扩展 · 出差申请）

- `emp_id` → `hr_employee.id`
- `project_id` → `prj_project.id`

### `crm_activity`（扩展 · 客户跟进活动）

- `customer_id` → `crm_customer.id`
- `emp_id` → `hr_employee.id`
- `opp_id` → `crm_opportunity.id`

### `crm_complaint`（扩展 · 客户投诉）

- `customer_id` → `crm_customer.id`
- `handler_emp_id` → `hr_employee.id`
- `project_id` → `prj_project.id`

### `crm_contact`（扩展 · 客户联系人）

- `customer_id` → `crm_customer.id`

### `crm_customer`（核心）

- `owner_emp_id` → `hr_employee.id`

### `crm_lead`（扩展 · 销售线索）

- `customer_id` → `crm_customer.id`
- `owner_emp_id` → `hr_employee.id`

### `crm_opportunity`（扩展 · 商机）

- `customer_id` → `crm_customer.id`
- `owner_emp_id` → `hr_employee.id`

### `crm_sla`（扩展 · 客户服务等级协议）

- `customer_id` → `crm_customer.id`

### `crm_visit`（扩展 · 客户拜访）

- `customer_id` → `crm_customer.id`
- `emp_id` → `hr_employee.id`

### `fin_activity_budget`（核心）

- `dept_id` → `org_department.id`
- `owner_emp_id` → `hr_employee.id`

### `fin_activity_expense`（核心）

- `budget_id` → `fin_activity_budget.id`

### `fin_asset_depr`（扩展 · 资产折旧明细）

- `asset_id` → `fin_fixed_asset.id`

### `fin_bank_account`（扩展 · 公司银行账户）

- `company_id` → `org_company.id`

### `fin_bank_txn`（扩展 · 银行流水）

- `acct_id` → `fin_bank_account.id`

### `fin_budget_line`（扩展 · 预算明细行）

- `budget_id` → `fin_budget_year.id`

### `fin_budget_year`（扩展 · 年度预算）

- `dept_id` → `org_department.id`

### `fin_cost_allocation`（扩展 · 费用分摊）

- `from_dept_id` → `org_department.id`
- `to_dept_id` → `org_department.id`

### `fin_fixed_asset`（扩展 · 固定资产）

- `custodian_emp_id` → `hr_employee.id`
- `dept_id` → `org_department.id`

### `fin_invoice`（扩展 · 进销项发票）

- `customer_id` → `crm_customer.id`
- `vendor_id` → `fin_vendor.id`

### `fin_journal`（扩展 · 会计凭证头）

- `created_by` → `hr_employee.id`

### `fin_journal_line`（扩展 · 会计凭证分录）

- `acct_id` → `fin_gl_account.id`
- `journal_id` → `fin_journal.id`

### `fin_loan`（扩展 · 对公借款）

- `emp_id` → `hr_employee.id`

### `fin_loan_repay`（扩展 · 借款核销）

- `loan_id` → `fin_loan.id`
- `reimburse_id` → `fin_reimburse.id`

### `fin_payment`（扩展 · 付款单）

- `applicant_emp_id` → `hr_employee.id`
- `vendor_id` → `fin_vendor.id`

### `fin_petty_cash`（扩展 · 备用金账户）

- `dept_id` → `org_department.id`
- `keeper_emp_id` → `hr_employee.id`

### `fin_petty_cash_txn`（扩展 · 备用金收支）

- `petty_id` → `fin_petty_cash.id`

### `fin_receipt`（扩展 · 收款单）

- `customer_id` → `crm_customer.id`
- `project_id` → `prj_project.id`

### `fin_reimburse`（核心）

- `dept_id` → `org_department.id`
- `emp_id` → `hr_employee.id`
- `project_id` → `prj_project.id`

### `fin_reimburse_item`（核心）

- `claim_id` → `fin_reimburse.id`

### `fin_salary_slip`（核心）

- `dept_id` → `org_department.id`
- `emp_id` → `hr_employee.id`
- `period_id` → `fin_salary_period.id`

### `hr_award`（扩展 · 奖惩记录）

- `emp_id` → `hr_employee.id`

### `hr_bank_account`（扩展 · 员工薪酬账户）

- `emp_id` → `hr_employee.id`

### `hr_certificate`（扩展 · 员工证书资质）

- `emp_id` → `hr_employee.id`

### `hr_contract`（扩展 · 劳动合同）

- `emp_id` → `hr_employee.id`
- `sign_company_id` → `org_company.id`

### `hr_education`（扩展 · 教育经历）

- `emp_id` → `hr_employee.id`

### `hr_emergency_contact`（扩展 · 紧急联系人）

- `emp_id` → `hr_employee.id`

### `hr_employee`（核心）

- `dept_id` → `org_department.id`
- `job_level_id` → `hr_job_level.id`

### `hr_family_member`（扩展 · 员工家属信息）

- `emp_id` → `hr_employee.id`

### `hr_headcount_plan`（扩展 · 编制计划）

- `dept_id` → `org_department.id`

### `hr_interview`（扩展 · 面试记录）

- `candidate_id` → `hr_candidate.id`
- `interviewer_emp_id` → `hr_employee.id`
- `req_id` → `hr_recruit_req.id`

### `hr_offer`（扩展 · 录用 Offer）

- `candidate_id` → `hr_candidate.id`
- `req_id` → `hr_recruit_req.id`

### `hr_onboarding`（扩展 · 入职办理单）

- `emp_id` → `hr_employee.id`

### `hr_performance_goal`（扩展 · 绩效目标）

- `cycle_id` → `hr_performance_cycle.id`
- `emp_id` → `hr_employee.id`

### `hr_performance_review`（扩展 · 绩效评估结果）

- `cycle_id` → `hr_performance_cycle.id`
- `emp_id` → `hr_employee.id`
- `reviewer_emp_id` → `hr_employee.id`

### `hr_probation`（扩展 · 试用期考核）

- `emp_id` → `hr_employee.id`
- `mentor_emp_id` → `hr_employee.id`

### `hr_promotion`（扩展 · 晋升记录）

- `emp_id` → `hr_employee.id`
- `from_level_id` → `hr_job_level.id`
- `to_level_id` → `hr_job_level.id`

### `hr_recruit_req`（扩展 · 招聘需求）

- `dept_id` → `org_department.id`
- `job_level_id` → `hr_job_level.id`
- `owner_emp_id` → `hr_employee.id`

### `hr_resignation`（扩展 · 离职办理）

- `emp_id` → `hr_employee.id`

### `hr_training_enroll`（扩展 · 培训报名）

- `emp_id` → `hr_employee.id`
- `session_id` → `hr_training_session.id`

### `hr_training_session`（扩展 · 培训场次）

- `course_id` → `hr_training_course.id`

### `hr_transfer`（扩展 · 人事调动）

- `emp_id` → `hr_employee.id`
- `from_dept_id` → `org_department.id`
- `to_dept_id` → `org_department.id`

### `hr_work_history`（扩展 · 入职前工作经历）

- `emp_id` → `hr_employee.id`

### `itm_access_request`（扩展 · 权限申请）

- `emp_id` → `hr_employee.id`
- `system_id` → `itm_system.id`

### `itm_account`（扩展 · 系统账号）

- `emp_id` → `hr_employee.id`
- `system_id` → `itm_system.id`

### `itm_asset`（扩展 · IT 资产）

- `assignee_emp_id` → `hr_employee.id`
- `office_id` → `org_office.id`

### `itm_asset_assign`（扩展 · IT 资产领用归还）

- `asset_id` → `itm_asset.id`
- `emp_id` → `hr_employee.id`

### `itm_change`（扩展 · 变更单）

- `applicant_emp_id` → `hr_employee.id`
- `system_id` → `itm_system.id`

### `itm_deploy`（扩展 · 发布部署记录）

- `operator_emp_id` → `hr_employee.id`
- `system_id` → `itm_system.id`

### `itm_incident`（扩展 · 生产故障）

- `commander_emp_id` → `hr_employee.id`
- `system_id` → `itm_system.id`

### `itm_system`（扩展 · 业务系统台账）

- `owner_emp_id` → `hr_employee.id`

### `itm_ticket`（扩展 · IT 服务工单）

- `assignee_emp_id` → `hr_employee.id`
- `requester_emp_id` → `hr_employee.id`

### `itm_ticket_comment`（扩展 · 工单评论）

- `author_emp_id` → `hr_employee.id`
- `ticket_id` → `itm_ticket.id`

### `kb_article`（扩展 · 内部知识文章）

- `author_emp_id` → `hr_employee.id`

### `kb_article_tag_rel`（扩展 · 文章标签关系）

- `article_id` → `kb_article.id`
- `tag_id` → `kb_article_tag.id`
- `tagged_by` → `hr_employee.id`

### `legal_compliance_check`（扩展 · 合规检查）

- `owner_emp_id` → `hr_employee.id`

### `legal_contract`（扩展 · 法务合同台账）

- `customer_id` → `crm_customer.id`
- `owner_emp_id` → `hr_employee.id`
- `vendor_id` → `fin_vendor.id`

### `legal_contract_clause`（扩展 · 合同关键条款）

- `contract_id` → `legal_contract.id`

### `legal_dispute`（扩展 · 诉讼/争议案件）

- `contract_id` → `legal_contract.id`

### `mkt_campaign`（扩展 · 市场活动）

- `owner_emp_id` → `hr_employee.id`

### `mkt_campaign_lead`（扩展 · 活动获客线索）

- `camp_id` → `mkt_campaign.id`
- `lead_id` → `crm_lead.id`

### `mkt_content`（扩展 · 内容素材）

- `author_emp_id` → `hr_employee.id`

### `mkt_event_reg`（扩展 · 活动报名）

- `camp_id` → `mkt_campaign.id`

### `ops_backup_job`（扩展 · 备份任务）

- `system_id` → `itm_system.id`

### `ops_duty_roster`（扩展 · 值班排班）

- `emp_id` → `hr_employee.id`
- `system_id` → `itm_system.id`

### `ops_monitor_alert`（扩展 · 监控告警）

- `acked_by` → `hr_employee.id`
- `system_id` → `itm_system.id`

### `ops_runbook`（扩展 · 运维手册）

- `owner_emp_id` → `hr_employee.id`
- `system_id` → `itm_system.id`

### `org_announcement`（扩展 · 内部公告）

- `publisher_emp_id` → `hr_employee.id`

### `org_biz_unit`（扩展 · 业务单元）

- `leader_emp_id` → `hr_employee.id`

### `org_cost_center`（扩展 · 成本中心）

- `dept_id` → `org_department.id`
- `owner_emp_id` → `hr_employee.id`

### `org_department`（核心）

- `parent_id` → `org_department.id`

### `org_dept_change`（扩展 · 部门变更记录）

- `dept_id` → `org_department.id`
- `operator_emp_id` → `hr_employee.id`

### `org_dept_closure`（扩展 · 部门闭包表（祖先-后代））

- `ancestor_id` → `org_department.id`
- `descendant_id` → `org_department.id`

### `org_office`（扩展 · 办公职场）

- `company_id` → `org_company.id`

### `org_position`（扩展 · 岗位编制）

- `dept_id` → `org_department.id`
- `job_level_id` → `hr_job_level.id`

### `org_seal`（扩展 · 公司印章台账）

- `company_id` → `org_company.id`
- `keeper_emp_id` → `hr_employee.id`

### `prd_feature`（扩展 · 产品功能点）

- `product_id` → `prd_product.id`

### `prd_license`（扩展 · 产品授权许可）

- `customer_id` → `crm_customer.id`
- `product_id` → `prd_product.id`

### `prd_product_cost`（核心）

- `product_id` → `prd_product.id`

### `prd_product_line`（扩展 · 产品线）

- `owner_emp_id` → `hr_employee.id`

### `prd_product_version`（扩展 · 产品版本）

- `product_id` → `prd_product.id`

### `prd_roadmap`（扩展 · 产品路线图项）

- `product_id` → `prd_product.id`

### `prj_acceptance`（扩展 · 项目验收）

- `project_id` → `prj_project.id`

### `prj_change_request`（扩展 · 项目变更申请）

- `project_id` → `prj_project.id`
- `requester_emp_id` → `hr_employee.id`

### `prj_document`（扩展 · 项目文档索引）

- `project_id` → `prj_project.id`
- `uploader_emp_id` → `hr_employee.id`

### `prj_issue`（扩展 · 项目问题单）

- `assignee_emp_id` → `hr_employee.id`
- `project_id` → `prj_project.id`
- `reporter_emp_id` → `hr_employee.id`

### `prj_milestone`（扩展 · 项目里程碑）

- `project_id` → `prj_project.id`

### `prj_project`（核心）

- `customer_id` → `crm_customer.id`
- `dept_id` → `org_department.id`
- `pm_emp_id` → `hr_employee.id`

### `prj_project_member`（核心）

- `emp_id` → `hr_employee.id`
- `project_id` → `prj_project.id`

### `prj_project_revenue`（核心）

- `project_id` → `prj_project.id`

### `prj_risk`（扩展 · 项目风险）

- `owner_emp_id` → `hr_employee.id`
- `project_id` → `prj_project.id`

### `prj_stakeholder`（扩展 · 项目干系人）

- `emp_id` → `hr_employee.id`
- `project_id` → `prj_project.id`

### `prj_task`（扩展 · 项目任务）

- `assignee_emp_id` → `hr_employee.id`
- `project_id` → `prj_project.id`

### `prj_warranty`（扩展 · 项目质保）

- `project_id` → `prj_project.id`

### `prj_weekly_report`（扩展 · 项目周报）

- `author_emp_id` → `hr_employee.id`
- `project_id` → `prj_project.id`

### `qa_defect`（扩展 · 缺陷）

- `assignee_emp_id` → `hr_employee.id`
- `product_id` → `prd_product.id`
- `project_id` → `prj_project.id`
- `reporter_emp_id` → `hr_employee.id`

### `qa_release_gate`（扩展 · 发布门禁检查）

- `checked_by` → `hr_employee.id`
- `system_id` → `itm_system.id`

### `qa_test_case`（扩展 · 测试用例）

- `plan_id` → `qa_test_plan.id`

### `qa_test_plan`（扩展 · 测试计划）

- `owner_emp_id` → `hr_employee.id`
- `product_id` → `prd_product.id`
- `project_id` → `prj_project.id`

### `sal_commission`（扩展 · 销售提成明细）

- `emp_id` → `hr_employee.id`
- `order_id` → `sal_sales_order.id`

### `sal_commission_rule`（扩展 · 销售提成规则）

- `product_id` → `prd_product.id`

### `sal_contract`（扩展 · 销售合同）

- `customer_id` → `crm_customer.id`
- `order_id` → `sal_sales_order.id`
- `owner_emp_id` → `hr_employee.id`

### `sal_contract_milestone`（扩展 · 合同里程碑收款）

- `contract_id` → `sal_contract.id`

### `sal_delivery`（扩展 · 发货/交付单）

- `order_id` → `sal_sales_order.id`

### `sal_delivery_item`（扩展 · 交付明细）

- `delivery_id` → `sal_delivery.id`
- `product_id` → `prd_product.id`

### `sal_price_list_item`（扩展 · 价格表明细）

- `plist_id` → `sal_price_list.id`
- `product_id` → `prd_product.id`

### `sal_quote`（扩展 · 销售报价单）

- `customer_id` → `crm_customer.id`
- `owner_emp_id` → `hr_employee.id`

### `sal_quote_item`（扩展 · 报价明细）

- `product_id` → `prd_product.id`
- `quote_id` → `sal_quote.id`

### `sal_return`（扩展 · 退货单）

- `order_id` → `sal_sales_order.id`

### `sal_sales_order`（核心）

- `customer_id` → `crm_customer.id`
- `dept_id` → `org_department.id`
- `owner_emp_id` → `hr_employee.id`

### `sal_sales_order_item`（核心）

- `order_id` → `sal_sales_order.id`
- `product_id` → `prd_product.id`

### `sal_target`（扩展 · 销售目标）

- `dept_id` → `org_department.id`
- `emp_id` → `hr_employee.id`

### `scm_inventory`（扩展 · 库存台账）

- `warehouse_id` → `scm_warehouse.id`

### `scm_inventory_txn`（扩展 · 库存流水）

- `warehouse_id` → `scm_warehouse.id`

### `scm_purchase_order`（扩展 · 采购订单）

- `buyer_emp_id` → `hr_employee.id`
- `req_id` → `scm_purchase_req.id`
- `vendor_id` → `fin_vendor.id`

### `scm_purchase_order_item`（扩展 · 采购订单明细）

- `po_id` → `scm_purchase_order.id`

### `scm_purchase_req`（扩展 · 采购申请）

- `applicant_emp_id` → `hr_employee.id`
- `dept_id` → `org_department.id`

### `scm_purchase_req_item`（扩展 · 采购申请明细）

- `req_id` → `scm_purchase_req.id`

### `scm_receipt`（扩展 · 采购入库单）

- `po_id` → `scm_purchase_order.id`
- `warehouse_id` → `scm_warehouse.id`

### `scm_vendor_eval`（扩展 · 供应商评价）

- `evaluator_emp_id` → `hr_employee.id`
- `vendor_id` → `fin_vendor.id`

### `scm_warehouse`（扩展 · 仓库）

- `office_id` → `org_office.id`

### `sec_audit_log`（扩展 · 安全审计日志）

- `emp_id` → `hr_employee.id`
- `system_id` → `itm_system.id`

### `sec_vulnerability`（扩展 · 漏洞台账）

- `system_id` → `itm_system.id`

## 业务域一览

| 前缀 | 域 |
|---|---|
| org_ | 组织/公司/职场/成本中心 |
| hr_ | 人事/绩效/招聘/培训 |
| att_ | 考勤/排班/打卡 |
| fin_ | 财务/发票/预算/总账 |
| crm_ | 客户/商机/跟进 |
| sal_ | 销售/合同/交付/提成 |
| prd_ | 产品 |
| prj_ | 项目交付 |
| scm_ | 采购/库存 |
| itm_ | IT 资产/服务台 |
| sec_ | 安全 |
| ops_ | 运维 |
| mkt_ | 市场 |
| adm_ | 行政 |
| legal_ | 法务 |
| qa_ | 质量 |
| kb_ | 知识 |
| dim_ | 通用字典 |

## 外键条数（按子表域）

| 域 | 条数 |
|---|---|
| 人事/绩效/招聘/培训 | 38 |
| 财务/发票/预算/总账 | 34 |
| 销售/合同/交付/提成 | 24 |
| 项目交付 | 24 |
| 考勤/排班/打卡 | 20 |
| IT 资产/服务台 | 19 |
| 客户/商机/跟进 | 15 |
| 组织/公司/职场/成本中心 | 14 |
| 采购/库存 | 14 |
| 质量 | 10 |
| 行政 | 9 |
| 产品 | 7 |
| 运维 | 7 |
| 法务 | 6 |
| 市场 | 5 |
| 知识 | 4 |
| 安全 | 3 |
