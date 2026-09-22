package com.lyj.dbc.manage.authz;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.client.audit.AuditAction;
import com.lyj.dbc.client.audit.AuditLog;
import com.lyj.dbc.manage.asset.DataScopeSupport;
import com.lyj.dbc.manage.asset.connection.entity.ConnectionEntity;
import com.lyj.dbc.manage.asset.connection.mapper.ConnectionMapper;
import com.lyj.dbc.manage.authz.cache.WorkspaceAuthzCacheService;
import com.lyj.dbc.manage.authz.dto.WorkspaceAdminRequests;
import com.lyj.dbc.manage.client.dto.DataScopeVO;
import com.lyj.dbc.manage.authz.entity.WorkspaceAssetEntity;
import com.lyj.dbc.manage.authz.entity.WorkspaceEntity;
import com.lyj.dbc.manage.authz.entity.WorkspaceMemberEntity;
import com.lyj.dbc.manage.authz.entity.WorkspaceMemberGrantEntity;
import com.lyj.dbc.manage.authz.mapper.WorkspaceAssetMapper;
import com.lyj.dbc.manage.authz.mapper.WorkspaceMapper;
import com.lyj.dbc.manage.authz.mapper.WorkspaceMemberGrantMapper;
import com.lyj.dbc.manage.authz.mapper.WorkspaceMemberMapper;
import com.lyj.dbc.manage.authz.vo.WorkspaceDetailVO;
import com.lyj.dbc.manage.authz.vo.WorkspaceListItemVO;
import com.lyj.dbc.manage.common.BizException;
import com.lyj.dbc.manage.inner.sqlwork.vo.WorkspaceSummaryVO;
import com.lyj.dbc.manage.security.DomainCodes;
import com.lyj.dbc.manage.security.DomainContext;
import com.lyj.dbc.manage.security.LoginUser;
import com.lyj.dbc.manage.security.PermissionCodes;
import com.lyj.dbc.manage.security.SecurityUtils;
import com.lyj.dbc.manage.security.UserContextHolder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 工作空间管理。
 */
@Service
public class WorkspaceAdminService {

    private static final Logger log = LoggerFactory.getLogger(WorkspaceAdminService.class);

    private static final String ROLE_OWNER = "OWNER";
    private static final String ROLE_ADMIN = "ADMIN";
    private static final String ROLE_OPERATOR = "OPERATOR";

    private final WorkspaceMapper workspaceMapper;
    private final WorkspaceMemberMapper workspaceMemberMapper;
    private final WorkspaceAssetMapper workspaceAssetMapper;
    private final WorkspaceMemberGrantMapper workspaceMemberGrantMapper;
    private final ConnectionMapper connectionMapper;
    private final WorkspaceAuthzCacheService authzCache;
    private final ObjectMapper objectMapper;

    public WorkspaceAdminService(WorkspaceMapper workspaceMapper,
                                 WorkspaceMemberMapper workspaceMemberMapper,
                                 WorkspaceAssetMapper workspaceAssetMapper,
                                 WorkspaceMemberGrantMapper workspaceMemberGrantMapper,
                                 ConnectionMapper connectionMapper,
                                 WorkspaceAuthzCacheService authzCache,
                                 ObjectMapper objectMapper) {
        this.workspaceMapper = workspaceMapper;
        this.workspaceMemberMapper = workspaceMemberMapper;
        this.workspaceAssetMapper = workspaceAssetMapper;
        this.workspaceMemberGrantMapper = workspaceMemberGrantMapper;
        this.connectionMapper = connectionMapper;
        this.authzCache = authzCache;
        this.objectMapper = objectMapper;
    }

    @AuditLog(module = "manage", action = AuditAction.CREATE, resourceType = "workspace", resourceId = "#return.id")
    @Transactional
    public WorkspaceSummaryVO create(WorkspaceAdminRequests.CreateWorkspaceRequest request) {
        assertCanCreateWorkspace();
        LoginUser user = SecurityUtils.requireUser();
        String name = request.getName().trim();
        Long exists = workspaceMapper.selectCount(new LambdaQueryWrapper<WorkspaceEntity>()
                .eq(WorkspaceEntity::getName, name));
        if (exists != null && exists > 0) {
            throw BizException.conflict("工作空间名称已存在");
        }

        OffsetDateTime now = OffsetDateTime.now();
        WorkspaceEntity ws = new WorkspaceEntity();
        ws.setName(name);
        ws.setDescription(request.getDescription());
        ws.setOwnerUserId(user.getUserId());
        ws.setSpaceType(DomainCodes.COMPANY);
        ws.setStatus(1);
        ws.setDeleted(0);
        ws.setCreatedAt(now);
        ws.setUpdatedAt(now);
        ws.setCreatedBy(user.getUserId());
        ws.setUpdatedBy(user.getUserId());
        workspaceMapper.insert(ws);

        WorkspaceMemberEntity member = new WorkspaceMemberEntity();
        member.setWorkspaceId(ws.getId());
        member.setUserId(user.getUserId());
        member.setRoleCode(ROLE_OWNER);
        member.setDeleted(0);
        member.setCreatedAt(now);
        workspaceMemberMapper.insert(member);

        return toSummary(ws, ROLE_OWNER);
    }

    /**
     * 查询当前用户个人空间（可能不存在）。
     */
    public WorkspaceSummaryVO getPersonal() {
        assertHasPersonalSpaceView();
        LoginUser user = SecurityUtils.requireUser();
        WorkspaceEntity ws = findPersonalWorkspace(user.getUserId());
        if (ws == null) {
            return null;
        }
        return toSummary(ws, ROLE_OWNER);
    }

