# company 库数据库结构说明

> Schema：`company`（PostgreSQL）  
> 版本：company_eval_v2（含扩展表，合计约 200 张）  
> 说明：**唯一完整**交付用表结构文档。每表四段：英文标题 → 中文用途 → 字段一行摘要 → 完整字段表。
> 枚举/状态类字段在「字段说明」中给出 key=中文含义；扩展表以 catalog/库注释为准。
> 外键按子表分组的可读版见 [table-relations.md](./table-relations.md)。

## 目录

1. [org_department](#org_department) — 组织部门表
2. [hr_job_level](#hr_job_level) — 职级字典表
3. [hr_employee](#hr_employee) — 员工主数据表
4. [att_leave_type](#att_leave_type) — 请假类型字典
5. [att_leave](#att_leave) — 请假单
6. [att_overtime](#att_overtime) — 加班申请记录
7. [att_daily_record](#att_daily_record) — 日考勤结果
8. [att_timesheet](#att_timesheet) — 项目工时填报
9. [fin_salary_period](#fin_salary_period) — 薪资结算期间
10. [fin_salary_slip](#fin_salary_slip) — 工资条
11. [fin_reimburse](#fin_reimburse) — 报销单头表
12. [fin_reimburse_item](#fin_reimburse_item) — 报销单明细
13. [fin_activity_budget](#fin_activity_budget) — 部门活动预算
14. [fin_activity_expense](#fin_activity_expense) — 部门活动花费
15. [crm_customer](#crm_customer) — 客户主数据
16. [prd_product](#prd_product) — 产品主数据
17. [prd_product_cost](#prd_product_cost) — 产品月度成本
18. [sal_sales_order](#sal_sales_order) — 销售订单头表
19. [sal_sales_order_item](#sal_sales_order_item) — 销售订单明细
20. [prj_project](#prj_project) — 交付项目
21. [prj_project_member](#prj_project_member) — 项目成员
22. [prj_project_revenue](#prj_project_revenue) — 项目回款记录
23. [adm_meeting_booking](#adm_meeting_booking) — 会议室预订
24. [adm_meeting_room](#adm_meeting_room) — 会议室
25. [adm_supply](#adm_supply) — 办公用品
26. [adm_supply_request](#adm_supply_request) — 办公用品领用
27. [adm_vehicle](#adm_vehicle) — 公务车
28. [adm_vehicle_trip](#adm_vehicle_trip) — 用车记录
29. [adm_visitor](#adm_visitor) — 访客登记
30. [att_device](#att_device) — 考勤设备
31. [att_leave_balance](#att_leave_balance) — 假期余额
32. [att_makeup_card](#att_makeup_card) — 补卡申请
33. [att_monthly_summary](#att_monthly_summary) — 月考勤汇总
34. [att_ot_rule](#att_ot_rule) — 加班规则
35. [att_punch](#att_punch) — 打卡流水
36. [att_remote_work](#att_remote_work) — 居家办公申请
37. [att_shift](#att_shift) — 班次定义
38. [att_shift_assign](#att_shift_assign) — 班次排班
39. [att_travel](#att_travel) — 出差申请
40. [crm_activity](#crm_activity) — 客户跟进活动
41. [crm_complaint](#crm_complaint) — 客户投诉
42. [crm_contact](#crm_contact) — 客户联系人
43. [crm_lead](#crm_lead) — 销售线索
44. [crm_opportunity](#crm_opportunity) — 商机
45. [crm_sla](#crm_sla) — 客户服务等级协议
46. [crm_visit](#crm_visit) — 客户拜访
47. [dim_lookup_001](#dim_lookup_001) — 通用字典项 001
48. [dim_lookup_002](#dim_lookup_002) — 通用字典项 002
49. [dim_lookup_003](#dim_lookup_003) — 通用字典项 003
50. [dim_lookup_004](#dim_lookup_004) — 通用字典项 004
51. [dim_lookup_005](#dim_lookup_005) — 通用字典项 005
52. [dim_lookup_006](#dim_lookup_006) — 通用字典项 006
53. [dim_lookup_007](#dim_lookup_007) — 通用字典项 007
54. [dim_lookup_008](#dim_lookup_008) — 通用字典项 008
55. [dim_lookup_009](#dim_lookup_009) — 通用字典项 009
56. [dim_lookup_010](#dim_lookup_010) — 通用字典项 010
57. [dim_lookup_011](#dim_lookup_011) — 通用字典项 011
58. [dim_lookup_012](#dim_lookup_012) — 通用字典项 012
59. [dim_lookup_013](#dim_lookup_013) — 通用字典项 013
60. [dim_lookup_014](#dim_lookup_014) — 通用字典项 014
61. [dim_lookup_015](#dim_lookup_015) — 通用字典项 015
62. [dim_lookup_016](#dim_lookup_016) — 通用字典项 016
63. [dim_lookup_017](#dim_lookup_017) — 通用字典项 017
64. [dim_lookup_018](#dim_lookup_018) — 通用字典项 018
65. [dim_lookup_019](#dim_lookup_019) — 通用字典项 019
66. [dim_lookup_020](#dim_lookup_020) — 通用字典项 020
67. [dim_lookup_021](#dim_lookup_021) — 通用字典项 021
68. [dim_lookup_022](#dim_lookup_022) — 通用字典项 022
69. [dim_lookup_023](#dim_lookup_023) — 通用字典项 023
70. [dim_lookup_024](#dim_lookup_024) — 通用字典项 024
71. [dim_lookup_025](#dim_lookup_025) — 通用字典项 025
72. [dim_lookup_026](#dim_lookup_026) — 通用字典项 026
73. [dim_lookup_027](#dim_lookup_027) — 通用字典项 027
74. [dim_lookup_028](#dim_lookup_028) — 通用字典项 028
75. [fin_asset_depr](#fin_asset_depr) — 资产折旧明细
76. [fin_bank_account](#fin_bank_account) — 公司银行账户
77. [fin_bank_txn](#fin_bank_txn) — 银行流水
78. [fin_budget_line](#fin_budget_line) — 预算明细行
79. [fin_budget_year](#fin_budget_year) — 年度预算
80. [fin_cost_allocation](#fin_cost_allocation) — 费用分摊
81. [fin_exchange_rate](#fin_exchange_rate) — 汇率
82. [fin_fixed_asset](#fin_fixed_asset) — 固定资产
83. [fin_gl_account](#fin_gl_account) — 会计科目
84. [fin_invoice](#fin_invoice) — 进销项发票
85. [fin_journal](#fin_journal) — 会计凭证头
86. [fin_journal_line](#fin_journal_line) — 会计凭证分录
87. [fin_loan](#fin_loan) — 对公借款
88. [fin_loan_repay](#fin_loan_repay) — 借款核销
89. [fin_payment](#fin_payment) — 付款单
90. [fin_petty_cash](#fin_petty_cash) — 备用金账户
91. [fin_petty_cash_txn](#fin_petty_cash_txn) — 备用金收支
92. [fin_receipt](#fin_receipt) — 收款单
93. [fin_tax_period](#fin_tax_period) — 税务申报期间
94. [fin_vendor](#fin_vendor) — 供应商主数据
95. [hr_award](#hr_award) — 奖惩记录
96. [hr_bank_account](#hr_bank_account) — 员工薪酬账户
97. [hr_candidate](#hr_candidate) — 候选人
98. [hr_certificate](#hr_certificate) — 员工证书资质
99. [hr_contract](#hr_contract) — 劳动合同
100. [hr_education](#hr_education) — 教育经历
101. [hr_emergency_contact](#hr_emergency_contact) — 紧急联系人
102. [hr_family_member](#hr_family_member) — 员工家属信息
103. [hr_headcount_plan](#hr_headcount_plan) — 编制计划
104. [hr_interview](#hr_interview) — 面试记录
105. [hr_offer](#hr_offer) — 录用 Offer
106. [hr_onboarding](#hr_onboarding) — 入职办理单
107. [hr_performance_cycle](#hr_performance_cycle) — 绩效考核周期
108. [hr_performance_goal](#hr_performance_goal) — 绩效目标
109. [hr_performance_review](#hr_performance_review) — 绩效评估结果
110. [hr_probation](#hr_probation) — 试用期考核
111. [hr_promotion](#hr_promotion) — 晋升记录
112. [hr_recruit_req](#hr_recruit_req) — 招聘需求
113. [hr_resignation](#hr_resignation) — 离职办理
114. [hr_training_course](#hr_training_course) — 培训课程
115. [hr_training_enroll](#hr_training_enroll) — 培训报名
116. [hr_training_session](#hr_training_session) — 培训场次
117. [hr_transfer](#hr_transfer) — 人事调动
118. [hr_work_calendar](#hr_work_calendar) — 工作日历
119. [hr_work_history](#hr_work_history) — 入职前工作经历
120. [itm_access_request](#itm_access_request) — 权限申请
121. [itm_account](#itm_account) — 系统账号
122. [itm_asset](#itm_asset) — IT 资产
123. [itm_asset_assign](#itm_asset_assign) — IT 资产领用归还
124. [itm_change](#itm_change) — 变更单
125. [itm_deploy](#itm_deploy) — 发布部署记录
126. [itm_incident](#itm_incident) — 生产故障
127. [itm_system](#itm_system) — 业务系统台账
128. [itm_ticket](#itm_ticket) — IT 服务工单
129. [itm_ticket_comment](#itm_ticket_comment) — 工单评论
130. [kb_article](#kb_article) — 内部知识文章
131. [kb_article_tag](#kb_article_tag) — 知识标签
132. [kb_article_tag_rel](#kb_article_tag_rel) — 文章标签关系
133. [legal_compliance_check](#legal_compliance_check) — 合规检查
134. [legal_contract](#legal_contract) — 法务合同台账
135. [legal_contract_clause](#legal_contract_clause) — 合同关键条款
136. [legal_dispute](#legal_dispute) — 诉讼/争议案件
137. [mkt_campaign](#mkt_campaign) — 市场活动
138. [mkt_campaign_lead](#mkt_campaign_lead) — 活动获客线索
139. [mkt_content](#mkt_content) — 内容素材
140. [mkt_event_reg](#mkt_event_reg) — 活动报名
141. [ops_backup_job](#ops_backup_job) — 备份任务
142. [ops_duty_roster](#ops_duty_roster) — 值班排班
143. [ops_monitor_alert](#ops_monitor_alert) — 监控告警
144. [ops_runbook](#ops_runbook) — 运维手册
145. [org_announcement](#org_announcement) — 内部公告
146. [org_biz_unit](#org_biz_unit) — 业务单元
147. [org_company](#org_company) — 法人公司
148. [org_cost_center](#org_cost_center) — 成本中心
149. [org_dept_change](#org_dept_change) — 部门变更记录
150. [org_dept_closure](#org_dept_closure) — 部门闭包表（祖先-后代）
151. [org_location](#org_location) — 地理区位
152. [org_office](#org_office) — 办公职场
153. [org_position](#org_position) — 岗位编制
154. [org_seal](#org_seal) — 公司印章台账
155. [prd_feature](#prd_feature) — 产品功能点
156. [prd_license](#prd_license) — 产品授权许可
157. [prd_product_line](#prd_product_line) — 产品线
158. [prd_product_version](#prd_product_version) — 产品版本
159. [prd_roadmap](#prd_roadmap) — 产品路线图项
160. [prj_acceptance](#prj_acceptance) — 项目验收
161. [prj_change_request](#prj_change_request) — 项目变更申请
162. [prj_document](#prj_document) — 项目文档索引
163. [prj_issue](#prj_issue) — 项目问题单
164. [prj_milestone](#prj_milestone) — 项目里程碑
165. [prj_risk](#prj_risk) — 项目风险
166. [prj_stakeholder](#prj_stakeholder) — 项目干系人
167. [prj_task](#prj_task) — 项目任务
168. [prj_warranty](#prj_warranty) — 项目质保
169. [prj_weekly_report](#prj_weekly_report) — 项目周报
170. [qa_defect](#qa_defect) — 缺陷
171. [qa_release_gate](#qa_release_gate) — 发布门禁检查
172. [qa_test_case](#qa_test_case) — 测试用例
173. [qa_test_plan](#qa_test_plan) — 测试计划
174. [sal_channel](#sal_channel) — 销售渠道
175. [sal_commission](#sal_commission) — 销售提成明细
176. [sal_commission_rule](#sal_commission_rule) — 销售提成规则
177. [sal_contract](#sal_contract) — 销售合同
178. [sal_contract_milestone](#sal_contract_milestone) — 合同里程碑收款
179. [sal_delivery](#sal_delivery) — 发货/交付单
180. [sal_delivery_item](#sal_delivery_item) — 交付明细
181. [sal_price_list](#sal_price_list) — 价格表
182. [sal_price_list_item](#sal_price_list_item) — 价格表明细
183. [sal_quote](#sal_quote) — 销售报价单
184. [sal_quote_item](#sal_quote_item) — 报价明细
185. [sal_return](#sal_return) — 退货单
186. [sal_target](#sal_target) — 销售目标
187. [scm_inventory](#scm_inventory) — 库存台账
188. [scm_inventory_txn](#scm_inventory_txn) — 库存流水
189. [scm_material](#scm_material) — 物料主数据
190. [scm_purchase_order](#scm_purchase_order) — 采购订单
191. [scm_purchase_order_item](#scm_purchase_order_item) — 采购订单明细
192. [scm_purchase_req](#scm_purchase_req) — 采购申请
193. [scm_purchase_req_item](#scm_purchase_req_item) — 采购申请明细
194. [scm_receipt](#scm_receipt) — 采购入库单
195. [scm_vendor_eval](#scm_vendor_eval) — 供应商评价
196. [scm_warehouse](#scm_warehouse) — 仓库
197. [sec_audit_log](#sec_audit_log) — 安全审计日志
198. [sec_data_class](#sec_data_class) — 数据分级分类
199. [sec_policy](#sec_policy) — 安全策略
200. [sec_vulnerability](#sec_vulnerability) — 漏洞台账

## org_department

组织部门表
id bigint 主键|dept_code varchar(32) 部门编码|dept_name varchar(64) 部门名称|parent_id bigint 上级部门 ID，根部门为空|manager_emp_id bigint 部门负责人员工 ID|status smallint 部门状态|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dept_code | 部门编码（业务唯一） | `varchar(32)` | 是 | - | 否 |
| dept_name | 部门名称 | `varchar(64)` | 是 | - | 否 |
| parent_id | 上级部门 ID，根部门为空 | `bigint` | 否 | - | 否 |
| manager_emp_id | 部门负责人员工 ID | `bigint` | 否 | - | 否 |
| status | 部门状态：`1`=有效 | `smallint` | 是 | 1 | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_job_level

职级字典表
id bigint 主键|level_code varchar(16) 职级编码|level_name varchar(32) 职级名称|rank_no integer 职级排序号，数值越大级别越高

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| level_code | 职级编码（如 P1/P2/M1） | `varchar(16)` | 是 | - | 否 |
| level_name | 职级名称 | `varchar(32)` | 是 | - | 否 |
| rank_no | 职级排序号，数值越大级别越高 | `integer` | 是 | - | 否 |

## hr_employee

员工主数据表
id bigint 主键|emp_no varchar(32) 工号|name varchar(64) 姓名|gender char(1) 性别|dept_id bigint 所属部门 ID|job_level_id bigint 职级 ID|title varchar(64) 职位名称|hire_date date 入职日期|leave_date date 离职日期|employment_status varchar(16) 人事状态|email varchar(128) 邮箱|phone varchar(32) 手机号|base_city varchar(32) 常驻城市|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_no | 工号（业务键，唯一） | `varchar(32)` | 是 | - | 否 |
| name | 姓名 | `varchar(64)` | 是 | - | 否 |
| gender | 性别：`M`=男、`F`=女；允许空 | `char(1)` | 否 | - | 否 |
| dept_id | 所属部门 ID | `bigint` | 否 | - | 否 |
| job_level_id | 职级 ID，关联 hr_job_level | `bigint` | 否 | - | 否 |
| title | 职位名称 | `varchar(64)` | 否 | - | 否 |
| hire_date | 入职日期 | `date` | 是 | - | 否 |
| leave_date | 离职日期；在职通常为空。判断是否在岗优先看本字段，勿仅依赖 employment_status | `date` | 否 | - | 否 |
| employment_status | 人事状态：`active`=在职、`resigned`=离职（库中存在 leave_date 非空但本字段仍为 active 的冲突行） | `varchar(16)` | 是 | active | 否 |
| email | 邮箱 | `varchar(128)` | 否 | - | 否 |
| phone | 手机号 | `varchar(32)` | 否 | - | 否 |
| base_city | 常驻城市 | `varchar(32)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_leave_type

请假类型字典
id bigint 主键|type_code varchar(32) 请假类型编码|type_name varchar(64) 请假类型名称|is_paid boolean 是否带薪|deduct_attendance boolean 是否扣考勤

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| type_code | 请假类型编码：`annual`=年假、`sick`=病假、`personal`=事假、`marriage`=婚假、`maternity`=产假、`compensatory`=调休 | `varchar(32)` | 是 | - | 否 |
| type_name | 请假类型名称 | `varchar(64)` | 是 | - | 否 |
| is_paid | 是否带薪：`true`=带薪、`false`=不带薪 | `boolean` | 是 | true | 否 |
| deduct_attendance | 是否扣考勤：`true`=扣考勤、`false`=不扣 | `boolean` | 是 | true | 否 |

## att_leave

请假单
id bigint 主键|emp_id bigint 请假员工 ID|leave_type_id bigint 请假类型 ID|start_at timestamp 请假开始时间|end_at timestamp 请假结束时间|leave_days numeric(6,2) 请假天数|reason varchar(256) 请假事由|status varchar(16) 审批状态|approved_by bigint 审批人员工 ID|approved_at timestamp 审批时间|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 请假员工 ID | `bigint` | 是 | - | 否 |
| leave_type_id | 请假类型 ID，关联 att_leave_type；允许空（脏数据） | `bigint` | 否 | - | 否 |
| start_at | 请假开始时间 | `timestamp` | 是 | - | 否 |
| end_at | 请假结束时间 | `timestamp` | 是 | - | 否 |
| leave_days | 请假天数（可含半天） | `numeric(6,2)` | 否 | - | 否 |
| reason | 请假事由 | `varchar(256)` | 否 | - | 否 |
| status | 审批状态：`draft`=草稿、`approved`=已通过、`rejected`=已驳回、`cancelled`=已取消 | `varchar(16)` | 是 | approved | 否 |
| approved_by | 审批人员工 ID | `bigint` | 否 | - | 否 |
| approved_at | 审批时间 | `timestamp` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_overtime

加班申请记录
id bigint 主键|emp_id bigint 加班员工 ID|project_id bigint 关联项目 ID，可空|overtime_date date 加班日期|start_at timestamp 加班开始时间|end_at timestamp 加班结束时间|hours numeric(6,2) 加班小时数|ot_type varchar(16) 加班类型|compensate_type varchar(16) 补偿方式|status varchar(16) 审批状态|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 加班员工 ID | `bigint` | 是 | - | 否 |
| project_id | 关联项目 ID，可空 | `bigint` | 否 | - | 否 |
| overtime_date | 加班日期 | `date` | 是 | - | 否 |
| start_at | 加班开始时间 | `timestamp` | 否 | - | 否 |
| end_at | 加班结束时间 | `timestamp` | 否 | - | 否 |
| hours | 加班小时数 | `numeric(6,2)` | 否 | - | 否 |
| ot_type | 加班类型：`workday`=工作日加班、`weekend`=周末加班、`holiday`=节假日加班 | `varchar(16)` | 否 | - | 否 |
| compensate_type | 补偿方式：`pay`=加班费、`leave`=调休 | `varchar(16)` | 否 | - | 否 |
| status | 审批状态：`draft`=草稿、`approved`=已通过、`rejected`=已驳回 | `varchar(16)` | 是 | approved | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_daily_record

日考勤结果
id bigint 主键|emp_id bigint 员工 ID|work_date date 考勤日期|check_in_at timestamp 签到时间|check_out_at timestamp 签退时间|work_hours numeric(6,2) 出勤工时|late_minutes integer 迟到分钟数|early_leave_minutes integer 早退分钟数|attendance_status varchar(16) 当日考勤状态|source varchar(16) 数据来源|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| work_date | 考勤日期 | `date` | 是 | - | 否 |
| check_in_at | 签到时间 | `timestamp` | 否 | - | 否 |
| check_out_at | 签退时间 | `timestamp` | 否 | - | 否 |
| work_hours | 出勤工时（小时） | `numeric(6,2)` | 否 | - | 否 |
| late_minutes | 迟到分钟数 | `integer` | 否 | - | 否 |
| early_leave_minutes | 早退分钟数 | `integer` | 否 | - | 否 |
| attendance_status | 当日考勤状态：`normal`=正常、`late`=迟到、`early`=早退、`leave`=请假、`absent`=缺勤 | `varchar(16)` | 否 | - | 否 |
| source | 数据来源：`device`=打卡设备、`manual`=手工补录 | `varchar(16)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_timesheet

项目工时填报
id bigint 主键|emp_id bigint 填报员工 ID|project_id bigint 项目 ID，可空|work_date date 填报日期|hours numeric(6,2) 填报工时|work_type varchar(16) 工时类型|remark varchar(256) 备注|status varchar(16) 审批状态|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 填报员工 ID | `bigint` | 是 | - | 否 |
| project_id | 项目 ID，可空 | `bigint` | 否 | - | 否 |
| work_date | 填报日期 | `date` | 是 | - | 否 |
| hours | 填报工时（小时） | `numeric(6,2)` | 是 | - | 否 |
| work_type | 工时类型：`develop`=开发、`test`=测试、`implement`=实施、`support`=支持、`manage`=管理 | `varchar(16)` | 否 | - | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| status | 审批状态：`draft`=草稿、`submitted`=已提交、`approved`=已通过 | `varchar(16)` | 是 | approved | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_salary_period

薪资结算期间
id bigint 主键|period_code varchar(16) 薪资月编码，格式 YYYY-MM|year_month date 所属年月|pay_date date 发薪日期|status varchar(16) 期间状态

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| period_code | 薪资月编码，格式 YYYY-MM | `varchar(16)` | 是 | - | 否 |
| year_month | 所属年月（取月首日） | `date` | 是 | - | 否 |
| pay_date | 发薪日期 | `date` | 否 | - | 否 |
| status | 期间状态：`open`=开放（未关账）、`closed`=已关账 | `varchar(16)` | 是 | closed | 否 |

## fin_salary_slip

工资条
id bigint 主键|period_id bigint 薪资期间 ID|emp_id bigint 员工 ID|dept_id bigint 发薪时部门 ID|base_salary numeric(12,2) 基本工资|allowance numeric(12,2) 津贴|overtime_pay numeric(12,2) 加班费|bonus numeric(12,2) 奖金|social_security_personal numeric(12,2) 个人社保扣款|housing_fund_personal numeric(12,2) 个人公积金扣款|tax numeric(12,2) 个人所得税|other_deduction numeric(12,2) 其他扣款|net_pay numeric(12,2) 实发合计|currency varchar(8) 币种|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| period_id | 薪资期间 ID，关联 fin_salary_period | `bigint` | 是 | - | 否 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| dept_id | 发薪时部门 ID | `bigint` | 否 | - | 否 |
| base_salary | 基本工资 | `numeric(12,2)` | 否 | - | 否 |
| allowance | 津贴 | `numeric(12,2)` | 否 | - | 否 |
| overtime_pay | 加班费 | `numeric(12,2)` | 否 | - | 否 |
| bonus | 奖金 | `numeric(12,2)` | 否 | - | 否 |
| social_security_personal | 个人社保扣款 | `numeric(12,2)` | 否 | - | 否 |
| housing_fund_personal | 个人公积金扣款 | `numeric(12,2)` | 否 | - | 否 |
| tax | 个人所得税 | `numeric(12,2)` | 否 | - | 否 |
| other_deduction | 其他扣款 | `numeric(12,2)` | 否 | - | 否 |
| net_pay | 实发合计 | `numeric(12,2)` | 否 | - | 否 |
| currency | 币种：`CNY`=人民币 | `varchar(8)` | 否 | CNY | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_reimburse

报销单头表
id bigint 主键|claim_no varchar(32) 报销单号|emp_id bigint 提单人员工 ID|dept_id bigint 费用归属部门 ID|project_id bigint 关联项目 ID，可空|claim_date date 报销申请日期|title varchar(128) 报销标题|total_amount numeric(12,2) 报销头表金额|status varchar(16) 报销状态|paid_at timestamp 付款时间|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| claim_no | 报销单号（业务键，唯一） | `varchar(32)` | 是 | - | 否 |
| emp_id | 提单人员工 ID | `bigint` | 是 | - | 否 |
| dept_id | 费用归属部门 ID | `bigint` | 否 | - | 否 |
| project_id | 关联项目 ID，可空 | `bigint` | 否 | - | 否 |
| claim_date | 报销申请日期（统计报销时间范围用本字段，不用 paid_at） | `date` | 是 | - | 否 |
| title | 报销标题 | `varchar(128)` | 否 | - | 否 |
| total_amount | 报销头表金额（单据总额口径） | `numeric(12,2)` | 否 | - | 否 |
| status | 报销状态：`draft`=草稿、`submitted`=已提交、`approved`=已通过、`rejected`=已驳回、`paid`=已付款 | `varchar(16)` | 是 | approved | 否 |
| paid_at | 付款时间；仅 status=paid 时通常有值 | `timestamp` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_reimburse_item

报销单明细
id bigint 主键|claim_id bigint 报销单头 ID|category varchar(32) 费用类别|amount numeric(12,2) 明细金额|occur_date date 费用发生日|invoice_no varchar(64) 发票号|remark varchar(256) 备注

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| claim_id | 报销单头 ID，关联 fin_reimburse | `bigint` | 是 | - | 否 |
| category | 费用类别：`travel`=差旅、`meal`=餐费、`traffic`=交通、`office`=办公、`entertainment`=招待、`training`=培训 | `varchar(32)` | 否 | - | 否 |
| amount | 明细金额 | `numeric(12,2)` | 否 | - | 否 |
| occur_date | 费用发生日 | `date` | 否 | - | 否 |
| invoice_no | 发票号 | `varchar(64)` | 否 | - | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |

## fin_activity_budget

部门活动预算
id bigint 主键|activity_code varchar(32) 活动编码|activity_name varchar(128) 活动名称|dept_id bigint 归属部门 ID|owner_emp_id bigint 活动负责人员工 ID|year integer 预算年度|budget_amount numeric(12,2) 预算金额|status varchar(16) 预算状态|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| activity_code | 活动编码（业务唯一） | `varchar(32)` | 是 | - | 否 |
| activity_name | 活动名称 | `varchar(128)` | 是 | - | 否 |
| dept_id | 归属部门 ID | `bigint` | 否 | - | 否 |
| owner_emp_id | 活动负责人员工 ID | `bigint` | 否 | - | 否 |
| year | 预算年度 | `integer` | 是 | - | 否 |
| budget_amount | 预算金额 | `numeric(12,2)` | 否 | - | 否 |
| status | 预算状态：`planned`=已规划、`ongoing`=进行中、`closed`=已关闭 | `varchar(16)` | 是 | ongoing | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_activity_expense

部门活动花费
id bigint 主键|budget_id bigint 活动预算 ID|expense_date date 花费日期|category varchar(32) 花费类别|amount numeric(12,2) 花费金额|payee varchar(128) 收款方|remark varchar(256) 备注|status varchar(16) 状态|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| budget_id | 活动预算 ID，关联 fin_activity_budget | `bigint` | 是 | - | 否 |
| expense_date | 花费日期 | `date` | 是 | - | 否 |
| category | 花费类别：`catering`=餐饮、`venue`=场地、`gift`=礼品、`transport`=交通、`other`=其他 | `varchar(32)` | 否 | - | 否 |
| amount | 花费金额 | `numeric(12,2)` | 否 | - | 否 |
| payee | 收款方 | `varchar(128)` | 否 | - | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| status | 状态：`draft`=草稿、`approved`=已通过、`paid`=已付款 | `varchar(16)` | 是 | paid | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## crm_customer

客户主数据
id bigint 主键|customer_code varchar(32) 客户编码|customer_name varchar(128) 客户名称|industry varchar(64) 所属行业|region varchar(32) 区域|customer_level varchar(8) 客户等级|owner_emp_id bigint 销售负责人员工 ID|status varchar(16) 客户状态|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| customer_code | 客户编码（业务键，唯一） | `varchar(32)` | 是 | - | 否 |
| customer_name | 客户名称 | `varchar(128)` | 是 | - | 否 |
| industry | 所属行业 | `varchar(64)` | 否 | - | 否 |
| region | 区域 | `varchar(32)` | 否 | - | 否 |
| customer_level | 客户等级：`A`=战略大客户、`B`=重要客户、`C`=普通客户 | `varchar(8)` | 否 | - | 否 |
| owner_emp_id | 销售负责人员工 ID | `bigint` | 否 | - | 否 |
| status | 客户状态：`active`=合作中、`churned`=已流失 | `varchar(16)` | 是 | active | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prd_product

产品主数据
id bigint 主键|product_code varchar(32) 产品编码|product_name varchar(128) 产品名称|product_line varchar(64) 产品线|pricing_model varchar(32) 计价模式|list_price numeric(12,2) 目录价|unit varchar(16) 计量单位|status varchar(16) 产品状态|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| product_code | 产品编码（业务键，唯一） | `varchar(32)` | 是 | - | 否 |
| product_name | 产品名称 | `varchar(128)` | 是 | - | 否 |
| product_line | 产品线 | `varchar(64)` | 否 | - | 否 |
| pricing_model | 计价模式：`subscription`=订阅、`license`=授权买断、`project`=项目制 | `varchar(32)` | 否 | - | 否 |
| list_price | 目录价 | `numeric(12,2)` | 否 | - | 否 |
| unit | 计量单位（如套/年、套、人月、场） | `varchar(16)` | 否 | - | 否 |
| status | 产品状态：`on_sale`=在售、`off`=停售 | `varchar(16)` | 是 | on_sale | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prd_product_cost

产品月度成本
id bigint 主键|product_id bigint 产品 ID|year_month date 成本年月|unit_cost numeric(12,2) 单位成本|cost_type varchar(32) 成本类型|remark varchar(256) 备注

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| product_id | 产品 ID，关联 prd_product | `bigint` | 是 | - | 否 |
| year_month | 成本年月（取月首日） | `date` | 是 | - | 否 |
| unit_cost | 单位成本 | `numeric(12,2)` | 否 | - | 否 |
| cost_type | 成本类型：`license_cost`=授权成本、`cloud`=云资源成本、`support`=支持成本、`other`=其他 | `varchar(32)` | 否 | - | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |

## sal_sales_order

销售订单头表
id bigint 主键|order_no varchar(32) 订单号|customer_id bigint 客户 ID|owner_emp_id bigint 销售负责人员工 ID|dept_id bigint 销售部门 ID|order_date date 下单日期|sign_date date 签约日期|currency varchar(8) 币种|total_amount numeric(14,2) 订单头金额|status varchar(16) 订单状态|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| order_no | 订单号（业务键，唯一） | `varchar(32)` | 是 | - | 否 |
| customer_id | 客户 ID，关联 crm_customer | `bigint` | 否 | - | 否 |
| owner_emp_id | 销售负责人员工 ID | `bigint` | 否 | - | 否 |
| dept_id | 销售部门 ID | `bigint` | 否 | - | 否 |
| order_date | 下单日期 | `date` | 否 | - | 否 |
| sign_date | 签约日期 | `date` | 否 | - | 否 |
| currency | 币种：`CNY`=人民币 | `varchar(8)` | 否 | CNY | 否 |
| total_amount | 订单头金额 | `numeric(14,2)` | 否 | - | 否 |
| status | 订单状态：`draft`=草稿、`signed`=已签约、`delivering`=交付中、`closed`=已关闭、`cancelled`=已取消；有效订单通常排除 cancelled/draft | `varchar(16)` | 是 | signed | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_sales_order_item

销售订单明细
id bigint 主键|order_id bigint 订单头 ID|product_id bigint 产品 ID|qty numeric(12,2) 数量|unit_price numeric(12,2) 单价|discount_rate numeric(6,4) 折扣率|amount numeric(14,2) 行金额|cost_amount numeric(14,2) 行成本金额

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| order_id | 订单头 ID，关联 sal_sales_order | `bigint` | 是 | - | 否 |
| product_id | 产品 ID，关联 prd_product | `bigint` | 否 | - | 否 |
| qty | 数量 | `numeric(12,2)` | 否 | - | 否 |
| unit_price | 单价 | `numeric(12,2)` | 否 | - | 否 |
| discount_rate | 折扣率（0~1，如 0.1 表示九折） | `numeric(6,4)` | 否 | - | 否 |
| amount | 行金额（折后） | `numeric(14,2)` | 否 | - | 否 |
| cost_amount | 行成本金额 | `numeric(14,2)` | 否 | - | 否 |

## prj_project

交付项目
id bigint 主键|project_code varchar(32) 项目编号|project_name varchar(128) 项目名称|customer_id bigint 客户 ID|project_type varchar(32) 项目类型|dept_id bigint 承接部门 ID|pm_emp_id bigint 项目经理员工 ID|start_date date 实际/立项开始日期|end_date date 实际结束日期|plan_end_date date 计划结束日期|contract_amount numeric(14,2) 合同金额|status varchar(16) 项目状态|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_code | 项目编号（业务键，唯一） | `varchar(32)` | 是 | - | 否 |
| project_name | 项目名称 | `varchar(128)` | 是 | - | 否 |
| customer_id | 客户 ID，关联 crm_customer | `bigint` | 否 | - | 否 |
| project_type | 项目类型：`implementation`=实施交付、`custom_dev`=定制开发、`ops`=运维托管、`poc`=POC 验证 | `varchar(32)` | 否 | - | 否 |
| dept_id | 承接部门 ID | `bigint` | 否 | - | 否 |
| pm_emp_id | 项目经理员工 ID | `bigint` | 否 | - | 否 |
| start_date | 实际/立项开始日期 | `date` | 否 | - | 否 |
| end_date | 实际结束日期；进行中可空 | `date` | 否 | - | 否 |
| plan_end_date | 计划结束日期 | `date` | 否 | - | 否 |
| contract_amount | 合同金额 | `numeric(14,2)` | 否 | - | 否 |
| status | 项目状态：`planning`=规划中、`active`=进行中、`closed`=已结项、`warranty`=质保中 | `varchar(16)` | 是 | active | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prj_project_member

项目成员
id bigint 主键|project_id bigint 项目 ID|emp_id bigint 成员员工 ID|role varchar(32) 项目角色|join_date date 加入项目日期|leave_date date 离开项目日期|allocation_pct numeric(6,2) 投入占比

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_id | 项目 ID，关联 prj_project | `bigint` | 是 | - | 否 |
| emp_id | 成员员工 ID | `bigint` | 是 | - | 否 |
| role | 项目角色：`pm`=项目经理、`dev`=开发、`qa`=测试、`implement`=实施、`support`=支持 | `varchar(32)` | 否 | - | 否 |
| join_date | 加入项目日期 | `date` | 否 | - | 否 |
| leave_date | 离开项目日期；仍在项目中可空 | `date` | 否 | - | 否 |
| allocation_pct | 投入占比（百分比，如 50 表示 50%） | `numeric(6,2)` | 否 | - | 否 |

## prj_project_revenue

项目回款记录
id bigint 主键|project_id bigint 项目 ID|revenue_date date 回款/收入确认日期|revenue_type varchar(32) 回款类型|amount numeric(14,2) 应回/确认金额|received_amount numeric(14,2) 已到账金额|invoice_no varchar(64) 发票号|remark varchar(256) 备注|created_at timestamp 创建时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_id | 项目 ID，关联 prj_project | `bigint` | 是 | - | 否 |
| revenue_date | 回款/收入确认日期 | `date` | 是 | - | 否 |
| revenue_type | 回款类型：`milestone`=里程碑款、`acceptance`=验收款、`monthly`=按月确认、`final`=尾款 | `varchar(32)` | 否 | - | 否 |
| amount | 应回/确认金额 | `numeric(14,2)` | 否 | - | 否 |
| received_amount | 已到账金额 | `numeric(14,2)` | 否 | - | 否 |
| invoice_no | 发票号 | `varchar(64)` | 否 | - | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## adm_meeting_booking

会议室预订
id bigint 主键|room_id bigint 会议室 ID|organizer_emp_id bigint 组织者员工 ID|start_at timestamp 开始时间|end_at timestamp 结束时间|title varchar(256) 会议主题|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| room_id | 会议室 ID | `bigint` | 是 | - | 否 |
| organizer_emp_id | 组织者员工 ID | `bigint` | 否 | - | 否 |
| start_at | 开始时间 | `timestamp` | 否 | - | 否 |
| end_at | 结束时间 | `timestamp` | 否 | - | 否 |
| title | 会议主题 | `varchar(256)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## adm_meeting_room

会议室
id bigint 主键|room_code varchar(32) 会议室编码|room_name varchar(128) 会议室名称|office_id bigint 职场 ID|capacity integer 可容纳人数|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| room_code | 会议室编码 | `varchar(32)` | 是 | - | 否 |
| room_name | 会议室名称 | `varchar(128)` | 是 | - | 否 |
| office_id | 职场 ID | `bigint` | 否 | - | 否 |
| capacity | 可容纳人数 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## adm_supply

办公用品
id bigint 主键|supply_code varchar(32) 用品编码|supply_name varchar(128) 用品名称|uom varchar(16) 单位|unit_cost numeric(12,2) 单价|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| supply_code | 用品编码 | `varchar(32)` | 是 | - | 否 |
| supply_name | 用品名称 | `varchar(128)` | 是 | - | 否 |
| uom | 单位 | `varchar(16)` | 否 | - | 否 |
| unit_cost | 单价 | `numeric(12,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## adm_supply_request

办公用品领用
id bigint 主键|supply_id bigint 用品 ID|emp_id bigint 领用人员工 ID|qty numeric(12,2) 数量|request_date date 领用日期|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| supply_id | 用品 ID | `bigint` | 是 | - | 否 |
| emp_id | 领用人员工 ID | `bigint` | 是 | - | 否 |
| qty | 数量 | `numeric(12,2)` | 否 | - | 否 |
| request_date | 领用日期 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## adm_vehicle

公务车
id bigint 主键|vehicle_code varchar(32) 车牌/编码|vehicle_name varchar(128) 车辆名称|plate_no varchar(16) 车牌号|seat_count integer 座位数|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| vehicle_code | 车牌/编码 | `varchar(32)` | 是 | - | 否 |
| vehicle_name | 车辆名称 | `varchar(128)` | 是 | - | 否 |
| plate_no | 车牌号 | `varchar(16)` | 否 | - | 否 |
| seat_count | 座位数 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## adm_vehicle_trip

用车记录
id bigint 主键|vehicle_id bigint 车辆 ID|driver_emp_id bigint 驾驶人员工 ID|start_at timestamp 出车时间|end_at timestamp 收车时间|destination varchar(128) 目的地|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| vehicle_id | 车辆 ID | `bigint` | 是 | - | 否 |
| driver_emp_id | 驾驶人员工 ID | `bigint` | 否 | - | 否 |
| start_at | 出车时间 | `timestamp` | 否 | - | 否 |
| end_at | 收车时间 | `timestamp` | 否 | - | 否 |
| destination | 目的地 | `varchar(128)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## adm_visitor

访客登记
id bigint 主键|visitor_name varchar(64) 访客姓名|host_emp_id bigint 接待员工 ID|visit_date date 来访日期|purpose varchar(256) 事由|office_id bigint 职场 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| visitor_name | 访客姓名 | `varchar(64)` | 否 | - | 否 |
| host_emp_id | 接待员工 ID | `bigint` | 否 | - | 否 |
| visit_date | 来访日期 | `date` | 否 | - | 否 |
| purpose | 事由 | `varchar(256)` | 否 | - | 否 |
| office_id | 职场 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_device

考勤设备
id bigint 主键|device_code varchar(32) 设备编码|device_name varchar(128) 设备名称|office_id bigint 职场 ID|ip_addr varchar(64) IP|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| device_code | 设备编码 | `varchar(32)` | 是 | - | 否 |
| device_name | 设备名称 | `varchar(128)` | 是 | - | 否 |
| office_id | 职场 ID | `bigint` | 否 | - | 否 |
| ip_addr | IP | `varchar(64)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_leave_balance

假期余额
id bigint 主键|emp_id bigint 员工 ID|leave_type_id bigint 请假类型 ID|year integer 年度|balance_days numeric(8,2) 剩余天数|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| leave_type_id | 请假类型 ID | `bigint` | 是 | - | 否 |
| year | 年度 | `integer` | 否 | - | 否 |
| balance_days | 剩余天数 | `numeric(8,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_makeup_card

补卡申请
id bigint 主键|emp_id bigint 员工 ID|work_date date 日期|punch_type varchar(16) 补卡类型|reason varchar(256) 事由|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| work_date | 日期 | `date` | 否 | - | 否 |
| punch_type | 补卡类型 | `varchar(16)` | 否 | - | 否 |
| reason | 事由 | `varchar(256)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_monthly_summary

月考勤汇总
id bigint 主键|emp_id bigint 员工 ID|year_month varchar(7) 年月|work_days numeric(8,2) 出勤天|leave_days numeric(8,2) 请假天|ot_hours numeric(8,2) 加班小时|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| year_month | 年月 | `varchar(7)` | 否 | - | 否 |
| work_days | 出勤天 | `numeric(8,2)` | 否 | - | 否 |
| leave_days | 请假天 | `numeric(8,2)` | 否 | - | 否 |
| ot_hours | 加班小时 | `numeric(8,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_ot_rule

加班规则
id bigint 主键|rule_code varchar(32) 规则编码|rule_name varchar(128) 规则名称|weekday_rate numeric(6,2) 工作日倍率|weekend_rate numeric(6,2) 周末倍率|holiday_rate numeric(6,2) 节假日倍率|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| rule_code | 规则编码 | `varchar(32)` | 是 | - | 否 |
| rule_name | 规则名称 | `varchar(128)` | 是 | - | 否 |
| weekday_rate | 工作日倍率 | `numeric(6,2)` | 否 | - | 否 |
| weekend_rate | 周末倍率 | `numeric(6,2)` | 否 | - | 否 |
| holiday_rate | 节假日倍率 | `numeric(6,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_punch

打卡流水
id bigint 主键|emp_id bigint 员工 ID|punch_at timestamp 打卡时间|punch_type varchar(16) 打卡类型|device_no varchar(64) 设备号|office_id bigint 职场 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| punch_at | 打卡时间 | `timestamp` | 是 | - | 否 |
| punch_type | 打卡类型 | `varchar(16)` | 否 | - | 否 |
| device_no | 设备号 | `varchar(64)` | 否 | - | 否 |
| office_id | 职场 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_remote_work

居家办公申请
id bigint 主键|emp_id bigint 员工 ID|work_date date 日期|reason varchar(256) 事由|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| work_date | 日期 | `date` | 否 | - | 否 |
| reason | 事由 | `varchar(256)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_shift

班次定义
id bigint 主键|shift_code varchar(32) 班次编码|shift_name varchar(128) 班次名称|start_time time 上班时间|end_time time 下班时间|break_minutes integer 休息分钟|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| shift_code | 班次编码 | `varchar(32)` | 是 | - | 否 |
| shift_name | 班次名称 | `varchar(128)` | 是 | - | 否 |
| start_time | 上班时间 | `time` | 否 | - | 否 |
| end_time | 下班时间 | `time` | 否 | - | 否 |
| break_minutes | 休息分钟 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_shift_assign

班次排班
id bigint 主键|emp_id bigint 员工 ID|shift_id bigint 班次 ID|work_date date 日期|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| shift_id | 班次 ID | `bigint` | 是 | - | 否 |
| work_date | 日期 | `date` | 是 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## att_travel

出差申请
id bigint 主键|emp_id bigint 员工 ID|start_date date 开始日期|end_date date 结束日期|destination varchar(128) 目的地|project_id bigint 关联项目 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| start_date | 开始日期 | `date` | 否 | - | 否 |
| end_date | 结束日期 | `date` | 否 | - | 否 |
| destination | 目的地 | `varchar(128)` | 否 | - | 否 |
| project_id | 关联项目 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## crm_activity

客户跟进活动
id bigint 主键|customer_id bigint 客户 ID|opp_id bigint 商机 ID|emp_id bigint 跟进人员工 ID|activity_type varchar(32) 活动类型|activity_at timestamp 活动时间|content text 内容|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| customer_id | 客户 ID | `bigint` | 否 | - | 否 |
| opp_id | 商机 ID | `bigint` | 否 | - | 否 |
| emp_id | 跟进人员工 ID | `bigint` | 否 | - | 否 |
| activity_type | 活动类型 | `varchar(32)` | 否 | - | 否 |
| activity_at | 活动时间 | `timestamp` | 否 | - | 否 |
| content | 内容 | `text` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## crm_complaint

客户投诉
id bigint 主键|customer_id bigint 客户 ID|project_id bigint 项目 ID|title varchar(256) 标题|severity_level varchar(16) 严重级别|handler_emp_id bigint 处理人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| customer_id | 客户 ID | `bigint` | 是 | - | 否 |
| project_id | 项目 ID | `bigint` | 否 | - | 否 |
| title | 标题 | `varchar(256)` | 否 | - | 否 |
| severity_level | 严重级别 | `varchar(16)` | 否 | - | 否 |
| handler_emp_id | 处理人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## crm_contact

客户联系人
id bigint 主键|customer_id bigint 客户 ID|contact_name varchar(64) 联系人姓名|title varchar(64) 职务|phone varchar(32) 电话|email varchar(128) 邮箱|is_primary boolean 是否主联系人|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| customer_id | 客户 ID | `bigint` | 是 | - | 否 |
| contact_name | 联系人姓名 | `varchar(64)` | 否 | - | 否 |
| title | 职务 | `varchar(64)` | 否 | - | 否 |
| phone | 电话 | `varchar(32)` | 否 | - | 否 |
| email | 邮箱 | `varchar(128)` | 否 | - | 否 |
| is_primary | 是否主联系人 | `boolean` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## crm_lead

销售线索
id bigint 主键|lead_code varchar(32) 线索编码|lead_name varchar(128) 线索名称|source varchar(32) 来源|owner_emp_id bigint 负责销售员工 ID|customer_id bigint 转化客户 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| lead_code | 线索编码 | `varchar(32)` | 是 | - | 否 |
| lead_name | 线索名称 | `varchar(128)` | 是 | - | 否 |
| source | 来源 | `varchar(32)` | 否 | - | 否 |
| owner_emp_id | 负责销售员工 ID | `bigint` | 否 | - | 否 |
| customer_id | 转化客户 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## crm_opportunity

商机
id bigint 主键|opp_code varchar(32) 商机编码|opp_name varchar(128) 商机名称|customer_id bigint 客户 ID|owner_emp_id bigint 负责销售员工 ID|amount numeric(14,2) 预计金额|stage varchar(32) 阶段|close_date date 预计成交日|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| opp_code | 商机编码 | `varchar(32)` | 是 | - | 否 |
| opp_name | 商机名称 | `varchar(128)` | 是 | - | 否 |
| customer_id | 客户 ID | `bigint` | 否 | - | 否 |
| owner_emp_id | 负责销售员工 ID | `bigint` | 否 | - | 否 |
| amount | 预计金额 | `numeric(14,2)` | 否 | - | 否 |
| stage | 阶段 | `varchar(32)` | 否 | - | 否 |
| close_date | 预计成交日 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## crm_sla

客户服务等级协议
id bigint 主键|customer_id bigint 客户 ID|sla_level varchar(16) SLA 等级|response_hours integer 响应时限小时|resolve_hours integer 解决时限小时|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| customer_id | 客户 ID | `bigint` | 是 | - | 否 |
| sla_level | SLA 等级 | `varchar(16)` | 否 | - | 否 |
| response_hours | 响应时限小时 | `integer` | 否 | - | 否 |
| resolve_hours | 解决时限小时 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## crm_visit

客户拜访
id bigint 主键|customer_id bigint 客户 ID|emp_id bigint 拜访人员工 ID|visit_date date 拜访日期|purpose varchar(256) 目的|result varchar(256) 结果|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| customer_id | 客户 ID | `bigint` | 是 | - | 否 |
| emp_id | 拜访人员工 ID | `bigint` | 否 | - | 否 |
| visit_date | 拜访日期 | `date` | 否 | - | 否 |
| purpose | 目的 | `varchar(256)` | 否 | - | 否 |
| result | 结果 | `varchar(256)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_001

通用字典项 001
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_002

通用字典项 002
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_003

通用字典项 003
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_004

通用字典项 004
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_005

通用字典项 005
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_006

通用字典项 006
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_007

通用字典项 007
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_008

通用字典项 008
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_009

通用字典项 009
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_010

通用字典项 010
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_011

通用字典项 011
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_012

通用字典项 012
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_013

通用字典项 013
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_014

通用字典项 014
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_015

通用字典项 015
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_016

通用字典项 016
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_017

通用字典项 017
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_018

通用字典项 018
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_019

通用字典项 019
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_020

通用字典项 020
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_021

通用字典项 021
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_022

通用字典项 022
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_023

通用字典项 023
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_024

通用字典项 024
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_025

通用字典项 025
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_026

通用字典项 026
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_027

通用字典项 027
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## dim_lookup_028

通用字典项 028
id bigint 主键|dict_code varchar(32) 字典编码|dict_name varchar(128) 字典名称|dict_group varchar(64) 字典分组|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dict_code | 字典编码 | `varchar(32)` | 是 | - | 否 |
| dict_name | 字典名称 | `varchar(128)` | 是 | - | 否 |
| dict_group | 字典分组 | `varchar(64)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_asset_depr

资产折旧明细
id bigint 主键|asset_id bigint 资产 ID|year_month varchar(7) 年月|depr_amount numeric(14,2) 折旧额|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| asset_id | 资产 ID | `bigint` | 是 | - | 否 |
| year_month | 年月 | `varchar(7)` | 否 | - | 否 |
| depr_amount | 折旧额 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_bank_account

公司银行账户
id bigint 主键|acct_code varchar(32) 账户编码|acct_name varchar(128) 账户名称|bank_name varchar(64) 开户行|account_no varchar(64) 账号|company_id bigint 所属公司 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| acct_code | 账户编码 | `varchar(32)` | 是 | - | 否 |
| acct_name | 账户名称 | `varchar(128)` | 是 | - | 否 |
| bank_name | 开户行 | `varchar(64)` | 否 | - | 否 |
| account_no | 账号 | `varchar(64)` | 否 | - | 否 |
| company_id | 所属公司 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_bank_txn

银行流水
id bigint 主键|acct_id bigint 账户 ID|txn_date date 交易日期|direction varchar(8) 收支方向|amount numeric(14,2) 金额|counterpart varchar(128) 对方户名|ref_no varchar(64) 银行参考号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| acct_id | 账户 ID | `bigint` | 是 | - | 否 |
| txn_date | 交易日期 | `date` | 否 | - | 否 |
| direction | 收支方向 | `varchar(8)` | 否 | - | 否 |
| amount | 金额 | `numeric(14,2)` | 否 | - | 否 |
| counterpart | 对方户名 | `varchar(128)` | 否 | - | 否 |
| ref_no | 银行参考号 | `varchar(64)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_budget_line

预算明细行
id bigint 主键|budget_id bigint 年度预算 ID|subject_code varchar(32) 科目编码|subject_name varchar(64) 科目名称|amount numeric(14,2) 金额|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| budget_id | 年度预算 ID | `bigint` | 是 | - | 否 |
| subject_code | 科目编码 | `varchar(32)` | 否 | - | 否 |
| subject_name | 科目名称 | `varchar(64)` | 否 | - | 否 |
| amount | 金额 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_budget_year

年度预算
id bigint 主键|year integer 年度|dept_id bigint 部门 ID|budget_amount numeric(14,2) 预算金额|used_amount numeric(14,2) 已用金额|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| year | 年度 | `integer` | 是 | - | 否 |
| dept_id | 部门 ID | `bigint` | 否 | - | 否 |
| budget_amount | 预算金额 | `numeric(14,2)` | 否 | - | 否 |
| used_amount | 已用金额 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_cost_allocation

费用分摊
id bigint 主键|year_month varchar(7) 年月|from_dept_id bigint 分出部门 ID|to_dept_id bigint 分入部门 ID|amount numeric(14,2) 分摊金额|subject_code varchar(32) 科目编码|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| year_month | 年月 | `varchar(7)` | 否 | - | 否 |
| from_dept_id | 分出部门 ID | `bigint` | 否 | - | 否 |
| to_dept_id | 分入部门 ID | `bigint` | 否 | - | 否 |
| amount | 分摊金额 | `numeric(14,2)` | 否 | - | 否 |
| subject_code | 科目编码 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_exchange_rate

汇率
id bigint 主键|currency varchar(8) 币种|rate_date date 汇率日期|rate numeric(18,8) 对人民币汇率|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| currency | 币种 | `varchar(8)` | 是 | - | 否 |
| rate_date | 汇率日期 | `date` | 是 | - | 否 |
| rate | 对人民币汇率 | `numeric(18,8)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_fixed_asset

固定资产
id bigint 主键|asset_code varchar(32) 资产编码|asset_name varchar(128) 资产名称|category varchar(32) 资产类别|purchase_date date 购置日期|original_value numeric(14,2) 原值|custodian_emp_id bigint 保管人员工 ID|dept_id bigint 使用部门 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| asset_code | 资产编码 | `varchar(32)` | 是 | - | 否 |
| asset_name | 资产名称 | `varchar(128)` | 是 | - | 否 |
| category | 资产类别 | `varchar(32)` | 否 | - | 否 |
| purchase_date | 购置日期 | `date` | 否 | - | 否 |
| original_value | 原值 | `numeric(14,2)` | 否 | - | 否 |
| custodian_emp_id | 保管人员工 ID | `bigint` | 否 | - | 否 |
| dept_id | 使用部门 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_gl_account

会计科目
id bigint 主键|acct_code varchar(32) 科目编码|acct_name varchar(128) 科目名称|acct_type varchar(32) 科目类型|parent_code varchar(32) 上级科目编码|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| acct_code | 科目编码 | `varchar(32)` | 是 | - | 否 |
| acct_name | 科目名称 | `varchar(128)` | 是 | - | 否 |
| acct_type | 科目类型 | `varchar(32)` | 否 | - | 否 |
| parent_code | 上级科目编码 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_invoice

进销项发票
id bigint 主键|invoice_no varchar(64) 发票号|invoice_type varchar(32) 发票类型|vendor_id bigint 供应商 ID|customer_id bigint 客户 ID|amount numeric(14,2) 含税金额|tax_amount numeric(14,2) 税额|invoice_date date 开票日期|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| invoice_no | 发票号 | `varchar(64)` | 是 | - | 否 |
| invoice_type | 发票类型 | `varchar(32)` | 否 | - | 否 |
| vendor_id | 供应商 ID | `bigint` | 否 | - | 否 |
| customer_id | 客户 ID | `bigint` | 否 | - | 否 |
| amount | 含税金额 | `numeric(14,2)` | 否 | - | 否 |
| tax_amount | 税额 | `numeric(14,2)` | 否 | - | 否 |
| invoice_date | 开票日期 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_journal

会计凭证头
id bigint 主键|voucher_no varchar(64) 凭证号|voucher_date date 凭证日期|period varchar(7) 会计期间|created_by bigint 制单人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| voucher_no | 凭证号 | `varchar(64)` | 是 | - | 否 |
| voucher_date | 凭证日期 | `date` | 否 | - | 否 |
| period | 会计期间 | `varchar(7)` | 否 | - | 否 |
| created_by | 制单人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_journal_line

会计凭证分录
id bigint 主键|journal_id bigint 凭证头 ID|acct_id bigint 科目 ID|debit numeric(14,2) 借方|credit numeric(14,2) 贷方|summary varchar(256) 摘要|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| journal_id | 凭证头 ID | `bigint` | 是 | - | 否 |
| acct_id | 科目 ID | `bigint` | 是 | - | 否 |
| debit | 借方 | `numeric(14,2)` | 否 | - | 否 |
| credit | 贷方 | `numeric(14,2)` | 否 | - | 否 |
| summary | 摘要 | `varchar(256)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_loan

对公借款
id bigint 主键|loan_no varchar(64) 借款单号|emp_id bigint 借款人员工 ID|amount numeric(14,2) 借款金额|loan_date date 借款日期|due_date date 应还日期|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| loan_no | 借款单号 | `varchar(64)` | 否 | - | 否 |
| emp_id | 借款人员工 ID | `bigint` | 是 | - | 否 |
| amount | 借款金额 | `numeric(14,2)` | 否 | - | 否 |
| loan_date | 借款日期 | `date` | 否 | - | 否 |
| due_date | 应还日期 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_loan_repay

借款核销
id bigint 主键|loan_id bigint 借款 ID|repay_amount numeric(14,2) 核销金额|repay_date date 核销日期|reimburse_id bigint 关联报销单 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| loan_id | 借款 ID | `bigint` | 是 | - | 否 |
| repay_amount | 核销金额 | `numeric(14,2)` | 否 | - | 否 |
| repay_date | 核销日期 | `date` | 否 | - | 否 |
| reimburse_id | 关联报销单 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_payment

付款单
id bigint 主键|payment_no varchar(64) 付款单号|vendor_id bigint 供应商 ID|amount numeric(14,2) 付款金额|pay_date date 付款日期|method varchar(32) 支付方式|applicant_emp_id bigint 申请人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| payment_no | 付款单号 | `varchar(64)` | 是 | - | 否 |
| vendor_id | 供应商 ID | `bigint` | 否 | - | 否 |
| amount | 付款金额 | `numeric(14,2)` | 否 | - | 否 |
| pay_date | 付款日期 | `date` | 否 | - | 否 |
| method | 支付方式 | `varchar(32)` | 否 | - | 否 |
| applicant_emp_id | 申请人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_petty_cash

备用金账户
id bigint 主键|dept_id bigint 部门 ID|keeper_emp_id bigint 保管人员工 ID|balance numeric(14,2) 余额|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dept_id | 部门 ID | `bigint` | 否 | - | 否 |
| keeper_emp_id | 保管人员工 ID | `bigint` | 否 | - | 否 |
| balance | 余额 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_petty_cash_txn

备用金收支
id bigint 主键|petty_id bigint 备用金账户 ID|txn_date date 日期|direction varchar(8) 收支|amount numeric(14,2) 金额|reason varchar(256) 事由|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| petty_id | 备用金账户 ID | `bigint` | 是 | - | 否 |
| txn_date | 日期 | `date` | 否 | - | 否 |
| direction | 收支 | `varchar(8)` | 否 | - | 否 |
| amount | 金额 | `numeric(14,2)` | 否 | - | 否 |
| reason | 事由 | `varchar(256)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_receipt

收款单
id bigint 主键|receipt_no varchar(64) 收款单号|customer_id bigint 客户 ID|amount numeric(14,2) 收款金额|receipt_date date 收款日期|project_id bigint 项目 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| receipt_no | 收款单号 | `varchar(64)` | 是 | - | 否 |
| customer_id | 客户 ID | `bigint` | 否 | - | 否 |
| amount | 收款金额 | `numeric(14,2)` | 否 | - | 否 |
| receipt_date | 收款日期 | `date` | 否 | - | 否 |
| project_id | 项目 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_tax_period

税务申报期间
id bigint 主键|year_month varchar(7) 年月|tax_type varchar(32) 税种|payable_amount numeric(14,2) 应纳税额|paid_amount numeric(14,2) 已缴税额|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| year_month | 年月 | `varchar(7)` | 是 | - | 否 |
| tax_type | 税种 | `varchar(32)` | 否 | - | 否 |
| payable_amount | 应纳税额 | `numeric(14,2)` | 否 | - | 否 |
| paid_amount | 已缴税额 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## fin_vendor

供应商主数据
id bigint 主键|vendor_code varchar(32) 供应商编码|vendor_name varchar(128) 供应商名称|tax_no varchar(64) 税号|contact varchar(64) 联系人|phone varchar(32) 电话|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| vendor_code | 供应商编码 | `varchar(32)` | 是 | - | 否 |
| vendor_name | 供应商名称 | `varchar(128)` | 是 | - | 否 |
| tax_no | 税号 | `varchar(64)` | 否 | - | 否 |
| contact | 联系人 | `varchar(64)` | 否 | - | 否 |
| phone | 电话 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_award

奖惩记录
id bigint 主键|emp_id bigint 员工 ID|award_type varchar(32) 奖惩类型|amount numeric(12,2) 金额|occur_date date 发生日期|reason varchar(256) 事由|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| award_type | 奖惩类型 | `varchar(32)` | 否 | - | 否 |
| amount | 金额 | `numeric(12,2)` | 否 | - | 否 |
| occur_date | 发生日期 | `date` | 否 | - | 否 |
| reason | 事由 | `varchar(256)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_bank_account

员工薪酬账户
id bigint 主键|emp_id bigint 员工 ID|bank_name varchar(64) 开户行|account_no varchar(64) 账号|is_primary boolean 是否主账户|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| bank_name | 开户行 | `varchar(64)` | 否 | - | 否 |
| account_no | 账号 | `varchar(64)` | 否 | - | 否 |
| is_primary | 是否主账户 | `boolean` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_candidate

候选人
id bigint 主键|cand_code varchar(32) 候选人编码|cand_name varchar(128) 候选人姓名|phone varchar(32) 电话|email varchar(128) 邮箱|source varchar(32) 来源渠道|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| cand_code | 候选人编码 | `varchar(32)` | 是 | - | 否 |
| cand_name | 候选人姓名 | `varchar(128)` | 是 | - | 否 |
| phone | 电话 | `varchar(32)` | 否 | - | 否 |
| email | 邮箱 | `varchar(128)` | 否 | - | 否 |
| source | 来源渠道 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_certificate

员工证书资质
id bigint 主键|emp_id bigint 员工 ID|cert_name varchar(128) 证书名称|cert_no varchar(64) 证书编号|expire_date date 到期日|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| cert_name | 证书名称 | `varchar(128)` | 否 | - | 否 |
| cert_no | 证书编号 | `varchar(64)` | 否 | - | 否 |
| expire_date | 到期日 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_contract

劳动合同
id bigint 主键|emp_id bigint 员工 ID|contract_no varchar(64) 合同编号|contract_type varchar(32) 合同类型|start_date date 开始日期|end_date date 结束日期|sign_company_id bigint 签约公司 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| contract_no | 合同编号 | `varchar(64)` | 否 | - | 否 |
| contract_type | 合同类型 | `varchar(32)` | 否 | - | 否 |
| start_date | 开始日期 | `date` | 否 | - | 否 |
| end_date | 结束日期 | `date` | 否 | - | 否 |
| sign_company_id | 签约公司 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_education

教育经历
id bigint 主键|emp_id bigint 员工 ID|school varchar(128) 学校|degree varchar(32) 学历|major varchar(64) 专业|graduate_date date 毕业日期|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| school | 学校 | `varchar(128)` | 否 | - | 否 |
| degree | 学历 | `varchar(32)` | 否 | - | 否 |
| major | 专业 | `varchar(64)` | 否 | - | 否 |
| graduate_date | 毕业日期 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_emergency_contact

紧急联系人
id bigint 主键|emp_id bigint 员工 ID|contact_name varchar(64) 联系人姓名|relation varchar(32) 关系|phone varchar(32) 电话|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| contact_name | 联系人姓名 | `varchar(64)` | 否 | - | 否 |
| relation | 关系 | `varchar(32)` | 否 | - | 否 |
| phone | 电话 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_family_member

员工家属信息
id bigint 主键|emp_id bigint 员工 ID|member_name varchar(64) 家属姓名|relation varchar(32) 关系|birthday date 生日|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| member_name | 家属姓名 | `varchar(64)` | 否 | - | 否 |
| relation | 关系 | `varchar(32)` | 否 | - | 否 |
| birthday | 生日 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_headcount_plan

编制计划
id bigint 主键|dept_id bigint 部门 ID|year_month varchar(7) 年月 YYYY-MM|plan_hc integer 计划编制|actual_hc integer 实际在岗|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dept_id | 部门 ID | `bigint` | 是 | - | 否 |
| year_month | 年月 YYYY-MM | `varchar(7)` | 否 | - | 否 |
| plan_hc | 计划编制 | `integer` | 否 | - | 否 |
| actual_hc | 实际在岗 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_interview

面试记录
id bigint 主键|candidate_id bigint 候选人 ID|req_id bigint 招聘需求 ID|interviewer_emp_id bigint 面试官员工 ID|interview_at timestamp 面试时间|result varchar(32) 结果|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| candidate_id | 候选人 ID | `bigint` | 是 | - | 否 |
| req_id | 招聘需求 ID | `bigint` | 否 | - | 否 |
| interviewer_emp_id | 面试官员工 ID | `bigint` | 否 | - | 否 |
| interview_at | 面试时间 | `timestamp` | 否 | - | 否 |
| result | 结果 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_offer

录用 Offer
id bigint 主键|candidate_id bigint 候选人 ID|req_id bigint 招聘需求 ID|offer_amount numeric(14,2) offer 年薪/月薪金额|accept_status varchar(32) 接受状态|join_date date 预计入职日|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| candidate_id | 候选人 ID | `bigint` | 是 | - | 否 |
| req_id | 招聘需求 ID | `bigint` | 否 | - | 否 |
| offer_amount | offer 年薪/月薪金额 | `numeric(14,2)` | 否 | - | 否 |
| accept_status | 接受状态 | `varchar(32)` | 否 | - | 否 |
| join_date | 预计入职日 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_onboarding

入职办理单
id bigint 主键|emp_id bigint 员工 ID|checklist_status varchar(32) 清单状态|it_ready boolean IT 是否就绪|badge_no varchar(32) 工牌号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| checklist_status | 清单状态 | `varchar(32)` | 否 | - | 否 |
| it_ready | IT 是否就绪 | `boolean` | 否 | - | 否 |
| badge_no | 工牌号 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_performance_cycle

绩效考核周期
id bigint 主键|cycle_code varchar(32) 周期编码|cycle_name varchar(128) 周期名称|start_date date 开始日期|end_date date 结束日期|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| cycle_code | 周期编码 | `varchar(32)` | 是 | - | 否 |
| cycle_name | 周期名称 | `varchar(128)` | 是 | - | 否 |
| start_date | 开始日期 | `date` | 否 | - | 否 |
| end_date | 结束日期 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_performance_goal

绩效目标
id bigint 主键|cycle_id bigint 周期 ID|emp_id bigint 员工 ID|goal_text text 目标描述|weight_pct numeric(6,2) 权重百分比|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| cycle_id | 周期 ID | `bigint` | 是 | - | 否 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| goal_text | 目标描述 | `text` | 否 | - | 否 |
| weight_pct | 权重百分比 | `numeric(6,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_performance_review

绩效评估结果
id bigint 主键|cycle_id bigint 周期 ID|emp_id bigint 员工 ID|score numeric(6,2) 得分|grade varchar(16) 等级|reviewer_emp_id bigint 评估人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| cycle_id | 周期 ID | `bigint` | 是 | - | 否 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| score | 得分 | `numeric(6,2)` | 否 | - | 否 |
| grade | 等级 | `varchar(16)` | 否 | - | 否 |
| reviewer_emp_id | 评估人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_probation

试用期考核
id bigint 主键|emp_id bigint 员工 ID|plan_end_date date 计划转正日|actual_end_date date 实际转正日|result varchar(32) 考核结果|mentor_emp_id bigint 导师员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| plan_end_date | 计划转正日 | `date` | 否 | - | 否 |
| actual_end_date | 实际转正日 | `date` | 否 | - | 否 |
| result | 考核结果 | `varchar(32)` | 否 | - | 否 |
| mentor_emp_id | 导师员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_promotion

晋升记录
id bigint 主键|emp_id bigint 员工 ID|from_level_id bigint 原职级 ID|to_level_id bigint 新职级 ID|effective_date date 生效日期|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| from_level_id | 原职级 ID | `bigint` | 否 | - | 否 |
| to_level_id | 新职级 ID | `bigint` | 否 | - | 否 |
| effective_date | 生效日期 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_recruit_req

招聘需求
id bigint 主键|req_code varchar(32) 需求编码|req_name varchar(128) 需求名称|dept_id bigint 需求部门 ID|headcount integer 需求人数|job_level_id bigint 目标职级 ID|owner_emp_id bigint 招聘负责人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| req_code | 需求编码 | `varchar(32)` | 是 | - | 否 |
| req_name | 需求名称 | `varchar(128)` | 是 | - | 否 |
| dept_id | 需求部门 ID | `bigint` | 否 | - | 否 |
| headcount | 需求人数 | `integer` | 否 | - | 否 |
| job_level_id | 目标职级 ID | `bigint` | 否 | - | 否 |
| owner_emp_id | 招聘负责人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_resignation

离职办理
id bigint 主键|emp_id bigint 员工 ID|apply_date date 申请日期|last_work_date date 最后工作日|reason_type varchar(32) 离职原因类型|exit_interview text 离职面谈纪要|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| apply_date | 申请日期 | `date` | 否 | - | 否 |
| last_work_date | 最后工作日 | `date` | 否 | - | 否 |
| reason_type | 离职原因类型 | `varchar(32)` | 否 | - | 否 |
| exit_interview | 离职面谈纪要 | `text` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_training_course

培训课程
id bigint 主键|course_code varchar(32) 课程编码|course_name varchar(128) 课程名称|hours numeric(6,2) 课时|vendor varchar(128) 培训供应商|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| course_code | 课程编码 | `varchar(32)` | 是 | - | 否 |
| course_name | 课程名称 | `varchar(128)` | 是 | - | 否 |
| hours | 课时 | `numeric(6,2)` | 否 | - | 否 |
| vendor | 培训供应商 | `varchar(128)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_training_enroll

培训报名
id bigint 主键|session_id bigint 场次 ID|emp_id bigint 员工 ID|attend_status varchar(32) 出勤状态|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| session_id | 场次 ID | `bigint` | 是 | - | 否 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| attend_status | 出勤状态 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_training_session

培训场次
id bigint 主键|course_id bigint 课程 ID|start_at timestamp 开始时间|end_at timestamp 结束时间|location varchar(128) 地点|trainer varchar(64) 讲师|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| course_id | 课程 ID | `bigint` | 是 | - | 否 |
| start_at | 开始时间 | `timestamp` | 否 | - | 否 |
| end_at | 结束时间 | `timestamp` | 否 | - | 否 |
| location | 地点 | `varchar(128)` | 否 | - | 否 |
| trainer | 讲师 | `varchar(64)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_transfer

人事调动
id bigint 主键|emp_id bigint 员工 ID|from_dept_id bigint 调出部门 ID|to_dept_id bigint 调入部门 ID|effective_date date 生效日期|transfer_type varchar(32) 调动类型|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| from_dept_id | 调出部门 ID | `bigint` | 否 | - | 否 |
| to_dept_id | 调入部门 ID | `bigint` | 否 | - | 否 |
| effective_date | 生效日期 | `date` | 否 | - | 否 |
| transfer_type | 调动类型 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_work_calendar

工作日历
id bigint 主键|cal_date date 日期|day_type varchar(16) 日类型|holiday_name varchar(64) 节假日名称|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| cal_date | 日期 | `date` | 是 | - | 否 |
| day_type | 日类型：work/weekend/holiday | `varchar(16)` | 否 | - | 否 |
| holiday_name | 节假日名称 | `varchar(64)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## hr_work_history

入职前工作经历
id bigint 主键|emp_id bigint 员工 ID|employer varchar(128) 原单位|title varchar(64) 职位|start_date date 开始日期|end_date date 结束日期|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| employer | 原单位 | `varchar(128)` | 否 | - | 否 |
| title | 职位 | `varchar(64)` | 否 | - | 否 |
| start_date | 开始日期 | `date` | 否 | - | 否 |
| end_date | 结束日期 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## itm_access_request

权限申请
id bigint 主键|system_id bigint 系统 ID|emp_id bigint 申请人员工 ID|role_name varchar(64) 申请角色|reason varchar(256) 事由|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| system_id | 系统 ID | `bigint` | 是 | - | 否 |
| emp_id | 申请人员工 ID | `bigint` | 是 | - | 否 |
| role_name | 申请角色 | `varchar(64)` | 否 | - | 否 |
| reason | 事由 | `varchar(256)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## itm_account

系统账号
id bigint 主键|system_id bigint 系统 ID|emp_id bigint 员工 ID|login_name varchar(64) 登录名|role_name varchar(64) 角色|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| system_id | 系统 ID | `bigint` | 是 | - | 否 |
| emp_id | 员工 ID | `bigint` | 否 | - | 否 |
| login_name | 登录名 | `varchar(64)` | 否 | - | 否 |
| role_name | 角色 | `varchar(64)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## itm_asset

IT 资产
id bigint 主键|asset_code varchar(32) 资产编码|asset_name varchar(128) 资产名称|asset_type varchar(32) 资产类型|sn varchar(64) 序列号|assignee_emp_id bigint 领用人员工 ID|office_id bigint 职场 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| asset_code | 资产编码 | `varchar(32)` | 是 | - | 否 |
| asset_name | 资产名称 | `varchar(128)` | 是 | - | 否 |
| asset_type | 资产类型 | `varchar(32)` | 否 | - | 否 |
| sn | 序列号 | `varchar(64)` | 否 | - | 否 |
| assignee_emp_id | 领用人员工 ID | `bigint` | 否 | - | 否 |
| office_id | 职场 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## itm_asset_assign

IT 资产领用归还
id bigint 主键|asset_id bigint 资产 ID|emp_id bigint 员工 ID|assign_date date 领用日期|return_date date 归还日期|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| asset_id | 资产 ID | `bigint` | 是 | - | 否 |
| emp_id | 员工 ID | `bigint` | 是 | - | 否 |
| assign_date | 领用日期 | `date` | 否 | - | 否 |
| return_date | 归还日期 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## itm_change

变更单
id bigint 主键|chg_code varchar(32) 变更单号|chg_name varchar(128) 变更标题|system_id bigint 系统 ID|planned_at timestamp 计划时间|risk_level varchar(16) 风险等级|applicant_emp_id bigint 申请人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| chg_code | 变更单号 | `varchar(32)` | 是 | - | 否 |
| chg_name | 变更标题 | `varchar(128)` | 是 | - | 否 |
| system_id | 系统 ID | `bigint` | 否 | - | 否 |
| planned_at | 计划时间 | `timestamp` | 否 | - | 否 |
| risk_level | 风险等级 | `varchar(16)` | 否 | - | 否 |
| applicant_emp_id | 申请人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## itm_deploy

发布部署记录
id bigint 主键|system_id bigint 系统 ID|version_no varchar(32) 版本号|deploy_at timestamp 发布时间|operator_emp_id bigint 操作人员工 ID|result varchar(32) 结果|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| system_id | 系统 ID | `bigint` | 是 | - | 否 |
| version_no | 版本号 | `varchar(32)` | 否 | - | 否 |
| deploy_at | 发布时间 | `timestamp` | 否 | - | 否 |
| operator_emp_id | 操作人员工 ID | `bigint` | 否 | - | 否 |
| result | 结果 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## itm_incident

生产故障
id bigint 主键|inc_code varchar(32) 故障单号|inc_name varchar(128) 故障标题|system_id bigint 系统 ID|severity varchar(16) 严重级别|started_at timestamp 开始时间|resolved_at timestamp 恢复时间|commander_emp_id bigint 指挥人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| inc_code | 故障单号 | `varchar(32)` | 是 | - | 否 |
| inc_name | 故障标题 | `varchar(128)` | 是 | - | 否 |
| system_id | 系统 ID | `bigint` | 否 | - | 否 |
| severity | 严重级别 | `varchar(16)` | 否 | - | 否 |
| started_at | 开始时间 | `timestamp` | 否 | - | 否 |
| resolved_at | 恢复时间 | `timestamp` | 否 | - | 否 |
| commander_emp_id | 指挥人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## itm_system

业务系统台账
id bigint 主键|sys_code varchar(32) 系统编码|sys_name varchar(128) 系统名称|owner_emp_id bigint 系统负责人员工 ID|env varchar(32) 环境|url varchar(256) 访问地址|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| sys_code | 系统编码 | `varchar(32)` | 是 | - | 否 |
| sys_name | 系统名称 | `varchar(128)` | 是 | - | 否 |
| owner_emp_id | 系统负责人员工 ID | `bigint` | 否 | - | 否 |
| env | 环境 | `varchar(32)` | 否 | - | 否 |
| url | 访问地址 | `varchar(256)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## itm_ticket

IT 服务工单
id bigint 主键|ticket_code varchar(32) 工单号|ticket_name varchar(128) 工单标题|requester_emp_id bigint 提单人员工 ID|assignee_emp_id bigint 处理人员工 ID|category varchar(32) 分类|priority varchar(16) 优先级|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| ticket_code | 工单号 | `varchar(32)` | 是 | - | 否 |
| ticket_name | 工单标题 | `varchar(128)` | 是 | - | 否 |
| requester_emp_id | 提单人员工 ID | `bigint` | 否 | - | 否 |
| assignee_emp_id | 处理人员工 ID | `bigint` | 否 | - | 否 |
| category | 分类 | `varchar(32)` | 否 | - | 否 |
| priority | 优先级 | `varchar(16)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## itm_ticket_comment

工单评论
id bigint 主键|ticket_id bigint 工单 ID|author_emp_id bigint 评论人员工 ID|content text 内容|commented_at timestamp 评论时间|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| ticket_id | 工单 ID | `bigint` | 是 | - | 否 |
| author_emp_id | 评论人员工 ID | `bigint` | 否 | - | 否 |
| content | 内容 | `text` | 否 | - | 否 |
| commented_at | 评论时间 | `timestamp` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## kb_article

内部知识文章
id bigint 主键|article_code varchar(32) 文章编码|article_name varchar(128) 标题|category varchar(64) 分类|author_emp_id bigint 作者员工 ID|body text 正文|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| article_code | 文章编码 | `varchar(32)` | 是 | - | 否 |
| article_name | 标题 | `varchar(128)` | 是 | - | 否 |
| category | 分类 | `varchar(64)` | 否 | - | 否 |
| author_emp_id | 作者员工 ID | `bigint` | 否 | - | 否 |
| body | 正文 | `text` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## kb_article_tag

知识标签
id bigint 主键|tag_code varchar(32) 标签编码|tag_name varchar(64) 标签名|color varchar(16) 展示色|sort_no integer 排序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| tag_code | 标签编码 | `varchar(32)` | 是 | - | 否 |
| tag_name | 标签名 | `varchar(64)` | 是 | - | 否 |
| color | 展示色 | `varchar(16)` | 否 | - | 否 |
| sort_no | 排序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## kb_article_tag_rel

文章标签关系
id bigint 主键|article_id bigint 文章 ID|tag_id bigint 标签 ID|tagged_by bigint 打标人员工 ID|tagged_at timestamp 打标时间|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| article_id | 文章 ID | `bigint` | 是 | - | 否 |
| tag_id | 标签 ID | `bigint` | 是 | - | 否 |
| tagged_by | 打标人员工 ID | `bigint` | 否 | - | 否 |
| tagged_at | 打标时间 | `timestamp` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## legal_compliance_check

合规检查
id bigint 主键|chk_code varchar(32) 检查编码|chk_name varchar(128) 检查名称|check_date date 检查日期|result varchar(32) 结果|owner_emp_id bigint 负责人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| chk_code | 检查编码 | `varchar(32)` | 是 | - | 否 |
| chk_name | 检查名称 | `varchar(128)` | 是 | - | 否 |
| check_date | 检查日期 | `date` | 否 | - | 否 |
| result | 结果 | `varchar(32)` | 否 | - | 否 |
| owner_emp_id | 负责人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## legal_contract

法务合同台账
id bigint 主键|lcontract_code varchar(32) 合同编号|lcontract_name varchar(128) 合同名称|counterparty varchar(128) 相对方|sign_date date 签订日期|amount numeric(14,2) 金额|owner_emp_id bigint 业务负责人员工 ID|customer_id bigint 关联客户 ID|vendor_id bigint 关联供应商 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| lcontract_code | 合同编号 | `varchar(32)` | 是 | - | 否 |
| lcontract_name | 合同名称 | `varchar(128)` | 是 | - | 否 |
| counterparty | 相对方 | `varchar(128)` | 否 | - | 否 |
| sign_date | 签订日期 | `date` | 否 | - | 否 |
| amount | 金额 | `numeric(14,2)` | 否 | - | 否 |
| owner_emp_id | 业务负责人员工 ID | `bigint` | 否 | - | 否 |
| customer_id | 关联客户 ID | `bigint` | 否 | - | 否 |
| vendor_id | 关联供应商 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## legal_contract_clause

合同关键条款
id bigint 主键|contract_id bigint 合同 ID|clause_title varchar(128) 条款标题|clause_text text 条款正文|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| contract_id | 合同 ID | `bigint` | 是 | - | 否 |
| clause_title | 条款标题 | `varchar(128)` | 否 | - | 否 |
| clause_text | 条款正文 | `text` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## legal_dispute

诉讼/争议案件
id bigint 主键|case_code varchar(32) 案件编号|case_name varchar(128) 案件名称|contract_id bigint 关联合同 ID|counterpart varchar(128) 对方当事人|opened_at date 立案日期|lawyer varchar(64) 承办律师|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| case_code | 案件编号 | `varchar(32)` | 是 | - | 否 |
| case_name | 案件名称 | `varchar(128)` | 是 | - | 否 |
| contract_id | 关联合同 ID | `bigint` | 否 | - | 否 |
| counterpart | 对方当事人 | `varchar(128)` | 否 | - | 否 |
| opened_at | 立案日期 | `date` | 否 | - | 否 |
| lawyer | 承办律师 | `varchar(64)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## mkt_campaign

市场活动
id bigint 主键|camp_code varchar(32) 活动编码|camp_name varchar(128) 活动名称|start_date date 开始日期|end_date date 结束日期|budget numeric(14,2) 预算|owner_emp_id bigint 负责人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| camp_code | 活动编码 | `varchar(32)` | 是 | - | 否 |
| camp_name | 活动名称 | `varchar(128)` | 是 | - | 否 |
| start_date | 开始日期 | `date` | 否 | - | 否 |
| end_date | 结束日期 | `date` | 否 | - | 否 |
| budget | 预算 | `numeric(14,2)` | 否 | - | 否 |
| owner_emp_id | 负责人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## mkt_campaign_lead

活动获客线索
id bigint 主键|camp_id bigint 活动 ID|lead_id bigint 线索 ID|channel varchar(32) 渠道|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| camp_id | 活动 ID | `bigint` | 是 | - | 否 |
| lead_id | 线索 ID | `bigint` | 否 | - | 否 |
| channel | 渠道 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## mkt_content

内容素材
id bigint 主键|content_code varchar(32) 素材编码|content_name varchar(128) 素材标题|content_type varchar(32) 类型|url varchar(512) 链接|author_emp_id bigint 作者员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| content_code | 素材编码 | `varchar(32)` | 是 | - | 否 |
| content_name | 素材标题 | `varchar(128)` | 是 | - | 否 |
| content_type | 类型 | `varchar(32)` | 否 | - | 否 |
| url | 链接 | `varchar(512)` | 否 | - | 否 |
| author_emp_id | 作者员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## mkt_event_reg

活动报名
id bigint 主键|camp_id bigint 活动 ID|reg_name varchar(64) 报名人|company_name varchar(128) 单位|phone varchar(32) 电话|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| camp_id | 活动 ID | `bigint` | 是 | - | 否 |
| reg_name | 报名人 | `varchar(64)` | 否 | - | 否 |
| company_name | 单位 | `varchar(128)` | 否 | - | 否 |
| phone | 电话 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## ops_backup_job

备份任务
id bigint 主键|bak_code varchar(32) 任务编码|bak_name varchar(128) 任务名称|system_id bigint 系统 ID|cron_expr varchar(64) 调度表达式|last_run_at timestamp 上次执行时间|last_result varchar(32) 上次结果|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| bak_code | 任务编码 | `varchar(32)` | 是 | - | 否 |
| bak_name | 任务名称 | `varchar(128)` | 是 | - | 否 |
| system_id | 系统 ID | `bigint` | 否 | - | 否 |
| cron_expr | 调度表达式 | `varchar(64)` | 否 | - | 否 |
| last_run_at | 上次执行时间 | `timestamp` | 否 | - | 否 |
| last_result | 上次结果 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## ops_duty_roster

值班排班
id bigint 主键|emp_id bigint 值班员工 ID|duty_date date 日期|shift_name varchar(32) 班次名|system_id bigint 值守系统 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 值班员工 ID | `bigint` | 是 | - | 否 |
| duty_date | 日期 | `date` | 是 | - | 否 |
| shift_name | 班次名 | `varchar(32)` | 否 | - | 否 |
| system_id | 值守系统 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## ops_monitor_alert

监控告警
id bigint 主键|system_id bigint 系统 ID|alert_name varchar(128) 告警名|severity varchar(16) 级别|fired_at timestamp 触发时间|acked_by bigint 确认人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| system_id | 系统 ID | `bigint` | 否 | - | 否 |
| alert_name | 告警名 | `varchar(128)` | 否 | - | 否 |
| severity | 级别 | `varchar(16)` | 否 | - | 否 |
| fired_at | 触发时间 | `timestamp` | 否 | - | 否 |
| acked_by | 确认人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## ops_runbook

运维手册
id bigint 主键|rb_code varchar(32) 手册编码|rb_name varchar(128) 手册名称|system_id bigint 系统 ID|content text 正文|owner_emp_id bigint 维护人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| rb_code | 手册编码 | `varchar(32)` | 是 | - | 否 |
| rb_name | 手册名称 | `varchar(128)` | 是 | - | 否 |
| system_id | 系统 ID | `bigint` | 否 | - | 否 |
| content | 正文 | `text` | 否 | - | 否 |
| owner_emp_id | 维护人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## org_announcement

内部公告
id bigint 主键|title varchar(256) 标题|content text 正文|publisher_emp_id bigint 发布人员工 ID|publish_at timestamp 发布时间|scope varchar(32) 发布范围|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| title | 标题 | `varchar(256)` | 是 | - | 否 |
| content | 正文 | `text` | 否 | - | 否 |
| publisher_emp_id | 发布人员工 ID | `bigint` | 否 | - | 否 |
| publish_at | 发布时间 | `timestamp` | 否 | - | 否 |
| scope | 发布范围 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## org_biz_unit

业务单元
id bigint 主键|bu_code varchar(32) 业务单元编码|bu_name varchar(128) 业务单元名称|leader_emp_id bigint 负责人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| bu_code | 业务单元编码 | `varchar(32)` | 是 | - | 否 |
| bu_name | 业务单元名称 | `varchar(128)` | 是 | - | 否 |
| leader_emp_id | 负责人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## org_company

法人公司
id bigint 主键|company_code varchar(32) 公司编码|company_name varchar(128) 公司名称|legal_name varchar(256) 法定名称|tax_no varchar(64) 税号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| company_code | 公司编码 | `varchar(32)` | 是 | - | 否 |
| company_name | 公司名称 | `varchar(128)` | 是 | - | 否 |
| legal_name | 法定名称 | `varchar(256)` | 否 | - | 否 |
| tax_no | 税号 | `varchar(64)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## org_cost_center

成本中心
id bigint 主键|cc_code varchar(32) 成本中心编码|cc_name varchar(128) 成本中心名称|dept_id bigint 关联部门 ID|owner_emp_id bigint 负责人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| cc_code | 成本中心编码 | `varchar(32)` | 是 | - | 否 |
| cc_name | 成本中心名称 | `varchar(128)` | 是 | - | 否 |
| dept_id | 关联部门 ID | `bigint` | 否 | - | 否 |
| owner_emp_id | 负责人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## org_dept_change

部门变更记录
id bigint 主键|dept_id bigint 部门 ID|change_type varchar(32) 变更类型|old_parent_id bigint 原上级部门 ID|new_parent_id bigint 新上级部门 ID|effective_date date 生效日期|operator_emp_id bigint 操作人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| dept_id | 部门 ID | `bigint` | 是 | - | 否 |
| change_type | 变更类型 | `varchar(32)` | 否 | - | 否 |
| old_parent_id | 原上级部门 ID | `bigint` | 否 | - | 否 |
| new_parent_id | 新上级部门 ID | `bigint` | 否 | - | 否 |
| effective_date | 生效日期 | `date` | 否 | - | 否 |
| operator_emp_id | 操作人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## org_dept_closure

部门闭包表（祖先-后代）
id bigint 主键|ancestor_id bigint 祖先部门 ID|descendant_id bigint 后代部门 ID|depth integer 层级深度

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| ancestor_id | 祖先部门 ID | `bigint` | 是 | - | 否 |
| descendant_id | 后代部门 ID | `bigint` | 是 | - | 否 |
| depth | 层级深度 | `integer` | 是 | - | 否 |

## org_location

地理区位
id bigint 主键|loc_code varchar(32) 区位编码|loc_name varchar(128) 区位名称|region varchar(32) 大区|country varchar(32) 国家地区|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| loc_code | 区位编码 | `varchar(32)` | 是 | - | 否 |
| loc_name | 区位名称 | `varchar(128)` | 是 | - | 否 |
| region | 大区 | `varchar(32)` | 否 | - | 否 |
| country | 国家地区 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## org_office

办公职场
id bigint 主键|office_code varchar(32) 职场编码|office_name varchar(128) 职场名称|city varchar(32) 城市|address varchar(256) 地址|company_id bigint 所属公司 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| office_code | 职场编码 | `varchar(32)` | 是 | - | 否 |
| office_name | 职场名称 | `varchar(128)` | 是 | - | 否 |
| city | 城市 | `varchar(32)` | 否 | - | 否 |
| address | 地址 | `varchar(256)` | 否 | - | 否 |
| company_id | 所属公司 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## org_position

岗位编制
id bigint 主键|pos_code varchar(32) 岗位编码|pos_name varchar(128) 岗位名称|dept_id bigint 所属部门 ID|job_level_id bigint 对应职级 ID|headcount integer 编制人数|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| pos_code | 岗位编码 | `varchar(32)` | 是 | - | 否 |
| pos_name | 岗位名称 | `varchar(128)` | 是 | - | 否 |
| dept_id | 所属部门 ID | `bigint` | 否 | - | 否 |
| job_level_id | 对应职级 ID | `bigint` | 否 | - | 否 |
| headcount | 编制人数 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## org_seal

公司印章台账
id bigint 主键|seal_code varchar(32) 印章编码|seal_name varchar(128) 印章名称|company_id bigint 所属公司 ID|keeper_emp_id bigint 保管人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| seal_code | 印章编码 | `varchar(32)` | 是 | - | 否 |
| seal_name | 印章名称 | `varchar(128)` | 是 | - | 否 |
| company_id | 所属公司 ID | `bigint` | 否 | - | 否 |
| keeper_emp_id | 保管人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prd_feature

产品功能点
id bigint 主键|product_id bigint 产品 ID|feature_code varchar(32) 功能编码|feature_name varchar(128) 功能名称|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| product_id | 产品 ID | `bigint` | 是 | - | 否 |
| feature_code | 功能编码 | `varchar(32)` | 否 | - | 否 |
| feature_name | 功能名称 | `varchar(128)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prd_license

产品授权许可
id bigint 主键|product_id bigint 产品 ID|customer_id bigint 客户 ID|license_key varchar(128) 许可密钥|seat_count integer 席位数|expire_date date 到期日|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| product_id | 产品 ID | `bigint` | 是 | - | 否 |
| customer_id | 客户 ID | `bigint` | 否 | - | 否 |
| license_key | 许可密钥 | `varchar(128)` | 否 | - | 否 |
| seat_count | 席位数 | `integer` | 否 | - | 否 |
| expire_date | 到期日 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prd_product_line

产品线
id bigint 主键|line_code varchar(32) 产品线编码|line_name varchar(128) 产品线名称|owner_emp_id bigint 负责人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| line_code | 产品线编码 | `varchar(32)` | 是 | - | 否 |
| line_name | 产品线名称 | `varchar(128)` | 是 | - | 否 |
| owner_emp_id | 负责人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prd_product_version

产品版本
id bigint 主键|product_id bigint 产品 ID|version_no varchar(32) 版本号|release_date date 发布日期|changelog text 变更说明|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| product_id | 产品 ID | `bigint` | 是 | - | 否 |
| version_no | 版本号 | `varchar(32)` | 否 | - | 否 |
| release_date | 发布日期 | `date` | 否 | - | 否 |
| changelog | 变更说明 | `text` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prd_roadmap

产品路线图项
id bigint 主键|product_id bigint 产品 ID|item_name varchar(128) 事项名称|target_quarter varchar(8) 目标季度|priority varchar(16) 优先级|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| product_id | 产品 ID | `bigint` | 是 | - | 否 |
| item_name | 事项名称 | `varchar(128)` | 否 | - | 否 |
| target_quarter | 目标季度 | `varchar(8)` | 否 | - | 否 |
| priority | 优先级 | `varchar(16)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prj_acceptance

项目验收
id bigint 主键|project_id bigint 项目 ID|accept_date date 验收日期|result varchar(32) 验收结果|customer_signer varchar(64) 客户签字人|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_id | 项目 ID | `bigint` | 是 | - | 否 |
| accept_date | 验收日期 | `date` | 否 | - | 否 |
| result | 验收结果 | `varchar(32)` | 否 | - | 否 |
| customer_signer | 客户签字人 | `varchar(64)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prj_change_request

项目变更申请
id bigint 主键|project_id bigint 项目 ID|title varchar(256) 变更标题|impact text 影响说明|requester_emp_id bigint 申请人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_id | 项目 ID | `bigint` | 是 | - | 否 |
| title | 变更标题 | `varchar(256)` | 否 | - | 否 |
| impact | 影响说明 | `text` | 否 | - | 否 |
| requester_emp_id | 申请人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prj_document

项目文档索引
id bigint 主键|project_id bigint 项目 ID|doc_name varchar(256) 文档名称|doc_type varchar(32) 文档类型|url varchar(512) 链接|uploader_emp_id bigint 上传人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_id | 项目 ID | `bigint` | 是 | - | 否 |
| doc_name | 文档名称 | `varchar(256)` | 否 | - | 否 |
| doc_type | 文档类型 | `varchar(32)` | 否 | - | 否 |
| url | 链接 | `varchar(512)` | 否 | - | 否 |
| uploader_emp_id | 上传人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prj_issue

项目问题单
id bigint 主键|project_id bigint 项目 ID|title varchar(256) 标题|severity varchar(16) 严重级别|reporter_emp_id bigint 报告人员工 ID|assignee_emp_id bigint 处理人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_id | 项目 ID | `bigint` | 是 | - | 否 |
| title | 标题 | `varchar(256)` | 否 | - | 否 |
| severity | 严重级别 | `varchar(16)` | 否 | - | 否 |
| reporter_emp_id | 报告人员工 ID | `bigint` | 否 | - | 否 |
| assignee_emp_id | 处理人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prj_milestone

项目里程碑
id bigint 主键|project_id bigint 项目 ID|milestone_name varchar(128) 里程碑名称|plan_date date 计划日期|actual_date date 实际日期|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_id | 项目 ID | `bigint` | 是 | - | 否 |
| milestone_name | 里程碑名称 | `varchar(128)` | 否 | - | 否 |
| plan_date | 计划日期 | `date` | 否 | - | 否 |
| actual_date | 实际日期 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prj_risk

项目风险
id bigint 主键|project_id bigint 项目 ID|risk_title varchar(256) 风险标题|level varchar(16) 风险等级|owner_emp_id bigint 责任人员工 ID|mitigation text 缓解措施|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_id | 项目 ID | `bigint` | 是 | - | 否 |
| risk_title | 风险标题 | `varchar(256)` | 否 | - | 否 |
| level | 风险等级 | `varchar(16)` | 否 | - | 否 |
| owner_emp_id | 责任人员工 ID | `bigint` | 否 | - | 否 |
| mitigation | 缓解措施 | `text` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prj_stakeholder

项目干系人
id bigint 主键|project_id bigint 项目 ID|emp_id bigint 内部员工 ID|external_name varchar(64) 外部干系人姓名|role varchar(64) 角色|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_id | 项目 ID | `bigint` | 是 | - | 否 |
| emp_id | 内部员工 ID | `bigint` | 否 | - | 否 |
| external_name | 外部干系人姓名 | `varchar(64)` | 否 | - | 否 |
| role | 角色 | `varchar(64)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prj_task

项目任务
id bigint 主键|project_id bigint 项目 ID|task_name varchar(128) 任务名称|assignee_emp_id bigint 负责人员工 ID|plan_start date 计划开始|plan_end date 计划结束|progress_pct numeric(6,2) 进度百分比|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_id | 项目 ID | `bigint` | 是 | - | 否 |
| task_name | 任务名称 | `varchar(128)` | 否 | - | 否 |
| assignee_emp_id | 负责人员工 ID | `bigint` | 否 | - | 否 |
| plan_start | 计划开始 | `date` | 否 | - | 否 |
| plan_end | 计划结束 | `date` | 否 | - | 否 |
| progress_pct | 进度百分比 | `numeric(6,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prj_warranty

项目质保
id bigint 主键|project_id bigint 项目 ID|start_date date 质保开始|end_date date 质保结束|terms text 质保条款|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_id | 项目 ID | `bigint` | 是 | - | 否 |
| start_date | 质保开始 | `date` | 否 | - | 否 |
| end_date | 质保结束 | `date` | 否 | - | 否 |
| terms | 质保条款 | `text` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## prj_weekly_report

项目周报
id bigint 主键|project_id bigint 项目 ID|week_start date 周起始日|author_emp_id bigint 填写人员工 ID|content text 周报内容|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| project_id | 项目 ID | `bigint` | 是 | - | 否 |
| week_start | 周起始日 | `date` | 否 | - | 否 |
| author_emp_id | 填写人员工 ID | `bigint` | 否 | - | 否 |
| content | 周报内容 | `text` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## qa_defect

缺陷
id bigint 主键|bug_code varchar(32) 缺陷编号|bug_name varchar(128) 缺陷标题|project_id bigint 项目 ID|product_id bigint 产品 ID|severity varchar(16) 严重级别|reporter_emp_id bigint 报告人员工 ID|assignee_emp_id bigint 修复人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| bug_code | 缺陷编号 | `varchar(32)` | 是 | - | 否 |
| bug_name | 缺陷标题 | `varchar(128)` | 是 | - | 否 |
| project_id | 项目 ID | `bigint` | 否 | - | 否 |
| product_id | 产品 ID | `bigint` | 否 | - | 否 |
| severity | 严重级别 | `varchar(16)` | 否 | - | 否 |
| reporter_emp_id | 报告人员工 ID | `bigint` | 否 | - | 否 |
| assignee_emp_id | 修复人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## qa_release_gate

发布门禁检查
id bigint 主键|system_id bigint 系统 ID|version_no varchar(32) 版本|gate_name varchar(64) 门禁项|passed boolean 是否通过|checked_by bigint 检查人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| system_id | 系统 ID | `bigint` | 否 | - | 否 |
| version_no | 版本 | `varchar(32)` | 否 | - | 否 |
| gate_name | 门禁项 | `varchar(64)` | 否 | - | 否 |
| passed | 是否通过 | `boolean` | 否 | - | 否 |
| checked_by | 检查人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## qa_test_case

测试用例
id bigint 主键|plan_id bigint 计划 ID|case_code varchar(32) 用例编码|case_name varchar(256) 用例名称|priority varchar(16) 优先级|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| plan_id | 计划 ID | `bigint` | 是 | - | 否 |
| case_code | 用例编码 | `varchar(32)` | 否 | - | 否 |
| case_name | 用例名称 | `varchar(256)` | 否 | - | 否 |
| priority | 优先级 | `varchar(16)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## qa_test_plan

测试计划
id bigint 主键|plan_code varchar(32) 计划编码|plan_name varchar(128) 计划名称|project_id bigint 项目 ID|product_id bigint 产品 ID|owner_emp_id bigint 测试负责人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| plan_code | 计划编码 | `varchar(32)` | 是 | - | 否 |
| plan_name | 计划名称 | `varchar(128)` | 是 | - | 否 |
| project_id | 项目 ID | `bigint` | 否 | - | 否 |
| product_id | 产品 ID | `bigint` | 否 | - | 否 |
| owner_emp_id | 测试负责人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_channel

销售渠道
id bigint 主键|channel_code varchar(32) 渠道编码|channel_name varchar(128) 渠道名称|channel_type varchar(32) 渠道类型|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| channel_code | 渠道编码 | `varchar(32)` | 是 | - | 否 |
| channel_name | 渠道名称 | `varchar(128)` | 是 | - | 否 |
| channel_type | 渠道类型 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_commission

销售提成明细
id bigint 主键|emp_id bigint 销售员工 ID|order_id bigint 订单 ID|year_month varchar(7) 年月|amount numeric(14,2) 提成金额|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 销售员工 ID | `bigint` | 是 | - | 否 |
| order_id | 订单 ID | `bigint` | 否 | - | 否 |
| year_month | 年月 | `varchar(7)` | 否 | - | 否 |
| amount | 提成金额 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_commission_rule

销售提成规则
id bigint 主键|rule_code varchar(32) 规则编码|rule_name varchar(128) 规则名称|rate_pct numeric(6,2) 提成比例|product_id bigint 适用产品 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| rule_code | 规则编码 | `varchar(32)` | 是 | - | 否 |
| rule_name | 规则名称 | `varchar(128)` | 是 | - | 否 |
| rate_pct | 提成比例 | `numeric(6,2)` | 否 | - | 否 |
| product_id | 适用产品 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_contract

销售合同
id bigint 主键|contract_code varchar(32) 合同编号|contract_name varchar(128) 合同名称|customer_id bigint 客户 ID|order_id bigint 关联订单 ID|sign_date date 签订日期|amount numeric(14,2) 合同金额|owner_emp_id bigint 负责销售员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| contract_code | 合同编号 | `varchar(32)` | 是 | - | 否 |
| contract_name | 合同名称 | `varchar(128)` | 是 | - | 否 |
| customer_id | 客户 ID | `bigint` | 否 | - | 否 |
| order_id | 关联订单 ID | `bigint` | 否 | - | 否 |
| sign_date | 签订日期 | `date` | 否 | - | 否 |
| amount | 合同金额 | `numeric(14,2)` | 否 | - | 否 |
| owner_emp_id | 负责销售员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_contract_milestone

合同里程碑收款
id bigint 主键|contract_id bigint 合同 ID|milestone_name varchar(128) 里程碑名称|due_date date 应收日期|amount numeric(14,2) 应收金额|received_amount numeric(14,2) 已收金额|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| contract_id | 合同 ID | `bigint` | 是 | - | 否 |
| milestone_name | 里程碑名称 | `varchar(128)` | 否 | - | 否 |
| due_date | 应收日期 | `date` | 否 | - | 否 |
| amount | 应收金额 | `numeric(14,2)` | 否 | - | 否 |
| received_amount | 已收金额 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_delivery

发货/交付单
id bigint 主键|delivery_code varchar(32) 交付单号|delivery_name varchar(128) 交付说明|order_id bigint 订单 ID|delivery_date date 交付日期|receiver varchar(64) 收货人|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| delivery_code | 交付单号 | `varchar(32)` | 是 | - | 否 |
| delivery_name | 交付说明 | `varchar(128)` | 是 | - | 否 |
| order_id | 订单 ID | `bigint` | 否 | - | 否 |
| delivery_date | 交付日期 | `date` | 否 | - | 否 |
| receiver | 收货人 | `varchar(64)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_delivery_item

交付明细
id bigint 主键|delivery_id bigint 交付单 ID|product_id bigint 产品 ID|qty numeric(12,2) 数量|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| delivery_id | 交付单 ID | `bigint` | 是 | - | 否 |
| product_id | 产品 ID | `bigint` | 否 | - | 否 |
| qty | 数量 | `numeric(12,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_price_list

价格表
id bigint 主键|plist_code varchar(32) 价格表编码|plist_name varchar(128) 价格表名称|currency varchar(8) 币种|effective_from date 生效起|effective_to date 生效止|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| plist_code | 价格表编码 | `varchar(32)` | 是 | - | 否 |
| plist_name | 价格表名称 | `varchar(128)` | 是 | - | 否 |
| currency | 币种 | `varchar(8)` | 否 | - | 否 |
| effective_from | 生效起 | `date` | 否 | - | 否 |
| effective_to | 生效止 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_price_list_item

价格表明细
id bigint 主键|plist_id bigint 价格表 ID|product_id bigint 产品 ID|unit_price numeric(14,2) 单价|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| plist_id | 价格表 ID | `bigint` | 是 | - | 否 |
| product_id | 产品 ID | `bigint` | 是 | - | 否 |
| unit_price | 单价 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_quote

销售报价单
id bigint 主键|quote_code varchar(32) 报价单号|quote_name varchar(128) 报价名称|customer_id bigint 客户 ID|owner_emp_id bigint 销售员工 ID|total_amount numeric(14,2) 总金额|valid_until date 有效期至|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| quote_code | 报价单号 | `varchar(32)` | 是 | - | 否 |
| quote_name | 报价名称 | `varchar(128)` | 是 | - | 否 |
| customer_id | 客户 ID | `bigint` | 否 | - | 否 |
| owner_emp_id | 销售员工 ID | `bigint` | 否 | - | 否 |
| total_amount | 总金额 | `numeric(14,2)` | 否 | - | 否 |
| valid_until | 有效期至 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_quote_item

报价明细
id bigint 主键|quote_id bigint 报价单 ID|product_id bigint 产品 ID|qty numeric(12,2) 数量|unit_price numeric(14,2) 单价|amount numeric(14,2) 金额|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| quote_id | 报价单 ID | `bigint` | 是 | - | 否 |
| product_id | 产品 ID | `bigint` | 否 | - | 否 |
| qty | 数量 | `numeric(12,2)` | 否 | - | 否 |
| unit_price | 单价 | `numeric(14,2)` | 否 | - | 否 |
| amount | 金额 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_return

退货单
id bigint 主键|return_code varchar(32) 退货单号|return_name varchar(128) 退货说明|order_id bigint 订单 ID|return_date date 退货日期|reason varchar(256) 原因|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| return_code | 退货单号 | `varchar(32)` | 是 | - | 否 |
| return_name | 退货说明 | `varchar(128)` | 是 | - | 否 |
| order_id | 订单 ID | `bigint` | 否 | - | 否 |
| return_date | 退货日期 | `date` | 否 | - | 否 |
| reason | 原因 | `varchar(256)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sal_target

销售目标
id bigint 主键|emp_id bigint 销售员工 ID|dept_id bigint 部门 ID|year_month varchar(7) 年月|target_amount numeric(14,2) 目标金额|actual_amount numeric(14,2) 实际金额|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| emp_id | 销售员工 ID | `bigint` | 否 | - | 否 |
| dept_id | 部门 ID | `bigint` | 否 | - | 否 |
| year_month | 年月 | `varchar(7)` | 否 | - | 否 |
| target_amount | 目标金额 | `numeric(14,2)` | 否 | - | 否 |
| actual_amount | 实际金额 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## scm_inventory

库存台账
id bigint 主键|warehouse_id bigint 仓库 ID|sku_code varchar(64) SKU 编码|sku_name varchar(128) SKU 名称|qty_on_hand numeric(14,2) 在库数量|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| warehouse_id | 仓库 ID | `bigint` | 是 | - | 否 |
| sku_code | SKU 编码 | `varchar(64)` | 否 | - | 否 |
| sku_name | SKU 名称 | `varchar(128)` | 否 | - | 否 |
| qty_on_hand | 在库数量 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## scm_inventory_txn

库存流水
id bigint 主键|warehouse_id bigint 仓库 ID|sku_code varchar(64) SKU|txn_type varchar(16) 出入库类型|qty numeric(14,2) 数量|txn_date date 日期|ref_no varchar(64) 来源单号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| warehouse_id | 仓库 ID | `bigint` | 是 | - | 否 |
| sku_code | SKU | `varchar(64)` | 否 | - | 否 |
| txn_type | 出入库类型 | `varchar(16)` | 否 | - | 否 |
| qty | 数量 | `numeric(14,2)` | 否 | - | 否 |
| txn_date | 日期 | `date` | 否 | - | 否 |
| ref_no | 来源单号 | `varchar(64)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## scm_material

物料主数据
id bigint 主键|mat_code varchar(32) 物料编码|mat_name varchar(128) 物料名称|uom varchar(16) 计量单位|category varchar(32) 物料类别|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| mat_code | 物料编码 | `varchar(32)` | 是 | - | 否 |
| mat_name | 物料名称 | `varchar(128)` | 是 | - | 否 |
| uom | 计量单位 | `varchar(16)` | 否 | - | 否 |
| category | 物料类别 | `varchar(32)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## scm_purchase_order

采购订单
id bigint 主键|po_code varchar(32) 采购订单号|po_name varchar(128) 订单说明|vendor_id bigint 供应商 ID|req_id bigint 来源申请 ID|total_amount numeric(14,2) 订单金额|buyer_emp_id bigint 采购员员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| po_code | 采购订单号 | `varchar(32)` | 是 | - | 否 |
| po_name | 订单说明 | `varchar(128)` | 是 | - | 否 |
| vendor_id | 供应商 ID | `bigint` | 否 | - | 否 |
| req_id | 来源申请 ID | `bigint` | 否 | - | 否 |
| total_amount | 订单金额 | `numeric(14,2)` | 否 | - | 否 |
| buyer_emp_id | 采购员员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## scm_purchase_order_item

采购订单明细
id bigint 主键|po_id bigint 采购订单 ID|item_name varchar(128) 物资名称|qty numeric(12,2) 数量|unit_price numeric(14,2) 单价|amount numeric(14,2) 金额|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| po_id | 采购订单 ID | `bigint` | 是 | - | 否 |
| item_name | 物资名称 | `varchar(128)` | 否 | - | 否 |
| qty | 数量 | `numeric(12,2)` | 否 | - | 否 |
| unit_price | 单价 | `numeric(14,2)` | 否 | - | 否 |
| amount | 金额 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## scm_purchase_req

采购申请
id bigint 主键|req_code varchar(32) 申请单号|req_name varchar(128) 申请标题|applicant_emp_id bigint 申请人员工 ID|dept_id bigint 申请部门 ID|total_amount numeric(14,2) 预估金额|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| req_code | 申请单号 | `varchar(32)` | 是 | - | 否 |
| req_name | 申请标题 | `varchar(128)` | 是 | - | 否 |
| applicant_emp_id | 申请人员工 ID | `bigint` | 否 | - | 否 |
| dept_id | 申请部门 ID | `bigint` | 否 | - | 否 |
| total_amount | 预估金额 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## scm_purchase_req_item

采购申请明细
id bigint 主键|req_id bigint 申请单 ID|item_name varchar(128) 物资名称|qty numeric(12,2) 数量|unit_price numeric(14,2) 预估单价|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| req_id | 申请单 ID | `bigint` | 是 | - | 否 |
| item_name | 物资名称 | `varchar(128)` | 否 | - | 否 |
| qty | 数量 | `numeric(12,2)` | 否 | - | 否 |
| unit_price | 预估单价 | `numeric(14,2)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## scm_receipt

采购入库单
id bigint 主键|grn_code varchar(32) 入库单号|grn_name varchar(128) 说明|po_id bigint 采购订单 ID|receipt_date date 入库日期|warehouse_id bigint 仓库 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| grn_code | 入库单号 | `varchar(32)` | 是 | - | 否 |
| grn_name | 说明 | `varchar(128)` | 是 | - | 否 |
| po_id | 采购订单 ID | `bigint` | 否 | - | 否 |
| receipt_date | 入库日期 | `date` | 否 | - | 否 |
| warehouse_id | 仓库 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## scm_vendor_eval

供应商评价
id bigint 主键|vendor_id bigint 供应商 ID|year_month varchar(7) 年月|score numeric(6,2) 得分|evaluator_emp_id bigint 评价人员工 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| vendor_id | 供应商 ID | `bigint` | 是 | - | 否 |
| year_month | 年月 | `varchar(7)` | 否 | - | 否 |
| score | 得分 | `numeric(6,2)` | 否 | - | 否 |
| evaluator_emp_id | 评价人员工 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## scm_warehouse

仓库
id bigint 主键|wh_code varchar(32) 仓库编码|wh_name varchar(128) 仓库名称|office_id bigint 职场 ID|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| wh_code | 仓库编码 | `varchar(32)` | 是 | - | 否 |
| wh_name | 仓库名称 | `varchar(128)` | 是 | - | 否 |
| office_id | 职场 ID | `bigint` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sec_audit_log

安全审计日志
id bigint 主键|system_id bigint 系统 ID|emp_id bigint 操作人员工 ID|action varchar(64) 动作|acted_at timestamp 操作时间|ip_addr varchar(64) IP|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| system_id | 系统 ID | `bigint` | 否 | - | 否 |
| emp_id | 操作人员工 ID | `bigint` | 否 | - | 否 |
| action | 动作 | `varchar(64)` | 否 | - | 否 |
| acted_at | 操作时间 | `timestamp` | 否 | - | 否 |
| ip_addr | IP | `varchar(64)` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sec_data_class

数据分级分类
id bigint 主键|class_code varchar(32) 分类编码|class_name varchar(128) 分类名称|level_no integer 密级序号|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| class_code | 分类编码 | `varchar(32)` | 是 | - | 否 |
| class_name | 分类名称 | `varchar(128)` | 是 | - | 否 |
| level_no | 密级序号 | `integer` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sec_policy

安全策略
id bigint 主键|pol_code varchar(32) 策略编码|pol_name varchar(128) 策略名称|policy_type varchar(32) 策略类型|content text 策略内容|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| pol_code | 策略编码 | `varchar(32)` | 是 | - | 否 |
| pol_name | 策略名称 | `varchar(128)` | 是 | - | 否 |
| policy_type | 策略类型 | `varchar(32)` | 否 | - | 否 |
| content | 策略内容 | `text` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## sec_vulnerability

漏洞台账
id bigint 主键|vuln_code varchar(32) 漏洞编号|vuln_name varchar(128) 漏洞标题|system_id bigint 系统 ID|severity varchar(16) 严重级别|discovered_at date 发现日期|fixed_at date 修复日期|status varchar(16) 状态|remark varchar(256) 备注|created_at timestamp 创建时间|updated_at timestamp 更新时间

| 列 | 字段说明 | 字段类型 | 是否必须 | 默认值 | 是否主键 |
|----|----------|----------|----------|--------|----------|
| id | 主键 | `bigint` | 是 | 自增 | 是 |
| vuln_code | 漏洞编号 | `varchar(32)` | 是 | - | 否 |
| vuln_name | 漏洞标题 | `varchar(128)` | 是 | - | 否 |
| system_id | 系统 ID | `bigint` | 否 | - | 否 |
| severity | 严重级别 | `varchar(16)` | 否 | - | 否 |
| discovered_at | 发现日期 | `date` | 否 | - | 否 |
| fixed_at | 修复日期 | `date` | 否 | - | 否 |
| status | 状态 | `varchar(16)` | 是 | active | 否 |
| remark | 备注 | `varchar(256)` | 否 | - | 否 |
| created_at | 创建时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |
| updated_at | 更新时间 | `timestamp` | 是 | CURRENT_TIMESTAMP | 否 |

## 关联关系（全量外键）

> 以库内实际 FOREIGN KEY 为准，共 **253** 条。
> 按子表分组的可读版见 [table-relations.md](./table-relations.md)。

| 从表.列 | 主表.列 |
|---------|---------|
| adm_meeting_booking.organizer_emp_id | hr_employee.id |
| adm_meeting_booking.room_id | adm_meeting_room.id |
| adm_meeting_room.office_id | org_office.id |
| adm_supply_request.emp_id | hr_employee.id |
| adm_supply_request.supply_id | adm_supply.id |
| adm_vehicle_trip.driver_emp_id | hr_employee.id |
| adm_vehicle_trip.vehicle_id | adm_vehicle.id |
| adm_visitor.host_emp_id | hr_employee.id |
| adm_visitor.office_id | org_office.id |
| att_daily_record.emp_id | hr_employee.id |
| att_device.office_id | org_office.id |
| att_leave.approved_by | hr_employee.id |
| att_leave.emp_id | hr_employee.id |
| att_leave.leave_type_id | att_leave_type.id |
| att_leave_balance.emp_id | hr_employee.id |
| att_leave_balance.leave_type_id | att_leave_type.id |
| att_makeup_card.emp_id | hr_employee.id |
| att_monthly_summary.emp_id | hr_employee.id |
| att_overtime.emp_id | hr_employee.id |
| att_overtime.project_id | prj_project.id |
| att_punch.emp_id | hr_employee.id |
| att_punch.office_id | org_office.id |
| att_remote_work.emp_id | hr_employee.id |
| att_shift_assign.emp_id | hr_employee.id |
| att_shift_assign.shift_id | att_shift.id |
| att_timesheet.emp_id | hr_employee.id |
| att_timesheet.project_id | prj_project.id |
| att_travel.emp_id | hr_employee.id |
| att_travel.project_id | prj_project.id |
| crm_activity.customer_id | crm_customer.id |
| crm_activity.emp_id | hr_employee.id |
| crm_activity.opp_id | crm_opportunity.id |
| crm_complaint.customer_id | crm_customer.id |
| crm_complaint.handler_emp_id | hr_employee.id |
| crm_complaint.project_id | prj_project.id |
| crm_contact.customer_id | crm_customer.id |
| crm_customer.owner_emp_id | hr_employee.id |
| crm_lead.customer_id | crm_customer.id |
| crm_lead.owner_emp_id | hr_employee.id |
| crm_opportunity.customer_id | crm_customer.id |
| crm_opportunity.owner_emp_id | hr_employee.id |
| crm_sla.customer_id | crm_customer.id |
| crm_visit.customer_id | crm_customer.id |
| crm_visit.emp_id | hr_employee.id |
| fin_activity_budget.dept_id | org_department.id |
| fin_activity_budget.owner_emp_id | hr_employee.id |
| fin_activity_expense.budget_id | fin_activity_budget.id |
| fin_asset_depr.asset_id | fin_fixed_asset.id |
| fin_bank_account.company_id | org_company.id |
| fin_bank_txn.acct_id | fin_bank_account.id |
| fin_budget_line.budget_id | fin_budget_year.id |
| fin_budget_year.dept_id | org_department.id |
| fin_cost_allocation.from_dept_id | org_department.id |
| fin_cost_allocation.to_dept_id | org_department.id |
| fin_fixed_asset.custodian_emp_id | hr_employee.id |
| fin_fixed_asset.dept_id | org_department.id |
| fin_invoice.customer_id | crm_customer.id |
| fin_invoice.vendor_id | fin_vendor.id |
| fin_journal.created_by | hr_employee.id |
| fin_journal_line.acct_id | fin_gl_account.id |
| fin_journal_line.journal_id | fin_journal.id |
| fin_loan.emp_id | hr_employee.id |
| fin_loan_repay.loan_id | fin_loan.id |
| fin_loan_repay.reimburse_id | fin_reimburse.id |
| fin_payment.applicant_emp_id | hr_employee.id |
| fin_payment.vendor_id | fin_vendor.id |
| fin_petty_cash.dept_id | org_department.id |
| fin_petty_cash.keeper_emp_id | hr_employee.id |
| fin_petty_cash_txn.petty_id | fin_petty_cash.id |
| fin_receipt.customer_id | crm_customer.id |
| fin_receipt.project_id | prj_project.id |
| fin_reimburse.dept_id | org_department.id |
| fin_reimburse.emp_id | hr_employee.id |
| fin_reimburse.project_id | prj_project.id |
| fin_reimburse_item.claim_id | fin_reimburse.id |
| fin_salary_slip.dept_id | org_department.id |
| fin_salary_slip.emp_id | hr_employee.id |
| fin_salary_slip.period_id | fin_salary_period.id |
| hr_award.emp_id | hr_employee.id |
| hr_bank_account.emp_id | hr_employee.id |
| hr_certificate.emp_id | hr_employee.id |
| hr_contract.emp_id | hr_employee.id |
| hr_contract.sign_company_id | org_company.id |
| hr_education.emp_id | hr_employee.id |
| hr_emergency_contact.emp_id | hr_employee.id |
| hr_employee.dept_id | org_department.id |
| hr_employee.job_level_id | hr_job_level.id |
| hr_family_member.emp_id | hr_employee.id |
| hr_headcount_plan.dept_id | org_department.id |
| hr_interview.candidate_id | hr_candidate.id |
| hr_interview.interviewer_emp_id | hr_employee.id |
| hr_interview.req_id | hr_recruit_req.id |
| hr_offer.candidate_id | hr_candidate.id |
| hr_offer.req_id | hr_recruit_req.id |
| hr_onboarding.emp_id | hr_employee.id |
| hr_performance_goal.cycle_id | hr_performance_cycle.id |
| hr_performance_goal.emp_id | hr_employee.id |
| hr_performance_review.cycle_id | hr_performance_cycle.id |
| hr_performance_review.emp_id | hr_employee.id |
| hr_performance_review.reviewer_emp_id | hr_employee.id |
| hr_probation.emp_id | hr_employee.id |
| hr_probation.mentor_emp_id | hr_employee.id |
| hr_promotion.emp_id | hr_employee.id |
| hr_promotion.from_level_id | hr_job_level.id |
| hr_promotion.to_level_id | hr_job_level.id |
| hr_recruit_req.dept_id | org_department.id |
| hr_recruit_req.job_level_id | hr_job_level.id |
| hr_recruit_req.owner_emp_id | hr_employee.id |
| hr_resignation.emp_id | hr_employee.id |
| hr_training_enroll.emp_id | hr_employee.id |
| hr_training_enroll.session_id | hr_training_session.id |
| hr_training_session.course_id | hr_training_course.id |
| hr_transfer.emp_id | hr_employee.id |
| hr_transfer.from_dept_id | org_department.id |
| hr_transfer.to_dept_id | org_department.id |
| hr_work_history.emp_id | hr_employee.id |
| itm_access_request.emp_id | hr_employee.id |
| itm_access_request.system_id | itm_system.id |
| itm_account.emp_id | hr_employee.id |
| itm_account.system_id | itm_system.id |
| itm_asset.assignee_emp_id | hr_employee.id |
| itm_asset.office_id | org_office.id |
| itm_asset_assign.asset_id | itm_asset.id |
| itm_asset_assign.emp_id | hr_employee.id |
| itm_change.applicant_emp_id | hr_employee.id |
| itm_change.system_id | itm_system.id |
| itm_deploy.operator_emp_id | hr_employee.id |
| itm_deploy.system_id | itm_system.id |
| itm_incident.commander_emp_id | hr_employee.id |
| itm_incident.system_id | itm_system.id |
| itm_system.owner_emp_id | hr_employee.id |
| itm_ticket.assignee_emp_id | hr_employee.id |
| itm_ticket.requester_emp_id | hr_employee.id |
| itm_ticket_comment.author_emp_id | hr_employee.id |
| itm_ticket_comment.ticket_id | itm_ticket.id |
| kb_article.author_emp_id | hr_employee.id |
| kb_article_tag_rel.article_id | kb_article.id |
| kb_article_tag_rel.tag_id | kb_article_tag.id |
| kb_article_tag_rel.tagged_by | hr_employee.id |
| legal_compliance_check.owner_emp_id | hr_employee.id |
| legal_contract.customer_id | crm_customer.id |
| legal_contract.owner_emp_id | hr_employee.id |
| legal_contract.vendor_id | fin_vendor.id |
| legal_contract_clause.contract_id | legal_contract.id |
| legal_dispute.contract_id | legal_contract.id |
| mkt_campaign.owner_emp_id | hr_employee.id |
| mkt_campaign_lead.camp_id | mkt_campaign.id |
| mkt_campaign_lead.lead_id | crm_lead.id |
| mkt_content.author_emp_id | hr_employee.id |
| mkt_event_reg.camp_id | mkt_campaign.id |
| ops_backup_job.system_id | itm_system.id |
| ops_duty_roster.emp_id | hr_employee.id |
| ops_duty_roster.system_id | itm_system.id |
| ops_monitor_alert.acked_by | hr_employee.id |
| ops_monitor_alert.system_id | itm_system.id |
| ops_runbook.owner_emp_id | hr_employee.id |
| ops_runbook.system_id | itm_system.id |
| org_announcement.publisher_emp_id | hr_employee.id |
| org_biz_unit.leader_emp_id | hr_employee.id |
| org_cost_center.dept_id | org_department.id |
| org_cost_center.owner_emp_id | hr_employee.id |
| org_department.parent_id | org_department.id |
| org_dept_change.dept_id | org_department.id |
| org_dept_change.operator_emp_id | hr_employee.id |
| org_dept_closure.ancestor_id | org_department.id |
| org_dept_closure.descendant_id | org_department.id |
| org_office.company_id | org_company.id |
| org_position.dept_id | org_department.id |
| org_position.job_level_id | hr_job_level.id |
| org_seal.company_id | org_company.id |
| org_seal.keeper_emp_id | hr_employee.id |
| prd_feature.product_id | prd_product.id |
| prd_license.customer_id | crm_customer.id |
| prd_license.product_id | prd_product.id |
| prd_product_cost.product_id | prd_product.id |
| prd_product_line.owner_emp_id | hr_employee.id |
| prd_product_version.product_id | prd_product.id |
| prd_roadmap.product_id | prd_product.id |
| prj_acceptance.project_id | prj_project.id |
| prj_change_request.project_id | prj_project.id |
| prj_change_request.requester_emp_id | hr_employee.id |
| prj_document.project_id | prj_project.id |
| prj_document.uploader_emp_id | hr_employee.id |
| prj_issue.assignee_emp_id | hr_employee.id |
| prj_issue.project_id | prj_project.id |
| prj_issue.reporter_emp_id | hr_employee.id |
| prj_milestone.project_id | prj_project.id |
| prj_project.customer_id | crm_customer.id |
| prj_project.dept_id | org_department.id |
| prj_project.pm_emp_id | hr_employee.id |
| prj_project_member.emp_id | hr_employee.id |
| prj_project_member.project_id | prj_project.id |
| prj_project_revenue.project_id | prj_project.id |
| prj_risk.owner_emp_id | hr_employee.id |
| prj_risk.project_id | prj_project.id |
| prj_stakeholder.emp_id | hr_employee.id |
| prj_stakeholder.project_id | prj_project.id |
| prj_task.assignee_emp_id | hr_employee.id |
| prj_task.project_id | prj_project.id |
| prj_warranty.project_id | prj_project.id |
| prj_weekly_report.author_emp_id | hr_employee.id |
| prj_weekly_report.project_id | prj_project.id |
| qa_defect.assignee_emp_id | hr_employee.id |
| qa_defect.product_id | prd_product.id |
| qa_defect.project_id | prj_project.id |
| qa_defect.reporter_emp_id | hr_employee.id |
| qa_release_gate.checked_by | hr_employee.id |
| qa_release_gate.system_id | itm_system.id |
| qa_test_case.plan_id | qa_test_plan.id |
| qa_test_plan.owner_emp_id | hr_employee.id |
| qa_test_plan.product_id | prd_product.id |
| qa_test_plan.project_id | prj_project.id |
| sal_commission.emp_id | hr_employee.id |
| sal_commission.order_id | sal_sales_order.id |
| sal_commission_rule.product_id | prd_product.id |
| sal_contract.customer_id | crm_customer.id |
| sal_contract.order_id | sal_sales_order.id |
| sal_contract.owner_emp_id | hr_employee.id |
| sal_contract_milestone.contract_id | sal_contract.id |
| sal_delivery.order_id | sal_sales_order.id |
| sal_delivery_item.delivery_id | sal_delivery.id |
| sal_delivery_item.product_id | prd_product.id |
| sal_price_list_item.plist_id | sal_price_list.id |
| sal_price_list_item.product_id | prd_product.id |
| sal_quote.customer_id | crm_customer.id |
| sal_quote.owner_emp_id | hr_employee.id |
| sal_quote_item.product_id | prd_product.id |
| sal_quote_item.quote_id | sal_quote.id |
| sal_return.order_id | sal_sales_order.id |
| sal_sales_order.customer_id | crm_customer.id |
| sal_sales_order.dept_id | org_department.id |
| sal_sales_order.owner_emp_id | hr_employee.id |
| sal_sales_order_item.order_id | sal_sales_order.id |
| sal_sales_order_item.product_id | prd_product.id |
| sal_target.dept_id | org_department.id |
| sal_target.emp_id | hr_employee.id |
| scm_inventory.warehouse_id | scm_warehouse.id |
| scm_inventory_txn.warehouse_id | scm_warehouse.id |
| scm_purchase_order.buyer_emp_id | hr_employee.id |
| scm_purchase_order.req_id | scm_purchase_req.id |
| scm_purchase_order.vendor_id | fin_vendor.id |
| scm_purchase_order_item.po_id | scm_purchase_order.id |
| scm_purchase_req.applicant_emp_id | hr_employee.id |
| scm_purchase_req.dept_id | org_department.id |
| scm_purchase_req_item.req_id | scm_purchase_req.id |
| scm_receipt.po_id | scm_purchase_order.id |
| scm_receipt.warehouse_id | scm_warehouse.id |
| scm_vendor_eval.evaluator_emp_id | hr_employee.id |
| scm_vendor_eval.vendor_id | fin_vendor.id |
| scm_warehouse.office_id | org_office.id |
| sec_audit_log.emp_id | hr_employee.id |
| sec_audit_log.system_id | itm_system.id |
| sec_vulnerability.system_id | itm_system.id |
