package com.lyj.dbc.manage.asset.connection;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.client.audit.AuditAction;
import com.lyj.dbc.client.audit.AuditLog;
import com.lyj.dbc.manage.asset.DataScopeSupport;
import com.lyj.dbc.manage.asset.DbType;
import com.lyj.dbc.manage.asset.connection.dto.ConnectionCreateRequest;
import com.lyj.dbc.manage.asset.connection.dto.ConnectionPingRequest;
import com.lyj.dbc.manage.asset.connection.dto.ConnectionUpdateRequest;
import com.lyj.dbc.manage.asset.connection.entity.ConnectionEntity;
import com.lyj.dbc.manage.asset.connection.mapper.ConnectionMapper;
import com.lyj.dbc.manage.asset.connection.vo.ConnectionPingResultVO;
import com.lyj.dbc.manage.asset.connection.vo.ConnectionVO;
import com.lyj.dbc.manage.asset.instance.InstanceService;
import com.lyj.dbc.manage.asset.instance.entity.InstanceEntity;
import com.lyj.dbc.manage.client.SqlworkMetaClient;
import com.lyj.dbc.manage.client.dto.DataScopeVO;
import com.lyj.dbc.manage.common.BizException;
import com.lyj.dbc.manage.inner.sqlwork.SqlworkInnerService;
import com.lyj.dbc.manage.inner.sqlwork.vo.ConnectionMaterialVO;
import com.lyj.dbc.manage.secrets.ManageKekCryptoService;
import com.lyj.dbc.manage.security.DomainCodes;
import com.lyj.dbc.manage.security.DomainContext;
import com.lyj.dbc.manage.security.LoginUser;
import com.lyj.dbc.manage.security.SecurityUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

/**
 * 连接资产管理（公司域 data-scope / 个人域本人资产）。
 */
@Service
public class ConnectionService {

    private static final String PASSWORD_MASK = "****";

    private final ConnectionMapper connectionMapper;
    private final InstanceService instanceService;
    private final ManageKekCryptoService kekCryptoService;
    private final SqlworkMetaClient sqlworkMetaClient;

    public ConnectionService(ConnectionMapper connectionMapper, InstanceService instanceService,
                             ManageKekCryptoService kekCryptoService, SqlworkMetaClient sqlworkMetaClient) {
        this.connectionMapper = connectionMapper;
        this.instanceService = instanceService;
        this.kekCryptoService = kekCryptoService;
        this.sqlworkMetaClient = sqlworkMetaClient;
    }

    public List<ConnectionVO> list() {
        LambdaQueryWrapper<ConnectionEntity> q = new LambdaQueryWrapper<ConnectionEntity>()
                .orderByDesc(ConnectionEntity::getId);
        if (DomainContext.isPersonal()) {
            Long userId = SecurityUtils.requireUser().getUserId();
            q.eq(ConnectionEntity::getOwnerScope, DomainCodes.PERSONAL)
                    .eq(ConnectionEntity::getOwnerUserId, userId);
        } else {
            q.eq(ConnectionEntity::getOwnerScope, DomainCodes.COMPANY);
            DataScopeVO scope = DataScopeSupport.current();
            if (!DataScopeSupport.isAll(scope)) {
                List<Long> deptIds = DataScopeSupport.scopeDeptIdList(scope);
                if (deptIds.isEmpty()) {
                    return List.of();
                }
                q.in(ConnectionEntity::getDeptId, deptIds);
            }
        }
        return connectionMapper.selectList(q).stream().map(this::toVo).toList();
    }

    public ConnectionVO getById(Long id) {
        return toVo(requireInScope(id));
    }