    /**
     * 自助创建或返回已有个人空间（每用户至多一个）。
     */
    @AuditLog(module = "manage", action = AuditAction.CREATE, resourceType = "workspace", resourceId = "#return.id")
    @Transactional
    public WorkspaceSummaryVO ensurePersonal(WorkspaceAdminRequests.CreateWorkspaceRequest request) {
        assertHasPersonalSpaceView();
        LoginUser user = SecurityUtils.requireUser();
        WorkspaceEntity existing = findPersonalWorkspace(user.getUserId());
        if (existing != null) {
            return toSummary(existing, ROLE_OWNER);
        }
        String name = request != null && StringUtils.hasText(request.getName())
                ? request.getName().trim()
                : defaultPersonalName(user);
        Long exists = workspaceMapper.selectCount(new LambdaQueryWrapper<WorkspaceEntity>()
                .eq(WorkspaceEntity::getName, name));
        if (exists != null && exists > 0) {
            name = name + "-" + user.getUserId();
        }
        OffsetDateTime now = OffsetDateTime.now();
        WorkspaceEntity ws = new WorkspaceEntity();
        ws.setName(name);
        ws.setDescription(request == null ? null : request.getDescription());
        ws.setOwnerUserId(user.getUserId());
        ws.setSpaceType(DomainCodes.PERSONAL);
        ws.setStatus(1);
        ws.setDeleted(0);
        ws.setCreatedAt(now);
        ws.setUpdatedAt(now);
        ws.setCreatedBy(user.getUserId());
        ws.setUpdatedBy(user.getUserId());
        workspaceMapper.insert(ws);

        WorkspaceMemberEntity member = new WorkspaceMemberEntity();
        member.setWorkspaceId(ws.getId());
        member.setUserId(user.getUserId());
        member.setRoleCode(ROLE_OWNER);
        member.setDeleted(0);
        member.setCreatedAt(now);
        workspaceMemberMapper.insert(member);
        return toSummary(ws, ROLE_OWNER);
    }

    private WorkspaceSummaryVO toSummary(WorkspaceEntity ws, String role) {
        return WorkspaceSummaryVO.builder()
                .id(ws.getId())
                .name(ws.getName())
                .description(ws.getDescription())
                .spaceType(normalizeSpaceType(ws.getSpaceType()))
                .myRole(role)
                .build();
    }

    private static String defaultPersonalName(LoginUser user) {
        String base = StringUtils.hasText(user.getUsername()) ? user.getUsername().trim() : ("user-" + user.getUserId());
        return base + "的个人空间";
    }

    private WorkspaceEntity findPersonalWorkspace(Long userId) {
        return workspaceMapper.selectOne(new LambdaQueryWrapper<WorkspaceEntity>()
                .eq(WorkspaceEntity::getOwnerUserId, userId)
                .eq(WorkspaceEntity::getSpaceType, DomainCodes.PERSONAL)
                .last("LIMIT 1"));
    }

    private void assertHasPersonalSpaceView() {
        Set<String> owned = UserContextHolder.permissionCodes();
        if (!PermissionCodes.implies(owned, "usercenter.personal.space.view")) {
            throw BizException.forbidden("无权限进入个人空间");
        }
    }

    private static String normalizeSpaceType(String spaceType) {
        return DomainCodes.isPersonal(spaceType) ? DomainCodes.PERSONAL : DomainCodes.COMPANY;
    }

    public List<WorkspaceSummaryVO> listMine() {
        LoginUser user = SecurityUtils.requireUser();
        List<WorkspaceMemberEntity> members = workspaceMemberMapper.selectList(
                new LambdaQueryWrapper<WorkspaceMemberEntity>()
                        .eq(WorkspaceMemberEntity::getUserId, user.getUserId()));
        List<WorkspaceSummaryVO> result = new ArrayList<>();
        for (WorkspaceMemberEntity member : members) {
            WorkspaceEntity ws = workspaceMapper.selectById(member.getWorkspaceId());
            if (ws == null || !matchCurrentDomain(ws, user.getUserId())) {
                continue;
            }
            result.add(toSummary(ws, member.getRoleCode()));
        }
        return result;
    }

    public List<WorkspaceListItemVO> listMineDetailed() {
        LoginUser user = SecurityUtils.requireUser();
        List<WorkspaceMemberEntity> members = workspaceMemberMapper.selectList(
                new LambdaQueryWrapper<WorkspaceMemberEntity>()
                        .eq(WorkspaceMemberEntity::getUserId, user.getUserId()));
        List<WorkspaceListItemVO> result = new ArrayList<>();
        for (WorkspaceMemberEntity member : members) {
            WorkspaceEntity ws = workspaceMapper.selectById(member.getWorkspaceId());
            if (ws == null || !matchCurrentDomain(ws, user.getUserId())) {
                continue;
            }
            Long memberCount = workspaceMemberMapper.selectCount(new LambdaQueryWrapper<WorkspaceMemberEntity>()
                    .eq(WorkspaceMemberEntity::getWorkspaceId, ws.getId()));
            Long assetCount = workspaceAssetMapper.selectCount(new LambdaQueryWrapper<WorkspaceAssetEntity>()
                    .eq(WorkspaceAssetEntity::getWorkspaceId, ws.getId()));
            result.add(WorkspaceListItemVO.builder()
                    .id(ws.getId())
                    .name(ws.getName())
                    .description(ws.getDescription())
                    .ownerUserId(ws.getOwnerUserId())
                    .spaceType(normalizeSpaceType(ws.getSpaceType()))
                    .myRole(member.getRoleCode())
                    .memberCount(memberCount == null ? 0 : memberCount)
                    .assetCount(assetCount == null ? 0 : assetCount)
                    .updatedAt(ws.getUpdatedAt())
                    .build());
        }
        return result;
    }

    /**
     * 管理列表按域过滤：公司域仅 COMPANY；个人域仅本人 PERSONAL。
     */
    private boolean matchCurrentDomain(WorkspaceEntity ws, Long userId) {
        boolean personal = DomainCodes.isPersonal(ws.getSpaceType());
        if (DomainContext.isPersonal()) {
            return personal && Objects.equals(ws.getOwnerUserId(), userId);
        }
        return !personal;
    }

