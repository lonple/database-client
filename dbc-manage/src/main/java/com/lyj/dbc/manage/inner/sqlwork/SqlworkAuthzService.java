package com.lyj.dbc.manage.inner.sqlwork;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.manage.authz.cache.AuthzCacheModels;
import com.lyj.dbc.manage.authz.cache.WorkspaceAuthzCacheService;
import com.lyj.dbc.manage.authz.policy.GlobalPolicyService;
import com.lyj.dbc.manage.authz.policy.ReauthTicketService;
import com.lyj.dbc.manage.authz.entity.WorkspaceAssetEntity;
import com.lyj.dbc.manage.authz.entity.WorkspaceEntity;
import com.lyj.dbc.manage.authz.entity.WorkspaceMemberEntity;
import com.lyj.dbc.manage.authz.entity.WorkspaceMemberGrantEntity;
import com.lyj.dbc.manage.authz.mapper.WorkspaceAssetMapper;
import com.lyj.dbc.manage.authz.mapper.WorkspaceMapper;
import com.lyj.dbc.manage.authz.mapper.WorkspaceMemberGrantMapper;
import com.lyj.dbc.manage.authz.mapper.WorkspaceMemberMapper;
import com.lyj.dbc.manage.inner.sqlwork.dto.AuthzEvaluateRequest;
import com.lyj.dbc.manage.inner.sqlwork.vo.AuthzEvaluateResult;
import com.lyj.dbc.manage.inner.sqlwork.vo.ObjectFilter;
import com.lyj.dbc.manage.security.LoginUser;
import com.lyj.dbc.manage.security.SecurityUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/**
 * sqlwork 数据权限裁决。
 */
@Service
public class SqlworkAuthzService {

    private static final Logger log = LoggerFactory.getLogger(SqlworkAuthzService.class);

    private static final String PURPOSE_WORKBENCH = "WORKBENCH";
    private static final String PURPOSE_EXECUTE = "EXECUTE";
    private static final String GRANT_ALL = "ALL";
    private static final String GRANT_SPECIFIC = "SPECIFIC";
    private static final String SCOPE_ALL_TABLES = "ALL_TABLES";
    private static final String SCOPE_CONNECTION = "CONNECTION";
    private static final String SCOPE_DATABASE = "DATABASE";
    private static final String SCOPE_SCHEMA = "SCHEMA";
    private static final String SCOPE_TABLE = "TABLE";
    private static final String SCOPE_SPECIFIC_TABLES = "SPECIFIC_TABLES";

    private final WorkspaceMapper workspaceMapper;
    private final WorkspaceMemberMapper workspaceMemberMapper;
    private final WorkspaceAssetMapper workspaceAssetMapper;
    private final WorkspaceMemberGrantMapper workspaceMemberGrantMapper;
    private final GlobalPolicyService globalPolicyService;
    private final ReauthTicketService reauthTicketService;
    private final WorkspaceAuthzCacheService authzCache;
    private final ObjectMapper objectMapper;

    public SqlworkAuthzService(WorkspaceMapper workspaceMapper,
                               WorkspaceMemberMapper workspaceMemberMapper,
                               WorkspaceAssetMapper workspaceAssetMapper,
                               WorkspaceMemberGrantMapper workspaceMemberGrantMapper,
                               GlobalPolicyService globalPolicyService,
                               ReauthTicketService reauthTicketService,
                               WorkspaceAuthzCacheService authzCache,
                               ObjectMapper objectMapper) {
        this.workspaceMapper = workspaceMapper;
        this.workspaceMemberMapper = workspaceMemberMapper;
        this.workspaceAssetMapper = workspaceAssetMapper;
        this.workspaceMemberGrantMapper = workspaceMemberGrantMapper;
        this.globalPolicyService = globalPolicyService;
        this.reauthTicketService = reauthTicketService;
        this.authzCache = authzCache;
        this.objectMapper = objectMapper;
    }

