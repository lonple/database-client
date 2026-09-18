package com.lyj.dbc.manage.security;

import com.lyj.dbc.manage.client.dto.DataScopeVO;
import com.lyj.dbc.manage.common.BizException;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * 读取 UserContextFilter 写入的请求级权限 / 数据范围。
 */
public final class UserContextHolder {

    private UserContextHolder() {
    }

    @SuppressWarnings("unchecked")
    public static Set<String> permissionCodes() {
        HttpServletRequest request = currentRequest();
        Object attr = request.getAttribute(UserContextFilter.ATTR_PERMISSIONS);
        if (attr instanceof List<?> list) {
            return new HashSet<>((List<String>) list);
        }
        return Collections.emptySet();
    }

    public static DataScopeVO requireDataScope() {
        HttpServletRequest request = currentRequest();
        Object attr = request.getAttribute(UserContextFilter.ATTR_DATA_SCOPE);
        if (attr instanceof DataScopeVO scope) {
            return scope;
        }
        throw BizException.unauthorized("缺少数据范围上下文");
    }

    private static HttpServletRequest currentRequest() {
        ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (attrs == null) {
            throw BizException.unauthorized("无请求上下文");
        }
        return attrs.getRequest();
    }
}