    public WorkspaceDetailVO getDetail(Long workspaceId) {
        assertCanViewWorkspace(workspaceId);
        WorkspaceEntity ws = workspaceMapper.selectById(workspaceId);
        LoginUser user = SecurityUtils.requireUser();
        WorkspaceMemberEntity me = workspaceMemberMapper.selectOne(new LambdaQueryWrapper<WorkspaceMemberEntity>()
                .eq(WorkspaceMemberEntity::getWorkspaceId, workspaceId)
                .eq(WorkspaceMemberEntity::getUserId, user.getUserId())
                .last("LIMIT 1"));

        List<WorkspaceMemberEntity> members = workspaceMemberMapper.selectList(
                new LambdaQueryWrapper<WorkspaceMemberEntity>()
                        .eq(WorkspaceMemberEntity::getWorkspaceId, workspaceId)
                        .orderByAsc(WorkspaceMemberEntity::getId));
        List<WorkspaceAssetEntity> assets = workspaceAssetMapper.selectList(
                new LambdaQueryWrapper<WorkspaceAssetEntity>()
                        .eq(WorkspaceAssetEntity::getWorkspaceId, workspaceId)
                        .orderByAsc(WorkspaceAssetEntity::getId));
        List<WorkspaceMemberGrantEntity> grants = workspaceMemberGrantMapper.selectList(
                new LambdaQueryWrapper<WorkspaceMemberGrantEntity>()
                        .eq(WorkspaceMemberGrantEntity::getWorkspaceId, workspaceId)
                        .orderByAsc(WorkspaceMemberGrantEntity::getId));

        Map<Long, String> connectionNames = loadConnectionNames(assets, grants);

        return WorkspaceDetailVO.builder()
                .id(ws.getId())
                .name(ws.getName())
                .description(ws.getDescription())
                .ownerUserId(ws.getOwnerUserId())
                .spaceType(normalizeSpaceType(ws.getSpaceType()))
                .myRole(me == null ? null : me.getRoleCode())
                .updatedAt(ws.getUpdatedAt())
                .members(members.stream()
                        .map(m -> WorkspaceDetailVO.MemberItem.builder()
                                .id(m.getId())
                                .userId(m.getUserId())
                                .roleCode(m.getRoleCode())
                                .joinedAt(m.getCreatedAt())
                                .build())
                        .toList())
                .assets(assets.stream()
                        .map(a -> {
                            List<WorkspaceDetailVO.ObjectRef> objs = parseObjects(a.getTablesJson());
                            return WorkspaceDetailVO.AssetItem.builder()
                                    .id(a.getId())
                                    .connectionId(a.getConnectionId())
                                    .connectionName(connectionNames.getOrDefault(a.getConnectionId(), "#" + a.getConnectionId()))
                                    .objectScope(ObjectScopeCodes.normalize(a.getObjectScope()))
                                    .objects(objs)
                                    .tables(objs)
                                    .ops(parseOps(a.getOpsJson()))
                                    .createdBy(a.getCreatedBy())
                                    .createdAt(a.getCreatedAt())
                                    .build();
                        })
                        .toList())
                .memberGrants(grants.stream()
                        .map(g -> {
                            List<WorkspaceDetailVO.ObjectRef> objs = parseObjects(g.getTablesJson());
                            return WorkspaceDetailVO.MemberGrantItem.builder()
                                    .id(g.getId())
                                    .userId(g.getUserId())
                                    .grantMode(g.getGrantMode())
                                    .connectionId(g.getConnectionId())
                                    .connectionName(g.getConnectionId() == null
                                            ? null
                                            : connectionNames.getOrDefault(g.getConnectionId(), "#" + g.getConnectionId()))
                                    .objectScope(g.getObjectScope() == null
                                            ? null
                                            : ObjectScopeCodes.normalize(g.getObjectScope()))
                                    .objects(objs)
                                    .tables(objs)
                                    .ops(parseOps(g.getOpsJson()))
                                    .createdBy(g.getCreatedBy())
                                    .createdAt(g.getCreatedAt())
                                    .build();
                        })
                        .toList())
                .build();
    }

    @AuditLog(module = "manage", action = AuditAction.UPDATE, resourceType = "workspace", resourceId = "#workspaceId")
    @Transactional
    public void addMembers(Long workspaceId, WorkspaceAdminRequests.AddMembersRequest request) {
        assertCanMutateWorkspace(workspaceId);
        OffsetDateTime now = OffsetDateTime.now();
        for (Long userId : request.getUserIds()) {
            if (userId == null) {
                continue;
            }
            WorkspaceMemberEntity existing = workspaceMemberMapper.selectOne(
                    new LambdaQueryWrapper<WorkspaceMemberEntity>()
                            .eq(WorkspaceMemberEntity::getWorkspaceId, workspaceId)
                            .eq(WorkspaceMemberEntity::getUserId, userId)
                            .last("LIMIT 1"));
            if (existing != null) {
                continue;
            }
            WorkspaceMemberEntity member = new WorkspaceMemberEntity();
            member.setWorkspaceId(workspaceId);
            member.setUserId(userId);
            member.setRoleCode(ROLE_OPERATOR);
            member.setDeleted(0);
            member.setCreatedAt(now);
            workspaceMemberMapper.insert(member);
        }
        touchWorkspace(workspaceId);
    }

    @AuditLog(module = "manage", action = AuditAction.UPDATE, resourceType = "workspace", resourceId = "#workspaceId")
    @Transactional
    public void setMemberRole(Long workspaceId, Long userId, WorkspaceAdminRequests.SetMemberRoleRequest request) {
        assertCanMutateWorkspace(workspaceId);
        String role = request.getRoleCode().trim().toUpperCase(Locale.ROOT);
        if (!ROLE_ADMIN.equals(role) && !ROLE_OPERATOR.equals(role)) {
            throw BizException.badRequest("roleCode 须为 ADMIN 或 OPERATOR");
        }
        WorkspaceMemberEntity member = requireMember(workspaceId, userId);
        if (ROLE_OWNER.equalsIgnoreCase(member.getRoleCode())) {
            throw BizException.badRequest("不可变更所有者角色");
        }
        member.setRoleCode(role);
        workspaceMemberMapper.updateById(member);
        touchWorkspace(workspaceId);
        authzCache.invalidateUser(workspaceId, userId);
    }

