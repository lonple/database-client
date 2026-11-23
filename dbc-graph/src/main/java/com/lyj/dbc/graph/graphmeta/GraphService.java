package com.lyj.dbc.graph.graphmeta;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.graph.category.CategoryService;
import com.lyj.dbc.graph.common.api.BizException;
import com.lyj.dbc.graph.graphmeta.dto.GraphCreateRequest;
import com.lyj.dbc.graph.graphmeta.dto.GraphUpdateRequest;
import com.lyj.dbc.graph.graphmeta.entity.GraphEntity;
import com.lyj.dbc.graph.graphmeta.mapper.GraphMapper;
import com.lyj.dbc.graph.neo4j.Neo4jGateway;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.OffsetDateTime;
import java.util.List;

@Service
public class GraphService {
    private final GraphMapper graphMapper;
    private final CategoryService categoryService;
    private final Neo4jGateway neo4jGateway;

    public GraphService(GraphMapper graphMapper, CategoryService categoryService, Neo4jGateway neo4jGateway) {
        this.graphMapper = graphMapper;
        this.categoryService = categoryService;
        this.neo4jGateway = neo4jGateway;
    }

    public List<GraphEntity> list(Long categoryId, String productName, String keyword, String code) {
        LambdaQueryWrapper<GraphEntity> q = new LambdaQueryWrapper<GraphEntity>()
                .orderByDesc(GraphEntity::getUpdatedAt);
        if (categoryId != null) {
            q.eq(GraphEntity::getCategoryId, categoryId);
        }
        if (StringUtils.hasText(code)) {
            q.eq(GraphEntity::getCode, code.trim());
        }
        if (StringUtils.hasText(productName)) {
            q.eq(GraphEntity::getProductName, productName.trim());
        }
        if (StringUtils.hasText(keyword)) {
            String kw = keyword.trim();
            q.and(w -> w.like(GraphEntity::getName, kw).or().like(GraphEntity::getSummary, kw));
        }
        return graphMapper.selectList(q);
    }

    public GraphEntity require(Long id) {
        GraphEntity g = graphMapper.selectById(id);
        if (g == null) {
            throw new BizException(404, "图谱不存在: " + id);
        }
        return g;
    }

    @Transactional
    public GraphEntity create(GraphCreateRequest req) {
        if (!StringUtils.hasText(req.getCode())) {
            throw new BizException("图谱编码不能为空");
        }
        String code = req.getCode().trim();
        if (findByCode(code) != null) {
            throw new BizException("图谱编码已存在");
        }
        Long categoryId = req.getCategoryId();
        if (categoryId == null) {
            categoryId = defaultCategoryId();
        } else {
            categoryService.require(categoryId);
        }
        if (!StringUtils.hasText(req.getName())) {
            throw new BizException("图谱名称不能为空");
        }
        if (!StringUtils.hasText(req.getSummary())) {
            throw new BizException("图谱简介不能为空");
        }
        GraphEntity g = new GraphEntity();
        g.setCategoryId(categoryId);
        g.setCode(code);
        g.setName(req.getName().trim());
        g.setSummary(req.getSummary().trim());
        g.setProductName(StringUtils.hasText(req.getProductName()) ? req.getProductName().trim() : null);
        g.setCreatedAt(OffsetDateTime.now());
        g.setUpdatedAt(OffsetDateTime.now());
        graphMapper.insert(g);
        return g;
    }

    @Transactional
    public GraphEntity update(Long id, GraphUpdateRequest req) {
        GraphEntity g = require(id);
        if (req.getCategoryId() != null) {
            categoryService.require(req.getCategoryId());
            g.setCategoryId(req.getCategoryId());
        }
        if (req.getCode() != null) {
            if (!StringUtils.hasText(req.getCode())) {
                throw new BizException("图谱编码不能为空");
            }
            String code = req.getCode().trim();
            GraphEntity other = findByCode(code);
            if (other != null && !other.getId().equals(g.getId())) {
                throw new BizException("图谱编码已存在");
            }
            g.setCode(code);
        }
        if (req.getName() != null) {
            if (!StringUtils.hasText(req.getName())) {
                throw new BizException("图谱名称不能为空");
            }
            g.setName(req.getName().trim());
        }
        if (req.getSummary() != null) {
            if (!StringUtils.hasText(req.getSummary())) {
                throw new BizException("图谱简介不能为空");
            }
            g.setSummary(req.getSummary().trim());
        }
        if (req.getProductName() != null) {
            g.setProductName(req.getProductName().isBlank() ? null : req.getProductName().trim());
        }
        g.setUpdatedAt(OffsetDateTime.now());
        graphMapper.updateById(g);
        return g;
    }

    @Transactional
    public void delete(Long id) {
        require(id);
        neo4jGateway.deleteGraphData(id);
        graphMapper.deleteById(id);
    }

    public GraphEntity findByName(String name) {
        return graphMapper.selectOne(new LambdaQueryWrapper<GraphEntity>()
                .eq(GraphEntity::getName, name)
                .last("LIMIT 1"));
    }

    public GraphEntity findByCode(String code) {
        if (!StringUtils.hasText(code)) {
            return null;
        }
        return graphMapper.selectOne(new LambdaQueryWrapper<GraphEntity>()
                .eq(GraphEntity::getCode, code.trim())
                .last("LIMIT 1"));
    }

    public GraphEntity requireByCode(String code) {
        GraphEntity g = findByCode(code);
        if (g == null) {
            throw new BizException(404, "图谱不存在: " + code);
        }
        return g;
    }

    private Long defaultCategoryId() {
        var existing = categoryService.tree();
        if (!existing.isEmpty()) {
            return existing.get(0).getId();
        }
        var req = new com.lyj.dbc.graph.category.dto.CategoryCreateRequest();
        req.setName("默认");
        req.setSortNo(0);
        return categoryService.create(req).getId();
    }
}
