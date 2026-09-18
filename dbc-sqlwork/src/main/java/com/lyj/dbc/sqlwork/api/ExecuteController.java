package com.lyj.dbc.sqlwork.api;

import com.lyj.dbc.sqlwork.api.dto.ExecuteRequest;
import com.lyj.dbc.sqlwork.api.vo.ExecuteResult;
import com.lyj.dbc.sqlwork.common.ApiResponse;
import com.lyj.dbc.sqlwork.pipeline.SqlPipeline;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * SQL 执行 API。
 */
@RestController
public class ExecuteController {

    private final SqlPipeline sqlPipeline;

    public ExecuteController(SqlPipeline sqlPipeline) {
        this.sqlPipeline = sqlPipeline;
    }

    @PostMapping("/execute")
    public ApiResponse<ExecuteResult> execute(@Valid @RequestBody ExecuteRequest request) {
        return ApiResponse.ok(sqlPipeline.execute(request));
    }
}
