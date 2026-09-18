package com.lyj.dbc.sqlwork.api.vo;

import com.lyj.dbc.sqlwork.api.dto.AuthzEvaluateRequest;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 鉴权裁决结果。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AuthzEvaluateResult {

    private boolean allowed;
    private String message;
    private boolean connectionAllowed;
    private List<String> grantedOps;
    /** null 表示连接上全部表；非空为可访问表集合（TABLE 级白名单，兼容旧逻辑） */
    private List<AuthzEvaluateRequest.TableRef> filterTables;
    /** 工作台对象树可见性 */
    private ObjectFilter objectFilter;

    private String globalPolicyAction;
    private Long globalPolicyId;
    private String globalPolicyName;
    private boolean needReauth;

    /** CONNECTION / MEMBER / OP / OBJECT / POLICY / OTHER */
    private String denyType;
    private List<String> denyObjects;
    private List<String> missingOps;
}
