package com.lyj.dbc.manage.inner.sqlwork;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.manage.asset.DbType;
import com.lyj.dbc.manage.asset.connection.entity.ConnectionEntity;
import com.lyj.dbc.manage.asset.connection.mapper.ConnectionMapper;
import com.lyj.dbc.manage.asset.instance.InstanceService;
import com.lyj.dbc.manage.asset.instance.entity.InstanceEntity;
import com.lyj.dbc.manage.authz.entity.WorkspaceEntity;
import com.lyj.dbc.manage.authz.entity.WorkspaceMemberEntity;
import com.lyj.dbc.manage.authz.mapper.WorkspaceMapper;
import com.lyj.dbc.manage.authz.mapper.WorkspaceMemberMapper;
import com.lyj.dbc.manage.authz.cache.AuthzCacheModels;
import com.lyj.dbc.manage.common.BizException;
import com.lyj.dbc.manage.inner.sqlwork.vo.ConnectionMaterialVO;
import com.lyj.dbc.manage.inner.sqlwork.vo.ConnectionSummaryVO;
import com.lyj.dbc.manage.inner.sqlwork.vo.MyWorkspaceAuthzVO;
import com.lyj.dbc.manage.inner.sqlwork.vo.WorkspaceSummaryVO;
import com.lyj.dbc.manage.secrets.ManageKekCryptoService;
import com.lyj.dbc.manage.security.LoginUser;
import com.lyj.dbc.manage.security.SecurityUtils;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * sqlwork inner API 业务。
 */
@Service
public class SqlworkInnerService {

    private final WorkspaceMapper workspaceMapper;
    private final WorkspaceMemberMapper workspaceMemberMapper;
    private final ConnectionMapper connectionMapper;
    private final InstanceService instanceService;
    private final ManageKekCryptoService kekCryptoService;
    private final SqlworkAuthzService sqlworkAuthzService;

    public SqlworkInnerService(WorkspaceMapper workspaceMapper,
                               WorkspaceMemberMapper workspaceMemberMapper,
                               ConnectionMapper connectionMapper,
                               InstanceService instanceService,
                               ManageKekCryptoService kekCryptoService,
                               SqlworkAuthzService sqlworkAuthzService) {
        this.workspaceMapper = workspaceMapper;
        this.workspaceMemberMapper = workspaceMemberMapper;
        this.connectionMapper = connectionMapper;
        this.instanceService = instanceService;
        this.kekCryptoService = kekCryptoService;
        this.sqlworkAuthzService = sqlworkAuthzService;
    }

    public List<WorkspaceSummaryVO> listMyWorkspaces() {
        LoginUser user = SecurityUtils.requireUser();
        List<WorkspaceMemberEntity> members = workspaceMemberMapper.selectList(
                new LambdaQueryWrapper<WorkspaceMemberEntity>()
                        .eq(WorkspaceMemberEntity::getUserId, user.getUserId()));
        if (members.isEmpty()) {
            return List.of();
        }
        List<WorkspaceSummaryVO> result = new ArrayList<>();
        for (WorkspaceMemberEntity member : members) {
            WorkspaceEntity ws = workspaceMapper.selectById(member.getWorkspaceId());
            if (ws == null || ws.getStatus() == null || ws.getStatus() != 1) {
                continue;
            }
            result.add(WorkspaceSummaryVO.builder()
                    .id(ws.getId())
                    .name(ws.getName())
                    .description(ws.getDescription())
                    .spaceType(ws.getSpaceType() == null ? "COMPANY" : ws.getSpaceType())
                    .myRole(member.getRoleCode())
                    .build());
        }
        return result;
    }

    public List<ConnectionSummaryVO> listWorkspaceConnections(Long workspaceId) {
        LoginUser user = SecurityUtils.requireUser();
        WorkspaceEntity ws = workspaceMapper.selectById(workspaceId);
        if (ws == null || ws.getStatus() == null || ws.getStatus() != 1) {
            throw BizException.notFound("工作空间不存在或未启用");
        }
        WorkspaceMemberEntity member = workspaceMemberMapper.selectOne(new LambdaQueryWrapper<WorkspaceMemberEntity>()
                .eq(WorkspaceMemberEntity::getWorkspaceId, workspaceId)
                .eq(WorkspaceMemberEntity::getUserId, user.getUserId())
                .last("LIMIT 1"));
        if (member == null) {
            throw BizException.forbidden("非工作空间成员");
        }

        Set<Long> connectionIds = sqlworkAuthzService.resolveGrantedConnectionIds(workspaceId, user.getUserId());
        if (connectionIds.isEmpty()) {
            return List.of();
        }
        List<ConnectionEntity> connections = connectionMapper.selectList(
                new LambdaQueryWrapper<ConnectionEntity>()
                        .in(ConnectionEntity::getId, connectionIds)
                        .eq(ConnectionEntity::getStatus, 1)
                        .orderByAsc(ConnectionEntity::getId));
        return connections.stream()
                .map(c -> ConnectionSummaryVO.builder()
                        .id(c.getId())
                        .name(c.getName())
                        .dbType(c.getDbType())
                        .build())
                .toList();
    }

