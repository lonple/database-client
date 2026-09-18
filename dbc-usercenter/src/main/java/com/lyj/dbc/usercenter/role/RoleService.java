package com.lyj.dbc.usercenter.role;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.client.audit.AuditAction;
import com.lyj.dbc.client.audit.AuditLog;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.dept.DeptService;
import com.lyj.dbc.usercenter.role.dto.RoleCreateRequest;
import com.lyj.dbc.usercenter.role.dto.RoleUpdateRequest;
import com.lyj.dbc.usercenter.role.entity.RoleDeptEntity;
import com.lyj.dbc.usercenter.role.entity.RoleEntity;
import com.lyj.dbc.usercenter.role.mapper.RoleDeptMapper;
import com.lyj.dbc.usercenter.role.mapper.RoleMapper;
import com.lyj.dbc.usercenter.role.vo.RoleVO;
import com.lyj.dbc.usercenter.user.entity.UserRoleEntity;
import com.lyj.dbc.usercenter.user.mapper.UserRoleMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * 角色业务服务。
 */
@Service
public class RoleService {

    private final RoleMapper roleMapper;
    private final RoleDeptMapper roleDeptMapper;
    private final UserRoleMapper userRoleMapper;
    private final DeptService deptService;

    public RoleService(RoleMapper roleMapper, RoleDeptMapper roleDeptMapper,
                       UserRoleMapper userRoleMapper, DeptService deptService) {
        this.roleMapper = roleMapper;
        this.roleDeptMapper = roleDeptMapper;
        this.userRoleMapper = userRoleMapper;
        this.deptService = deptService;
    }

    /**
     * 查询全部未删除角色。
     */
    public List<RoleVO> listAll() {
        return roleMapper.selectList(new LambdaQueryWrapper<RoleEntity>().orderByAsc(RoleEntity::getId))
                .stream()
                .map(this::toView)
                .toList();
    }

    /**
     * 按ID查询角色。
     */
    public RoleVO getById(Long id) {
        return toView(requireRole(id));
    }

    /**
     * 新建自定义角色。
     */
    @AuditLog(module = "usercenter", action = AuditAction.CREATE, resourceType = "role", resourceId = "#return.id")
    @Transactional
    public RoleVO create(RoleCreateRequest request) {
        String code = request.getCode().trim();
        Long exists = roleMapper.selectCount(new LambdaQueryWrapper<RoleEntity>().eq(RoleEntity::getCode, code));
        if (exists != null && exists > 0) {
            throw BizException.conflict("角色编码已存在");
        }
        DataScopeType scope = parseScope(request.getDataScope());
        List<Long> deptIds = normalizeCustomDepts(scope, request.getDeptIds());
        OffsetDateTime now = OffsetDateTime.now();
        RoleEntity role = new RoleEntity();
        role.setCode(code);
        role.setName(request.getName().trim());
        role.setDescription(blankToNull(request.getDescription()));
        role.setDataScope(scope.name());
        role.setBuiltin(0);
        role.setDeleted(0);
        role.setCreatedAt(now);
        role.setUpdatedAt(now);
        roleMapper.insert(role);
        replaceRoleDepts(role.getId(), deptIds);
        return toView(role);
    }

    /**
     * 更新非内置角色。
     */
    @AuditLog(module = "usercenter", action = AuditAction.UPDATE, resourceType = "role", resourceId = "#id",
            loadBefore = "getById(#id)")
    @Transactional
    public RoleVO update(Long id, RoleUpdateRequest request) {
        RoleEntity role = requireRole(id);
        assertMutable(role);
        DataScopeType scope = parseScope(request.getDataScope());
        List<Long> deptIds = normalizeCustomDepts(scope, request.getDeptIds());
        role.setName(request.getName().trim());
        role.setDescription(blankToNull(request.getDescription()));
        role.setDataScope(scope.name());
        role.setUpdatedAt(OffsetDateTime.now());
        roleMapper.updateById(role);
        replaceRoleDepts(role.getId(), deptIds);
        return toView(role);
    }

