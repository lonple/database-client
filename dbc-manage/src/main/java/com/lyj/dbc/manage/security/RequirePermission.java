package com.lyj.dbc.manage.security;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 接口功能权限校验。
 * 校验规则：拥有声明的权限码，或同功能的 operate（当声明为 view 时）即通过。
 */
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface RequirePermission {

    /**
     * 所需权限码，如 manage.instance.view。
     */
    String value();
}