    @AuditLog(module = "manage", action = AuditAction.DELETE, resourceType = "workspace", resourceId = "#workspaceId")
    @Transactional
    public void removeMember(Long workspaceId, Long userId) {
        assertCanMutateWorkspace(workspaceId);
        WorkspaceMemberEntity member = requireMember(workspaceId, userId);
        if (ROLE_OWNER.equalsIgnoreCase(member.getRoleCode())) {
            throw BizException.badRequest("不可移除所有者");
        }
        workspaceMemberMapper.deleteById(member.getId());
        List<WorkspaceMemberGrantEntity> grants = workspaceMemberGrantMapper.selectList(
                new LambdaQueryWrapper<WorkspaceMemberGrantEntity>()
                        .eq(WorkspaceMemberGrantEntity::getWorkspaceId, workspaceId)
                        .eq(WorkspaceMemberGrantEntity::getUserId, userId));
        for (WorkspaceMemberGrantEntity grant : grants) {
            workspaceMemberGrantMapper.deleteById(grant.getId());
        }
        touchWorkspace(workspaceId);
        authzCache.invalidateUser(workspaceId, userId);
    }

    @AuditLog(module = "manage", action = AuditAction.CREATE, resourceType = "workspace_asset", resourceId = "#workspaceId")
    @Transactional
    public void addAsset(Long workspaceId, WorkspaceAdminRequests.AddAssetRequest request) {
        assertCanMutateWorkspace(workspaceId);
        WorkspaceEntity ws = workspaceMapper.selectById(workspaceId);
        ConnectionEntity connection = connectionMapper.selectById(request.getConnectionId());
        if (connection == null) {
            throw BizException.notFound("连接不存在");
        }
        assertMountAllowed(ws, connection);
        String scope = ObjectScopeCodes.normalize(request.getObjectScope());
        if (!ObjectScopeCodes.isValid(scope)) {
            throw BizException.badRequest("objectScope 无效");
        }
        List<WorkspaceAdminRequests.ObjectRef> refs = resolveObjectRefs(request.getObjects(), request.getTables());
        validateObjectRefs(scope, refs);
        LoginUser user = SecurityUtils.requireUser();
        WorkspaceAssetEntity asset = new WorkspaceAssetEntity();
        asset.setWorkspaceId(workspaceId);
        asset.setConnectionId(request.getConnectionId());
        asset.setObjectScope(scope);
        asset.setTablesJson(ObjectScopeCodes.isWholeConnection(scope) ? "[]" : toJson(refs));
        asset.setOpsJson(toJson(normalizeOps(request.getOps())));
        asset.setDeleted(0);
        asset.setCreatedAt(OffsetDateTime.now());
        asset.setCreatedBy(user.getUserId());
        workspaceAssetMapper.insert(asset);
        touchWorkspace(workspaceId);
        authzCache.invalidateAssets(workspaceId);
    }

    @AuditLog(module = "manage", action = AuditAction.UPDATE, resourceType = "workspace_asset", resourceId = "#assetId")
    @Transactional
    public void updateAsset(Long workspaceId, Long assetId, WorkspaceAdminRequests.UpdateAssetRequest request) {
        assertCanMutateWorkspace(workspaceId);
        WorkspaceAssetEntity asset = workspaceAssetMapper.selectById(assetId);
        if (asset == null || !Objects.equals(asset.getWorkspaceId(), workspaceId)) {
            throw BizException.notFound("资产授权不存在");
        }
        WorkspaceEntity ws = workspaceMapper.selectById(workspaceId);
        ConnectionEntity connection = connectionMapper.selectById(request.getConnectionId());
        if (connection == null) {
            throw BizException.notFound("连接不存在");
        }
        assertMountAllowed(ws, connection);
        String scope = ObjectScopeCodes.normalize(request.getObjectScope());
        if (!ObjectScopeCodes.isValid(scope)) {
            throw BizException.badRequest("objectScope 无效");
        }
        List<WorkspaceAdminRequests.ObjectRef> refs = resolveObjectRefs(request.getObjects(), request.getTables());
        validateObjectRefs(scope, refs);
        asset.setConnectionId(request.getConnectionId());
        asset.setObjectScope(scope);
        asset.setTablesJson(ObjectScopeCodes.isWholeConnection(scope) ? "[]" : toJson(refs));
        asset.setOpsJson(toJson(normalizeOps(request.getOps())));
        workspaceAssetMapper.updateById(asset);
        touchWorkspace(workspaceId);
        authzCache.invalidateAssets(workspaceId);
    }

    /**
     * 个人连接只能挂本人 PERSONAL 空间；公司连接只能挂 COMPANY 空间且需 data-scope。
     */
    private void assertMountAllowed(WorkspaceEntity ws, ConnectionEntity connection) {
        boolean personalSpace = DomainCodes.isPersonal(ws.getSpaceType());
        boolean personalConn = DomainCodes.isPersonal(connection.getOwnerScope());
        LoginUser user = SecurityUtils.requireUser();
        if (personalConn) {
            if (!personalSpace) {
                throw BizException.badRequest("个人连接只能挂载到个人空间");
            }
            if (!Objects.equals(connection.getOwnerUserId(), user.getUserId())
                    || !Objects.equals(ws.getOwnerUserId(), user.getUserId())) {
                throw BizException.forbidden("个人连接只能挂载到本人个人空间");
            }
            return;
        }
        if (personalSpace) {
            throw BizException.badRequest("公司连接不能挂载到个人空间");
        }
        DataScopeVO scope = DataScopeSupport.current();
        if (!DataScopeSupport.isAll(scope) && !DataScopeSupport.inScope(connection.getDeptId(), scope)) {
            throw BizException.forbidden("无权将该连接挂载到工作空间（不在数据范围内）");
        }
    }

    @AuditLog(module = "manage", action = AuditAction.DELETE, resourceType = "workspace_asset", resourceId = "#assetId")
    @Transactional
    public void removeAsset(Long workspaceId, Long assetId) {
        assertCanMutateWorkspace(workspaceId);
        WorkspaceAssetEntity asset = workspaceAssetMapper.selectById(assetId);
        if (asset == null || !Objects.equals(asset.getWorkspaceId(), workspaceId)) {
            throw BizException.notFound("资产授权不存在");
        }
        workspaceAssetMapper.deleteById(assetId);
        touchWorkspace(workspaceId);
        authzCache.invalidateAssets(workspaceId);
    }