    /**
     * 删除非内置角色。
     */
    @AuditLog(module = "usercenter", action = AuditAction.DELETE, resourceType = "role", resourceId = "#id",
            loadBefore = "getById(#id)")
    @Transactional
    public void delete(Long id) {
        RoleEntity role = requireRole(id);
        assertMutable(role);
        Long bound = userRoleMapper.selectCount(new LambdaQueryWrapper<UserRoleEntity>()
                .eq(UserRoleEntity::getRoleId, id));
        if (bound != null && bound > 0) {
            throw BizException.badRequest("角色已绑定用户，无法删除");
        }
        roleDeptMapper.delete(new LambdaQueryWrapper<RoleDeptEntity>().eq(RoleDeptEntity::getRoleId, id));
        roleMapper.deleteById(id);
    }

    /**
     * 按ID加载角色实体。
     */
    public RoleEntity requireRole(Long id) {
        RoleEntity role = roleMapper.selectById(id);
        if (role == null) {
            throw BizException.notFound("角色不存在");
        }
        return role;
    }

    /**
     * 批量加载角色。
     */
    public List<RoleEntity> listByIds(List<Long> ids) {
        if (ids == null || ids.isEmpty()) {
            return List.of();
        }
        return roleMapper.selectList(new LambdaQueryWrapper<RoleEntity>().in(RoleEntity::getId, ids));
    }

    /**
     * CUSTOM 勾选部门 ID。
     */
    public List<Long> listCustomDeptIds(Long roleId) {
        return roleDeptMapper.selectList(new LambdaQueryWrapper<RoleDeptEntity>()
                        .eq(RoleDeptEntity::getRoleId, roleId))
                .stream()
                .map(RoleDeptEntity::getDeptId)
                .toList();
    }

    private RoleVO toView(RoleEntity role) {
        List<Long> deptIds = Objects.equals(role.getDataScope(), DataScopeType.CUSTOM.name())
                ? listCustomDeptIds(role.getId())
                : List.of();
        return RoleVO.builder()
                .id(role.getId())
                .code(role.getCode())
                .name(role.getName())
                .description(role.getDescription())
                .dataScope(role.getDataScope())
                .deptIds(deptIds)
                .builtin(role.getBuiltin() != null && role.getBuiltin() == 1)
                .build();
    }

    private void assertMutable(RoleEntity role) {
        if (role.getBuiltin() != null && role.getBuiltin() == 1) {
            throw BizException.badRequest("内置角色不可修改或删除");
        }
    }

    private DataScopeType parseScope(String raw) {
        try {
            return DataScopeType.valueOf(raw);
        } catch (Exception ex) {
            throw BizException.badRequest("数据范围取值非法");
        }
    }

    private List<Long> normalizeCustomDepts(DataScopeType scope, List<Long> deptIds) {
        if (scope != DataScopeType.CUSTOM) {
            return List.of();
        }
        if (deptIds == null || deptIds.isEmpty()) {
            throw BizException.badRequest("自定义数据范围须至少勾选一个部门");
        }
        Set<Long> unique = new LinkedHashSet<>();
        for (Long deptId : deptIds) {
            if (deptId == null) {
                continue;
            }
            deptService.requireDept(deptId);
            unique.add(deptId);
        }
        if (unique.isEmpty()) {
            throw BizException.badRequest("自定义数据范围须至少勾选一个部门");
        }
        return new ArrayList<>(unique);
    }

    private void replaceRoleDepts(Long roleId, List<Long> deptIds) {
        roleDeptMapper.delete(new LambdaQueryWrapper<RoleDeptEntity>().eq(RoleDeptEntity::getRoleId, roleId));
        OffsetDateTime now = OffsetDateTime.now();
        for (Long deptId : deptIds) {
            RoleDeptEntity row = new RoleDeptEntity();
            row.setRoleId(roleId);
            row.setDeptId(deptId);
            row.setCreatedAt(now);
            roleDeptMapper.insert(row);
        }
    }

    private static String blankToNull(String value) {
        return StringUtils.hasText(value) ? value.trim() : null;
    }
}