    /**
     * 创建/编辑表单探活：组装材料后经 sqlwork 短超时探测（本服务不直连目标库）。
     */
    public ConnectionPingResultVO ping(ConnectionPingRequest request) {
        InstanceEntity instance = instanceService.requireSelectable(request.getInstanceId());
        assertInstanceDomainMatch(instance);

        String password;
        Long connectionId = request.getConnectionId();
        if (StringUtils.hasText(request.getPassword())) {
            password = request.getPassword();
        } else if (connectionId != null) {
            ConnectionEntity existing = requireInScope(connectionId);
            password = kekCryptoService.decrypt(existing.getSecretCipher());
        } else {
            throw BizException.badRequest("请填写密码");
        }

        String database = StringUtils.hasText(request.getInitialDatabase())
                ? request.getInitialDatabase().trim()
                : defaultDatabase(instance.getDbType());
        String jdbcUrl = SqlworkInnerService.buildJdbcUrl(
                instance.getDbType(), instance.getHost(), instance.getPort(), database);
        String driver = StringUtils.hasText(instance.getDriverClassName())
                ? instance.getDriverClassName()
                : DbType.from(instance.getDbType()).defaultDriverClassName();

        ConnectionMaterialVO material = ConnectionMaterialVO.builder()
                .connectionId(connectionId)
                .name(request.getUsername().trim())
                .dbType(instance.getDbType())
                .jdbcUrl(jdbcUrl)
                .username(request.getUsername().trim())
                .password(password)
                .driverClassName(driver)
                .initialDatabase(request.getInitialDatabase())
                .host(instance.getHost())
                .port(instance.getPort())
                .build();
        return sqlworkMetaClient.ping(material);
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

    @AuditLog(module = "manage", action = AuditAction.CREATE, resourceType = "connection", resourceId = "#return.id")
    @Transactional
    public ConnectionVO create(ConnectionCreateRequest request) {
        InstanceEntity instance = instanceService.requireSelectable(request.getInstanceId());
        assertInstanceDomainMatch(instance);
        assertNameUnique(request.getName(), null);

        LoginUser user = SecurityUtils.requireUser();
        OffsetDateTime now = OffsetDateTime.now();
        ConnectionEntity entity = new ConnectionEntity();
        entity.setName(request.getName().trim());
        entity.setInstanceId(instance.getId());
        entity.setDbType(instance.getDbType());
        entity.setUsername(request.getUsername().trim());
        entity.setSecretCipher(kekCryptoService.encrypt(request.getPassword()));
        entity.setInitialDatabase(request.getInitialDatabase());
        entity.setStatus(request.getStatus() == null ? 1 : request.getStatus());
        entity.setDeleted(0);
        entity.setCreatedAt(now);
        entity.setUpdatedAt(now);
        entity.setCreatedBy(user.getUserId());
        entity.setUpdatedBy(user.getUserId());
        if (DomainContext.isPersonal()) {
            entity.setOwnerScope(DomainCodes.PERSONAL);
            entity.setOwnerUserId(user.getUserId());
            entity.setDeptId(null);
        } else {
            DataScopeSupport.assertWritableDept(request.getDeptId());
            entity.setOwnerScope(DomainCodes.COMPANY);
            entity.setOwnerUserId(null);
            entity.setDeptId(request.getDeptId());
        }
        connectionMapper.insert(entity);
        return toVo(entity, instance.getName());
    }

    @AuditLog(module = "manage", action = AuditAction.UPDATE, resourceType = "connection", resourceId = "#id",
            loadBefore = "getById(#id)")
    @Transactional
    public ConnectionVO update(Long id, ConnectionUpdateRequest request) {
        ConnectionEntity entity = requireInScope(id);
        InstanceEntity instance = instanceService.requireSelectable(request.getInstanceId());
        assertInstanceDomainMatch(instance);
        assertNameUnique(request.getName(), id);

        LoginUser user = SecurityUtils.requireUser();
        entity.setName(request.getName().trim());
        entity.setInstanceId(instance.getId());
        entity.setDbType(instance.getDbType());
        entity.setUsername(request.getUsername().trim());
        if (StringUtils.hasText(request.getPassword())) {
            entity.setSecretCipher(kekCryptoService.encrypt(request.getPassword()));
        }
        entity.setInitialDatabase(request.getInitialDatabase());
        if (request.getStatus() != null) {
            entity.setStatus(request.getStatus());
        }
        if (DomainCodes.isPersonal(entity.getOwnerScope())) {
            entity.setDeptId(null);
            entity.setOwnerUserId(user.getUserId());
        } else {
            DataScopeSupport.assertWritableDept(request.getDeptId());
            entity.setDeptId(request.getDeptId());
        }
        entity.setUpdatedAt(OffsetDateTime.now());
        entity.setUpdatedBy(user.getUserId());
        connectionMapper.updateById(entity);
        return toVo(entity, instance.getName());
    }

    @AuditLog(module = "manage", action = AuditAction.DELETE, resourceType = "connection", resourceId = "#id",
            loadBefore = "getById(#id)")
    @Transactional
    public void delete(Long id) {
        ConnectionEntity entity = requireInScope(id);
        LoginUser user = SecurityUtils.requireUser();
        entity.setUpdatedAt(OffsetDateTime.now());
        entity.setUpdatedBy(user.getUserId());
        connectionMapper.updateById(entity);
        connectionMapper.deleteById(id);
    }

    private void assertInstanceDomainMatch(InstanceEntity instance) {
        boolean personalInstance = DomainCodes.isPersonal(instance.getOwnerScope());
        if (DomainContext.isPersonal() != personalInstance) {
            throw BizException.badRequest(DomainContext.isPersonal()
                    ? "个人连接只能关联个人实例"
                    : "公司连接只能关联公司实例");
        }
    }

    private ConnectionEntity requireInScope(Long id) {
        ConnectionEntity entity = connectionMapper.selectById(id);
        if (entity == null) {
            throw BizException.notFound("连接不存在");
        }
        if (DomainCodes.isPersonal(entity.getOwnerScope())) {
            if (!DomainContext.isPersonal()) {
                throw BizException.forbidden("无权访问该连接");
            }
            Long userId = SecurityUtils.requireUser().getUserId();
            if (!Objects.equals(entity.getOwnerUserId(), userId)) {
                throw BizException.forbidden("无权访问该连接");
            }
            return entity;
        }
        if (DomainContext.isPersonal()) {
            throw BizException.forbidden("无权访问该连接");
        }
        DataScopeVO scope = DataScopeSupport.current();
        if (!DataScopeSupport.isAll(scope) && !DataScopeSupport.inScope(entity.getDeptId(), scope)) {
            throw BizException.forbidden("无权访问该连接");
        }
        return entity;
    }

    private void assertNameUnique(String name, Long excludeId) {
        LambdaQueryWrapper<ConnectionEntity> q = new LambdaQueryWrapper<ConnectionEntity>()
                .eq(ConnectionEntity::getName, name.trim());
        if (excludeId != null) {
            q.ne(ConnectionEntity::getId, excludeId);
        }
        if (connectionMapper.selectCount(q) > 0) {
            throw BizException.conflict("连接名称已存在");
        }
    }

    private ConnectionVO toVo(ConnectionEntity entity) {
        InstanceEntity instance = instanceService.findById(entity.getInstanceId());
        return toVo(entity, instance == null ? null : instance.getName());
    }

    private ConnectionVO toVo(ConnectionEntity entity, String instanceName) {
        return ConnectionVO.builder()
                .id(entity.getId())
                .name(entity.getName())
                .deptId(entity.getDeptId())
                .ownerScope(entity.getOwnerScope())
                .ownerUserId(entity.getOwnerUserId())
                .instanceId(entity.getInstanceId())
                .instanceName(instanceName)
                .dbType(entity.getDbType())
                .username(entity.getUsername())
                .passwordMasked(PASSWORD_MASK)
                .initialDatabase(entity.getInitialDatabase())
                .status(entity.getStatus())
                .createdAt(entity.getCreatedAt())
                .updatedAt(entity.getUpdatedAt())
                .build();
    }
}
