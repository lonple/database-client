package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * SQL 批执行结果：可含多条语句结果；遇错停止时 {@link #stoppedOnError} 为 true。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ExecuteResult {

    /** 本批语句总数（解析后） */
    private int totalCount;

    /** 成功执行条数 */
    private int successCount;

    /** 是否因错误中止后续语句 */
    private boolean stoppedOnError;

    /** 批摘要 / 中止原因 */
    private String message;

    /** 整批耗时 */
    private long elapsedMs;

    /** 工作台会话 ID（回传） */
    private String sessionId;

    /** 是否手动提交模式 */
    private boolean manualMode;

    /** 当前是否处于事务中（持有租约） */
    private boolean inTransaction;

    /** 各语句结果（含中止那条的失败信息） */
    private List<StatementResult> statements;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class StatementResult {

        /** 从 1 开始 */
        private int index;

        /** 语句预览（过长截断） */
        private String sqlPreview;

        private String statementType;
        private List<ColumnMeta> columns;
        private List<List<Object>> rows;
        private int rowCount;
        private boolean truncated;
        private long elapsedMs;
        private Integer affectedRows;
        private boolean success;
        private String message;

        /**
         * 日志级别：SUCCESS / WARN / ERROR。
         * ALERT 策略命中且仍执行成功时为 WARN。
         */
        private String severity;

        /** 命中的全局策略动作：BLOCK / ALERT / REAUTH，可空 */
        private String globalPolicyAction;

        /** 命中的全局策略名称，可空 */
        private String globalPolicyName;

        /** 拒绝类型：CONNECTION / MEMBER / OP / OBJECT / POLICY / OTHER */
        private String denyType;

        /** 权限不足涉及的资产对象 */
        private List<String> denyObjects;

        /** 缺失的操作权限 */
        private List<String> missingOps;

        /** 当前连接上已有的操作（便于对照） */
        private List<String> grantedOps;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ColumnMeta {
        private String name;
        private String type;
    }
}
