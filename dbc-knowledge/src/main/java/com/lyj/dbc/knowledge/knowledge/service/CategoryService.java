package com.lyj.dbc.knowledge.knowledge.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.knowledge.common.api.BizException;
import com.lyj.dbc.knowledge.knowledge.domain.Category;
import com.lyj.dbc.knowledge.knowledge.domain.Document;
import com.lyj.dbc.knowledge.knowledge.dto.CategoryCreateRequest;
import com.lyj.dbc.knowledge.knowledge.dto.CategoryTreeNode;
import com.lyj.dbc.knowledge.knowledge.mapper.CategoryMapper;
import com.lyj.dbc.knowledge.knowledge.mapper.DocumentMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Service
public class CategoryService {
    private final CategoryMapper categoryMapper;
    private final DocumentMapper documentMapper;

    public CategoryService(CategoryMapper categoryMapper, DocumentMapper documentMapper) {
        this.categoryMapper = categoryMapper;
        this.documentMapper = documentMapper;
    }

    public List<CategoryTreeNode> tree() {
        List<Category> all = categoryMapper.selectList(new LambdaQueryWrapper<Category>()
                .orderByAsc(Category::getSortNo)
                .orderByAsc(Category::getId));
        Map<Long, CategoryTreeNode> map = new HashMap<>();
        List<CategoryTreeNode> roots = new ArrayList<>();
        for (Category c : all) {
            CategoryTreeNode node = toNode(c);
            map.put(c.getId(), node);
        }
        for (Category c : all) {
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
    public Category create(CategoryCreateRequest req) {
        if (!StringUtils.hasText(req.getName())) {
            throw new BizException("分类名称不能为空");
        }
        String code = normalizeCode(req.getCode());
        if (code == null) {
            throw new BizException("分类编码不能为空");
        }
        Long codeCount = categoryMapper.selectCount(new LambdaQueryWrapper<Category>()
                .eq(Category::getCode, code));
        if (codeCount != null && codeCount > 0) {
            throw new BizException("分类编码已存在");
        }
        Long parentId = req.getParentId();
        if (parentId != null) {
            Category parent = categoryMapper.selectById(parentId);
            if (parent == null) {
                throw new BizException("父分类不存在");
            }
        }
        Long count = categoryMapper.selectCount(new LambdaQueryWrapper<Category>()
                .eq(Category::getName, req.getName().trim())
                .eq(parentId != null, Category::getParentId, parentId)
                .isNull(parentId == null, Category::getParentId));
        if (count != null && count > 0) {
            throw new BizException("同级分类名称已存在");
        }

        Category cat = new Category();
        cat.setParentId(parentId);
        cat.setName(req.getName().trim());
        cat.setCode(code);
        cat.setSortNo(req.getSortNo() == null ? 0 : req.getSortNo());
        cat.setPath("");
        cat.setCreatedAt(OffsetDateTime.now());
        cat.setUpdatedAt(OffsetDateTime.now());
        categoryMapper.insert(cat);

        String path = parentId == null
                ? "/" + cat.getId()
                : Objects.requireNonNull(categoryMapper.selectById(parentId)).getPath() + "/" + cat.getId();
        cat.setPath(path);
        categoryMapper.updateById(cat);
        return cat;
    }

    @Transactional
    public Category rename(Long id, String name) {
        Category cat = require(id);
        if (!StringUtils.hasText(name)) {
            throw new BizException("分类名称不能为空");
        }
        Long count = categoryMapper.selectCount(new LambdaQueryWrapper<Category>()
                .eq(Category::getName, name.trim())
                .eq(cat.getParentId() != null, Category::getParentId, cat.getParentId())
                .isNull(cat.getParentId() == null, Category::getParentId)
                .ne(Category::getId, id));
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
        Category cat = require(id);
        Long children = categoryMapper.selectCount(new LambdaQueryWrapper<Category>()
                .eq(Category::getParentId, id));
        if (children != null && children > 0) {
            throw new BizException("请先删除子分类");
        }
        Long docs = documentMapper.selectCount(new LambdaQueryWrapper<Document>()
                .eq(Document::getCategoryId, id));
        if (docs != null && docs > 0) {
            throw new BizException("分类下仍有原文，无法删除");
        }
        categoryMapper.deleteById(cat.getId());
    }

    public Category requireByCode(String code) {
        String normalized = normalizeCode(code);
        if (normalized == null) {
            throw new BizException("分类编码不能为空");
        }
        Category cat = categoryMapper.selectOne(new LambdaQueryWrapper<Category>()
                .eq(Category::getCode, normalized)
                .last("LIMIT 1"));
        if (cat == null) {
            throw new BizException(404, "分类不存在: " + normalized);
        }
        return cat;
    }

    private static String normalizeCode(String code) {
        if (!StringUtils.hasText(code)) {
            return null;
        }
        return code.trim().toUpperCase();
    }

    public Category require(Long id) {
        Category cat = categoryMapper.selectById(id);
        if (cat == null) {
            throw new BizException(404, "分类不存在: " + id);
        }
        return cat;
    }

    public String pathLabel(Long categoryId) {
        if (categoryId == null) {
            return null;
        }
        Category cat = categoryMapper.selectById(categoryId);
        if (cat == null) {
            return null;
        }
        if (!StringUtils.hasText(cat.getPath())) {
            return cat.getName();
        }
        String[] parts = cat.getPath().split("/");
        List<String> names = new ArrayList<>();
        for (String p : parts) {
            if (!StringUtils.hasText(p)) {
                continue;
            }
            // path 约定为 /id/id；兼容历史脏数据（曾写入编码如 METADATA）
            if (!p.chars().allMatch(Character::isDigit)) {
                continue;
            }
            Category c = categoryMapper.selectById(Long.parseLong(p));
            if (c != null) {
                names.add(c.getName());
            }
        }
        if (names.isEmpty()) {
            return cat.getName();
        }
        return String.join(" / ", names);
    }

    private CategoryTreeNode toNode(Category c) {
        CategoryTreeNode n = new CategoryTreeNode();
        n.setId(c.getId());
        n.setParentId(c.getParentId());
        n.setName(c.getName());
        n.setCode(c.getCode());
        n.setPath(c.getPath());
        n.setSortNo(c.getSortNo());
        return n;
    }
}