    /**
     * 当前用户在空间内可见的资产与权限（选空间页右侧）。
     */
    public MyWorkspaceAuthzVO getMyAuthz(Long workspaceId) {
        LoginUser user = SecurityUtils.requireUser();
        WorkspaceEntity ws = workspaceMapper.selectById(workspaceId);
        if (ws == null || ws.getStatus() == null || ws.getStatus() != 1) {
            throw BizException.notFound("工作空间不存在或未启用");
        }
        WorkspaceMemberEntity member = workspaceMemberMapper.selectOne(new LambdaQueryWrapper<WorkspaceMemberEntity>()
                .eq(WorkspaceMemberEntity::getWorkspaceId, workspaceId)
                .eq(WorkspaceMemberEntity::getUserId, user.getUserId())
                .last("LIMIT 1"));
        if (member == null) {
            throw BizException.forbidden("非工作空间成员");
        }

        AuthzCacheModels.UserAuthzSnapshot snap =
                sqlworkAuthzService.peekUserAuthz(workspaceId, user.getUserId());
        String role = snap != null && snap.getRole() != null ? snap.getRole() : member.getRoleCode();
        boolean manager = "OWNER".equalsIgnoreCase(role) || "ADMIN".equalsIgnoreCase(role);

        Map<Long, ConnectionEntity> connById = loadConnections(
                sqlworkAuthzService.resolveGrantedConnectionIds(workspaceId, user.getUserId()));

        List<MyWorkspaceAuthzVO.GrantItem> grants = new ArrayList<>();
        boolean grantAll = false;
        if (manager) {
            grants.addAll(spaceAssetGrants(workspaceId, connById));
        } else if (snap != null && snap.getGrants() != null) {
            grantAll = snap.getGrants().stream()
                    .anyMatch(g -> "ALL".equalsIgnoreCase(g.getMode()));
            if (grantAll) {
                grants.addAll(spaceAssetGrants(workspaceId, connById));
            } else {
                for (AuthzCacheModels.GrantEntry g : snap.getGrants()) {
                    if (!"SPECIFIC".equalsIgnoreCase(g.getMode())) {
                        continue;
                    }
                    ConnectionEntity c = g.getConnectionId() == null ? null : connById.get(g.getConnectionId());
                    grants.add(MyWorkspaceAuthzVO.GrantItem.builder()
                            .mode("SPECIFIC")
                            .connectionId(g.getConnectionId())
                            .connectionName(c == null ? null : c.getName())
                            .dbType(c == null ? null : c.getDbType())
                            .scope(g.getScope())
                            .tables(toVoTables(g.getTables()))
                            .ops(g.getOps() == null ? List.of() : List.copyOf(g.getOps()))
                            .build());
                }
            }
        }

        return MyWorkspaceAuthzVO.builder()
                .workspaceId(ws.getId())
                .workspaceName(ws.getName())
                .description(ws.getDescription())
                .spaceType(ws.getSpaceType() == null ? "COMPANY" : ws.getSpaceType())
                .role(role)
                .spaceManager(manager)
                .grantAll(grantAll)
                .grants(grants)
                .build();
    }

    private List<MyWorkspaceAuthzVO.GrantItem> spaceAssetGrants(Long workspaceId,
                                                                Map<Long, ConnectionEntity> connById) {
        List<MyWorkspaceAuthzVO.GrantItem> items = new ArrayList<>();
        Map<Long, List<AuthzCacheModels.AssetEntry>> byConn =
                sqlworkAuthzService.peekWorkspaceAssets(workspaceId);
        for (Map.Entry<Long, List<AuthzCacheModels.AssetEntry>> e : byConn.entrySet()) {
            ConnectionEntity c = connById.get(e.getKey());
            if (c == null) {
                c = connectionMapper.selectById(e.getKey());
            }
            for (AuthzCacheModels.AssetEntry asset : e.getValue()) {
                items.add(MyWorkspaceAuthzVO.GrantItem.builder()
                        .mode("SPACE_ASSET")
                        .connectionId(e.getKey())
                        .connectionName(c == null ? null : c.getName())
                        .dbType(c == null ? null : c.getDbType())
                        .scope(asset.getScope())
                        .tables(toVoTables(asset.getTables()))
                        .ops(asset.getOps() == null ? List.of() : List.copyOf(asset.getOps()))
                        .build());
            }
        }
        return items;
    }

