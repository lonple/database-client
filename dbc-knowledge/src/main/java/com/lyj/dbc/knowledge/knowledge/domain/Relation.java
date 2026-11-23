package com.lyj.dbc.knowledge.knowledge.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

@Data
@TableName("t_knowledge_relation")
public class Relation {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String fromKind;
    private Long fromId;
    private String toKind;
    private Long toId;
    private String relType;
    private OffsetDateTime createdAt;
}
