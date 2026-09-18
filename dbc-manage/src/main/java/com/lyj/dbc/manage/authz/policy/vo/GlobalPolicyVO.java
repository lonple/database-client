package com.lyj.dbc.manage.authz.policy.vo;

import lombok.Builder;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.List;

/**
 * 全局管控策略视图。
 */
@Data
@Builder
public class GlobalPolicyVO {
    private Long id;
    private String name;
    private List<String> ops;
    private String strategy;
    private String workspaceScope;
    private List<Long> workspaceIds;
    private Integer sortNo;
    private Integer status;
    private OffsetDateTime updatedAt;
}
