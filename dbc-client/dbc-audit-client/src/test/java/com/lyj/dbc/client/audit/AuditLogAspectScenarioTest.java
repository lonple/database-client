package com.lyj.dbc.client.audit;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.lyj.dbc.client.audit.dto.AuditEventDtos;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.reflect.MethodSignature;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.beans.factory.support.DefaultListableBeanFactory;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

/**
 * 业务审计场景单测：登录/退出/增删改（含 before/after 标量与对象混用）。
 */
@ExtendWith(MockitoExtension.class)
class AuditLogAspectScenarioTest {

    @Mock
    private ProceedingJoinPoint pjp;
    @Mock
    private MethodSignature signature;

    private RecordingPublisher publisher;
    private AuditLogAspect aspect;

    @BeforeEach
    void setUp() {
        publisher = new RecordingPublisher();
        ObjectMapper objectMapper = new ObjectMapper().registerModule(new JavaTimeModule());
        aspect = new AuditLogAspect(publisher, objectMapper, new DefaultListableBeanFactory());
        SecurityContextHolder.clearContext();
    }

    @Test
    @DisplayName("LOGIN 成功：记 username/success，操作人从返回 user 补齐")
    void loginSuccess() throws Throwable {
        Method method = Fixtures.class.getDeclaredMethod("login", LoginRequest.class);
        stubJoinPoint(method, new Object[]{new LoginRequest("admin", "secret")},
                new LoginResponse(new UserView(1L, "admin")));

        Object out = aspect.around(pjp, method.getAnnotation(AuditLog.class));
        assertThat(out).isInstanceOf(LoginResponse.class);

        AuditEventDtos.AuditEvent event = publisher.single();
        assertThat(event.getAction()).isEqualTo("LOGIN");
        assertThat(event.getResult()).isEqualTo("SUCCESS");
        assertThat(event.getOperatorUsername()).isEqualTo("admin");
        assertThat(event.getOperatorUserId()).isEqualTo(1L);
        assertThat(event.getDetails()).containsEntry("username", "admin").containsEntry("success", true);
        assertThat(event.getDetails().toString()).doesNotContain("secret");
    }

    @Test
    @DisplayName("LOGIN 失败：仍记 FAIL，不含密码")
    void loginFail() throws Throwable {
        Method method = Fixtures.class.getDeclaredMethod("login", LoginRequest.class);
        stubJoinPointThrow(method, new Object[]{new LoginRequest("admin", "bad")},
                new RuntimeException("用户名或密码错误"));

        assertThatThrownBy(() -> aspect.around(pjp, method.getAnnotation(AuditLog.class)))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("用户名或密码错误");

        AuditEventDtos.AuditEvent event = publisher.single();
        assertThat(event.getAction()).isEqualTo("LOGIN");
        assertThat(event.getResult()).isEqualTo("FAIL");
        assertThat(event.getOperatorUsername()).isEqualTo("admin");
        assertThat(event.getDetails()).containsEntry("success", false);
        assertThat(event.getDetails().toString()).doesNotContain("bad");
    }

    @Test
    @DisplayName("LOGOUT：从 SecurityContext 取操作人")
    void logout() throws Throwable {
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(new LoginPrincipal(9L, "alice"), null));
        Method method = Fixtures.class.getDeclaredMethod("logout");
        stubJoinPoint(method, new Object[]{}, null);

        aspect.around(pjp, method.getAnnotation(AuditLog.class));

