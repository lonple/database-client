package com.lyj.dbc.usercenter.dept;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.client.audit.AuditAction;
import com.lyj.dbc.client.audit.AuditLog;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.dept.dto.DeptCreateRequest;
import com.lyj.dbc.usercenter.dept.dto.DeptUpdateRequest;
import com.lyj.dbc.usercenter.dept.entity.DeptEntity;
import com.lyj.dbc.usercenter.dept.mapper.DeptMapper;
import com.lyj.dbc.usercenter.dept.vo.DeptTreeNodeVO;
import com.lyj.dbc.usercenter.dept.vo.DeptVO;
import com.lyj.dbc.usercenter.security.LoginUser;
import com.lyj.dbc.usercenter.security.SecurityUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * 部门业务服务。
 */
@Service
public class DeptService {

    /** 部门最大层级 */
    public static final int MAX_LEVEL = 10;

    private final DeptMapper deptMapper;

    public DeptService(DeptMapper deptMapper) {
        this.deptMapper = deptMapper;
    }

    /**
     * 整棵部门树。
     */
    public List<DeptTreeNodeVO> tree() {
        List<DeptEntity> all = deptMapper.selectList(new LambdaQueryWrapper<DeptEntity>()
                .orderByAsc(DeptEntity::getLevel)
                .orderByAsc(DeptEntity::getId));
        Map<Long, DeptTreeNodeVO> map = new HashMap<>();
        List<DeptTreeNodeVO> roots = new ArrayList<>();
        for (DeptEntity e : all) {
            DeptTreeNodeVO node = DeptTreeNodeVO.builder()
                    .id(e.getId())
                    .name(e.getName())
                    .description(e.getDescription())
                    .parentId(e.getParentId())
                    .level(e.getLevel())
                    .path(e.getPath())
                    .children(new ArrayList<>())
                    .build();
            map.put(e.getId(), node);
        }
        for (DeptEntity e : all) {
            DeptTreeNodeVO node = map.get(e.getId());
            if (e.getParentId() == null) {
                roots.add(node);
            } else {
                DeptTreeNodeVO parent = map.get(e.getParentId());
                if (parent != null) {
                    parent.getChildren().add(node);
                }
            }
        }
        return roots;
    }

    /**
     * 部门详情。
     */
    public DeptVO getById(Long id) {
        DeptEntity dept = requireDept(id);
        String parentName = null;
        if (dept.getParentId() != null) {
            DeptEntity parent = deptMapper.selectById(dept.getParentId());
            parentName = parent == null ? null : parent.getName();
        }
        return toVo(dept, parentName);
    }

    /**
     * 新增子部门（禁止新建根）。
     */
    @AuditLog(module = "usercenter", action = AuditAction.CREATE, resourceType = "dept", resourceId = "#return.id")
    @Transactional
    public DeptVO create(DeptCreateRequest request) {
        DeptEntity parent = requireDept(request.getParentId());
        int level = parent.getLevel() + 1;
        if (level > MAX_LEVEL) {
            throw BizException.badRequest("部门最多支持" + MAX_LEVEL + "层");
        }
        assertSiblingNameUnique(parent.getId(), request.getName().trim(), null);
        LoginUser operator = SecurityUtils.requireUser();
        OffsetDateTime now = OffsetDateTime.now();
        DeptEntity dept = new DeptEntity();
        dept.setName(request.getName().trim());
        dept.setDescription(blankToNull(request.getDescription()));
        dept.setParentId(parent.getId());
        dept.setLevel(level);
        dept.setPath("/"); // 占位，插入后更新
        dept.setDeleted(0);
        dept.setCreatedAt(now);
        dept.setUpdatedAt(now);
        dept.setCreatedBy(operator.getUserId());
        dept.setUpdatedBy(operator.getUserId());
        deptMapper.insert(dept);
        dept.setPath(parent.getPath() + dept.getId() + "/");
        deptMapper.updateById(dept);
        return toVo(dept, parent.getName());
    }

    /**
     * 更新部门；修改父部门时整棵子树迁移。
     */
    @AuditLog(module = "usercenter", action = AuditAction.UPDATE, resourceType = "dept", resourceId = "#id",
            loadBefore = "getById(#id)")
    @Transactional
    public DeptVO update(Long id, DeptUpdateRequest request) {
        DeptEntity dept = requireDept(id);
        boolean isRoot = dept.getParentId() == null;
        Long newParentId = request.getParentId();
        if (isRoot) {
            if (newParentId != null) {
                throw BizException.badRequest("根部门不可变更父部门");
            }
        } else {
            if (newParentId == null) {
                throw BizException.badRequest("仅允许一个顶级部门，不可将部门提升为根");
            }
        }

        String newName = request.getName().trim();
        Long siblingParentId = isRoot ? null : newParentId;
        assertSiblingNameUnique(siblingParentId, newName, id);

        LoginUser operator = SecurityUtils.requireUser();
        boolean parentChanged = !isRoot && !Objects.equals(dept.getParentId(), newParentId);
        if (parentChanged) {
            migrateSubtree(dept, newParentId);
        }

        dept.setName(newName);
        dept.setDescription(blankToNull(request.getDescription()));
        dept.setUpdatedAt(OffsetDateTime.now());
        dept.setUpdatedBy(operator.getUserId());
        deptMapper.updateById(dept);
        return getById(id);
    }