    public AuthzEvaluateResult evaluate(AuthzEvaluateRequest request) {
        if (request == null || request.getWorkspaceId() == null || request.getConnectionId() == null) {
            return deny("缺少 workspaceId 或 connectionId", "OTHER", false, List.of(), null, null, null);
        }

        LoginUser current = SecurityUtils.requireUser();
        Long userId = request.getUserId() != null ? request.getUserId() : current.getUserId();
        if (!Objects.equals(userId, current.getUserId())) {
            return deny("userId 与当前登录用户不一致", "OTHER", false, List.of(), null, null, null);
        }

        WorkspaceEntity workspace = workspaceMapper.selectById(request.getWorkspaceId());
        if (workspace == null || workspace.getStatus() == null || workspace.getStatus() != 1) {
            return deny("工作空间不存在或未启用", "OTHER", false, List.of(), null, null, null);
        }

        WorkspaceMemberEntity member = workspaceMemberMapper.selectOne(new LambdaQueryWrapper<WorkspaceMemberEntity>()
                .eq(WorkspaceMemberEntity::getWorkspaceId, request.getWorkspaceId())
                .eq(WorkspaceMemberEntity::getUserId, userId)
                .last("LIMIT 1"));
        if (member == null) {
            return deny("无权限：非工作空间成员", "MEMBER", false, List.of(), null, null, null);
        }

        List<EffectiveAsset> matching = resolveMatchingAssets(
                request.getWorkspaceId(), userId, request.getConnectionId());
        if (matching.isEmpty()) {
            return deny("无权限：无权使用该连接（连接未挂载到本空间或未对你授权）",
                    "CONNECTION", false, List.of(), null, null, null);
        }

        Set<String> grantedOps = new LinkedHashSet<>();
        for (EffectiveAsset asset : matching) {
            grantedOps.addAll(asset.ops);
        }
        List<String> opsList = List.copyOf(grantedOps);
        if (opsList.isEmpty()) {
            return deny("无权限：连接未授予任何操作", "OP", false, opsList, null, List.of(), null);
        }

        List<AuthzEvaluateRequest.TableRef> filterTables = buildFilterTables(matching);
        ObjectFilter objectFilter = buildObjectFilter(matching);
        String purpose = request.getPurpose() == null ? "" : request.getPurpose().trim().toUpperCase(Locale.ROOT);

        if (PURPOSE_WORKBENCH.equals(purpose)) {
            // 具备任意 SQL 操作权限即可浏览对象树；可见对象由 objectFilter 裁剪
            return AuthzEvaluateResult.builder()
                    .allowed(true)
                    .message("ok")
                    .connectionAllowed(true)
                    .grantedOps(opsList)
                    .filterTables(filterTables)
                    .objectFilter(objectFilter)
                    .globalPolicyAction(GlobalPolicyService.ACTION_NONE)
                    .build();
        }

        if (PURPOSE_EXECUTE.equals(purpose)) {
            String sqlOp = normalizeOp(request.getSqlOp());
            if (!StringUtils.hasText(sqlOp)) {
                return AuthzEvaluateResult.builder()
                        .allowed(false)
                        .message("缺少 sqlOp")
                        .connectionAllowed(true)
                        .grantedOps(opsList)
                        .filterTables(filterTables)
                        .objectFilter(objectFilter)
                        .denyType("OTHER")
                        .globalPolicyAction(GlobalPolicyService.ACTION_NONE)
                        .build();
            }
            List<AuthzEvaluateRequest.TableRef> tables =
                    request.getTables() == null ? List.of() : request.getTables();
            if (tables.isEmpty()) {
                // 无对象引用（如 SELECT 1）：按连接级操作并集校验
                if (!containsOp(grantedOps, sqlOp)) {
                    return denyPermission(
                            "无权限：缺少操作「" + sqlOp + "」；当前已授权操作：" + formatOps(opsList),
                            "OP",
                            List.of(),
                            List.of(sqlOp),
                            opsList,
                            filterTables,
                            objectFilter);
                }
            } else {
                List<ObjectDeny> denies = new ArrayList<>();
                for (AuthzEvaluateRequest.TableRef table : tables) {
                    ObjectDeny d = explainObjectDeny(matching, table, sqlOp);
                    if (d != null) {
                        denies.add(d);
                    }
                }
                if (!denies.isEmpty()) {
                    List<String> denyObjects = denies.stream().map(ObjectDeny::objectLabel).distinct().toList();
                    List<String> missingOps = denies.stream()
                            .map(ObjectDeny::missingOp)
                            .filter(StringUtils::hasText)
                            .distinct()
                            .toList();
                    boolean anyObjectMissing = denies.stream().anyMatch(d -> "OBJECT".equals(d.denyType()));
                    String denyType = anyObjectMissing ? "OBJECT" : "OP";
                    return denyPermission(buildObjectDenyMessage(denies, sqlOp, opsList),
                            denyType, denyObjects, missingOps.isEmpty() ? List.of(sqlOp) : missingOps,
                            opsList, filterTables, objectFilter);
                }
            }
            return applyGlobalPolicy(workspace, sqlOp, request.getReauthTicket(), request.getSessionId(),
                    opsList, filterTables, objectFilter, tables);
        }

        return AuthzEvaluateResult.builder()
                .allowed(false)
                .message("不支持的 purpose: " + request.getPurpose())
                .connectionAllowed(true)
                .grantedOps(opsList)
                .filterTables(filterTables)
                .objectFilter(objectFilter)
                .denyType("OTHER")
                .build();
    }

    /**
     * 解释对象级拒绝：对象未挂载，或对象上缺少指定操作。
     *
     * @return null 表示允许
     */
    private ObjectDeny explainObjectDeny(List<EffectiveAsset> matching,
                                         AuthzEvaluateRequest.TableRef table,
                                         String sqlOp) {
        boolean covered = false;
        Set<String> opsOnObject = new LinkedHashSet<>();
        for (EffectiveAsset asset : matching) {
            if (!assetCoversTable(asset, table)) {
                continue;
            }
            covered = true;
            opsOnObject.addAll(asset.ops);
            if (containsOp(asset.ops, sqlOp)) {
                return null;
            }
        }
        String label = formatTable(table);
        if (!covered) {
            return new ObjectDeny("OBJECT", label, sqlOp, List.of());
        }
        return new ObjectDeny("OP", label, sqlOp, List.copyOf(opsOnObject));
    }

