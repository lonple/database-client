package com.lyj.dbc.usercenter.security;

import com.lyj.dbc.usercenter.config.AuthProperties;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseCookie;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Arrays;
import java.util.Optional;
import java.util.UUID;

/**
 * refresh / csrf Cookie 读写。
 */
@Service
public class AuthCookieService {

    public static final String CSRF_HEADER = "X-Dbc-CSRF";

    private final AuthProperties authProperties;

    public AuthCookieService(AuthProperties authProperties) {
        this.authProperties = authProperties;
    }

    public void writeSessionCookies(HttpServletResponse response, String refreshToken, String csrfToken,
                                    Duration refreshMaxAge) {
        AuthProperties.Cookie c = authProperties.getCookie();
        response.addHeader(HttpHeaders.SET_COOKIE, ResponseCookie.from(c.getRefreshName(), refreshToken)
                .httpOnly(true)
                .secure(c.isSecure())
                .sameSite(c.getSameSite())
                .path(c.getRefreshPath())
                .maxAge(refreshMaxAge)
                .build()
                .toString());
        response.addHeader(HttpHeaders.SET_COOKIE, ResponseCookie.from(c.getCsrfName(), csrfToken)
                .httpOnly(false)
                .secure(c.isSecure())
                .sameSite(c.getSameSite())
                .path(c.getCsrfPath())
                .maxAge(refreshMaxAge)
                .build()
                .toString());
    }

    public void clearSessionCookies(HttpServletResponse response) {
        AuthProperties.Cookie c = authProperties.getCookie();
        response.addHeader(HttpHeaders.SET_COOKIE, ResponseCookie.from(c.getRefreshName(), "")
                .httpOnly(true)
                .secure(c.isSecure())
                .sameSite(c.getSameSite())
                .path(c.getRefreshPath())
                .maxAge(Duration.ZERO)
                .build()
                .toString());
        response.addHeader(HttpHeaders.SET_COOKIE, ResponseCookie.from(c.getCsrfName(), "")
                .httpOnly(false)
                .secure(c.isSecure())
                .sameSite(c.getSameSite())
                .path(c.getCsrfPath())
                .maxAge(Duration.ZERO)
                .build()
                .toString());
    }

    public Optional<String> readCookie(HttpServletRequest request, String name) {
        Cookie[] cookies = request.getCookies();
        if (cookies == null) {
            return Optional.empty();
        }
        return Arrays.stream(cookies)
                .filter(cookie -> name.equals(cookie.getName()))
                .map(Cookie::getValue)
                .filter(v -> v != null && !v.isBlank())
                .findFirst();
    }

    public Optional<String> readRefresh(HttpServletRequest request) {
        return readCookie(request, authProperties.getCookie().getRefreshName());
    }

    public Optional<String> readCsrf(HttpServletRequest request) {
        return readCookie(request, authProperties.getCookie().getCsrfName());
    }

    public String newCsrfToken() {
        return UUID.randomUUID().toString().replace("-", "");
    }
}
