package com.lyj.dbc.sqlwork.api;

import com.lyj.dbc.sqlwork.api.dto.ExecuteCancelRequest;
import com.lyj.dbc.sqlwork.api.dto.ExecuteRequest;
import com.lyj.dbc.sqlwork.api.vo.ExecuteResult;
import com.lyj.dbc.sqlwork.common.ApiResponse;
import com.lyj.dbc.sqlwork.pipeline.SqlPipeline;
import com.lyj.dbc.sqlwork.runtime.jdbc.ExecuteCancelRegistry;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * SQL 执行 API。
 */
@RestController
public class ExecuteController {

    private final SqlPipeline sqlPipeline;
    private final ExecuteCancelRegistry cancelRegistry;

    public ExecuteController(SqlPipeline sqlPipeline, ExecuteCancelRegistry cancelRegistry) {
        this.sqlPipeline = sqlPipeline;
        this.cancelRegistry = cancelRegistry;
    }

    @PostMapping("/execute")
    public ApiResponse<ExecuteResult> execute(@Valid @RequestBody ExecuteRequest request) {
        return ApiResponse.ok(sqlPipeline.execute(request));
    }

    @PostMapping("/execute/cancel")
    public ApiResponse<Map<String, Object>> cancel(@Valid @RequestBody ExecuteCancelRequest request) {
        boolean cancelled = cancelRegistry.cancel(request.getCancelToken());
        return ApiResponse.ok(Map.of(
                "cancelled", cancelled,
                "cancelToken", request.getCancelToken()
        ));
    }
}