    @AuditLog(module = "manage", action = AuditAction.CREATE, resourceType = "workspace_grant", resourceId = "#workspaceId")
    @Transactional
    public void addMemberGrant(Long workspaceId, WorkspaceAdminRequests.AddMemberGrantRequest request) {
        assertCanMutateWorkspace(workspaceId);
        String mode = request.getGrantMode().trim().toUpperCase(Locale.ROOT);
        if (!"ALL".equals(mode) && !"SPECIFIC".equals(mode)) {
            throw BizException.badRequest("grantMode 须为 ALL 或 SPECIFIC");
        }
        WorkspaceMemberEntity target = requireMember(workspaceId, request.getUserId());
        if (ROLE_OWNER.equalsIgnoreCase(target.getRoleCode())) {
            throw BizException.badRequest("所有者无需成员授权");
        }

        LoginUser user = SecurityUtils.requireUser();
        WorkspaceMemberGrantEntity grant = new WorkspaceMemberGrantEntity();
        grant.setWorkspaceId(workspaceId);
        grant.setUserId(request.getUserId());
        grant.setGrantMode(mode);
        if ("SPECIFIC".equals(mode)) {
            if (request.getConnectionId() == null) {
                throw BizException.badRequest("SPECIFIC 模式须指定 connectionId");
            }
            String scope = ObjectScopeCodes.normalize(
                    StringUtils.hasText(request.getObjectScope()) ? request.getObjectScope() : ObjectScopeCodes.CONNECTION);
            if (!ObjectScopeCodes.isValid(scope)) {
                throw BizException.badRequest("objectScope 无效");
            }
            List<WorkspaceAdminRequests.ObjectRef> refs = resolveObjectRefs(request.getObjects(), request.getTables());
            validateObjectRefs(scope, refs);
            List<String> ops = normalizeOps(request.getOps());
            assertWithinWorkspaceAssets(workspaceId, request.getConnectionId(), scope, refs, ops);
            grant.setConnectionId(request.getConnectionId());
            grant.setObjectScope(scope);
            grant.setTablesJson(ObjectScopeCodes.isWholeConnection(scope) ? "[]" : toJson(refs));
            grant.setOpsJson(toJson(ops));
        } else {
            grant.setConnectionId(null);
            grant.setObjectScope(null);
            grant.setTablesJson(null);
            grant.setOpsJson(null);
        }
        grant.setDeleted(0);
        grant.setCreatedAt(OffsetDateTime.now());
        grant.setCreatedBy(user.getUserId());
        workspaceMemberGrantMapper.insert(grant);
        touchWorkspace(workspaceId);
        authzCache.invalidateUser(workspaceId, request.getUserId());
    }

    /**
     * 三步向导：自动加人（默认 OPERATOR）并为每人写入多条 SPECIFIC 授权。
     */
    @AuditLog(module = "manage", action = AuditAction.UPDATE, resourceType = "workspace_grant", resourceId = "#workspaceId")
    @Transactional
    public void batchMemberGrants(Long workspaceId, WorkspaceAdminRequests.BatchMemberGrantRequest request) {
        assertCanMutateWorkspace(workspaceId);
        List<String> ops = normalizeOps(request.getOps());
        WorkspaceAdminRequests.AddMembersRequest addMembers = new WorkspaceAdminRequests.AddMembersRequest();
        addMembers.setUserIds(request.getUserIds());
        addMembers(workspaceId, addMembers);

        for (Long userId : request.getUserIds()) {
            WorkspaceMemberEntity target = requireMember(workspaceId, userId);
            if (ROLE_OWNER.equalsIgnoreCase(target.getRoleCode())) {
                continue;
            }
            for (WorkspaceAdminRequests.GrantTarget targetScope : request.getTargets()) {
                WorkspaceAdminRequests.AddMemberGrantRequest one = new WorkspaceAdminRequests.AddMemberGrantRequest();
                one.setUserId(userId);
                one.setGrantMode("SPECIFIC");
                one.setConnectionId(targetScope.getConnectionId());
                one.setObjectScope(targetScope.getObjectScope());
                one.setObjects(targetScope.getObjects());
                one.setOps(ops);
                addMemberGrant(workspaceId, one);
            }
        }
    }

    @AuditLog(module = "manage", action = AuditAction.UPDATE, resourceType = "workspace_grant", resourceId = "#grantId")
    @Transactional
    public void updateMemberGrant(Long workspaceId, Long grantId,
                                  WorkspaceAdminRequests.UpdateMemberGrantRequest request) {
        assertCanMutateWorkspace(workspaceId);
        WorkspaceMemberGrantEntity grant = workspaceMemberGrantMapper.selectById(grantId);
        if (grant == null || !Objects.equals(grant.getWorkspaceId(), workspaceId)) {
            throw BizException.notFound("成员授权不存在");
        }
        if (!"SPECIFIC".equalsIgnoreCase(grant.getGrantMode())) {
            throw BizException.badRequest("「跟随全部空间资产」授权无需编辑对象与权限，请删除后改用指定授权");
        }
        String scope = ObjectScopeCodes.normalize(
                StringUtils.hasText(request.getObjectScope()) ? request.getObjectScope() : ObjectScopeCodes.CONNECTION);
        if (!ObjectScopeCodes.isValid(scope)) {
            throw BizException.badRequest("objectScope 无效");
        }
        List<WorkspaceAdminRequests.ObjectRef> refs = resolveObjectRefs(request.getObjects(), request.getTables());
        validateObjectRefs(scope, refs);
        List<String> ops = normalizeOps(request.getOps());
        assertWithinWorkspaceAssets(workspaceId, request.getConnectionId(), scope, refs, ops);
        grant.setConnectionId(request.getConnectionId());
        grant.setObjectScope(scope);
        grant.setTablesJson(ObjectScopeCodes.isWholeConnection(scope) ? "[]" : toJson(refs));
        grant.setOpsJson(toJson(ops));
        workspaceMemberGrantMapper.updateById(grant);
        touchWorkspace(workspaceId);
        authzCache.invalidateUser(workspaceId, grant.getUserId());
    }