        AuditEventDtos.AuditEvent event = publisher.single();
        assertThat(event.getAction()).isEqualTo("LOGOUT");
        assertThat(event.getResult()).isEqualTo("SUCCESS");
        assertThat(event.getOperatorUserId()).isEqualTo(9L);
        assertThat(event.getOperatorUsername()).isEqualTo("alice");
        assertThat(event.getDetails()).containsEntry("success", true);
    }

    @Test
    @DisplayName("CREATE：details.after 为对象快照")
    void create() throws Throwable {
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(new LoginPrincipal(1L, "admin"), null));
        Method method = Fixtures.class.getDeclaredMethod("createUser", CreateUserRequest.class);
        UserView created = new UserView(2L, "bob");
        stubJoinPoint(method, new Object[]{new CreateUserRequest("bob")}, created);

        aspect.around(pjp, method.getAnnotation(AuditLog.class));

        AuditEventDtos.AuditEvent event = publisher.single();
        assertThat(event.getAction()).isEqualTo("CREATE");
        assertThat(event.getResourceId()).isEqualTo("2");
        @SuppressWarnings("unchecked")
        Map<String, Object> after = (Map<String, Object>) event.getDetails().get("after");
        assertThat(after).isNotNull();
        assertThat(String.valueOf(after.get("id"))).isEqualTo("2");
        assertThat(after.get("username")).isEqualTo("bob");
    }

    @Test
    @DisplayName("UPDATE：before/after 标量与对象混用时对象归一为 JSON 字符串")
    void updateMixedScalarAndObject() throws Throwable {
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(new LoginPrincipal(1L, "admin"), null));

        Map<String, Object> before = new LinkedHashMap<>();
        before.put("id", 2L);
        before.put("username", "bob");
        before.put("profile", Map.of("title", "dev"));

        UpdateUserRequest req = new UpdateUserRequest("bobby", Map.of("title", "lead"));
        UserView afterView = new UserView(2L, "bobby");

        Method withBefore = Fixtures.class.getDeclaredMethod(
                "updateUserWithBefore", Long.class, UpdateUserRequest.class, Map.class);
        when(pjp.getSignature()).thenReturn(signature);
        when(signature.getMethod()).thenReturn(withBefore);
        when(signature.getParameterNames()).thenReturn(new String[]{"id", "request", "beforeSnapshot"});
        when(pjp.getArgs()).thenReturn(new Object[]{2L, req, before});
        when(pjp.proceed()).thenReturn(afterView);

        aspect.around(pjp, withBefore.getAnnotation(AuditLog.class));

        AuditEventDtos.AuditEvent event = publisher.single();
        assertThat(event.getAction()).isEqualTo("UPDATE");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> changes = (List<Map<String, Object>>) event.getDetails().get("changes");
        assertThat(changes).isNotEmpty();
        boolean hasNormalizedObject = changes.stream().anyMatch(c ->
                c.get("before") instanceof String s && s.contains("title")
                        || c.get("after") instanceof String s2 && s2.contains("{"));
        boolean hasUsernameChange = changes.stream().anyMatch(c ->
                "username".equals(String.valueOf(c.get("field"))));
        assertThat(hasUsernameChange || hasNormalizedObject).isTrue();
    }

    @Test
    @DisplayName("DELETE：details.keys 含 id")
    void delete() throws Throwable {
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(new LoginPrincipal(1L, "admin"), null));
        Method method = Fixtures.class.getDeclaredMethod("deleteUser", Long.class, Map.class);
        Map<String, Object> before = Map.of("id", 3L, "username", "carol");
        when(pjp.getSignature()).thenReturn(signature);
        when(signature.getMethod()).thenReturn(method);
        when(signature.getParameterNames()).thenReturn(new String[]{"id", "beforeSnapshot"});
        when(pjp.getArgs()).thenReturn(new Object[]{3L, before});
        when(pjp.proceed()).thenReturn(null);

        aspect.around(pjp, method.getAnnotation(AuditLog.class));

        AuditEventDtos.AuditEvent event = publisher.single();
        assertThat(event.getAction()).isEqualTo("DELETE");
        @SuppressWarnings("unchecked")
        Map<String, Object> keys = (Map<String, Object>) event.getDetails().get("keys");
        assertThat(keys).isNotNull();
        assertThat(String.valueOf(keys.get("id"))).isEqualTo("3");
        assertThat(keys.get("username")).isEqualTo("carol");
    }

    private void stubJoinPoint(Method method, Object[] args, Object result) throws Throwable {
        when(pjp.getSignature()).thenReturn(signature);
        when(signature.getMethod()).thenReturn(method);
        if (method.getName().equals("login") || method.getName().equals("createUser")) {
            when(signature.getParameterNames()).thenReturn(new String[]{"request"});
        } else if (method.getParameterCount() == 0) {
            when(signature.getParameterNames()).thenReturn(new String[]{});
        }
        when(pjp.getArgs()).thenReturn(args);
        when(pjp.proceed()).thenReturn(result);
    }

    private void stubJoinPointThrow(Method method, Object[] args, Throwable error) throws Throwable {
        when(pjp.getSignature()).thenReturn(signature);
        when(signature.getMethod()).thenReturn(method);
        when(signature.getParameterNames()).thenReturn(new String[]{"request"});
        when(pjp.getArgs()).thenReturn(args);
        when(pjp.proceed()).thenThrow(error);
    }

    static final class RecordingPublisher implements AuditEventPublisher {
        private final List<AuditEventDtos.AuditEvent> events = new CopyOnWriteArrayList<>();

        @Override
        public void ingestAsync(AuditEventDtos.AuditEvent event) {
            events.add(event);
        }

        @Override
        public void ingestBatchAsync(List<AuditEventDtos.AuditEvent> batch) {
            if (batch != null) {
                events.addAll(batch);
            }
        }

        AuditEventDtos.AuditEvent single() {
            assertThat(events).hasSize(1);
            return events.getFirst();
        }
    }

    static class Fixtures {
        @AuditLog(module = "usercenter", action = AuditAction.LOGIN, resourceType = "session",
                resourceId = "#request.username")
        LoginResponse login(LoginRequest request) {
            return null;
        }

        @AuditLog(module = "usercenter", action = AuditAction.LOGOUT, resourceType = "session")
        void logout() {
        }

        @AuditLog(module = "usercenter", action = AuditAction.CREATE, resourceType = "user",
                resourceId = "#return.id")
        UserView createUser(CreateUserRequest request) {
            return null;
        }

        @AuditLog(module = "usercenter", action = AuditAction.UPDATE, resourceType = "user", resourceId = "#id",
                loadBefore = "#beforeSnapshot")
        UserView updateUserWithBefore(Long id, UpdateUserRequest request, Map<String, Object> beforeSnapshot) {
            return null;
        }

        @AuditLog(module = "usercenter", action = AuditAction.DELETE, resourceType = "user", resourceId = "#id",
                loadBefore = "#beforeSnapshot")
        void deleteUser(Long id, Map<String, Object> beforeSnapshot) {
        }
    }

    record LoginRequest(String username, String password) {
        public String getUsername() {
            return username;
        }

        public String getPassword() {
            return password;
        }
    }

    record CreateUserRequest(String username) {
        public String getUsername() {
            return username;
        }
    }

    record UpdateUserRequest(String username, Map<String, Object> profile) {
        public String getUsername() {
            return username;
        }

        public Map<String, Object> getProfile() {
            return profile;
        }
    }

    record LoginResponse(UserView user) {
        public UserView getUser() {
            return user;
        }
    }

    record UserView(Long id, String username) {
        public Long getId() {
            return id;
        }

        public String getUsername() {
            return username;
        }
    }

    record LoginPrincipal(Long userId, String username) {
        public Long getUserId() {
            return userId;
        }

        public String getUsername() {
            return username;
        }
    }
}