    private Map<Long, ConnectionEntity> loadConnections(Set<Long> ids) {
        Map<Long, ConnectionEntity> map = new HashMap<>();
        if (ids == null || ids.isEmpty()) {
            return map;
        }
        List<ConnectionEntity> list = connectionMapper.selectList(
                new LambdaQueryWrapper<ConnectionEntity>()
                        .in(ConnectionEntity::getId, ids)
                        .eq(ConnectionEntity::getStatus, 1));
        for (ConnectionEntity c : list) {
            map.put(c.getId(), c);
        }
        return map;
    }

    private static List<MyWorkspaceAuthzVO.TableRef> toVoTables(
            List<AuthzCacheModels.TableRef> tables) {
        if (tables == null || tables.isEmpty()) {
            return List.of();
        }
        List<MyWorkspaceAuthzVO.TableRef> out = new ArrayList<>(tables.size());
        for (AuthzCacheModels.TableRef t : tables) {
            out.add(MyWorkspaceAuthzVO.TableRef.builder()
                    .database(t.getDatabase())
                    .schema(t.getSchema())
                    .name(t.getName())
                    .build());
        }
        return out;
    }

    public ConnectionMaterialVO getConnectionMaterial(Long connectionId) {
        LoginUser user = SecurityUtils.requireUser();
        ConnectionEntity connection = connectionMapper.selectById(connectionId);
        if (connection == null) {
            throw BizException.notFound("连接不存在");
        }
        if (connection.getStatus() == null || connection.getStatus() != 1) {
            throw BizException.badRequest("连接未启用");
        }

        boolean allowed = user.hasSuperAdmin()
                || sqlworkAuthzService.hasAnyGrantCoveringConnection(user.getUserId(), connectionId);
        if (!allowed) {
            throw BizException.forbidden("无权获取该连接凭证");
        }

        InstanceEntity instance = instanceService.findById(connection.getInstanceId());
        if (instance == null) {
            throw BizException.notFound("连接所属实例不存在");
        }
        if (instance.getStatus() == null || instance.getStatus() != 1) {
            throw BizException.badRequest("实例未启用");
        }

        String password = kekCryptoService.decrypt(connection.getSecretCipher());
        String database = StringUtils.hasText(connection.getInitialDatabase())
                ? connection.getInitialDatabase().trim()
                : defaultDatabase(connection.getDbType());
        String jdbcUrl = buildJdbcUrl(connection.getDbType(), instance.getHost(), instance.getPort(), database);
        String driver = StringUtils.hasText(instance.getDriverClassName())
                ? instance.getDriverClassName()
                : DbType.from(connection.getDbType()).defaultDriverClassName();

        return ConnectionMaterialVO.builder()
                .connectionId(connection.getId())
                .name(connection.getName())
                .dbType(connection.getDbType())
                .jdbcUrl(jdbcUrl)
                .username(connection.getUsername())
                .password(password)
                .driverClassName(driver)
                .initialDatabase(connection.getInitialDatabase())
                .host(instance.getHost())
                .port(instance.getPort())
                .build();
    }

    public static String buildJdbcUrl(String dbType, String host, Integer port, String database) {
        DbType type = DbType.from(dbType);
        String db = StringUtils.hasText(database) ? database : defaultDatabase(dbType);
        return switch (type) {
            case POSTGRESQL -> "jdbc:postgresql://" + host + ":" + port + "/" + db;
            case MYSQL, MARIADB -> "jdbc:mysql://" + host + ":" + port + "/" + db
                    + "?useSSL=false&allowPublicKeyRetrieval=true";
            case ORACLE -> "jdbc:oracle:thin:@" + host + ":" + port + "/" + db;
            case SQLSERVER -> "jdbc:sqlserver://" + host + ":" + port + ";databaseName=" + db;
        };
    }

    private static String defaultDatabase(String dbType) {
        if (dbType != null && dbType.trim().toUpperCase(Locale.ROOT).startsWith("MYSQL")) {
            return "mysql";
        }
        if (dbType != null && "MARIADB".equalsIgnoreCase(dbType.trim())) {
            return "mysql";
        }
        return "postgres";
    }
}
