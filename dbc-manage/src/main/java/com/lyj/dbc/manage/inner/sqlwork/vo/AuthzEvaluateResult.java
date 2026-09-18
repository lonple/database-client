package com.lyj.dbc.manage.inner.sqlwork.vo;

import com.lyj.dbc.manage.inner.sqlwork.dto.AuthzEvaluateRequest;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 鉴权裁决结果（与 sqlwork 客户端字段一致）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuthzEvaluateResult {

    private boolean allowed;
    private String message;
    private boolean connectionAllowed;
    private List<String> grantedOps;
    /** null 表示连接上全部表；非空为可访问表集合（TABLE 级白名单，兼容旧逻辑） */
    private List<AuthzEvaluateRequest.TableRef> filterTables;
    /** 工作台对象树可见性；优先于仅依赖 filterTables 的裁剪 */
    private ObjectFilter objectFilter;

    /** NONE / BLOCK / ALERT / REAUTH */
    private String globalPolicyAction;
    private Long globalPolicyId;
    private String globalPolicyName;
    /** REAUTH 且未带有效 ticket 时为 true */
    private boolean needReauth;

    /**
     * 拒绝类型：CONNECTION / MEMBER / OP / OBJECT / POLICY / OTHER
     */
    private String denyType;

    /** 未授权或权限不足的资产对象展示名，如 public.t_order */
    private List<String> denyObjects;

    /** 缺失的操作权限，如 SELECT / INSERT */
    private List<String> missingOps;
}
