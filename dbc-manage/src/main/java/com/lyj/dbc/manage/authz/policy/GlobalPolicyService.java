package com.lyj.dbc.manage.authz.policy;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.client.audit.AuditAction;
import com.lyj.dbc.client.audit.AuditLog;
import com.lyj.dbc.manage.authz.SqlOpCodes;
import com.lyj.dbc.manage.authz.policy.dto.GlobalPolicyRequests;
import com.lyj.dbc.manage.authz.policy.entity.GlobalPolicyEntity;
import com.lyj.dbc.manage.authz.policy.mapper.GlobalPolicyMapper;
import com.lyj.dbc.manage.authz.policy.vo.GlobalPolicyVO;
import com.lyj.dbc.manage.common.BizException;
import com.lyj.dbc.manage.security.LoginUser;
import com.lyj.dbc.manage.security.SecurityUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * 全局管控策略 CRUD 与执行期裁决。
 */
@Service
public class GlobalPolicyService {

    private static final Logger log = LoggerFactory.getLogger(GlobalPolicyService.class);

    public static final String STRATEGY_BLOCK = "BLOCK";
    public static final String STRATEGY_ALERT = "ALERT";
    public static final String STRATEGY_REAUTH = "REAUTH";
    public static final String SCOPE_ALL = "ALL";
    public static final String SCOPE_SPECIFIC = "SPECIFIC";
    public static final String ACTION_NONE = "NONE";

    private static final Set<String> ALLOWED_STRATEGIES = Set.of(STRATEGY_BLOCK, STRATEGY_ALERT, STRATEGY_REAUTH);

    private final GlobalPolicyMapper globalPolicyMapper;
    private final ObjectMapper objectMapper;

    public GlobalPolicyService(GlobalPolicyMapper globalPolicyMapper, ObjectMapper objectMapper) {
        this.globalPolicyMapper = globalPolicyMapper;
        this.objectMapper = objectMapper;
    }

    public List<GlobalPolicyVO> listAll() {
        List<GlobalPolicyEntity> rows = globalPolicyMapper.selectList(new LambdaQueryWrapper<GlobalPolicyEntity>()
                .orderByAsc(GlobalPolicyEntity::getSortNo)
                .orderByDesc(GlobalPolicyEntity::getId));
        List<GlobalPolicyVO> out = new ArrayList<>();
        for (GlobalPolicyEntity row : rows) {
            out.add(toVo(row));
        }
        return out;
    }

    public GlobalPolicyVO get(Long id) {
        GlobalPolicyEntity entity = require(id);
        return toVo(entity);
    }

    @AuditLog(module = "manage", action = AuditAction.CREATE, resourceType = "global_policy", resourceId = "#return.id")
    @Transactional
    public GlobalPolicyVO create(GlobalPolicyRequests.SaveRequest request) {
        LoginUser user = SecurityUtils.requireUser();
        validateRequest(request);
        assertNameUnique(request.getName().trim(), null);
        GlobalPolicyEntity entity = new GlobalPolicyEntity();
        fill(entity, request, user.getUserId(), true);
        globalPolicyMapper.insert(entity);
        return toVo(entity);
    }

    @AuditLog(module = "manage", action = AuditAction.UPDATE, resourceType = "global_policy", resourceId = "#id",
            loadBefore = "get(#id)")
    @Transactional
    public GlobalPolicyVO update(Long id, GlobalPolicyRequests.SaveRequest request) {
        LoginUser user = SecurityUtils.requireUser();
        validateRequest(request);
        GlobalPolicyEntity entity = require(id);
        assertNameUnique(request.getName().trim(), id);
        fill(entity, request, user.getUserId(), false);
        globalPolicyMapper.updateById(entity);
        return toVo(entity);
    }

    @AuditLog(module = "manage", action = AuditAction.DELETE, resourceType = "global_policy", resourceId = "#id",
            loadBefore = "get(#id)")
    @Transactional
    public void delete(Long id) {
        require(id);
        globalPolicyMapper.deleteById(id);
    }

    /**
     * 按优先级选出命中策略：BLOCK > REAUTH > ALERT。
     */
    public Hit evaluate(Long workspaceId, String sqlOp) {
        if (workspaceId == null || !StringUtils.hasText(sqlOp)) {
            return Hit.none();
        }
        String op = sqlOp.trim().toUpperCase(Locale.ROOT);
        List<GlobalPolicyEntity> rows = globalPolicyMapper.selectList(new LambdaQueryWrapper<GlobalPolicyEntity>()
                .eq(GlobalPolicyEntity::getStatus, 1)
                .orderByAsc(GlobalPolicyEntity::getSortNo)
                .orderByAsc(GlobalPolicyEntity::getId));
        List<Hit> hits = new ArrayList<>();
        for (GlobalPolicyEntity row : rows) {
            if (!matchesWorkspace(row, workspaceId)) {
                continue;
            }
            List<String> ops = readStringList(row.getOpsJson());
            if (!SqlOpCodes.covers(ops, op)) {
                continue;
            }
            hits.add(new Hit(normalizeStrategy(row.getStrategy()), row.getId(), row.getName()));
        }
        if (hits.isEmpty()) {
            return Hit.none();
        }
        hits.sort(Comparator.comparingInt(h -> strategyRank(h.action())));
        return hits.get(0);
    }

    private static int strategyRank(String action) {
        return switch (action) {
            case STRATEGY_BLOCK -> 0;
            case STRATEGY_REAUTH -> 1;
            case STRATEGY_ALERT -> 2;
            default -> 9;
        };
    }

