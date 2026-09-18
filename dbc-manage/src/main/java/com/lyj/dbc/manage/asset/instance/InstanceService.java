package com.lyj.dbc.manage.asset.instance;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.client.audit.AuditAction;
import com.lyj.dbc.client.audit.AuditLog;
import com.lyj.dbc.manage.asset.DataScopeSupport;
import com.lyj.dbc.manage.asset.DbType;
import com.lyj.dbc.manage.asset.instance.dto.InstanceCreateRequest;
import com.lyj.dbc.manage.asset.instance.dto.InstanceUpdateRequest;
import com.lyj.dbc.manage.asset.instance.entity.InstanceEntity;
import com.lyj.dbc.manage.asset.instance.mapper.InstanceMapper;
import com.lyj.dbc.manage.asset.instance.vo.InstanceVO;
import com.lyj.dbc.manage.client.dto.DataScopeVO;
import com.lyj.dbc.manage.common.BizException;
import com.lyj.dbc.manage.config.ManageProperties;
import com.lyj.dbc.manage.security.DomainCodes;
import com.lyj.dbc.manage.security.DomainContext;
import com.lyj.dbc.manage.security.LoginUser;
import com.lyj.dbc.manage.security.SecurityUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.OffsetDateTime;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * 实例资产管理（公司域 data-scope / 个人域本人资产）。
 */
@Service
public class InstanceService {

    private final InstanceMapper instanceMapper;
    private final ManageProperties manageProperties;

    public InstanceService(InstanceMapper instanceMapper, ManageProperties manageProperties) {
        this.instanceMapper = instanceMapper;
        this.manageProperties = manageProperties;
    }

    public List<InstanceVO> list() {
        if (DomainContext.isPersonal()) {
            Long userId = SecurityUtils.requireUser().getUserId();
            return instanceMapper.selectVisiblePersonal(userId).stream().map(this::toVo).toList();
        }
        DataScopeVO scope = DataScopeSupport.current();
        boolean all = DataScopeSupport.isAll(scope);
        List<Long> deptIds = DataScopeSupport.scopeDeptIdList(scope);
        if (!all && deptIds.isEmpty()) {
            return List.of();
        }
        return instanceMapper.selectVisibleCompany(all, deptIds).stream().map(this::toVo).toList();
    }

    public InstanceVO getById(Long id) {
        return toVo(requireVisible(id));
    }

    @AuditLog(module = "manage", action = AuditAction.CREATE, resourceType = "instance", resourceId = "#return.id")
    @Transactional
    public InstanceVO create(InstanceCreateRequest request) {
        DbType dbType = parseDbType(request.getDbType());
        assertNameUnique(request.getName(), null);
        LoginUser user = SecurityUtils.requireUser();
        OffsetDateTime now = OffsetDateTime.now();
        InstanceEntity entity = new InstanceEntity();
        entity.setName(request.getName().trim());
        entity.setDbType(dbType.name());
        entity.setHost(request.getHost().trim());
        entity.setPort(request.getPort());
        entity.setDriverClassName(resolveDriverClass(dbType, request.getDriverClassName()));
        entity.setStatus(request.getStatus() == null ? 1 : request.getStatus());
        entity.setDescription(request.getDescription());
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
        instanceMapper.insert(entity);
        return toVo(entity);
    }

    @AuditLog(module = "manage", action = AuditAction.UPDATE, resourceType = "instance", resourceId = "#id",
            loadBefore = "getById(#id)")
    @Transactional
    public InstanceVO update(Long id, InstanceUpdateRequest request) {
        InstanceEntity entity = requireOwnedWritable(id);
        DbType dbType = parseDbType(request.getDbType());
        assertNameUnique(request.getName(), id);

        LoginUser user = SecurityUtils.requireUser();
        entity.setName(request.getName().trim());
        entity.setDbType(dbType.name());
        entity.setHost(request.getHost().trim());
        entity.setPort(request.getPort());
        entity.setDriverClassName(resolveDriverClass(dbType, request.getDriverClassName()));
        if (request.getStatus() != null) {
            entity.setStatus(request.getStatus());
        }
        entity.setDescription(request.getDescription());
        if (DomainCodes.isPersonal(entity.getOwnerScope())) {
            entity.setDeptId(null);
            entity.setOwnerUserId(user.getUserId());
        } else {
            DataScopeSupport.assertWritableDept(request.getDeptId());
            entity.setDeptId(request.getDeptId());
        }
        entity.setUpdatedAt(OffsetDateTime.now());
        entity.setUpdatedBy(user.getUserId());
        instanceMapper.updateById(entity);
        return toVo(entity);
    }