    private boolean assetCoversTable(EffectiveAsset asset, AuthzEvaluateRequest.TableRef table) {
        if (isWholeConnection(asset.objectScope)) {
            return true;
        }
        if (SCOPE_DATABASE.equals(normalizeScope(asset.objectScope))) {
            for (AuthzEvaluateRequest.TableRef allowed : asset.tables) {
                if (eqIgnore(allowed.getDatabase(), table.getDatabase())) {
                    return true;
                }
            }
            return false;
        }
        if (SCOPE_SCHEMA.equals(normalizeScope(asset.objectScope))) {
            for (AuthzEvaluateRequest.TableRef allowed : asset.tables) {
                if (eqIgnore(allowed.getDatabase(), table.getDatabase())
                        && schemaMatches(allowed.getSchema(), table.getSchema())) {
                    return true;
                }
            }
            return false;
        }
        for (AuthzEvaluateRequest.TableRef allowed : asset.tables) {
            if (tableMatches(allowed, table)) {
                return true;
            }
        }
        return false;
    }

    private static String buildObjectDenyMessage(List<ObjectDeny> denies, String sqlOp, List<String> opsList) {
        StringBuilder sb = new StringBuilder("无权限：");
        List<ObjectDeny> objectMissing = denies.stream().filter(d -> "OBJECT".equals(d.denyType())).toList();
        List<ObjectDeny> opMissing = denies.stream().filter(d -> "OP".equals(d.denyType())).toList();
        if (!objectMissing.isEmpty()) {
            sb.append("资产对象未授权 [")
                    .append(objectMissing.stream().map(ObjectDeny::objectLabel).distinct().collect(java.util.stream.Collectors.joining(", ")))
                    .append("]");
        }
        if (!opMissing.isEmpty()) {
            if (!objectMissing.isEmpty()) {
                sb.append("；");
            }
            sb.append("资产对象缺少操作「").append(sqlOp).append("」[");
            sb.append(opMissing.stream().map(d -> {
                String granted = d.opsOnObject().isEmpty() ? "无" : String.join("/", d.opsOnObject());
                return d.objectLabel() + "（已有:" + granted + "）";
            }).collect(java.util.stream.Collectors.joining(", ")));
            sb.append("]");
        }
        sb.append("；当前连接已授权操作：").append(formatOps(opsList));
        return sb.toString();
    }

    private static String formatTable(AuthzEvaluateRequest.TableRef t) {
        if (t == null) {
            return "?";
        }
        StringBuilder sb = new StringBuilder();
        if (StringUtils.hasText(t.getDatabase())) {
            sb.append(t.getDatabase()).append('.');
        }
        if (StringUtils.hasText(t.getSchema())) {
            sb.append(t.getSchema()).append('.');
        }
        sb.append(StringUtils.hasText(t.getName()) ? t.getName() : "?");
        return sb.toString();
    }

    private static String formatOps(List<String> ops) {
        if (ops == null || ops.isEmpty()) {
            return "无";
        }
        return String.join(", ", ops);
    }

    private record ObjectDeny(String denyType, String objectLabel, String missingOp, List<String> opsOnObject) {
    }

    /**
     * 解析对指定连接生效的授权条目（已展开 ALL 模式）。
     * <p>
     * 空间所有者 / 空间管理员：隐式拥有空间全部资产授权（无需成员授权行）。
     * 数据操作人员：仅看成员授权。
     */
    List<EffectiveAsset> resolveMatchingAssets(Long workspaceId, Long userId, Long connectionId) {
        AuthzCacheModels.UserAuthzSnapshot userSnap = loadUserAuthz(workspaceId, userId);
        if (userSnap == null || !StringUtils.hasText(userSnap.getRole())) {
            return List.of();
        }
        if (isSpaceManager(userSnap.getRole())) {
            return loadWorkspaceAssetsForConnection(workspaceId, connectionId);
        }

        List<AuthzCacheModels.GrantEntry> grants = userSnap.getGrants() == null
                ? List.of() : userSnap.getGrants();
        if (grants.isEmpty()) {
            return List.of();
        }

        boolean hasAll = grants.stream().anyMatch(g -> GRANT_ALL.equalsIgnoreCase(g.getMode()));
        if (hasAll) {
            return loadWorkspaceAssetsForConnection(workspaceId, connectionId);
        }

        List<EffectiveAsset> matching = new ArrayList<>();
        for (AuthzCacheModels.GrantEntry grant : grants) {
            if (!GRANT_SPECIFIC.equalsIgnoreCase(grant.getMode())) {
                continue;
            }
            if (grant.getConnectionId() != null && !grant.getConnectionId().equals(connectionId)) {
                continue;
            }
            matching.add(toEffectiveFromCache(connectionId, grant));
        }
        return matching;
    }

