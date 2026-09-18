package com.lyj.dbc.client.audit;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.client.audit.dto.AuditEventDtos;
import jakarta.servlet.http.HttpServletRequest;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.BeanFactory;
import org.springframework.context.expression.BeanFactoryResolver;
import org.springframework.core.DefaultParameterNameDiscoverer;
import org.springframework.core.ParameterNameDiscoverer;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.lang.reflect.Method;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * {@link AuditLog} 环绕切面：组装事件后仅异步上报，禁止同步等待。
 */
@Aspect
public class AuditLogAspect {

    private static final Logger log = LoggerFactory.getLogger(AuditLogAspect.class);

    private final AuditEventPublisher ingestClient;
    private final ObjectMapper objectMapper;
    private final BeanFactory beanFactory;
    private final ExpressionParser parser = new SpelExpressionParser();
    private final ParameterNameDiscoverer nameDiscoverer = new DefaultParameterNameDiscoverer();

    public AuditLogAspect(AuditEventPublisher ingestClient, ObjectMapper objectMapper, BeanFactory beanFactory) {
        this.ingestClient = Objects.requireNonNull(ingestClient, "ingestClient");
        this.objectMapper = objectMapper == null ? new ObjectMapper() : objectMapper;
        this.beanFactory = Objects.requireNonNull(beanFactory, "beanFactory");
    }

    @Around("@annotation(auditLog)")
    public Object around(ProceedingJoinPoint pjp, AuditLog auditLog) throws Throwable {
        MethodSignature signature = (MethodSignature) pjp.getSignature();
        Method method = signature.getMethod();
        Object[] args = pjp.getArgs();
        String[] paramNames = resolveParamNames(method, signature);

        Object before = null;
        Object target = pjp.getTarget();
        if (auditLog.loadBefore() != null && !auditLog.loadBefore().isBlank()) {
            String expr = normalizeBeanSpel(auditLog.loadBefore());
            try {
                before = eval(expr, paramNames, args, null, target);
            } catch (Throwable e) {
                // loadBefore 失败不得阻断业务（常见原因：误写 #bean 而非 @bean / 方法名）
                log.warn("审计 loadBefore 失败 method={} expr={}", method.getName(), expr, e);
            }
        }

        try {
            Object result = pjp.proceed();
            try {
                submit(auditLog, paramNames, args, before, result, true, null, target);
            } catch (Exception e) {
                log.warn("审计提交失败 method={}", method.getName(), e);
            }
            return result;
        } catch (Throwable ex) {
            try {
                submit(auditLog, paramNames, args, before, null, false, ex, target);
            } catch (Exception e) {
                log.warn("审计失败事件提交失败 method={}", method.getName(), e);
            }
            throw ex;
        }
    }

    private void submit(AuditLog auditLog, String[] paramNames, Object[] args,
                        Object before, Object result, boolean success, Throwable error, Object target) {
        String action = resolveAction(auditLog);
        String resourceId = null;
        try {
            if (auditLog.resourceId() != null && !auditLog.resourceId().isBlank()) {
                Object v = eval(auditLog.resourceId(), paramNames, args, result, target);
                resourceId = v == null ? null : String.valueOf(v);
            }
        } catch (Exception e) {
            log.warn("审计 resourceId SpEL 失败", e);
        }

        Operator op = resolveOperator(auditLog, paramNames, args, success);
        if (success && auditLog.action() == AuditAction.LOGIN) {
            op = enrichLoginOperator(op, result);
        }
        Map<String, Object> details = buildDetails(auditLog.action(), paramNames, args, before, result, success);
        details = AuditDetailsNormalizer.normalize(details, objectMapper);
        details = SensitiveFieldFilter.sanitizeMap(details);

        AuditEventDtos.AuditEvent event = AuditEventDtos.AuditEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .category("BIZ")
                .occurredAt(Instant.now())
                .module(auditLog.module())
                .action(action)
                .resourceType(blankToNull(auditLog.resourceType()))
                .resourceId(resourceId)
                .operatorUserId(op.userId())
                .operatorUsername(op.username())
                .clientIp(resolveClientIp())
                .result(success ? "SUCCESS" : "FAIL")
                .failReason(success ? null : summarizeError(error))
                .details(details)
                .build();
        ingestClient.ingestAsync(event);
    }

