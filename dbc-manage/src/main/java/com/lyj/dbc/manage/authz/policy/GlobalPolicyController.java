package com.lyj.dbc.manage.authz.policy;

import com.lyj.dbc.manage.authz.policy.dto.GlobalPolicyRequests;
import com.lyj.dbc.manage.authz.policy.vo.GlobalPolicyVO;
import com.lyj.dbc.manage.common.ApiResponse;
import com.lyj.dbc.manage.security.RequirePermission;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 全局管控策略 API。
 */
@Validated
@RestController
@RequestMapping("/auth/global-policies")
public class GlobalPolicyController {

    private final GlobalPolicyService globalPolicyService;

    public GlobalPolicyController(GlobalPolicyService globalPolicyService) {
        this.globalPolicyService = globalPolicyService;
    }

    @RequirePermission("auth.global.policy.view")
    @GetMapping
    public ApiResponse<List<GlobalPolicyVO>> list() {
        return ApiResponse.ok(globalPolicyService.listAll());
    }

    @RequirePermission("auth.global.policy.view")
    @GetMapping("/{id}")
    public ApiResponse<GlobalPolicyVO> detail(@PathVariable @Min(1) Long id) {
        return ApiResponse.ok(globalPolicyService.get(id));
    }

    @RequirePermission("auth.global.policy.operate")
    @PostMapping
    public ApiResponse<GlobalPolicyVO> create(@Valid @RequestBody GlobalPolicyRequests.SaveRequest request) {
        return ApiResponse.ok(globalPolicyService.create(request));
    }

    @RequirePermission("auth.global.policy.operate")
    @PutMapping("/{id}")
    public ApiResponse<GlobalPolicyVO> update(@PathVariable @Min(1) Long id,
                                              @Valid @RequestBody GlobalPolicyRequests.SaveRequest request) {
        return ApiResponse.ok(globalPolicyService.update(id, request));
    }

    @RequirePermission("auth.global.policy.operate")
    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable @Min(1) Long id) {
        globalPolicyService.delete(id);
        return ApiResponse.ok(null);
    }
}