    private AuthzCacheModels.UserAuthzSnapshot loadUserAuthz(Long workspaceId, Long userId) {
        Optional<AuthzCacheModels.UserAuthzSnapshot> cached = authzCache.getUser(workspaceId, userId);
        if (cached.isPresent()) {
            return cached.get();
        }
        WorkspaceMemberEntity member = workspaceMemberMapper.selectOne(new LambdaQueryWrapper<WorkspaceMemberEntity>()
                .eq(WorkspaceMemberEntity::getWorkspaceId, workspaceId)
                .eq(WorkspaceMemberEntity::getUserId, userId)
                .last("LIMIT 1"));
        if (member == null) {
            return null;
        }
        List<WorkspaceMemberGrantEntity> grantRows = workspaceMemberGrantMapper.selectList(
                new LambdaQueryWrapper<WorkspaceMemberGrantEntity>()
                        .eq(WorkspaceMemberGrantEntity::getWorkspaceId, workspaceId)
                        .eq(WorkspaceMemberGrantEntity::getUserId, userId));
        List<AuthzCacheModels.GrantEntry> grants = new ArrayList<>();
        for (WorkspaceMemberGrantEntity g : grantRows) {
            if (GRANT_ALL.equalsIgnoreCase(g.getGrantMode())) {
                grants.add(AuthzCacheModels.GrantEntry.builder().mode(GRANT_ALL).build());
                continue;
            }
            if (!GRANT_SPECIFIC.equalsIgnoreCase(g.getGrantMode())) {
                continue;
            }
            grants.add(AuthzCacheModels.GrantEntry.builder()
                    .mode(GRANT_SPECIFIC)
                    .connectionId(g.getConnectionId())
                    .scope(g.getObjectScope())
                    .tables(toCacheTables(parseTables(g.getTablesJson())))
                    .ops(parseOps(g.getOpsJson()))
                    .build());
        }
        AuthzCacheModels.UserAuthzSnapshot snap = AuthzCacheModels.UserAuthzSnapshot.builder()
                .role(member.getRoleCode())
                .grants(grants)
                .build();
        authzCache.putUser(workspaceId, userId, snap);
        return snap;
    }

    private List<EffectiveAsset> loadWorkspaceAssetsForConnection(Long workspaceId, Long connectionId) {
        Optional<List<AuthzCacheModels.AssetEntry>> cached =
                authzCache.getAssetsForConnection(workspaceId, connectionId);
        if (cached.isPresent()) {
            return toEffectiveList(cached.get());
        }
        warmAssetsCache(workspaceId);
        cached = authzCache.getAssetsForConnection(workspaceId, connectionId);
        if (cached.isPresent()) {
            return toEffectiveList(cached.get());
        }
        // 缓存不可用时直接读库
        List<WorkspaceAssetEntity> assets = workspaceAssetMapper.selectList(
                new LambdaQueryWrapper<WorkspaceAssetEntity>()
                        .eq(WorkspaceAssetEntity::getWorkspaceId, workspaceId)
                        .eq(WorkspaceAssetEntity::getConnectionId, connectionId));
        List<EffectiveAsset> matching = new ArrayList<>();
        for (WorkspaceAssetEntity asset : assets) {
            matching.add(toEffective(asset.getConnectionId(), asset.getObjectScope(),
                    asset.getTablesJson(), asset.getOpsJson()));
        }
        return matching;
    }

    private void warmAssetsCache(Long workspaceId) {
        if (authzCache.hasAssetsSnapshot(workspaceId)) {
            return;
        }
        List<WorkspaceAssetEntity> assets = workspaceAssetMapper.selectList(
                new LambdaQueryWrapper<WorkspaceAssetEntity>()
                        .eq(WorkspaceAssetEntity::getWorkspaceId, workspaceId));
        Map<Long, List<AuthzCacheModels.AssetEntry>> byConn = new java.util.LinkedHashMap<>();
        for (WorkspaceAssetEntity asset : assets) {
            byConn.computeIfAbsent(asset.getConnectionId(), k -> new ArrayList<>())
                    .add(AuthzCacheModels.AssetEntry.builder()
                            .connectionId(asset.getConnectionId())
                            .scope(asset.getObjectScope())
                            .tables(toCacheTables(parseTables(asset.getTablesJson())))
                            .ops(parseOps(asset.getOpsJson()))
                            .build());
        }
        authzCache.putAssetsSnapshot(workspaceId, byConn);
    }

    private List<EffectiveAsset> toEffectiveList(List<AuthzCacheModels.AssetEntry> entries) {
        if (entries == null || entries.isEmpty()) {
            return List.of();
        }
        List<EffectiveAsset> list = new ArrayList<>(entries.size());
        for (AuthzCacheModels.AssetEntry e : entries) {
            list.add(toEffectiveFromAsset(e));
        }
        return list;
    }

    private EffectiveAsset toEffectiveFromCache(Long connectionId, AuthzCacheModels.GrantEntry grant) {
        String scope = StringUtils.hasText(grant.getScope()) ? grant.getScope().trim().toUpperCase(Locale.ROOT)
                : SCOPE_ALL_TABLES;
        return new EffectiveAsset(connectionId, scope,
                toRequestTables(grant.getTables()),
                grant.getOps() == null ? List.of() : List.copyOf(grant.getOps()));
    }

    private EffectiveAsset toEffectiveFromAsset(AuthzCacheModels.AssetEntry asset) {
        Long connId = asset.getConnectionId();
        String scope = StringUtils.hasText(asset.getScope()) ? asset.getScope().trim().toUpperCase(Locale.ROOT)
                : SCOPE_ALL_TABLES;
        return new EffectiveAsset(connId, scope,
                toRequestTables(asset.getTables()),
                asset.getOps() == null ? List.of() : List.copyOf(asset.getOps()));
    }

    private static List<AuthzCacheModels.TableRef> toCacheTables(List<AuthzEvaluateRequest.TableRef> tables) {
        if (tables == null || tables.isEmpty()) {
            return List.of();
        }
        List<AuthzCacheModels.TableRef> out = new ArrayList<>(tables.size());
        for (AuthzEvaluateRequest.TableRef t : tables) {
            out.add(AuthzCacheModels.TableRef.builder()
                    .database(t.getDatabase())
                    .schema(t.getSchema())
                    .name(t.getName())
                    .build());
        }
        return out;
    }

