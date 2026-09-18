package com.lyj.dbc.manage.asset.dept;

import com.lyj.dbc.client.usercenter.dto.DeptTreeNode;
import com.lyj.dbc.manage.common.ApiResponse;
import com.lyj.dbc.manage.common.BizException;
import com.lyj.dbc.manage.security.PermissionCodes;
import com.lyj.dbc.manage.security.SecurityUtils;
import com.lyj.dbc.manage.security.UserContextHolder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Set;

/**
 * 资产管理侧部门树：前端调 manage，manage 再调 usercenter inner。
 * <p>
 * 具备实例或连接查看权限即可；不要求 usercenter.dept.view。
 */
@RestController
@RequestMapping("/depts")
public class DeptFacadeController {

    private final DeptFacadeService deptFacadeService;

    public DeptFacadeController(DeptFacadeService deptFacadeService) {
        this.deptFacadeService = deptFacadeService;
    }

    @GetMapping("/tree")
    public ApiResponse<List<DeptTreeNode>> tree() {
        SecurityUtils.requireUser();
        Set<String> owned = UserContextHolder.permissionCodes();
        boolean ok = PermissionCodes.implies(owned, "manage.instance.view")
                || PermissionCodes.implies(owned, "manage.connection.view");
        if (!ok) {
            throw BizException.forbidden("无权限（需要 manage.instance.view 或 manage.connection.view）");
        }
        return ApiResponse.ok(deptFacadeService.treeForCurrentUser());
    }
}
