# company 表关系

> 可导入格式：元数据用列表；外键用表格。导入时每条 FK 生成双向边（父→子=父列名，子→父=子列名）。

- code: `default`
- name: `company 表关系`
- summary: `demo-company 库表外键图谱（子表.col → 父表.col）`
- productName: `dbc产品`
- bidirectional: `true`

> 共 163 张表 / 253 条外键（来源 seed/company-table-fks.json）

## 外键

| 子表 | 子列 | 父表 | 父列 | 说明 |
| --- | --- | --- | --- | --- |
| `att_daily_record` | `emp_id` | `hr_employee` | `id` |  |
| `att_leave` | `approved_by` | `hr_employee` | `id` |  |
| `att_leave` | `emp_id` | `hr_employee` | `id` |  |
| `att_leave` | `leave_type_id` | `att_leave_type` | `id` |  |
| `att_overtime` | `emp_id` | `hr_employee` | `id` |  |
| `att_overtime` | `project_id` | `prj_project` | `id` |  |
| `att_timesheet` | `emp_id` | `hr_employee` | `id` |  |
| `att_timesheet` | `project_id` | `prj_project` | `id` |  |
| `crm_customer` | `owner_emp_id` | `hr_employee` | `id` |  |
| `fin_activity_budget` | `dept_id` | `org_department` | `id` |  |
| `fin_activity_budget` | `owner_emp_id` | `hr_employee` | `id` |  |
| `fin_activity_expense` | `budget_id` | `fin_activity_budget` | `id` |  |
| `fin_reimburse` | `dept_id` | `org_department` | `id` |  |
| `fin_reimburse` | `emp_id` | `hr_employee` | `id` |  |
| `fin_reimburse` | `project_id` | `prj_project` | `id` |  |
| `fin_reimburse_item` | `claim_id` | `fin_reimburse` | `id` |  |
| `fin_salary_slip` | `dept_id` | `org_department` | `id` |  |
| `fin_salary_slip` | `emp_id` | `hr_employee` | `id` |  |
| `fin_salary_slip` | `period_id` | `fin_salary_period` | `id` |  |
| `hr_employee` | `dept_id` | `org_department` | `id` |  |
| `hr_employee` | `job_level_id` | `hr_job_level` | `id` |  |
| `org_department` | `parent_id` | `org_department` | `id` |  |
| `prd_product_cost` | `product_id` | `prd_product` | `id` |  |
| `prj_project` | `customer_id` | `crm_customer` | `id` |  |
| `prj_project` | `dept_id` | `org_department` | `id` |  |
| `prj_project` | `pm_emp_id` | `hr_employee` | `id` |  |
| `prj_project_member` | `emp_id` | `hr_employee` | `id` |  |
| `prj_project_member` | `project_id` | `prj_project` | `id` |  |
| `prj_project_revenue` | `project_id` | `prj_project` | `id` |  |
| `sal_sales_order` | `customer_id` | `crm_customer` | `id` |  |
| `sal_sales_order` | `dept_id` | `org_department` | `id` |  |
| `sal_sales_order` | `owner_emp_id` | `hr_employee` | `id` |  |
| `sal_sales_order_item` | `order_id` | `sal_sales_order` | `id` |  |
| `sal_sales_order_item` | `product_id` | `prd_product` | `id` |  |
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
