package com.lyj.dbc.graph.workspace;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.graph.category.entity.GraphCategoryEntity;
import com.lyj.dbc.graph.category.mapper.GraphCategoryMapper;
import com.lyj.dbc.graph.graphmeta.entity.GraphEntity;
import com.lyj.dbc.graph.graphmeta.mapper.GraphMapper;
import com.lyj.dbc.graph.workspace.dto.WorkspaceTreeNode;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class WorkspaceService {
    private final GraphCategoryMapper categoryMapper;
    private final GraphMapper graphMapper;

    public WorkspaceService(GraphCategoryMapper categoryMapper, GraphMapper graphMapper) {
        this.categoryMapper = categoryMapper;
        this.graphMapper = graphMapper;
    }

    /**
     * 统一树：文件夹可挂子文件夹与图谱；图谱为叶子。
     */
    public List<WorkspaceTreeNode> tree() {
        List<GraphCategoryEntity> folders = categoryMapper.selectList(new LambdaQueryWrapper<GraphCategoryEntity>()
                .orderByAsc(GraphCategoryEntity::getSortNo)
                .orderByAsc(GraphCategoryEntity::getId));
        List<GraphEntity> graphs = graphMapper.selectList(new LambdaQueryWrapper<GraphEntity>()
                .orderByAsc(GraphEntity::getName)
                .orderByAsc(GraphEntity::getId));

        Map<Long, WorkspaceTreeNode> folderMap = new HashMap<>();
        List<WorkspaceTreeNode> roots = new ArrayList<>();

        for (GraphCategoryEntity f : folders) {
            WorkspaceTreeNode n = new WorkspaceTreeNode();
            n.setKind("FOLDER");
            n.setId(f.getId());
            n.setName(f.getName());
            n.setParentId(f.getParentId());
            folderMap.put(f.getId(), n);
        }
        for (GraphCategoryEntity f : folders) {
            WorkspaceTreeNode n = folderMap.get(f.getId());
            if (f.getParentId() == null) {
                roots.add(n);
            } else {
                WorkspaceTreeNode parent = folderMap.get(f.getParentId());
                if (parent != null) {
                    parent.getChildren().add(n);
                } else {
                    roots.add(n);
                }
            }
        }
        for (GraphEntity g : graphs) {
            WorkspaceTreeNode n = new WorkspaceTreeNode();
            n.setKind("GRAPH");
            n.setId(g.getId());
            n.setName(g.getName());
            n.setParentId(g.getCategoryId());
            n.setSummary(g.getSummary());
            n.setProductName(g.getProductName());
            WorkspaceTreeNode folder = folderMap.get(g.getCategoryId());
            if (folder != null) {
                folder.getChildren().add(n);
            } else {
                // 孤儿图谱挂到根，便于发现
                roots.add(n);
            }
        }
        sortRec(roots);
        return roots;
    }

    private void sortRec(List<WorkspaceTreeNode> nodes) {
        nodes.sort(Comparator
                .comparing((WorkspaceTreeNode n) -> "FOLDER".equals(n.getKind()) ? 0 : 1)
                .thenComparing(WorkspaceTreeNode::getName, Comparator.nullsLast(String::compareTo)));
        for (WorkspaceTreeNode n : nodes) {
            if (n.getChildren() != null && !n.getChildren().isEmpty()) {
                sortRec(n.getChildren());
            }
        }
    }
}
