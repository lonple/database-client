package com.lyj.dbc.knowledge.knowledge.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

@Data
@TableName("t_knowledge_vector_sync_event")
public class VectorSyncEvent {
    public static final String OP_UPSERT = "UPSERT";
    public static final String OP_DELETE = "DELETE";
    public static final String STATUS_PENDING = "PENDING";
    public static final String STATUS_SUCCESS = "SUCCESS";
    public static final String STATUS_FAILED = "FAILED";

    public static final String DOC_SYNC_NONE = "NONE";
    public static final String DOC_SYNC_PENDING = "PENDING";
    public static final String DOC_SYNC_SYNCED = "SYNCED";
    public static final String DOC_SYNC_UNSYNCED = "UNSYNCED";

    @TableId(type = IdType.AUTO)
    private Long id;
    private Long documentId;
    private String opType;
    private String status;
    private Integer retryCount;
    private Integer maxRetries;
    private OffsetDateTime nextRetryAt;
    private String lastError;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
