package com.lyj.dbc.usercenter.user;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.lyj.dbc.client.audit.AuditAction;
import com.lyj.dbc.client.audit.AuditLog;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.common.PageResult;
import com.lyj.dbc.usercenter.dept.DeptService;
import com.lyj.dbc.usercenter.dept.entity.DeptEntity;
import com.lyj.dbc.usercenter.dept.mapper.DeptMapper;
import com.lyj.dbc.usercenter.role.entity.RoleEntity;
import com.lyj.dbc.usercenter.role.RoleService;
import com.lyj.dbc.usercenter.security.LoginUser;
import com.lyj.dbc.usercenter.security.SecurityUtils;
import com.lyj.dbc.usercenter.user.dto.PasswordResetRequest;
import com.lyj.dbc.usercenter.user.dto.UserCreateRequest;
import com.lyj.dbc.usercenter.user.dto.UserQueryRequest;
import com.lyj.dbc.usercenter.user.dto.UserUpdateRequest;
import com.lyj.dbc.usercenter.user.entity.UserEntity;
import com.lyj.dbc.usercenter.user.entity.UserRoleEntity;
import com.lyj.dbc.usercenter.user.mapper.UserMapper;
import com.lyj.dbc.usercenter.user.mapper.UserRoleMapper;
import com.lyj.dbc.usercenter.user.vo.UserVO;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 用户业务服务。
 */
@Service
public class UserService {

    private final UserMapper userMapper;
    private final UserRoleMapper userRoleMapper;
    private final RoleService roleService;
    private final DeptMapper deptMapper;
    private final DeptService deptService;
    private final PasswordEncoder passwordEncoder;

    public UserService(UserMapper userMapper, UserRoleMapper userRoleMapper, RoleService roleService,
                       DeptMapper deptMapper, DeptService deptService, PasswordEncoder passwordEncoder) {
        this.userMapper = userMapper;
        this.userRoleMapper = userRoleMapper;
        this.roleService = roleService;
        this.deptMapper = deptMapper;
        this.deptService = deptService;
        this.passwordEncoder = passwordEncoder;
    }

    /**
     * 按ID查询用户视图。
     */
    public UserVO getById(Long id) {
        UserEntity user = requireUser(id);
        return toView(user, loadRolesForUser(id), loadDeptName(user.getDeptId()));
    }

    /**
     * 按账号加载实体（含密码哈希，仅内部使用）。
     */
    public UserEntity loadEntityByUsername(String username) {
        return userMapper.selectOne(new LambdaQueryWrapper<UserEntity>()
                .eq(UserEntity::getUsername, username));
    }

    /**
     * 用户绑定的角色实体列表。
     */
    public List<RoleEntity> listRolesOfUser(Long userId) {
        return loadRolesForUser(userId);
    }