    @AuditLog(module = "manage", action = AuditAction.DELETE, resourceType = "workspace_grant", resourceId = "#grantId")
    @Transactional
    public void removeMemberGrant(Long workspaceId, Long grantId) {
        assertCanMutateWorkspace(workspaceId);
        WorkspaceMemberGrantEntity grant = workspaceMemberGrantMapper.selectById(grantId);
        if (grant == null || !Objects.equals(grant.getWorkspaceId(), workspaceId)) {
            throw BizException.notFound("成员授权不存在");
        }
        workspaceMemberGrantMapper.deleteById(grantId);
        touchWorkspace(workspaceId);
        authzCache.invalidateUser(workspaceId, grant.getUserId());
    }

    private static List<WorkspaceAdminRequests.ObjectRef> resolveObjectRefs(
            List<WorkspaceAdminRequests.ObjectRef> objects,
            List<WorkspaceAdminRequests.ObjectRef> tables) {
        if (objects != null && !objects.isEmpty()) {
            return objects;
        }
        return tables == null ? List.of() : tables;
    }

    private static void validateObjectRefs(String scope, List<WorkspaceAdminRequests.ObjectRef> refs) {
        if (ObjectScopeCodes.isWholeConnection(scope)) {
            return;
        }
        if (refs == null || refs.isEmpty()) {
            throw BizException.badRequest("非整连接授权时 objects 不能为空");
        }
        for (WorkspaceAdminRequests.ObjectRef ref : refs) {
            if (ObjectScopeCodes.isDatabase(scope) && !StringUtils.hasText(ref.getDatabase())) {
                throw BizException.badRequest("DATABASE 范围须指定 database");
            }
            if (ObjectScopeCodes.isSchema(scope)
                    && (!StringUtils.hasText(ref.getDatabase()) || !StringUtils.hasText(ref.getSchema()))) {
                throw BizException.badRequest("SCHEMA 范围须指定 database 与 schema");
            }
            if (ObjectScopeCodes.isTableLevel(scope) && !StringUtils.hasText(ref.getName())) {
                throw BizException.badRequest("TABLE 范围须指定表名");
            }
        }
    }

    /**
     * 成员 SPECIFIC 授权必须 ⊆ 空间资产授权（对象范围 + SQL 操作）。
     */
    private void assertWithinWorkspaceAssets(Long workspaceId, Long connectionId, String scope,
                                             List<WorkspaceAdminRequests.ObjectRef> refs,
                                             List<String> grantOps) {
        List<WorkspaceAssetEntity> assets = workspaceAssetMapper.selectList(
                new LambdaQueryWrapper<WorkspaceAssetEntity>()
                        .eq(WorkspaceAssetEntity::getWorkspaceId, workspaceId)
                        .eq(WorkspaceAssetEntity::getConnectionId, connectionId));
        if (assets.isEmpty()) {
            throw BizException.badRequest("连接未挂载到本空间资产，无法授权给成员");
        }
        String grantScope = ObjectScopeCodes.normalize(scope);
        if (ObjectScopeCodes.isWholeConnection(grantScope)) {
            boolean ok = assets.stream().anyMatch(a -> ObjectScopeCodes.isWholeConnection(a.getObjectScope()));
            if (!ok) {
                throw BizException.badRequest("空间资产未授权「整个连接」，成员不能授予连接级权限");
            }
            Set<String> allowedOps = collectCoveringAssetOps(assets, grantScope, null);
            assertOpsWithin(allowedOps, grantOps, "整个连接");
            return;
        }
        List<WorkspaceAdminRequests.ObjectRef> grantRefs = refs == null ? List.of() : refs;
        for (WorkspaceAdminRequests.ObjectRef ref : grantRefs) {
            if (!assetCoversRef(assets, grantScope, ref)) {
                throw BizException.badRequest("成员授权对象超出空间资产范围: " + formatRef(grantScope, ref));
            }
            Set<String> allowedOps = collectCoveringAssetOps(assets, grantScope, ref);
            assertOpsWithin(allowedOps, grantOps, formatRef(grantScope, ref));
        }
    }

    /**
     * 覆盖某授权对象的空间资产 ops 并集。
     */
    private Set<String> collectCoveringAssetOps(List<WorkspaceAssetEntity> assets, String grantScope,
                                                WorkspaceAdminRequests.ObjectRef ref) {
        Set<String> ops = new HashSet<>();
        for (WorkspaceAssetEntity asset : assets) {
            if (!singleAssetCovers(asset, grantScope, ref)) {
                continue;
            }
            ops.addAll(parseOps(asset.getOpsJson()));
        }
        return ops;
    }

    private boolean singleAssetCovers(WorkspaceAssetEntity asset, String grantScope,
                                      WorkspaceAdminRequests.ObjectRef ref) {
        String assetScope = ObjectScopeCodes.normalize(asset.getObjectScope());
        if (ObjectScopeCodes.isWholeConnection(grantScope)) {
            return ObjectScopeCodes.isWholeConnection(assetScope);
        }
        if (ObjectScopeCodes.isWholeConnection(assetScope)) {
            return true;
        }
        List<WorkspaceAdminRequests.ObjectRef> assetRefs = parseRequestRefs(asset.getTablesJson());
        if (ObjectScopeCodes.isDatabase(assetScope)) {
            if (ObjectScopeCodes.isWholeConnection(grantScope)) {
                return false;
            }
            return assetRefs.stream().anyMatch(a -> eqIgnore(a.getDatabase(), ref.getDatabase()));
        }
        if (ObjectScopeCodes.isSchema(assetScope)) {
            if (ObjectScopeCodes.isWholeConnection(grantScope) || ObjectScopeCodes.isDatabase(grantScope)) {
                return false;
            }
            return assetRefs.stream().anyMatch(a ->
                    eqIgnore(a.getDatabase(), ref.getDatabase())
                            && eqIgnore(a.getSchema(), ref.getSchema()));
        }
        if (ObjectScopeCodes.isTableLevel(assetScope)) {
            if (!ObjectScopeCodes.isTableLevel(grantScope)) {
                return false;
            }
            return assetRefs.stream().anyMatch(a ->
                    eqIgnore(a.getDatabase(), ref.getDatabase())
                            && eqIgnore(a.getSchema(), ref.getSchema())
                            && eqIgnore(a.getName(), ref.getName()));
        }
        return false;
    }

