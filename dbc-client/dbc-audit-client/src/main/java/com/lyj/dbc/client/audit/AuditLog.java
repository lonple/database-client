package com.lyj.dbc.client.audit;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 标记业务方法写入审计（异步 HTTP，不阻断主流程）。
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface AuditLog {

    /** 模块，如 usercenter / manage */
    String module();

    /** 动作 */
    AuditAction action();

    /** 资源类型，如 user / instance */
    String resourceType() default "";

    /** 资源主键 SpEL，如 {@code #id}、{@code #return.id}、{@code #request.username} */
    String resourceId() default "";

    /**
     * UPDATE/DELETE 取旧值 SpEL。
     * <ul>
     *   <li>同服务方法：{@code getById(#id)}（切面将当前 bean 设为 root）</li>
     *   <li>其它 Spring Bean：{@code @roleService.getById(#roleId)}（注意是 {@code @} 不是 {@code #}）</li>
     * </ul>
     * 失败仅打 warn，不阻断业务。
     */
    String loadBefore() default "";

    /** CUSTOM 时的动作名覆盖 */
    String customAction() default "";
}