    private Map<String, Object> buildDetails(AuditAction action, String[] paramNames, Object[] args,
                                             Object before, Object result, boolean success) {
        Map<String, Object> details = new LinkedHashMap<>();
        if (action == AuditAction.LOGIN || action == AuditAction.LOGOUT) {
            Object usernameObj = findArg(paramNames, args, "request", "username");
            String username = usernameObj == null ? null : String.valueOf(usernameObj);
            if (username == null || "null".equals(username)) {
                username = extractUsernameFromRequestArg(args);
            }
            if (username == null || "null".equals(username)) {
                Operator fromCtx = resolveOperatorFromSecurity();
                username = fromCtx.username();
            }
            details.put("username", username);
            details.put("success", success);
            return details;
        }
        if (action == AuditAction.CREATE) {
            Object after = result != null ? result : firstNonNullArg(args);
            details.put("after", toSanitizedMap(after));
            return details;
        }
        if (action == AuditAction.UPDATE) {
            Object after = result != null ? result : findRequestArg(args);
            details.put("changes", diff(toSanitizedMap(before), toSanitizedMap(after)));
            return details;
        }
        if (action == AuditAction.DELETE) {
            Map<String, Object> keys = new LinkedHashMap<>();
            Map<String, Object> beforeMap = toSanitizedMap(before);
            if (beforeMap != null) {
                if (beforeMap.get("id") != null) {
                    keys.put("id", beforeMap.get("id"));
                }
                if (beforeMap.get("name") != null) {
                    keys.put("name", beforeMap.get("name"));
                }
                if (beforeMap.get("username") != null) {
                    keys.put("username", beforeMap.get("username"));
                }
                if (beforeMap.get("code") != null) {
                    keys.put("code", beforeMap.get("code"));
                }
                if (keys.isEmpty()) {
                    keys.putAll(beforeMap);
                }
            } else {
                Object id = findArg(paramNames, args, "id");
                if (id != null) {
                    keys.put("id", id);
                }
            }
            details.put("keys", keys);
            return details;
        }
        // CUSTOM
        if (result != null) {
            details.put("after", toSanitizedMap(result));
        }
        Object req = findRequestArg(args);
        if (req != null) {
            details.put("request", toSanitizedMap(req));
        }
        return details;
    }

    private List<Map<String, Object>> diff(Map<String, Object> before, Map<String, Object> after) {
        List<Map<String, Object>> changes = new ArrayList<>();
        if (after == null && before == null) {
            return changes;
        }
        Map<String, Object> left = before == null ? Map.of() : before;
        Map<String, Object> right = after == null ? Map.of() : after;
        for (String key : unionKeys(left, right)) {
            if (SensitiveFieldFilter.isSensitiveName(key)) {
                continue;
            }
            Object b = left.get(key);
            Object a = right.get(key);
            if (Objects.equals(stringify(b), stringify(a))) {
                continue;
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("field", key);
            row.put("before", b);
            row.put("after", a);
            changes.add(row);
        }
        return changes;
    }

    private static List<String> unionKeys(Map<String, Object> a, Map<String, Object> b) {
        LinkedHashMap<String, Boolean> keys = new LinkedHashMap<>();
        a.keySet().forEach(k -> keys.put(k, Boolean.TRUE));
        b.keySet().forEach(k -> keys.put(k, Boolean.TRUE));
        return new ArrayList<>(keys.keySet());
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> toSanitizedMap(Object value) {
        if (value == null) {
            return null;
        }
        try {
            Object converted = objectMapper.convertValue(value, Map.class);
            Object sanitized = SensitiveFieldFilter.sanitize(converted);
            if (sanitized instanceof Map<?, ?> map) {
                return (Map<String, Object>) map;
            }
        } catch (Exception e) {
            log.debug("审计对象转 Map 失败: {}", e.getMessage());
        }
        Map<String, Object> fallback = new LinkedHashMap<>();
        fallback.put("value", String.valueOf(value));
        return fallback;
    }

    /**
     * 兼容误写：{@code #userService.getById(#id)} → {@code @userService.getById(#id)}。
     * {@code #} 是变量，服务 Bean 必须用 {@code @}。
     */
    static String normalizeBeanSpel(String expression) {
        if (expression == null || expression.isBlank()) {
            return expression;
        }
        return expression.replaceAll("#([A-Za-z][\\w]*Service)\\.", "@$1.");
    }

    private Object eval(String expression, String[] paramNames, Object[] args, Object result, Object target) {
        StandardEvaluationContext ctx = new StandardEvaluationContext();
        ctx.setBeanResolver(new BeanFactoryResolver(beanFactory));
        if (target != null) {
            // 同服务内 loadBefore 可写 getById(#id)，无需 #xxxService（那是变量且常为 null）
            ctx.setRootObject(target);
            ctx.setVariable("target", target);
        }
        if (paramNames != null) {
            for (int i = 0; i < paramNames.length && i < args.length; i++) {
                if (paramNames[i] != null) {
                    ctx.setVariable(paramNames[i], args[i]);
                }
            }
        }
        if (result != null) {
            ctx.setVariable("return", result);
        }
        return parser.parseExpression(expression).getValue(ctx);
    }

    private String[] resolveParamNames(Method method, MethodSignature signature) {
        String[] names = signature.getParameterNames();
        if (names != null && names.length > 0) {
            return names;
        }
        return nameDiscoverer.getParameterNames(method);
    }

    private static String resolveAction(AuditLog auditLog) {
        if (auditLog.action() == AuditAction.CUSTOM
                && auditLog.customAction() != null
                && !auditLog.customAction().isBlank()) {
            return auditLog.customAction().trim();
        }
        return auditLog.action().name();
    }

    private Operator resolveOperator(AuditLog auditLog, String[] paramNames, Object[] args, boolean success) {
        Operator fromCtx = resolveOperatorFromSecurity();
        if (fromCtx.username() != null || fromCtx.userId() != null) {
            return fromCtx;
        }
        if (auditLog.action() == AuditAction.LOGIN) {
            String username = extractUsernameFromRequestArg(args);
            return new Operator(null, username);
        }
        return new Operator(null, null);
    }

    /**
     * 登录成功后补充操作人：SecurityContext 尚无用户，从返回体 user 取 id/username。
     */
    private Operator enrichLoginOperator(Operator current, Object result) {
        if (current.userId() != null && current.username() != null) {
            return current;
        }
        if (result == null) {
            return current;
        }
        Object user = invokeObject(result, "getUser");
        if (user == null) {
            return current;
        }
        Long userId = current.userId() != null ? current.userId() : invokeLong(user, "getId");
        String username = current.username() != null ? current.username() : invokeString(user, "getUsername");
        return new Operator(userId, username);
    }

    private Operator resolveOperatorFromSecurity() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() != null
                && !(auth.getPrincipal() instanceof String)) {
            Object principal = auth.getPrincipal();
            Long userId = invokeLong(principal, "getUserId");
            String username = invokeString(principal, "getUsername");
            if (username != null || userId != null) {
                return new Operator(userId, username);
            }
        }
        return new Operator(null, null);
    }

