package com.lyj.dbc.usercenter.dept;

import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.dept.vo.DeptTreeNodeVO;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 部门 inner API：供其它微服务经 mTLS 调用，不做终端用户功能权限判定。
 */
@RestController
@RequestMapping("/inner/depts")
public class InnerDeptController {

    private final DeptService deptService;

    public InnerDeptController(DeptService deptService) {
        this.deptService = deptService;
    }

    @GetMapping("/tree")
    public ApiResponse<List<DeptTreeNodeVO>> tree() {
        return ApiResponse.ok(deptService.tree());
    }
}
