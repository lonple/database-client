package com.lyj.dbc.manage.authz.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

/**
 * 工作空间列表项。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WorkspaceListItemVO {

    private Long id;
    private String name;
    private String description;
    private Long ownerUserId;
    private String spaceType;
    private String myRole;
    private long memberCount;
    private long assetCount;
    private OffsetDateTime updatedAt;
}