    private static List<AuthzEvaluateRequest.TableRef> toRequestTables(List<AuthzCacheModels.TableRef> tables) {
        if (tables == null || tables.isEmpty()) {
            return List.of();
        }
        List<AuthzEvaluateRequest.TableRef> out = new ArrayList<>(tables.size());
        for (AuthzCacheModels.TableRef t : tables) {
            AuthzEvaluateRequest.TableRef r = new AuthzEvaluateRequest.TableRef();
            r.setDatabase(t.getDatabase());
            r.setSchema(t.getSchema());
            r.setName(t.getName());
            out.add(r);
        }
        return out;
    }

    /**
     * 用户是否在任一空间拥有覆盖该连接的成员授权（或空间管理员身份）。
     */
    public boolean hasAnyGrantCoveringConnection(Long userId, Long connectionId) {
        List<WorkspaceMemberEntity> memberships = workspaceMemberMapper.selectList(
                new LambdaQueryWrapper<WorkspaceMemberEntity>()
                        .eq(WorkspaceMemberEntity::getUserId, userId));
        for (WorkspaceMemberEntity membership : memberships) {
            if (isSpaceManager(membership.getRoleCode())) {
                List<EffectiveAsset> assets = loadWorkspaceAssetsForConnection(
                        membership.getWorkspaceId(), connectionId);
                if (!assets.isEmpty()) {
                    return true;
                }
            }
        }

        for (WorkspaceMemberEntity membership : memberships) {
            AuthzCacheModels.UserAuthzSnapshot snap =
                    loadUserAuthz(membership.getWorkspaceId(), userId);
            if (snap == null || snap.getGrants() == null) {
                continue;
            }
            for (AuthzCacheModels.GrantEntry grant : snap.getGrants()) {
                if (GRANT_ALL.equalsIgnoreCase(grant.getMode())) {
                    List<EffectiveAsset> assets = loadWorkspaceAssetsForConnection(
                            membership.getWorkspaceId(), connectionId);
                    if (!assets.isEmpty()) {
                        return true;
                    }
                } else if (GRANT_SPECIFIC.equalsIgnoreCase(grant.getMode())) {
                    if (grant.getConnectionId() == null || grant.getConnectionId().equals(connectionId)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    /**
     * 读取用户授权快照（走缓存）。
     */
    public AuthzCacheModels.UserAuthzSnapshot peekUserAuthz(Long workspaceId, Long userId) {
        return loadUserAuthz(workspaceId, userId);
    }

    /**
     * 整空间资产（按连接分组，走缓存）。
     */
    public Map<Long, List<AuthzCacheModels.AssetEntry>> peekWorkspaceAssets(Long workspaceId) {
        warmAssetsCache(workspaceId);
        Map<Long, List<AuthzCacheModels.AssetEntry>> byConn = new java.util.LinkedHashMap<>();
        for (Long connId : authzCache.listCachedAssetConnectionIds(workspaceId)) {
            Optional<List<AuthzCacheModels.AssetEntry>> entries =
                    authzCache.getAssetsForConnection(workspaceId, connId);
            byConn.put(connId, entries.orElse(List.of()));
        }
        if (!byConn.isEmpty() || authzCache.hasAssetsSnapshot(workspaceId)) {
            return byConn;
        }
        List<WorkspaceAssetEntity> assets = workspaceAssetMapper.selectList(
                new LambdaQueryWrapper<WorkspaceAssetEntity>()
                        .eq(WorkspaceAssetEntity::getWorkspaceId, workspaceId));
        for (WorkspaceAssetEntity asset : assets) {
            byConn.computeIfAbsent(asset.getConnectionId(), k -> new ArrayList<>())
                    .add(AuthzCacheModels.AssetEntry.builder()
                            .connectionId(asset.getConnectionId())
                            .scope(asset.getObjectScope())
                            .tables(toCacheTables(parseTables(asset.getTablesJson())))
                            .ops(parseOps(asset.getOpsJson()))
                            .build());
        }
        return byConn;
    }

    private static boolean isSpaceManager(String roleCode) {
        return "OWNER".equalsIgnoreCase(roleCode) || "ADMIN".equalsIgnoreCase(roleCode);
    }

    /**
     * 用户在空间内可使用的连接 ID（供连接列表）。走同一套授权缓存。
     */
    public Set<Long> resolveGrantedConnectionIds(Long workspaceId, Long userId) {
        AuthzCacheModels.UserAuthzSnapshot snap = loadUserAuthz(workspaceId, userId);
        if (snap == null || !StringUtils.hasText(snap.getRole())) {
            return Set.of();
        }
        if (isSpaceManager(snap.getRole())) {
            return listAssetConnectionIds(workspaceId);
        }
        List<AuthzCacheModels.GrantEntry> grants = snap.getGrants() == null ? List.of() : snap.getGrants();
        boolean hasAll = grants.stream().anyMatch(g -> GRANT_ALL.equalsIgnoreCase(g.getMode()));
        if (hasAll) {
            return listAssetConnectionIds(workspaceId);
        }
        Set<Long> ids = new LinkedHashSet<>();
        for (AuthzCacheModels.GrantEntry grant : grants) {
            if (!GRANT_SPECIFIC.equalsIgnoreCase(grant.getMode())) {
                continue;
            }
            if (grant.getConnectionId() != null) {
                ids.add(grant.getConnectionId());
            } else {
                ids.addAll(listAssetConnectionIds(workspaceId));
            }
        }
        return ids;
    }

    private Set<Long> listAssetConnectionIds(Long workspaceId) {
        warmAssetsCache(workspaceId);
        Set<Long> cached = authzCache.listCachedAssetConnectionIds(workspaceId);
        if (authzCache.hasAssetsSnapshot(workspaceId)) {
            return cached;
        }
        List<WorkspaceAssetEntity> assets = workspaceAssetMapper.selectList(
                new LambdaQueryWrapper<WorkspaceAssetEntity>()
                        .eq(WorkspaceAssetEntity::getWorkspaceId, workspaceId));
        Set<Long> ids = new LinkedHashSet<>();
        for (WorkspaceAssetEntity asset : assets) {
            ids.add(asset.getConnectionId());
        }
        return ids;
    }

    private EffectiveAsset toEffective(Long connectionId, String objectScope,
                                       String tablesJson, String opsJson) {
        String scope = StringUtils.hasText(objectScope) ? objectScope.trim().toUpperCase(Locale.ROOT)
                : SCOPE_ALL_TABLES;
        return new EffectiveAsset(connectionId, scope, parseTables(tablesJson), parseOps(opsJson));
    }

    private List<AuthzEvaluateRequest.TableRef> buildFilterTables(List<EffectiveAsset> matching) {
        boolean allTables = matching.stream().anyMatch(a -> isWholeConnection(a.objectScope));
        if (allTables) {
            return null;
        }
        // DATABASE / SCHEMA 级授权：不返回表清单（由 objectFilter / 执行侧按范围匹配）；TABLE 级返回表列表
        boolean onlyTableLevel = matching.stream().allMatch(a -> isTableLevel(a.objectScope));
        if (!onlyTableLevel) {
            return null;
        }
        LinkedHashSet<String> keys = new LinkedHashSet<>();
        List<AuthzEvaluateRequest.TableRef> result = new ArrayList<>();
        for (EffectiveAsset asset : matching) {
            for (AuthzEvaluateRequest.TableRef t : asset.tables) {
                String key = tableKey(t.getDatabase(), t.getSchema(), t.getName());
                if (keys.add(key)) {
                    result.add(t);
                }
            }
        }
        return result;
    }

    /**
     * 构建工作台元数据可见性：连接级全量，或 DATABASE/SCHEMA/TABLE 范围并集。
     */
    private ObjectFilter buildObjectFilter(List<EffectiveAsset> matching) {
        if (matching == null || matching.isEmpty()) {
            return ObjectFilter.builder().unrestricted(false).scopes(List.of()).build();
        }
        if (matching.stream().anyMatch(a -> isWholeConnection(a.objectScope))) {
            return ObjectFilter.builder().unrestricted(true).scopes(List.of()).build();
        }
        LinkedHashSet<String> keys = new LinkedHashSet<>();
        List<ObjectFilter.Scope> scopes = new ArrayList<>();
        for (EffectiveAsset asset : matching) {
            String level = normalizeScope(asset.objectScope);
            if (SCOPE_DATABASE.equals(level)) {
                for (AuthzEvaluateRequest.TableRef t : asset.tables) {
                    String db = t.getDatabase();
                    String key = "DB|" + norm(db);
                    if (keys.add(key)) {
                        scopes.add(ObjectFilter.Scope.builder()
                                .level(SCOPE_DATABASE)
                                .database(db)
                                .build());
                    }
                }
            } else if (SCOPE_SCHEMA.equals(level)) {
                for (AuthzEvaluateRequest.TableRef t : asset.tables) {
                    String key = "SC|" + norm(t.getDatabase()) + "|" + norm(t.getSchema());
                    if (keys.add(key)) {
                        scopes.add(ObjectFilter.Scope.builder()
                                .level(SCOPE_SCHEMA)
                                .database(t.getDatabase())
                                .schema(t.getSchema())
                                .build());
                    }
                }
            } else if (isTableLevel(level)) {
                for (AuthzEvaluateRequest.TableRef t : asset.tables) {
                    String key = "TB|" + tableKey(t.getDatabase(), t.getSchema(), t.getName());
                    if (keys.add(key)) {
                        scopes.add(ObjectFilter.Scope.builder()
                                .level(SCOPE_TABLE)
                                .database(t.getDatabase())
                                .schema(t.getSchema())
                                .name(t.getName())
                                .build());
                    }
                }
            }
        }
        return ObjectFilter.builder().unrestricted(false).scopes(scopes).build();
    }

    private static String norm(String s) {
        return s == null ? "" : s.trim().toLowerCase(Locale.ROOT);
    }

    private boolean allTablesAllowed(List<EffectiveAsset> matching, List<AuthzEvaluateRequest.TableRef> tables) {
        for (AuthzEvaluateRequest.TableRef table : tables) {
            if (!isTableAllowed(matching, table)) {
                return false;
            }
        }
        return true;
    }

    private boolean isTableAllowed(List<EffectiveAsset> matching, AuthzEvaluateRequest.TableRef table) {
        for (EffectiveAsset asset : matching) {
            if (isWholeConnection(asset.objectScope)) {
                return true;
            }
            if (SCOPE_DATABASE.equals(normalizeScope(asset.objectScope))) {
                for (AuthzEvaluateRequest.TableRef allowed : asset.tables) {
                    if (eqIgnore(allowed.getDatabase(), table.getDatabase())) {
                        return true;
                    }
                }
                continue;
            }
            if (SCOPE_SCHEMA.equals(normalizeScope(asset.objectScope))) {
                for (AuthzEvaluateRequest.TableRef allowed : asset.tables) {
                    if (eqIgnore(allowed.getDatabase(), table.getDatabase())
                            && schemaMatches(allowed.getSchema(), table.getSchema())) {
                        return true;
                    }
                }
                continue;
            }
            for (AuthzEvaluateRequest.TableRef allowed : asset.tables) {
                if (tableMatches(allowed, table)) {
                    return true;
                }
            }
        }
        return false;
    }

    private static boolean isWholeConnection(String scope) {
        String n = normalizeScope(scope);
        return SCOPE_ALL_TABLES.equals(n) || SCOPE_CONNECTION.equals(n);
    }

    private static boolean isTableLevel(String scope) {
        String n = normalizeScope(scope);
        return SCOPE_TABLE.equals(n) || SCOPE_SPECIFIC_TABLES.equals(n);
    }

    private static String normalizeScope(String scope) {
        if (scope == null || scope.isBlank()) {
            return SCOPE_CONNECTION;
        }
        return scope.trim().toUpperCase(Locale.ROOT);
    }

    /**
     * 表级匹配：database/schema 可空则放宽；name 必须相等。
     */
    private static boolean tableMatches(AuthzEvaluateRequest.TableRef allowed,
                                        AuthzEvaluateRequest.TableRef request) {
        if (allowed.getName() == null || request.getName() == null) {
            return false;
        }
        if (!allowed.getName().equalsIgnoreCase(request.getName())) {
            return false;
        }
        if (StringUtils.hasText(allowed.getDatabase()) && StringUtils.hasText(request.getDatabase())
                && !allowed.getDatabase().equalsIgnoreCase(request.getDatabase())) {
            return false;
        }
        return schemaMatches(allowed.getSchema(), request.getSchema());
    }

    private static boolean schemaMatches(String allowedSchema, String requestSchema) {
        String as = normalizeSchema(allowedSchema);
        String rs = normalizeSchema(requestSchema);
        if (as == null || rs == null) {
            return true;
        }
        return as.equalsIgnoreCase(rs);
    }

    private static boolean eqIgnore(String a, String b) {
        if (!StringUtils.hasText(a) || !StringUtils.hasText(b)) {
            return true;
        }
        return a.trim().equalsIgnoreCase(b.trim());
    }

    private static String normalizeSchema(String schema) {
        if (!StringUtils.hasText(schema)) {
            return null;
        }
        return schema.trim();
    }

    private static String tableKey(String database, String schema, String name) {
        String d = database == null ? "" : database.toLowerCase(Locale.ROOT);
        String s = schema == null ? "" : schema.toLowerCase(Locale.ROOT);
        String n = name == null ? "" : name.toLowerCase(Locale.ROOT);
        return d + "." + s + "." + n;
    }

    private List<String> parseOps(String opsJson) {
        if (!StringUtils.hasText(opsJson)) {
            return List.of();
        }
        try {
            List<String> raw = objectMapper.readValue(opsJson, new TypeReference<List<String>>() {});
            LinkedHashSet<String> set = new LinkedHashSet<>();
            for (String op : raw) {
                String n = normalizeOp(op);
                if (StringUtils.hasText(n)) {
                    set.add(n);
                }
            }
            return List.copyOf(set);
        } catch (Exception e) {
            log.warn("解析 ops_json 失败: {}", opsJson, e);
            return List.of();
        }
    }

    private List<AuthzEvaluateRequest.TableRef> parseTables(String tablesJson) {
        if (!StringUtils.hasText(tablesJson)) {
            return List.of();
        }
        try {
            List<AuthzEvaluateRequest.TableRef> list = objectMapper.readValue(
                    tablesJson, new TypeReference<List<AuthzEvaluateRequest.TableRef>>() {});
            return list == null ? List.of() : list;
        } catch (Exception e) {
            log.warn("解析 tables_json 失败: {}", tablesJson, e);
            return List.of();
        }
    }

    private static String normalizeOp(String op) {
        return op == null ? "" : op.trim().toUpperCase(Locale.ROOT);
    }

    private static boolean containsOp(java.util.Collection<String> ops, String op) {
        return ops.stream().anyMatch(o -> o.equalsIgnoreCase(op));
    }

    private AuthzEvaluateResult applyGlobalPolicy(WorkspaceEntity workspace, String sqlOp,
                                                  String reauthTicket, String sessionId,
                                                  List<String> opsList,
                                                  List<AuthzEvaluateRequest.TableRef> filterTables,
                                                  ObjectFilter objectFilter,
                                                  List<AuthzEvaluateRequest.TableRef> requestTables) {
        List<String> objectLabels = requestTables == null ? List.of()
                : requestTables.stream().map(SqlworkAuthzService::formatTable).distinct().toList();
        // 全局管控仅作用于公司空间
        if (workspace != null && "PERSONAL".equalsIgnoreCase(workspace.getSpaceType())) {
            return AuthzEvaluateResult.builder()
                    .allowed(true)
                    .message("ok")
                    .connectionAllowed(true)
                    .grantedOps(opsList)
                    .filterTables(filterTables)
                    .objectFilter(objectFilter)
                    .globalPolicyAction(GlobalPolicyService.ACTION_NONE)
                    .build();
        }
        Long workspaceId = workspace == null ? null : workspace.getId();
        GlobalPolicyService.Hit hit = globalPolicyService.evaluate(workspaceId, sqlOp);
        if (GlobalPolicyService.ACTION_NONE.equals(hit.action())) {
            return AuthzEvaluateResult.builder()
                    .allowed(true)
                    .message("ok")
                    .connectionAllowed(true)
                    .grantedOps(opsList)
                    .filterTables(filterTables)
                    .objectFilter(objectFilter)
                    .globalPolicyAction(GlobalPolicyService.ACTION_NONE)
                    .build();
        }
        if (GlobalPolicyService.STRATEGY_BLOCK.equals(hit.action())) {
            String msg = "全局管控阻断：策略「" + hit.policyName() + "」禁止操作「" + sqlOp + "」"
                    + (objectLabels.isEmpty() ? "" : "；涉及对象：" + String.join(", ", objectLabels));
            return AuthzEvaluateResult.builder()
                    .allowed(false)
                    .message(msg)
                    .connectionAllowed(true)
                    .grantedOps(opsList)
                    .filterTables(filterTables)
                    .objectFilter(objectFilter)
                    .globalPolicyAction(GlobalPolicyService.STRATEGY_BLOCK)
                    .globalPolicyId(hit.policyId())
                    .globalPolicyName(hit.policyName())
                    .denyType("POLICY")
                    .denyObjects(objectLabels)
                    .missingOps(List.of(sqlOp))
                    .build();
        }
        if (GlobalPolicyService.STRATEGY_REAUTH.equals(hit.action())) {
            LoginUser user = SecurityUtils.requireUser();
            boolean ok = reauthTicketService.verify(user.getUserId(), sessionId, reauthTicket);
            if (!ok) {
                String msg = "全局管控要求二次鉴权：策略「" + hit.policyName() + "」操作「" + sqlOp + "」"
                        + (objectLabels.isEmpty() ? "" : "；涉及对象：" + String.join(", ", objectLabels));
                return AuthzEvaluateResult.builder()
                        .allowed(false)
                        .message(msg)
                        .connectionAllowed(true)
                        .grantedOps(opsList)
                        .filterTables(filterTables)
                        .objectFilter(objectFilter)
                        .globalPolicyAction(GlobalPolicyService.STRATEGY_REAUTH)
                        .globalPolicyId(hit.policyId())
                        .globalPolicyName(hit.policyName())
                        .needReauth(true)
                        .denyType("POLICY")
                        .denyObjects(objectLabels)
                        .missingOps(List.of(sqlOp))
                        .build();
            }
            return AuthzEvaluateResult.builder()
                    .allowed(true)
                    .message("ok")
                    .connectionAllowed(true)
                    .grantedOps(opsList)
                    .filterTables(filterTables)
                    .objectFilter(objectFilter)
                    .globalPolicyAction(GlobalPolicyService.STRATEGY_REAUTH)
                    .globalPolicyId(hit.policyId())
                    .globalPolicyName(hit.policyName())
                    .build();
        }
        return AuthzEvaluateResult.builder()
                .allowed(true)
                .message("全局管控告警: " + hit.policyName())
                .connectionAllowed(true)
                .grantedOps(opsList)
                .filterTables(filterTables)
                .objectFilter(objectFilter)
                .globalPolicyAction(GlobalPolicyService.STRATEGY_ALERT)
                .globalPolicyId(hit.policyId())
                .globalPolicyName(hit.policyName())
                .build();
    }

    private static AuthzEvaluateResult denyPermission(String message, String denyType,
                                                      List<String> denyObjects,
                                                      List<String> missingOps,
                                                      List<String> grantedOps,
                                                      List<AuthzEvaluateRequest.TableRef> filterTables,
                                                      ObjectFilter objectFilter) {
        return AuthzEvaluateResult.builder()
                .allowed(false)
                .message(message)
                .connectionAllowed(true)
                .grantedOps(grantedOps)
                .filterTables(filterTables)
                .objectFilter(objectFilter)
                .denyType(denyType)
                .denyObjects(denyObjects)
                .missingOps(missingOps)
                .globalPolicyAction(GlobalPolicyService.ACTION_NONE)
                .build();
    }

    private static AuthzEvaluateResult deny(String message, String denyType, boolean connectionAllowed,
                                            List<String> grantedOps,
                                            List<AuthzEvaluateRequest.TableRef> filterTables,
                                            List<String> denyObjects,
                                            List<String> missingOps) {
        return AuthzEvaluateResult.builder()
                .allowed(false)
                .message(message)
                .connectionAllowed(connectionAllowed)
                .grantedOps(grantedOps)
                .filterTables(filterTables)
                .denyType(denyType)
                .denyObjects(denyObjects)
                .missingOps(missingOps)
                .globalPolicyAction(GlobalPolicyService.ACTION_NONE)
                .build();
    }

    record EffectiveAsset(Long connectionId, String objectScope,
                          List<AuthzEvaluateRequest.TableRef> tables, List<String> ops) {
    }
}