    private static void assertOpsWithin(Set<String> allowedOps, List<String> grantOps, String objectHint) {
        if (grantOps == null || grantOps.isEmpty()) {
            throw BizException.badRequest("ops 不能为空");
        }
        if (allowedOps == null || allowedOps.isEmpty()) {
            throw BizException.badRequest("空间资产未授予可用 SQL 权限: " + objectHint);
        }
        Set<String> allowedUpper = allowedOps.stream()
                .filter(StringUtils::hasText)
                .map(s -> s.trim().toUpperCase(Locale.ROOT))
                .collect(Collectors.toSet());
        List<String> exceeded = grantOps.stream()
                .filter(op -> !allowedUpper.contains(op))
                .toList();
        if (!exceeded.isEmpty()) {
            throw BizException.badRequest(
                    "成员授权 SQL 权限超出空间资产范围(" + objectHint + "): " + String.join(",", exceeded));
        }
    }

    private boolean assetCoversRef(List<WorkspaceAssetEntity> assets, String grantScope,
                                   WorkspaceAdminRequests.ObjectRef ref) {
        for (WorkspaceAssetEntity asset : assets) {
            if (singleAssetCovers(asset, grantScope, ref)) {
                return true;
            }
        }
        return false;
    }

    private List<WorkspaceAdminRequests.ObjectRef> parseRequestRefs(String json) {
        if (!StringUtils.hasText(json)) {
            return List.of();
        }
        try {
            List<WorkspaceAdminRequests.ObjectRef> raw = objectMapper.readValue(json, new TypeReference<>() {
            });
            return raw == null ? List.of() : raw;
        } catch (Exception e) {
            log.warn("解析空间资产 objects 失败: {}", json, e);
            return List.of();
        }
    }

    private static String formatRef(String scope, WorkspaceAdminRequests.ObjectRef ref) {
        if (ObjectScopeCodes.isDatabase(scope)) {
            return ref.getDatabase();
        }
        if (ObjectScopeCodes.isSchema(scope)) {
            return ref.getDatabase() + "." + ref.getSchema();
        }
        String schema = StringUtils.hasText(ref.getSchema()) ? ref.getSchema() + "." : "";
        return (StringUtils.hasText(ref.getDatabase()) ? ref.getDatabase() + "." : "") + schema + ref.getName();
    }

    private static boolean eqIgnore(String a, String b) {
        String x = a == null ? "" : a.trim();
        String y = b == null ? "" : b.trim();
        return x.equalsIgnoreCase(y);
    }

    private WorkspaceMemberEntity requireMember(Long workspaceId, Long userId) {
        WorkspaceMemberEntity member = workspaceMemberMapper.selectOne(
                new LambdaQueryWrapper<WorkspaceMemberEntity>()
                        .eq(WorkspaceMemberEntity::getWorkspaceId, workspaceId)
                        .eq(WorkspaceMemberEntity::getUserId, userId)
                        .last("LIMIT 1"));
        if (member == null) {
            throw BizException.badRequest("目标用户不是空间成员");
        }
        return member;
    }

    private void touchWorkspace(Long workspaceId) {
        WorkspaceEntity ws = workspaceMapper.selectById(workspaceId);
        if (ws == null) {
            return;
        }
        LoginUser user = SecurityUtils.requireUser();
        ws.setUpdatedAt(OffsetDateTime.now());
        ws.setUpdatedBy(user.getUserId());
        workspaceMapper.updateById(ws);
    }

    private Map<Long, String> loadConnectionNames(List<WorkspaceAssetEntity> assets,
                                                  List<WorkspaceMemberGrantEntity> grants) {
        Set<Long> ids = assets.stream().map(WorkspaceAssetEntity::getConnectionId).collect(Collectors.toSet());
        for (WorkspaceMemberGrantEntity grant : grants) {
            if (grant.getConnectionId() != null) {
                ids.add(grant.getConnectionId());
            }
        }
        Map<Long, String> map = new HashMap<>();
        if (ids.isEmpty()) {
            return map;
        }
        List<ConnectionEntity> connections = connectionMapper.selectList(
                new LambdaQueryWrapper<ConnectionEntity>().in(ConnectionEntity::getId, ids));
        for (ConnectionEntity c : connections) {
            map.put(c.getId(), c.getName());
        }
        return map;
    }

    private List<WorkspaceDetailVO.ObjectRef> parseObjects(String json) {
        if (!StringUtils.hasText(json)) {
            return List.of();
        }
        try {
            List<WorkspaceAdminRequests.ObjectRef> raw = objectMapper.readValue(json, new TypeReference<>() {
            });
            if (raw == null) {
                return List.of();
            }
            return raw.stream()
                    .map(t -> WorkspaceDetailVO.ObjectRef.builder()
                            .database(t.getDatabase())
                            .schema(t.getSchema())
                            .name(t.getName())
                            .build())
                    .toList();
        } catch (JsonProcessingException e) {
            log.warn("解析 tables_json 失败", e);
            return List.of();
        }
    }

    private List<String> parseOps(String json) {
        if (!StringUtils.hasText(json)) {
            return List.of();
        }
        try {
            List<String> ops = objectMapper.readValue(json, new TypeReference<>() {
            });
            return ops == null ? List.of() : ops;
        } catch (JsonProcessingException e) {
            log.warn("解析 ops_json 失败", e);
            return List.of();
        }
    }

