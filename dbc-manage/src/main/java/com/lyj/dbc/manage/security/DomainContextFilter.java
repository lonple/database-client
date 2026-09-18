package com.lyj.dbc.manage.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * 解析 {@code X-Dbc-Domain}，写入 {@link DomainContext}。
 */
@Component
@Order
public class DomainContextFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        try {
            DomainContext.set(request.getHeader(DomainCodes.HEADER));
            filterChain.doFilter(request, response);
        } finally {
            DomainContext.clear();
        }
    }
}
