package com.lyj.dbc.graph.graphmeta.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

@Data
@TableName("t_graph")
public class GraphEntity {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long categoryId;
    private String code;
    private String name;
    private String summary;
    private String productName;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
