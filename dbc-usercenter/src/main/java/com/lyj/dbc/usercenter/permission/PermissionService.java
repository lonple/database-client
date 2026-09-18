package com.lyj.dbc.usercenter.permission;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.client.audit.AuditAction;
import com.lyj.dbc.client.audit.AuditLog;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.permission.dto.PermissionRegisterItem;
import com.lyj.dbc.usercenter.permission.entity.PermissionEntity;
import com.lyj.dbc.usercenter.permission.entity.RolePermissionEntity;
import com.lyj.dbc.usercenter.permission.mapper.PermissionMapper;
import com.lyj.dbc.usercenter.permission.mapper.RolePermissionMapper;
import com.lyj.dbc.usercenter.permission.vo.PermissionModuleVO;
import com.lyj.dbc.usercenter.permission.vo.PermissionVO;
import com.lyj.dbc.usercenter.role.entity.RoleEntity;
import com.lyj.dbc.usercenter.role.mapper.RoleMapper;
import com.lyj.dbc.usercenter.security.SecurityUtils;
import com.lyj.dbc.usercenter.user.entity.UserRoleEntity;
import com.lyj.dbc.usercenter.user.mapper.UserRoleMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * 功能权限业务服务。
 */
@Service
public class PermissionService {

    private final PermissionMapper permissionMapper;
    private final RolePermissionMapper rolePermissionMapper;
    private final UserRoleMapper userRoleMapper;
    private final RoleMapper roleMapper;

    public PermissionService(PermissionMapper permissionMapper, RolePermissionMapper rolePermissionMapper,
                             UserRoleMapper userRoleMapper, RoleMapper roleMapper) {
        this.permissionMapper = permissionMapper;
        this.rolePermissionMapper = rolePermissionMapper;
        this.userRoleMapper = userRoleMapper;
        this.roleMapper = roleMapper;
    }

    /**
     * 按模块分组的权限列表（权限管理页）。
     */
    public List<PermissionModuleVO> listGroupedByModule() {
        List<PermissionEntity> all = permissionMapper.selectList(new LambdaQueryWrapper<PermissionEntity>()
                .orderByAsc(PermissionEntity::getSortNo)
                .orderByAsc(PermissionEntity::getId));
        Map<String, PermissionModuleVO> map = new LinkedHashMap<>();
        for (PermissionEntity p : all) {
            PermissionModuleVO module = map.computeIfAbsent(p.getModuleCode(), code ->
                    PermissionModuleVO.builder()
                            .moduleCode(p.getModuleCode())
                            .moduleName(p.getModuleName())
                            .permissions(new ArrayList<>())
                            .build());
            module.getPermissions().add(toVo(p));
        }
        return new ArrayList<>(map.values());
    }

    /**
     * 功能授权树数据（扁平权限列表，前端组树）。
     */
    public List<PermissionVO> listAll() {
        return permissionMapper.selectList(new LambdaQueryWrapper<PermissionEntity>()
                        .orderByAsc(PermissionEntity::getSortNo)
                        .orderByAsc(PermissionEntity::getId))
                .stream()
                .map(this::toVo)
                .toList();
    }

    /**
     * 角色已授权的权限ID列表。
     */
    public List<Long> listPermissionIdsByRole(Long roleId) {
        return rolePermissionMapper.selectList(new LambdaQueryWrapper<RolePermissionEntity>()
                        .eq(RolePermissionEntity::getRoleId, roleId))
                .stream()
                .map(RolePermissionEntity::getPermissionId)
                .toList();
    }

    /**
     * 角色已授权的权限码列表。
     */
    public List<String> listPermissionCodesByRole(Long roleId) {
        List<Long> ids = listPermissionIdsByRole(roleId);
        if (ids.isEmpty()) {
            return List.of();
        }
        return permissionMapper.selectList(new LambdaQueryWrapper<PermissionEntity>().in(PermissionEntity::getId, ids))
                .stream()
                .map(PermissionEntity::getCode)
                .toList();
    }

    /**
     * 用户多角色权限码并集（仅来自角色-权限绑定，不按角色名硬编码放行）。
     */
    public List<String> listPermissionCodesByUser(Long userId) {
        List<Long> roleIds = userRoleMapper.selectList(new LambdaQueryWrapper<UserRoleEntity>()
                        .eq(UserRoleEntity::getUserId, userId))
                .stream()
                .map(UserRoleEntity::getRoleId)
                .toList();
        if (roleIds.isEmpty()) {
            return List.of();
        }
        List<Long> permIds = rolePermissionMapper.selectList(new LambdaQueryWrapper<RolePermissionEntity>()
                        .in(RolePermissionEntity::getRoleId, roleIds))
                .stream()
                .map(RolePermissionEntity::getPermissionId)
                .distinct()
                .toList();
        if (permIds.isEmpty()) {
            return List.of();
        }
        return permissionMapper.selectList(new LambdaQueryWrapper<PermissionEntity>().in(PermissionEntity::getId, permIds))
                .stream()
                .map(PermissionEntity::getCode)
                .sorted()
                .toList();
    }