    /**
     * 分页查询用户。
     */
    public PageResult<UserVO> page(UserQueryRequest query) {
        Page<UserEntity> p = userMapper.selectPage(new Page<>(query.getPage(), query.getSize()),
                new LambdaQueryWrapper<UserEntity>()
                        .like(StringUtils.hasText(query.getUsername()), UserEntity::getUsername, query.getUsername())
                        .orderByDesc(UserEntity::getCreatedAt));
        List<Long> userIds = p.getRecords().stream().map(UserEntity::getId).toList();
        Map<Long, List<RoleEntity>> roleMap = loadRolesForUsers(userIds);
        Set<Long> deptIds = p.getRecords().stream()
                .map(UserEntity::getDeptId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        Map<Long, String> deptNames = loadDeptNames(deptIds);
        List<UserVO> records = p.getRecords().stream()
                .map(u -> toView(u, roleMap.getOrDefault(u.getId(), List.of()), deptNames.get(u.getDeptId())))
                .toList();
        return new PageResult<>(records, p.getTotal(), p.getCurrent(), p.getSize());
    }

    /**
     * 新增用户。
     */
    @AuditLog(module = "usercenter", action = AuditAction.CREATE, resourceType = "user", resourceId = "#return.id")
    @Transactional
    public UserVO create(UserCreateRequest request) {
        Long count = userMapper.selectCount(new LambdaQueryWrapper<UserEntity>()
                .eq(UserEntity::getUsername, request.getUsername()));
        if (count != null && count > 0) {
            throw BizException.conflict("账号已存在");
        }
        List<RoleEntity> roles = requireRoles(request.getRoleIds());
        Long deptId = normalizeDeptId(request.getDeptId());
        LoginUser operator = SecurityUtils.requireUser();
        OffsetDateTime now = OffsetDateTime.now();
        UserEntity user = new UserEntity();
        user.setUsername(request.getUsername().trim());
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        user.setDeptId(deptId);
        user.setMobile(blankToNull(request.getMobile()));
        user.setDescription(blankToNull(request.getDescription()));
        user.setStatus(request.getStatus() == null ? 1 : request.getStatus());
        user.setBuiltin(0);
        user.setDeleted(0);
        user.setCreatedAt(now);
        user.setUpdatedAt(now);
        user.setCreatedBy(operator.getUserId());
        user.setUpdatedBy(operator.getUserId());
        userMapper.insert(user);
        replaceUserRoles(user.getId(), roles.stream().map(RoleEntity::getId).toList());
        return toView(user, roles, loadDeptName(deptId));
    }

    /**
     * 编辑用户。
     */
    @AuditLog(module = "usercenter", action = AuditAction.UPDATE, resourceType = "user", resourceId = "#id",
            loadBefore = "getById(#id)")
    @Transactional
    public UserVO update(Long id, UserUpdateRequest request) {
        UserEntity user = requireUser(id);
        LoginUser operator = SecurityUtils.requireUser();
        if (isBuiltin(user) && Objects.equals(request.getStatus(), 0)) {
            throw BizException.badRequest("内置账号不可禁用");
        }
        if (Objects.equals(operator.getUserId(), id) && Objects.equals(request.getStatus(), 0)) {
            throw BizException.badRequest("不能禁用当前登录用户");
        }
        List<RoleEntity> roles = requireRoles(request.getRoleIds());
        Long deptId = normalizeDeptId(request.getDeptId());
        user.setMobile(blankToNull(request.getMobile()));
        user.setDescription(blankToNull(request.getDescription()));
        user.setStatus(request.getStatus());
        user.setUpdatedAt(OffsetDateTime.now());
        user.setUpdatedBy(operator.getUserId());
        userMapper.updateById(user);
        // 允许清空归属部门（updateById 默认忽略 null）
        userMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<UserEntity>()
                .eq(UserEntity::getId, id)
                .set(UserEntity::getDeptId, deptId));
        replaceUserRoles(user.getId(), roles.stream().map(RoleEntity::getId).toList());
        user.setDeptId(deptId);
        return toView(user, roles, loadDeptName(deptId));
    }

    /**
     * 逻辑删除用户。
     */
    @AuditLog(module = "usercenter", action = AuditAction.DELETE, resourceType = "user", resourceId = "#id",
            loadBefore = "getById(#id)")
    @Transactional
    public void delete(Long id) {
        UserEntity user = requireUser(id);
        LoginUser operator = SecurityUtils.requireUser();
        if (isBuiltin(user)) {
            throw BizException.badRequest("内置账号不可删除");
        }
        if (Objects.equals(operator.getUserId(), id)) {
            throw BizException.badRequest("不能删除当前登录用户");
        }
        userRoleMapper.delete(new LambdaQueryWrapper<UserRoleEntity>().eq(UserRoleEntity::getUserId, id));
        userMapper.deleteById(id);
    }

    /**
     * 重置密码。
     */
    @AuditLog(module = "usercenter", action = AuditAction.UPDATE, resourceType = "user", resourceId = "#id",
            loadBefore = "getById(#id)")
    @Transactional
    public void resetPassword(Long id, PasswordResetRequest request) {
        UserEntity user = requireUser(id);
        LoginUser operator = SecurityUtils.requireUser();
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        user.setUpdatedAt(OffsetDateTime.now());
        user.setUpdatedBy(operator.getUserId());
        userMapper.updateById(user);
    }