    private static String extractUsernameFromRequestArg(Object[] args) {
        if (args == null) {
            return null;
        }
        for (Object arg : args) {
            if (arg == null) {
                continue;
            }
            String username = invokeString(arg, "getUsername");
            if (username != null && !username.isBlank()) {
                return username.trim();
            }
        }
        return null;
    }

    private static Object findRequestArg(Object[] args) {
        if (args == null) {
            return null;
        }
        for (Object arg : args) {
            if (arg == null) {
                continue;
            }
            String simple = arg.getClass().getSimpleName();
            if (simple.endsWith("Request") || simple.contains("Request")) {
                return arg;
            }
        }
        return firstNonNullArg(args);
    }

    private static Object firstNonNullArg(Object[] args) {
        if (args == null) {
            return null;
        }
        for (Object arg : args) {
            if (arg != null) {
                return arg;
            }
        }
        return null;
    }

    private static Object findArg(String[] paramNames, Object[] args, String... candidates) {
        if (paramNames == null || args == null) {
            return null;
        }
        for (String c : candidates) {
            for (int i = 0; i < paramNames.length && i < args.length; i++) {
                if (c.equals(paramNames[i])) {
                    Object v = args[i];
                    if (v != null && "request".equals(c)) {
                        String u = invokeString(v, "getUsername");
                        return u != null ? u : v;
                    }
                    return v;
                }
            }
        }
        return null;
    }

    private static String resolveClientIp() {
        try {
            ServletRequestAttributes attrs =
                    (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs == null) {
                return null;
            }
            HttpServletRequest request = attrs.getRequest();
            String xff = request.getHeader("X-Forwarded-For");
            if (xff != null && !xff.isBlank()) {
                return xff.split(",")[0].trim();
            }
            String realIp = request.getHeader("X-Real-IP");
            if (realIp != null && !realIp.isBlank()) {
                return realIp.trim();
            }
            return request.getRemoteAddr();
        } catch (Exception e) {
            return null;
        }
    }

    private static String summarizeError(Throwable error) {
        if (error == null) {
            return "FAIL";
        }
        String msg = error.getMessage();
        if (msg == null || msg.isBlank()) {
            return error.getClass().getSimpleName();
        }
        return msg.length() > 500 ? msg.substring(0, 500) : msg;
    }

    private static Long invokeLong(Object target, String method) {
        try {
            Object v = target.getClass().getMethod(method).invoke(target);
            if (v instanceof Number n) {
                return n.longValue();
            }
        } catch (Exception ignored) {
            // ignore
        }
        return null;
    }

    private static Object invokeObject(Object target, String method) {
        try {
            return target.getClass().getMethod(method).invoke(target);
        } catch (Exception ignored) {
            return null;
        }
    }

    private static String invokeString(Object target, String method) {
        try {
            Object v = target.getClass().getMethod(method).invoke(target);
            return v == null ? null : String.valueOf(v);
        } catch (Exception ignored) {
            return null;
        }
    }

    private static String stringify(Object v) {
        return v == null ? null : String.valueOf(v);
    }

    private static String blankToNull(String s) {
        return s == null || s.isBlank() ? null : s;
    }

    private record Operator(Long userId, String username) {
    }
}
