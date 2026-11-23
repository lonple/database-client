package com.lyj.dbc.knowledge.common.controller;

import com.lyj.dbc.knowledge.common.api.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class HealthController {
    @GetMapping({"/health", "/api/health"})
    public ApiResponse<Map<String, Object>> health() {
        return ApiResponse.ok(Map.of("service", "dbc-knowledge", "status", "UP"));
    }
}
