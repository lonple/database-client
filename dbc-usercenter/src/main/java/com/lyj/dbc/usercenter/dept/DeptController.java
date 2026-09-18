package com.lyj.dbc.usercenter.dept;

import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.dept.dto.DeptCreateRequest;
import com.lyj.dbc.usercenter.dept.dto.DeptUpdateRequest;
import com.lyj.dbc.usercenter.dept.vo.DeptTreeNodeVO;
import com.lyj.dbc.usercenter.dept.vo.DeptVO;
import com.lyj.dbc.usercenter.security.RequirePermission;
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
 * 部门管理接口。
 */
@Validated
@RestController
@RequestMapping("/depts")
public class DeptController {

    private final DeptService deptService;

    public DeptController(DeptService deptService) {
        this.deptService = deptService;
    }

    /**
     * 部门树。
     */
    @GetMapping("/tree")
    @RequirePermission("usercenter.dept.view")
    public ApiResponse<List<DeptTreeNodeVO>> tree() {
        return ApiResponse.ok(deptService.tree());
    }

    /**
     * 部门详情。
     */
    @GetMapping("/{id}")
    @RequirePermission("usercenter.dept.view")
    public ApiResponse<DeptVO> detail(@PathVariable @Min(1) Long id) {
        return ApiResponse.ok(deptService.getById(id));
    }

    /**
     * 新增子部门。
     */
    @PostMapping
    @RequirePermission("usercenter.dept.operate")
    public ApiResponse<DeptVO> create(@Valid @RequestBody DeptCreateRequest request) {
        return ApiResponse.ok(deptService.create(request));
    }

    /**
     * 更新部门（可整树迁移）。
     */
    @PutMapping("/{id}")
    @RequirePermission("usercenter.dept.operate")
    public ApiResponse<DeptVO> update(@PathVariable @Min(1) Long id,
                                      @Valid @RequestBody DeptUpdateRequest request) {
        return ApiResponse.ok(deptService.update(id, request));
    }

    /**
     * 删除部门。
     */
    @DeleteMapping("/{id}")
    @RequirePermission("usercenter.dept.operate")
    public ApiResponse<Void> delete(@PathVariable @Min(1) Long id) {
        deptService.delete(id);
        return ApiResponse.ok(null);
    }
}
