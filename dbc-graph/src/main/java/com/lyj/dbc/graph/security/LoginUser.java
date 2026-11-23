package com.lyj.dbc.graph.security;

import lombok.AllArgsConstructor;
import lombok.Data;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

@Data
@AllArgsConstructor
public class LoginUser {
    private Long userId;
    private String username;
    private List<String> roleCodes;

    public static LoginUser of(Long userId, String username, String roleCodesCsv) {
        List<String> roles = roleCodesCsv == null || roleCodesCsv.isBlank()
                ? Collections.emptyList()
                : Arrays.stream(roleCodesCsv.split(",")).map(String::trim).filter(s -> !s.isEmpty()).toList();
        return new LoginUser(userId, username, roles);
    }
}
