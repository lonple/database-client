package com.lyj.dbc.graph.seed;

import com.lyj.dbc.graph.common.api.ApiResponse;
import com.lyj.dbc.graph.graphmeta.entity.GraphEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/seed")
public class SeedController {
    private final CompanyTableRelationsSeed companyTableRelationsSeed;

    public SeedController(CompanyTableRelationsSeed companyTableRelationsSeed) {
        this.companyTableRelationsSeed = companyTableRelationsSeed;
    }

    /** demo-company 表外键双向边图谱（父列 / 子列作 relType），编码 default。 */
    @PostMapping("/company-table-relations")
    public ApiResponse<GraphEntity> seedCompanyTables(@RequestParam(defaultValue = "false") boolean force) {
        return ApiResponse.ok(companyTableRelationsSeed.ensureSeeded(force));
    }
}
