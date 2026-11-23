package com.lyj.dbc.graph.category;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.graph.category.dto.CategoryCreateRequest;
import com.lyj.dbc.graph.category.dto.CategoryTreeNode;
import com.lyj.dbc.graph.category.entity.GraphCategoryEntity;
import com.lyj.dbc.graph.category.mapper.GraphCategoryMapper;
import com.lyj.dbc.graph.common.api.BizException;
import com.lyj.dbc.graph.graphmeta.entity.GraphEntity;
import com.lyj.dbc.graph.graphmeta.mapper.GraphMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class CategoryService {
    private final GraphCategoryMapper categoryMapper;
    private final GraphMapper graphMapper;

    public CategoryService(GraphCategoryMapper categoryMapper, GraphMapper graphMapper) {
        this.categoryMapper = categoryMapper;
        this.graphMapper = graphMapper;
    }

    public List<CategoryTreeNode> tree() {
        List<GraphCategoryEntity> all = categoryMapper.selectList(new LambdaQueryWrapper<GraphCategoryEntity>()
                .orderByAsc(GraphCategoryEntity::getSortNo)
                .orderByAsc(GraphCategoryEntity::getId));
        Map<Long, CategoryTreeNode> map = new HashMap<>();
        List<CategoryTreeNode> roots = new ArrayList<>();
        for (GraphCategoryEntity c : all) {
            CategoryTreeNode node = new CategoryTreeNode();
            node.setId(c.getId());
            node.setParentId(c.getParentId());
            node.setName(c.getName());
            node.setSortNo(c.getSortNo());
            map.put(c.getId(), node);
        }
        for (GraphCategoryEntity c : all) {
            CategoryTreeNode node = map.get(c.getId());
            if (c.getParentId() == null) {
                roots.add(node);
            } else {
                CategoryTreeNode parent = map.get(c.getParentId());
                if (parent != null) {
                    parent.getChildren().add(node);
                } else {
                    roots.add(node);
                }
            }
        }
        return roots;
    }

    @Transactional
    public GraphCategoryEntity create(CategoryCreateRequest req) {
        if (!StringUtils.hasText(req.getName())) {
            throw new BizException("分类名称不能为空");
        }
        Long parentId = req.getParentId();
        if (parentId != null && categoryMapper.selectById(parentId) == null) {
            throw new BizException("父分类不存在");
        }
        Long count = categoryMapper.selectCount(new LambdaQueryWrapper<GraphCategoryEntity>()
                .eq(GraphCategoryEntity::getName, req.getName().trim())
                .eq(parentId != null, GraphCategoryEntity::getParentId, parentId)
                .isNull(parentId == null, GraphCategoryEntity::getParentId));
        if (count != null && count > 0) {
            throw new BizException("同级分类名称已存在");
        }
        GraphCategoryEntity cat = new GraphCategoryEntity();
        cat.setParentId(parentId);
        cat.setName(req.getName().trim());
        cat.setSortNo(req.getSortNo() == null ? 0 : req.getSortNo());
        cat.setCreatedAt(OffsetDateTime.now());
        cat.setUpdatedAt(OffsetDateTime.now());
        categoryMapper.insert(cat);
        return cat;
    }

    @Transactional
    public GraphCategoryEntity rename(Long id, String name) {
        GraphCategoryEntity cat = require(id);
        if (!StringUtils.hasText(name)) {
            throw new BizException("分类名称不能为空");
        }
        Long count = categoryMapper.selectCount(new LambdaQueryWrapper<GraphCategoryEntity>()
                .eq(GraphCategoryEntity::getName, name.trim())
                .eq(cat.getParentId() != null, GraphCategoryEntity::getParentId, cat.getParentId())
                .isNull(cat.getParentId() == null, GraphCategoryEntity::getParentId)
                .ne(GraphCategoryEntity::getId, id));
        if (count != null && count > 0) {
            throw new BizException("同级分类名称已存在");
        }
        cat.setName(name.trim());
        cat.setUpdatedAt(OffsetDateTime.now());
        categoryMapper.updateById(cat);
        return cat;
    }

    @Transactional
    public void delete(Long id) {
        require(id);
        Long childCount = categoryMapper.selectCount(new LambdaQueryWrapper<GraphCategoryEntity>()
                .eq(GraphCategoryEntity::getParentId, id));
        if (childCount != null && childCount > 0) {
            throw new BizException("分类下仍有子分类，无法删除");
        }
        Long graphCount = graphMapper.selectCount(new LambdaQueryWrapper<GraphEntity>()
                .eq(GraphEntity::getCategoryId, id));
        if (graphCount != null && graphCount > 0) {
            throw new BizException("分类下仍有图谱，无法删除");
        }
        categoryMapper.deleteById(id);
    }

    public GraphCategoryEntity require(Long id) {
        GraphCategoryEntity cat = categoryMapper.selectById(id);
        if (cat == null) {
            throw new BizException(404, "分类不存在: " + id);
        }
        return cat;
    }
}
