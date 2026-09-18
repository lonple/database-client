package com.lyj.dbc.sqlwork.api;

import com.lyj.dbc.sqlwork.api.dto.CreateSessionRequest;
import com.lyj.dbc.sqlwork.api.dto.UpdateSessionRequest;
import com.lyj.dbc.sqlwork.api.vo.SessionVO;
import com.lyj.dbc.sqlwork.common.ApiResponse;
import com.lyj.dbc.sqlwork.runtime.session.SqlSessionManager;
import com.lyj.dbc.sqlwork.runtime.session.WorkbenchSession;
import com.lyj.dbc.sqlwork.security.LoginUser;
import com.lyj.dbc.sqlwork.security.SecurityUtils;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 工作台会话：创建 / 心跳更新 / 关闭（事务中则 rollback 并释放租约）。
 */
@Validated
@RestController
@RequestMapping("/sessions")
public class SessionController {

    private final SqlSessionManager sessionManager;

    public SessionController(SqlSessionManager sessionManager) {
        this.sessionManager = sessionManager;
    }

    @PostMapping
    public ApiResponse<SessionVO> create(@Valid @RequestBody CreateSessionRequest request) {
        LoginUser user = SecurityUtils.requireUser();
        WorkbenchSession session = sessionManager.create(
                user.getUserId(),
                request.getWorkspaceId(),
                request.getConnectionId(),
                request.getDatabase(),
                request.getSchema(),
                Boolean.TRUE.equals(request.getManualMode()));
        return ApiResponse.ok(toVo(session));
    }

    @PutMapping("/{sessionId}")
    public ApiResponse<SessionVO> update(@PathVariable @NotBlank String sessionId,
                                         @RequestBody UpdateSessionRequest request) {
        LoginUser user = SecurityUtils.requireUser();
        WorkbenchSession session = sessionManager.update(
                sessionId,
                user.getUserId(),
                request.getConnectionId(),
                request.getDatabase(),
                request.getSchema(),
                request.getManualMode());
        return ApiResponse.ok(toVo(session));
    }

    @PostMapping("/{sessionId}/heartbeat")
    public ApiResponse<SessionVO> heartbeat(@PathVariable @NotBlank String sessionId) {
        LoginUser user = SecurityUtils.requireUser();
        return ApiResponse.ok(toVo(sessionManager.heartbeat(sessionId, user.getUserId())));
    }

    @DeleteMapping("/{sessionId}")
    public ApiResponse<Void> close(@PathVariable @NotBlank String sessionId) {
        LoginUser user = SecurityUtils.requireUser();
        sessionManager.close(sessionId, user.getUserId());
        return ApiResponse.ok(null);
    }

    private static SessionVO toVo(WorkbenchSession session) {
        return SessionVO.builder()
                .sessionId(session.getSessionId())
                .workspaceId(session.getWorkspaceId())
                .connectionId(session.getConnectionId())
                .database(session.getDatabase())
                .schema(session.getSchema())
                .manualMode(session.isManualMode())
                .inTransaction(session.inTransaction())
                .build();
    }
}
