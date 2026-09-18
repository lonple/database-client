package com.lyj.dbc.manage.authz.policy;

import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 二次鉴权 ticket：30s 有效，绑定 userId + sessionId。
 */
@Service
public class ReauthTicketService {

    private static final long TTL_SECONDS = 30L;

    private final ConcurrentHashMap<String, Ticket> tickets = new ConcurrentHashMap<>();

    public String issue(Long userId, String sessionId) {
        if (userId == null || !StringUtils.hasText(sessionId)) {
            throw new IllegalArgumentException("userId/sessionId 不能为空");
        }
        purgeExpired();
        String token = UUID.randomUUID().toString().replace("-", "");
        tickets.put(token, new Ticket(userId, sessionId.trim(), Instant.now().plusSeconds(TTL_SECONDS)));
        return token;
    }

    public boolean verify(Long userId, String sessionId, String ticket) {
        if (userId == null || !StringUtils.hasText(sessionId) || !StringUtils.hasText(ticket)) {
            return false;
        }
        purgeExpired();
        Ticket t = tickets.get(ticket.trim());
        if (t == null) {
            return false;
        }
        if (t.expireAt().isBefore(Instant.now())) {
            tickets.remove(ticket.trim());
            return false;
        }
        return userId.equals(t.userId()) && sessionId.trim().equals(t.sessionId());
    }

    private void purgeExpired() {
        Instant now = Instant.now();
        for (Map.Entry<String, Ticket> e : tickets.entrySet()) {
            if (e.getValue().expireAt().isBefore(now)) {
                tickets.remove(e.getKey(), e.getValue());
            }
        }
    }

    private record Ticket(Long userId, String sessionId, Instant expireAt) {
    }
}