    @AuditLog(module = "manage", action = AuditAction.DELETE, resourceType = "instance", resourceId = "#id",
            loadBefore = "getById(#id)")
    @Transactional
    public void delete(Long id) {
        InstanceEntity entity = requireOwnedWritable(id);
        LoginUser user = SecurityUtils.requireUser();
        entity.setUpdatedAt(OffsetDateTime.now());
        entity.setUpdatedBy(user.getUserId());
        instanceMapper.updateById(entity);
        instanceMapper.deleteById(id);
    }

    @AuditLog(module = "manage", action = AuditAction.UPDATE, resourceType = "instance", resourceId = "#id",
            loadBefore = "getById(#id)")
    @Transactional
    public InstanceVO uploadDriver(Long id, MultipartFile file) {
        InstanceEntity entity = requireOwnedWritable(id);
        if (file == null || file.isEmpty()) {
            throw BizException.badRequest("驱动文件不能为空");
        }
        String original = file.getOriginalFilename() == null ? "driver.jar" : file.getOriginalFilename();
        String safeName = Path.of(original).getFileName().toString();
        if (!safeName.toLowerCase().endsWith(".jar")) {
            throw BizException.badRequest("仅支持 .jar 驱动文件");
        }
        if (file.getSize() > manageProperties.getDriverMaxBytes()) {
            throw BizException.badRequest("驱动文件超过大小上限");
        }

        String relative = "drivers/" + id + "/" + UUID.randomUUID() + ".jar";
        Path root = Path.of(manageProperties.getDriverDir()).toAbsolutePath().normalize();
        Path target = root.resolve(relative).normalize();
        if (!target.startsWith(root)) {
            throw BizException.badRequest("非法驱动存储路径");
        }
        try {
            Files.createDirectories(target.getParent());
            String sha256;
            try (InputStream in = file.getInputStream()) {
                byte[] bytes = in.readAllBytes();
                if (bytes.length > manageProperties.getDriverMaxBytes()) {
                    throw BizException.badRequest("驱动文件超过大小上限");
                }
                MessageDigest digest = MessageDigest.getInstance("SHA-256");
                sha256 = HexFormat.of().formatHex(digest.digest(bytes));
                Files.write(target, bytes);
            }
            String oldPath = entity.getDriverStoragePath();
            entity.setDriverFileName(safeName);
            entity.setDriverStoragePath(relative.replace('\\', '/'));
            entity.setDriverSha256(sha256);
            entity.setDriverSize(Files.size(target));
            entity.setUpdatedAt(OffsetDateTime.now());
            entity.setUpdatedBy(SecurityUtils.requireUser().getUserId());
            instanceMapper.updateById(entity);
            cleanupOldDriver(root, oldPath);
            return toVo(entity);
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            throw BizException.badRequest("驱动上传失败: " + e.getMessage());
        }
    }

    /**
     * 创建连接时可选实例：当前域可见且启用。
     */
    public List<InstanceVO> listSelectable(String dbType) {
        String type = StringUtils.hasText(dbType) ? parseDbType(dbType).name() : null;
        if (DomainContext.isPersonal()) {
            Long userId = SecurityUtils.requireUser().getUserId();
            return instanceMapper.selectSelectablePersonal(userId, type).stream().map(this::toVoBrief).toList();
        }
        DataScopeVO scope = DataScopeSupport.current();
        boolean all = DataScopeSupport.isAll(scope);
        List<Long> deptIds = DataScopeSupport.scopeDeptIdList(scope);
        if (!all && deptIds.isEmpty()) {
            return List.of();
        }
        return instanceMapper.selectSelectableCompany(all, deptIds, type).stream().map(this::toVoBrief).toList();
    }

    public InstanceEntity findById(Long instanceId) {
        return instanceMapper.selectById(instanceId);
    }

    /**
     * 判断实例是否可作为连接目标（须在当前域可见且启用）。
     */
    public InstanceEntity requireSelectable(Long instanceId) {
        InstanceEntity entity = instanceMapper.selectById(instanceId);
        if (entity == null) {
            throw BizException.notFound("实例不存在");
        }
        if (entity.getStatus() == null || entity.getStatus() != 1) {
            throw BizException.badRequest("实例未启用");
        }
        assertVisible(entity);
        return entity;
    }

