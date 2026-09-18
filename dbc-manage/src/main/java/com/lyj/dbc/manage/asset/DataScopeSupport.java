package com.lyj.dbc.manage.asset;

import com.lyj.dbc.manage.client.dto.DataScopeVO;
import com.lyj.dbc.manage.common.BizException;
import com.lyj.dbc.manage.security.UserContextHolder;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * 数据范围校验与过滤辅助。
 */
public final class DataScopeSupport {

    private DataScopeSupport() {
    }

    public static DataScopeVO current() {
        return UserContextHolder.requireDataScope();
    }

    public static boolean isAll(DataScopeVO scope) {
        return Boolean.TRUE.equals(scope.getAll());
    }

    public static Set<Long> deptIds(DataScopeVO scope) {
        if (scope.getDeptIds() == null || scope.getDeptIds().isEmpty()) {
            return Collections.emptySet();
        }
        return new HashSet<>(scope.getDeptIds());
    }

    /**
     * 写入时校验目标部门必须在可写范围；无 ALL 且无可用部门时禁止创建。
     */
    public static void assertWritableDept(Long deptId) {
        if (deptId == null) {
            throw BizException.badRequest("归属部门不能为空");
        }
        DataScopeVO scope = current();
        if (isAll(scope)) {
            return;
        }
        Set<Long> ids = deptIds(scope);
        if (ids.isEmpty()) {
            throw BizException.forbidden("当前用户无可用部门数据范围，无法创建或修改资产");
        }
        if (!ids.contains(deptId)) {
            throw BizException.forbidden("归属部门不在数据范围内");
        }
    }

    /**
     * 读过滤：部门在范围内。
     */
    public static boolean inScope(Long deptId, DataScopeVO scope) {
        if (isAll(scope)) {
            return true;
        }
        return deptId != null && deptIds(scope).contains(deptId);
    }

    public static List<Long> scopeDeptIdList(DataScopeVO scope) {
        if (isAll(scope)) {
            return List.of();
        }
        return List.copyOf(deptIds(scope));
    }
}