    /**
     * Entity 转 VO。
     */
    public UserVO toView(UserEntity user, List<RoleEntity> roles, String deptName) {
        List<UserVO.RoleBrief> briefs = roles == null ? List.of() : roles.stream()
                .map(r -> UserVO.RoleBrief.builder()
                        .id(r.getId())
                        .code(r.getCode())
                        .name(r.getName())
                        .dataScope(r.getDataScope())
                        .build())
                .toList();
        return UserVO.builder()
                .id(user.getId())
                .username(user.getUsername())
                .mobile(user.getMobile())
                .description(user.getDescription())
                .status(user.getStatus())
                .builtin(isBuiltin(user))
                .deptId(user.getDeptId())
                .deptName(deptName)
                .createdAt(user.getCreatedAt())
                .roles(briefs)
                .role(briefs.isEmpty() ? null : briefs.get(0))
                .build();
    }

    private UserEntity requireUser(Long id) {
        UserEntity user = userMapper.selectById(id);
        if (user == null) {
            throw BizException.notFound("用户不存在");
        }
        return user;
    }

    private List<RoleEntity> requireRoles(List<Long> roleIds) {
        if (roleIds == null || roleIds.isEmpty()) {
            throw BizException.badRequest("至少绑定一个角色");
        }
        Set<Long> unique = new LinkedHashSet<>(roleIds);
        List<RoleEntity> roles = roleService.listByIds(new ArrayList<>(unique));
        if (roles.size() != unique.size()) {
            throw BizException.badRequest("存在无效角色");
        }
        return roles;
    }

    private Long normalizeDeptId(Long deptId) {
        if (deptId == null) {
            return null;
        }
        deptService.requireDept(deptId);
        return deptId;
    }

    private void replaceUserRoles(Long userId, List<Long> roleIds) {
        userRoleMapper.delete(new LambdaQueryWrapper<UserRoleEntity>().eq(UserRoleEntity::getUserId, userId));
        OffsetDateTime now = OffsetDateTime.now();
        for (Long roleId : roleIds) {
            UserRoleEntity row = new UserRoleEntity();
            row.setUserId(userId);
            row.setRoleId(roleId);
            row.setCreatedAt(now);
            userRoleMapper.insert(row);
        }
    }

    private List<RoleEntity> loadRolesForUser(Long userId) {
        List<Long> roleIds = userRoleMapper.selectList(new LambdaQueryWrapper<UserRoleEntity>()
                        .eq(UserRoleEntity::getUserId, userId))
                .stream()
                .map(UserRoleEntity::getRoleId)
                .toList();
        return roleService.listByIds(roleIds);
    }

    private Map<Long, List<RoleEntity>> loadRolesForUsers(List<Long> userIds) {
        Map<Long, List<RoleEntity>> result = new HashMap<>();
        if (userIds == null || userIds.isEmpty()) {
            return result;
        }
        List<UserRoleEntity> links = userRoleMapper.selectList(new LambdaQueryWrapper<UserRoleEntity>()
                .in(UserRoleEntity::getUserId, userIds));
        Set<Long> roleIds = links.stream().map(UserRoleEntity::getRoleId).collect(Collectors.toSet());
        Map<Long, RoleEntity> roleMap = roleService.listByIds(new ArrayList<>(roleIds)).stream()
                .collect(Collectors.toMap(RoleEntity::getId, r -> r, (a, b) -> a));
        for (UserRoleEntity link : links) {
            RoleEntity role = roleMap.get(link.getRoleId());
            if (role == null) {
                continue;
            }
            result.computeIfAbsent(link.getUserId(), k -> new ArrayList<>()).add(role);
        }
        return result;
    }

    private String loadDeptName(Long deptId) {
        if (deptId == null) {
            return null;
        }
        DeptEntity dept = deptMapper.selectById(deptId);
        return dept == null ? null : dept.getName();
    }

    private Map<Long, String> loadDeptNames(Set<Long> deptIds) {
        if (deptIds == null || deptIds.isEmpty()) {
            // 不可用 Map.of()：对其 get(null) 会 NPE（用户未绑定部门时常见）
            return new HashMap<>();
        }
        return deptMapper.selectList(new LambdaQueryWrapper<DeptEntity>().in(DeptEntity::getId, deptIds))
                .stream()
                .collect(Collectors.toMap(DeptEntity::getId, DeptEntity::getName, (a, b) -> a, HashMap::new));
    }

    private static boolean isBuiltin(UserEntity user) {
        return user.getBuiltin() != null && user.getBuiltin() == 1;
    }

    private static String blankToNull(String value) {
        return StringUtils.hasText(value) ? value.trim() : null;
    }
}