    /**
     * 逻辑删除；根不可删；有子不可删。
     */
    @AuditLog(module = "usercenter", action = AuditAction.DELETE, resourceType = "dept", resourceId = "#id",
            loadBefore = "getById(#id)")
    @Transactional
    public void delete(Long id) {
        DeptEntity dept = requireDept(id);
        if (dept.getParentId() == null) {
            throw BizException.badRequest("根部门不可删除");
        }
        Long childCount = deptMapper.selectCount(new LambdaQueryWrapper<DeptEntity>()
                .eq(DeptEntity::getParentId, id));
        if (childCount != null && childCount > 0) {
            throw BizException.badRequest("请先删除子部门");
        }
        deptMapper.deleteById(id);
    }

    /**
     * 查询未删除部门实体。
     */
    public DeptEntity requireDept(Long id) {
        DeptEntity dept = deptMapper.selectById(id);
        if (dept == null) {
            throw BizException.notFound("部门不存在");
        }
        return dept;
    }

    /**
     * 按 path 前缀列出本部门及子孙 ID（含自身）。
     */
    public List<Long> listSelfAndDescendantIds(Long deptId) {
        DeptEntity dept = requireDept(deptId);
        return deptMapper.selectList(new LambdaQueryWrapper<DeptEntity>()
                        .likeRight(DeptEntity::getPath, dept.getPath()))
                .stream()
                .map(DeptEntity::getId)
                .toList();
    }

    private void migrateSubtree(DeptEntity node, Long newParentId) {
        if (Objects.equals(node.getId(), newParentId)) {
            throw BizException.badRequest("父部门不能是自己");
        }
        DeptEntity newParent = requireDept(newParentId);
        if (newParent.getPath().startsWith(node.getPath())) {
            throw BizException.badRequest("父部门不能是当前部门的子部门");
        }
        String oldPath = node.getPath();
        int oldLevel = node.getLevel();
        int newLevel = newParent.getLevel() + 1;
        int delta = newLevel - oldLevel;
        String newPath = newParent.getPath() + node.getId() + "/";

        List<DeptEntity> subtree = deptMapper.selectList(new LambdaQueryWrapper<DeptEntity>()
                .likeRight(DeptEntity::getPath, oldPath)
                .orderByAsc(DeptEntity::getLevel));
        int maxLevel = subtree.stream()
                .mapToInt(e -> e.getLevel() + delta)
                .max()
                .orElse(newLevel);
        if (maxLevel > MAX_LEVEL) {
            throw BizException.badRequest("迁移后部门层级将超过" + MAX_LEVEL + "层");
        }

        OffsetDateTime now = OffsetDateTime.now();
        Long operatorId = SecurityUtils.requireUser().getUserId();
        for (DeptEntity e : subtree) {
            String suffix = e.getPath().substring(oldPath.length());
            e.setPath(newPath + suffix);
            e.setLevel(e.getLevel() + delta);
            if (Objects.equals(e.getId(), node.getId())) {
                e.setParentId(newParentId);
            }
            e.setUpdatedAt(now);
            e.setUpdatedBy(operatorId);
            deptMapper.updateById(e);
        }
        node.setParentId(newParentId);
        node.setPath(newPath);
        node.setLevel(newLevel);
    }

    private void assertSiblingNameUnique(Long parentId, String name, Long excludeId) {
        LambdaQueryWrapper<DeptEntity> q = new LambdaQueryWrapper<DeptEntity>()
                .eq(DeptEntity::getName, name);
        if (parentId == null) {
            q.isNull(DeptEntity::getParentId);
        } else {
            q.eq(DeptEntity::getParentId, parentId);
        }
        if (excludeId != null) {
            q.ne(DeptEntity::getId, excludeId);
        }
        Long count = deptMapper.selectCount(q);
        if (count != null && count > 0) {
            throw BizException.conflict("同一层级下部门名称已存在");
        }
    }

    private DeptVO toVo(DeptEntity dept, String parentName) {
        return DeptVO.builder()
                .id(dept.getId())
                .name(dept.getName())
                .description(dept.getDescription())
                .parentId(dept.getParentId())
                .parentName(parentName)
                .level(dept.getLevel())
                .path(dept.getPath())
                .root(dept.getParentId() == null)
                .build();
    }

    private static String blankToNull(String value) {
        return StringUtils.hasText(value) ? value.trim() : null;
    }
}