    /**
     * 保存角色功能权限。
     * <ul>
     *   <li>超级管理员角色：始终不可改（默认全量授权）</li>
     *   <li>系统管理员角色：超级管理员、系统管理员可改</li>
     *   <li>其他角色：超管 / 系统管理员 / 其它具备 role.operate 的账号可改</li>
     * </ul>
     */
    @AuditLog(module = "usercenter", action = AuditAction.UPDATE, resourceType = "role", resourceId = "#roleId",
            loadBefore = "@roleService.getById(#roleId)")
    @Transactional
    public void replaceRolePermissions(Long roleId, List<Long> permissionIds) {
        RoleEntity role = roleMapper.selectById(roleId);
        if (role == null) {
            throw BizException.notFound("角色不存在");
        }
        assertCanEditRoleAuth(SecurityUtils.requireUser().getUserId(), role);
        Set<Long> unique = new LinkedHashSet<>();
        if (permissionIds != null) {
            for (Long id : permissionIds) {
                if (id != null) {
                    unique.add(id);
                }
            }
        }
        if (!unique.isEmpty()) {
            Long count = permissionMapper.selectCount(new LambdaQueryWrapper<PermissionEntity>()
                    .in(PermissionEntity::getId, unique));
            if (count == null || count != unique.size()) {
                throw BizException.badRequest("存在无效权限");
            }
        }
        rolePermissionMapper.delete(new LambdaQueryWrapper<RolePermissionEntity>()
                .eq(RolePermissionEntity::getRoleId, roleId));
        OffsetDateTime now = OffsetDateTime.now();
        for (Long permissionId : unique) {
            RolePermissionEntity row = new RolePermissionEntity();
            row.setRoleId(roleId);
            row.setPermissionId(permissionId);
            row.setCreatedAt(now);
            rolePermissionMapper.insert(row);
        }
    }

    /**
     * 当前用户是否可编辑目标角色的功能授权（前端展示用，与保存规则一致）。
     */
    public boolean canEditRoleAuth(Long actorUserId, Long targetRoleId) {
        RoleEntity role = roleMapper.selectById(targetRoleId);
        if (role == null) {
            return false;
        }
        try {
            assertCanEditRoleAuth(actorUserId, role);
            return true;
        } catch (BizException ex) {
            return false;
        }
    }

    /**
     * 角色功能授权可写规则。
     */
    private void assertCanEditRoleAuth(Long actorUserId, RoleEntity target) {
        String targetCode = target.getCode();
        if (Objects.equals("SUPER_ADMIN", targetCode)) {
            throw BizException.forbidden("超级管理员的功能授权不可修改");
        }
        Set<String> actorCodes = new LinkedHashSet<>(listRoleCodesByUser(actorUserId));
        boolean actorSuper = actorCodes.contains("SUPER_ADMIN");
        boolean actorSys = actorCodes.contains("SYS_ADMIN");
        if (Objects.equals("SYS_ADMIN", targetCode)) {
            if (!actorSuper && !actorSys) {
                throw BizException.forbidden("仅超级管理员或系统管理员可修改系统管理员的功能授权");
            }
            return;
        }
        // 其他角色：超管、系统管理员或其它具备 operate 的账号均可（operate 由接口注解校验）
    }

    private List<String> listRoleCodesByUser(Long userId) {
        List<Long> roleIds = userRoleMapper.selectList(new LambdaQueryWrapper<UserRoleEntity>()
                        .eq(UserRoleEntity::getUserId, userId))
                .stream()
                .map(UserRoleEntity::getRoleId)
                .toList();
        if (roleIds.isEmpty()) {
            return List.of();
        }
        return roleMapper.selectList(new LambdaQueryWrapper<RoleEntity>().in(RoleEntity::getId, roleIds))
                .stream()
                .map(RoleEntity::getCode)
                .toList();
    }

    /**
     * 是否具备所需权限：精确匹配，或声明 view 时持有同功能 operate 也可。
     */
    public static boolean implies(Set<String> owned, String required) {
        if (owned == null || required == null || required.isBlank()) {
            return false;
        }
        if (owned.contains(required)) {
            return true;
        }
        if (required.endsWith(".view")) {
            String operate = required.substring(0, required.length() - ".view".length()) + ".operate";
            return owned.contains(operate);
        }
        return false;
    }

    /**
     * 当前用户是否具备权限。
     */
    public boolean userHas(Long userId, String required) {
        Set<String> owned = new LinkedHashSet<>(listPermissionCodesByUser(userId));
        return implies(owned, required);
    }

