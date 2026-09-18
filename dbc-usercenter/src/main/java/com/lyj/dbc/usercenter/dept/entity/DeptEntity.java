package com.lyj.dbc.usercenter.dept.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 部门实体，对应表 t_usercenter_dept。
 */
@Data
@TableName("t_usercenter_dept")
public class DeptEntity {

    /** 主键ID */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 部门名称 */
    private String name;

    /** 部门描述 */
    private String description;

    /** 父部门ID，根节点为空 */
    private Long parentId;

    /** 物化路径，如 /1/3/8/ */
    private String path;

    /** 层级，根为1，最大10 */
    private Integer level;

    /**
     * 逻辑删除标记。
     * 0：未删除；1：已删除
     */
    @TableLogic
    private Integer deleted;

    /** 创建时间 */
    private OffsetDateTime createdAt;

    /** 更新时间 */
    private OffsetDateTime updatedAt;

    /** 创建人用户ID */
    private Long createdBy;

    /** 更新人用户ID */
    private Long updatedBy;
}
