package com.lyj.dbc.graph.workspace.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class WorkspaceTreeNode {
    /** FOLDER | GRAPH */
    private String kind;
    private Long id;
    private String name;
    /** 文件夹的父 id；图谱则为所属文件夹 id */
    private Long parentId;
    private String summary;
    private String productName;
    private List<WorkspaceTreeNode> children = new ArrayList<>();
}