    /**
     * 服务启动注册：按 code 幂等 upsert 权限点，并默认绑定到 SUPER_ADMIN（只增不减）。
     * 其它业务角色（如 DB_ADMIN）由调用方再调 bindPermissionsToRoles，或由 Flyway 默认脚本补齐。
     */
    @Transactional
    public void registerPermissions(List<PermissionRegisterItem> items) {
        if (items == null || items.isEmpty()) {
            return;
        }
        OffsetDateTime now = OffsetDateTime.now();
        List<String> codes = new ArrayList<>();
        for (PermissionRegisterItem item : items) {
            if (item == null || item.getCode() == null || item.getCode().isBlank()) {
                throw BizException.badRequest("权限码不能为空");
            }
            String code = item.getCode().trim();
            codes.add(code);
            PermissionEntity existing = permissionMapper.selectOne(new LambdaQueryWrapper<PermissionEntity>()
                    .eq(PermissionEntity::getCode, code));
            if (existing == null) {
                PermissionEntity row = new PermissionEntity();
                row.setCode(code);
                row.setName(requireText(item.getName(), "权限名称"));
                row.setDescription(item.getDescription());
                row.setModuleCode(requireText(item.getModuleCode(), "moduleCode"));
                row.setModuleName(requireText(item.getModuleName(), "moduleName"));
                row.setFeatureCode(requireText(item.getFeatureCode(), "featureCode"));
                row.setFeatureName(requireText(item.getFeatureName(), "featureName"));
                row.setSortNo(item.getSortNo() == null ? 100 : item.getSortNo());
                row.setBuiltin(0);
                row.setDeleted(0);
                row.setCreatedAt(now);
                row.setUpdatedAt(now);
                permissionMapper.insert(row);
            } else {
                existing.setName(requireText(item.getName(), "权限名称"));
                existing.setDescription(item.getDescription());
                existing.setModuleCode(requireText(item.getModuleCode(), "moduleCode"));
                existing.setModuleName(requireText(item.getModuleName(), "moduleName"));
                existing.setFeatureCode(requireText(item.getFeatureCode(), "featureCode"));
                existing.setFeatureName(requireText(item.getFeatureName(), "featureName"));
                if (item.getSortNo() != null) {
                    existing.setSortNo(item.getSortNo());
                }
                existing.setUpdatedAt(now);
                permissionMapper.updateById(existing);
            }
        }
        // 默认权限：任何新注册权限自动授予超级管理员
        bindPermissionsToRoles(List.of("SUPER_ADMIN"), codes);
    }

    /**
     * 服务启动绑定：按角色 code 为权限码做只增绑定（不撤销既有）。
     */
    @Transactional
    public void bindPermissionsToRoles(List<String> roleCodes, List<String> permissionCodes) {
        if (roleCodes == null || roleCodes.isEmpty() || permissionCodes == null || permissionCodes.isEmpty()) {
            return;
        }
        List<PermissionEntity> perms = permissionMapper.selectList(new LambdaQueryWrapper<PermissionEntity>()
                .in(PermissionEntity::getCode, permissionCodes));
        if (perms.size() != new LinkedHashSet<>(permissionCodes).size()) {
            throw BizException.badRequest("存在未注册的权限码");
        }
        OffsetDateTime now = OffsetDateTime.now();
        for (String roleCode : roleCodes) {
            if (roleCode == null || roleCode.isBlank()) {
                continue;
            }
            RoleEntity role = roleMapper.selectOne(new LambdaQueryWrapper<RoleEntity>()
                    .eq(RoleEntity::getCode, roleCode.trim()));
            if (role == null) {
                throw BizException.badRequest("角色不存在: " + roleCode);
            }
            Set<Long> owned = new LinkedHashSet<>(listPermissionIdsByRole(role.getId()));
            for (PermissionEntity perm : perms) {
                if (owned.contains(perm.getId())) {
                    continue;
                }
                RolePermissionEntity row = new RolePermissionEntity();
                row.setRoleId(role.getId());
                row.setPermissionId(perm.getId());
                row.setCreatedAt(now);
                // ON CONFLICT DO NOTHING：多服务并发启动注册时避免唯一约束冲突
                rolePermissionMapper.insertIgnore(row);
                owned.add(perm.getId());
            }
        }
    }

    private static String requireText(String value, String label) {
        if (value == null || value.isBlank()) {
            throw BizException.badRequest(label + "不能为空");
        }
        return value.trim();
    }

    private PermissionVO toVo(PermissionEntity p) {
        return PermissionVO.builder()
                .id(p.getId())
                .code(p.getCode())
                .name(p.getName())
                .description(p.getDescription())
                .moduleCode(p.getModuleCode())
                .moduleName(p.getModuleName())
                .featureCode(p.getFeatureCode())
                .featureName(p.getFeatureName())
                .sortNo(p.getSortNo())
                .builtin(p.getBuiltin() != null && p.getBuiltin() == 1)
                .build();
    }
}