    private InstanceEntity requireVisible(Long id) {
        InstanceEntity entity = instanceMapper.selectById(id);
        if (entity == null) {
            throw BizException.notFound("实例不存在");
        }
        assertVisible(entity);
        return entity;
    }

    private InstanceEntity requireOwnedWritable(Long id) {
        InstanceEntity entity = requireVisible(id);
        if (DomainCodes.isPersonal(entity.getOwnerScope())) {
            Long userId = SecurityUtils.requireUser().getUserId();
            if (!Objects.equals(entity.getOwnerUserId(), userId)) {
                throw BizException.forbidden("无权维护该实例");
            }
            if (!DomainContext.isPersonal()) {
                throw BizException.forbidden("请在个人空间中维护个人实例");
            }
            return entity;
        }
        if (DomainContext.isPersonal()) {
            throw BizException.forbidden("公司实例不可在个人域维护");
        }
        DataScopeVO scope = DataScopeSupport.current();
        if (!DataScopeSupport.isAll(scope) && !DataScopeSupport.inScope(entity.getDeptId(), scope)) {
            throw BizException.forbidden("无权维护该实例");
        }
        return entity;
    }

    private void assertVisible(InstanceEntity entity) {
        if (DomainCodes.isPersonal(entity.getOwnerScope())) {
            if (!DomainContext.isPersonal()) {
                throw BizException.forbidden("无权查看该实例");
            }
            Long userId = SecurityUtils.requireUser().getUserId();
            if (!Objects.equals(entity.getOwnerUserId(), userId)) {
                throw BizException.forbidden("无权查看该实例");
            }
            return;
        }
        if (DomainContext.isPersonal()) {
            throw BizException.forbidden("无权查看该实例");
        }
        DataScopeVO scope = DataScopeSupport.current();
        if (DataScopeSupport.isAll(scope) || DataScopeSupport.inScope(entity.getDeptId(), scope)) {
            return;
        }
        throw BizException.forbidden("无权查看该实例");
    }

    private void assertNameUnique(String name, Long excludeId) {
        LambdaQueryWrapper<InstanceEntity> q = new LambdaQueryWrapper<InstanceEntity>()
                .eq(InstanceEntity::getName, name.trim());
        if (excludeId != null) {
            q.ne(InstanceEntity::getId, excludeId);
        }
        if (instanceMapper.selectCount(q) > 0) {
            throw BizException.conflict("实例名称已存在");
        }
    }

    private static DbType parseDbType(String value) {
        try {
            return DbType.from(value);
        } catch (Exception e) {
            throw BizException.badRequest("不支持的库类型: " + value);
        }
    }

    private static String resolveDriverClass(DbType dbType, String override) {
        if (StringUtils.hasText(override)) {
            return override.trim();
        }
        return dbType.defaultDriverClassName();
    }

    private InstanceVO toVo(InstanceEntity entity) {
        return InstanceVO.builder()
                .id(entity.getId())
                .name(entity.getName())
                .deptId(entity.getDeptId())
                .ownerScope(entity.getOwnerScope())
                .ownerUserId(entity.getOwnerUserId())
                .dbType(entity.getDbType())
                .host(entity.getHost())
                .port(entity.getPort())
                .driverFileName(entity.getDriverFileName())
                .driverStoragePath(entity.getDriverStoragePath())
                .driverSha256(entity.getDriverSha256())
                .driverSize(entity.getDriverSize())
                .driverClassName(entity.getDriverClassName())
                .status(entity.getStatus())
                .description(entity.getDescription())
                .createdAt(entity.getCreatedAt())
                .updatedAt(entity.getUpdatedAt())
                .build();
    }

    private InstanceVO toVoBrief(InstanceEntity entity) {
        return InstanceVO.builder()
                .id(entity.getId())
                .name(entity.getName())
                .deptId(entity.getDeptId())
                .ownerScope(entity.getOwnerScope())
                .ownerUserId(entity.getOwnerUserId())
                .dbType(entity.getDbType())
                .host(entity.getHost())
                .port(entity.getPort())
                .status(entity.getStatus())
                .driverClassName(entity.getDriverClassName())
                .build();
    }

    private void cleanupOldDriver(Path root, String oldRelative) {
        if (!StringUtils.hasText(oldRelative)) {
            return;
        }
        try {
            Path old = root.resolve(oldRelative).normalize();
            if (old.startsWith(root) && Files.exists(old)) {
                Files.deleteIfExists(old);
            }
        } catch (IOException ignored) {
            // 旧文件清理失败不影响主流程
        }
    }
}