    private boolean matchesWorkspace(GlobalPolicyEntity row, Long workspaceId) {
        String scope = row.getWorkspaceScope() == null ? SCOPE_ALL : row.getWorkspaceScope().trim().toUpperCase(Locale.ROOT);
        if (SCOPE_ALL.equals(scope)) {
            return true;
        }
        List<Long> ids = readLongList(row.getWorkspaceIdsJson());
        return ids.contains(workspaceId);
    }

    private void validateRequest(GlobalPolicyRequests.SaveRequest request) {
        String strategy = request.getStrategy().trim().toUpperCase(Locale.ROOT);
        if (!ALLOWED_STRATEGIES.contains(strategy)) {
            throw BizException.badRequest("非法策略: " + request.getStrategy());
        }
        String scope = request.getWorkspaceScope().trim().toUpperCase(Locale.ROOT);
        if (!SCOPE_ALL.equals(scope) && !SCOPE_SPECIFIC.equals(scope)) {
            throw BizException.badRequest("非法空间范围: " + request.getWorkspaceScope());
        }
        if (SCOPE_SPECIFIC.equals(scope) && (request.getWorkspaceIds() == null || request.getWorkspaceIds().isEmpty())) {
            throw BizException.badRequest("指定空间时至少选择一个工作空间");
        }
        LinkedHashSet<String> ops = new LinkedHashSet<>();
        for (String raw : request.getOps()) {
            if (!StringUtils.hasText(raw)) {
                continue;
            }
            String op = raw.trim().toUpperCase(Locale.ROOT);
            if (!SqlOpCodes.isAllowedWriteOp(op)) {
                throw BizException.badRequest("不支持的 SQL 操作: " + op);
            }
            ops.add(op);
        }
        List<String> normalized = SqlOpCodes.normalize(ops);
        if (normalized.isEmpty()) {
            throw BizException.badRequest("管控指令不能为空，请勾选操作或选择「所有权限（任意 SQL）」");
        }
        request.setOps(normalized);
        request.setStrategy(strategy);
        request.setWorkspaceScope(scope);
        if (request.getStatus() == null || (request.getStatus() != 0 && request.getStatus() != 1)) {
            throw BizException.badRequest("status 仅支持 0/1");
        }
    }

    private void fill(GlobalPolicyEntity entity, GlobalPolicyRequests.SaveRequest request, Long userId, boolean creating) {
        OffsetDateTime now = OffsetDateTime.now();
        entity.setName(request.getName().trim());
        entity.setOpsJson(writeJson(request.getOps()));
        entity.setStrategy(request.getStrategy());
        entity.setWorkspaceScope(request.getWorkspaceScope());
        if (SCOPE_SPECIFIC.equals(request.getWorkspaceScope())) {
            entity.setWorkspaceIdsJson(writeJson(request.getWorkspaceIds()));
        } else {
            entity.setWorkspaceIdsJson("[]");
        }
        entity.setSortNo(request.getSortNo() == null ? 0 : request.getSortNo());
        entity.setStatus(request.getStatus());
        entity.setUpdatedAt(now);
        entity.setUpdatedBy(userId);
        if (creating) {
            entity.setCreatedAt(now);
            entity.setCreatedBy(userId);
            entity.setDeleted(0);
        }
    }

    private void assertNameUnique(String name, Long excludeId) {
        LambdaQueryWrapper<GlobalPolicyEntity> q = new LambdaQueryWrapper<GlobalPolicyEntity>()
                .eq(GlobalPolicyEntity::getName, name);
        if (excludeId != null) {
            q.ne(GlobalPolicyEntity::getId, excludeId);
        }
        Long cnt = globalPolicyMapper.selectCount(q);
        if (cnt != null && cnt > 0) {
            throw BizException.badRequest("管控名称已存在");
        }
    }

    private GlobalPolicyEntity require(Long id) {
        GlobalPolicyEntity entity = globalPolicyMapper.selectById(id);
        if (entity == null) {
            throw BizException.notFound("策略不存在: " + id);
        }
        return entity;
    }

    private GlobalPolicyVO toVo(GlobalPolicyEntity entity) {
        return GlobalPolicyVO.builder()
                .id(entity.getId())
                .name(entity.getName())
                .ops(readStringList(entity.getOpsJson()))
                .strategy(entity.getStrategy())
                .workspaceScope(entity.getWorkspaceScope())
                .workspaceIds(readLongList(entity.getWorkspaceIdsJson()))
                .sortNo(entity.getSortNo())
                .status(entity.getStatus())
                .updatedAt(entity.getUpdatedAt())
                .build();
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? List.of() : value);
        } catch (Exception e) {
            throw BizException.badRequest("JSON 序列化失败");
        }
    }

    private List<String> readStringList(String json) {
        if (!StringUtils.hasText(json)) {
            return List.of();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<String>>() {});
        } catch (Exception e) {
            log.warn("解析 ops_json 失败", e);
            return List.of();
        }
    }

    private List<Long> readLongList(String json) {
        if (!StringUtils.hasText(json)) {
            return List.of();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<Long>>() {});
        } catch (Exception e) {
            log.warn("解析 workspace_ids_json 失败", e);
            return List.of();
        }
    }

    private static String normalizeStrategy(String strategy) {
        if (!StringUtils.hasText(strategy)) {
            return STRATEGY_BLOCK;
        }
        return strategy.trim().toUpperCase(Locale.ROOT);
    }

    /**
     * 全局策略命中结果。
     */
    public record Hit(String action, Long policyId, String policyName) {
        public static Hit none() {
            return new Hit(ACTION_NONE, null, null);
        }
    }
}
