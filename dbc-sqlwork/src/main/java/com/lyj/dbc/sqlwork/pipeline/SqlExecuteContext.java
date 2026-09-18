package com.lyj.dbc.sqlwork.pipeline;

import com.lyj.dbc.sqlwork.api.vo.AuthzEvaluateResult;
import lombok.Builder;
import lombok.Data;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 一次批执行上下文：鉴权/执行只写入句级项，审计 Stage 只读上报。
 */
@Data
@Builder
public class SqlExecuteContext {

    private String batchId;
    private Long operatorUserId;
    private String operatorUsername;
    private String clientIp;
    private Long workspaceId;
    private String workspaceName;
    private Long connectionId;
    private String connectionName;
    private String dbType;

    @Builder.Default
    private List<StatementAuditItem> statements = new ArrayList<>();

    @Data
    @Builder
    public static class StatementAuditItem {
        private int statementIndex;
        private String sqlText;
        private String statementType;
        private boolean success;
        private long elapsedMs;
        private String message;
        private String denyType;
        private List<String> denyObjects;
        private List<String> missingOps;
        private String globalPolicyAction;
        private String globalPolicyName;

        public static StatementAuditItem fromAuthzFail(int index, String sql, String statementType,
                                                       String message, AuthzEvaluateResult authz) {
            return StatementAuditItem.builder()
                    .statementIndex(index)
                    .sqlText(sql)
                    .statementType(statementType)
                    .success(false)
                    .elapsedMs(0)
                    .message(message)
                    .denyType(authz == null ? null : authz.getDenyType())
                    .denyObjects(authz == null ? null : authz.getDenyObjects())
                    .missingOps(authz == null ? null : authz.getMissingOps())
                    .globalPolicyAction(authz == null ? null : authz.getGlobalPolicyAction())
                    .globalPolicyName(authz == null ? null : authz.getGlobalPolicyName())
                    .build();
        }

        public Map<String, Object> toFailDetail() {
            if (success) {
                return null;
            }
            LinkedHashMap<String, Object> m = new LinkedHashMap<>();
            if (denyType != null) {
                m.put("denyType", denyType);
            }
            if (denyObjects != null && !denyObjects.isEmpty()) {
                m.put("denyObjects", denyObjects);
            }
            if (missingOps != null && !missingOps.isEmpty()) {
                m.put("missingOps", missingOps);
            }
            if (globalPolicyAction != null) {
                m.put("globalPolicyAction", globalPolicyAction);
            }
            if (globalPolicyName != null) {
                m.put("globalPolicyName", globalPolicyName);
            }
            if (message != null) {
                m.put("message", message);
            }
            return m.isEmpty() ? null : m;
        }
    }
}