    /**
     * 授权配置侧浏览元数据：可维护该空间，且连接已是空间资产或当前域可见。
     */
    public void assertMetaBrowseAccess(Long workspaceId, Long connectionId) {
        if (connectionId == null || connectionId <= 0) {
            throw BizException.badRequest("connectionId 无效");
        }
        assertCanMutateWorkspace(workspaceId);
        Long assetCnt = workspaceAssetMapper.selectCount(new LambdaQueryWrapper<WorkspaceAssetEntity>()
                .eq(WorkspaceAssetEntity::getWorkspaceId, workspaceId)
                .eq(WorkspaceAssetEntity::getConnectionId, connectionId));
        if (assetCnt != null && assetCnt > 0) {
            return;
        }
        ConnectionEntity entity = connectionMapper.selectById(connectionId);
        if (entity == null) {
            throw BizException.notFound("连接不存在");
        }
        WorkspaceEntity ws = workspaceMapper.selectById(workspaceId);
        if (ws == null) {
            throw BizException.notFound("工作空间不存在");
        }
        if (DomainCodes.isPersonal(ws.getSpaceType())) {
            LoginUser user = SecurityUtils.requireUser();
            if (DomainCodes.isPersonal(entity.getOwnerScope())
                    && Objects.equals(entity.getOwnerUserId(), user.getUserId())
                    && Objects.equals(ws.getOwnerUserId(), user.getUserId())) {
                return;
            }
            throw BizException.forbidden("无权浏览该连接元数据");
        }
        if (DomainCodes.isPersonal(entity.getOwnerScope())) {
            throw BizException.forbidden("无权浏览该连接元数据");
        }
        DataScopeVO scope = DataScopeSupport.current();
        if (!DataScopeSupport.isAll(scope) && !DataScopeSupport.inScope(entity.getDeptId(), scope)) {
            throw BizException.forbidden("无权浏览该连接元数据（需纳入空间资产或属于数据范围）");
        }
    }

    private void assertCanCreateWorkspace() {
        if (DomainContext.isPersonal()) {
            throw BizException.badRequest("个人空间请通过个人空间入口创建");
        }
        LoginUser user = SecurityUtils.requireUser();
        if (hasOperatePermission() || hasPlatformAdminRole(user)) {
            return;
        }
        throw BizException.forbidden("无权创建工作空间");
    }

    private void assertCanViewWorkspace(Long workspaceId) {
        LoginUser user = SecurityUtils.requireUser();
        WorkspaceEntity ws = workspaceMapper.selectById(workspaceId);
        if (ws == null) {
            throw BizException.notFound("工作空间不存在");
        }
        if (DomainCodes.isPersonal(ws.getSpaceType())) {
            WorkspaceMemberEntity member = workspaceMemberMapper.selectOne(
                    new LambdaQueryWrapper<WorkspaceMemberEntity>()
                            .eq(WorkspaceMemberEntity::getWorkspaceId, workspaceId)
                            .eq(WorkspaceMemberEntity::getUserId, user.getUserId())
                            .last("LIMIT 1"));
            if (member != null) {
                return;
            }
            throw BizException.forbidden("无权查看该工作空间");
        }
        if (hasViewPermission() || hasOperatePermission() || hasPlatformAdminRole(user)) {
            return;
        }
        WorkspaceMemberEntity member = workspaceMemberMapper.selectOne(
                new LambdaQueryWrapper<WorkspaceMemberEntity>()
                        .eq(WorkspaceMemberEntity::getWorkspaceId, workspaceId)
                        .eq(WorkspaceMemberEntity::getUserId, user.getUserId())
                        .last("LIMIT 1"));
        if (member != null) {
            return;
        }
        throw BizException.forbidden("无权查看该工作空间");
    }

    private void assertCanMutateWorkspace(Long workspaceId) {
        LoginUser user = SecurityUtils.requireUser();
        WorkspaceEntity ws = workspaceMapper.selectById(workspaceId);
        if (ws == null) {
            throw BizException.notFound("工作空间不存在");
        }
        // 个人空间：仅 OWNER/ADMIN 成员可维护（平台 operate 不可越权改他人个人空间）
        if (DomainCodes.isPersonal(ws.getSpaceType())) {
            WorkspaceMemberEntity member = workspaceMemberMapper.selectOne(
                    new LambdaQueryWrapper<WorkspaceMemberEntity>()
                            .eq(WorkspaceMemberEntity::getWorkspaceId, workspaceId)
                            .eq(WorkspaceMemberEntity::getUserId, user.getUserId())
                            .last("LIMIT 1"));
            if (member != null && (ROLE_OWNER.equalsIgnoreCase(member.getRoleCode())
                    || ROLE_ADMIN.equalsIgnoreCase(member.getRoleCode()))) {
                return;
            }
            throw BizException.forbidden("无权维护该个人空间");
        }
        if (hasOperatePermission() || hasPlatformAdminRole(user)) {
            return;
        }
        WorkspaceMemberEntity member = workspaceMemberMapper.selectOne(
                new LambdaQueryWrapper<WorkspaceMemberEntity>()
                        .eq(WorkspaceMemberEntity::getWorkspaceId, workspaceId)
                        .eq(WorkspaceMemberEntity::getUserId, user.getUserId())
                        .last("LIMIT 1"));
        if (member != null && (ROLE_OWNER.equalsIgnoreCase(member.getRoleCode())
                || ROLE_ADMIN.equalsIgnoreCase(member.getRoleCode()))) {
            return;
        }
        throw BizException.forbidden("无权维护该工作空间");
    }

    private static boolean hasViewPermission() {
        Set<String> owned = UserContextHolder.permissionCodes();
        return PermissionCodes.implies(owned, "auth.workspace.view");
    }

    private static boolean hasOperatePermission() {
        Set<String> owned = UserContextHolder.permissionCodes();
        return PermissionCodes.implies(owned, "auth.workspace.operate");
    }

    private static boolean hasPlatformAdminRole(LoginUser user) {
        if (user.getRoleCodes() == null) {
            return false;
        }
        return user.hasSuperAdmin()
                || user.getRoleCodes().contains("DB_ADMIN")
                || user.getRoleCodes().contains("SYS_ADMIN")
                || user.getRoleCodes().contains("ADMIN");
    }

    private List<String> normalizeOps(List<String> ops) {
        if (ops == null || ops.isEmpty()) {
            throw BizException.badRequest("ops 不能为空");
        }
        return ops.stream()
                .filter(StringUtils::hasText)
                .map(s -> s.trim().toUpperCase(Locale.ROOT))
                .distinct()
                .toList();
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? List.of() : value);
        } catch (JsonProcessingException e) {
            log.warn("工作空间授权 JSON 序列化失败", e);
            throw BizException.badRequest("JSON 序列化失败");
        }
    }
}
