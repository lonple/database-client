package com.lyj.dbc.usercenter.auth;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.usercenter.auth.vo.DataScopeVO;
import com.lyj.dbc.usercenter.dept.DeptService;
import com.lyj.dbc.usercenter.dept.entity.DeptEntity;
import com.lyj.dbc.usercenter.dept.mapper.DeptMapper;
import com.lyj.dbc.usercenter.role.DataScopeType;
import com.lyj.dbc.usercenter.role.RoleService;
import com.lyj.dbc.usercenter.role.entity.RoleEntity;
import com.lyj.dbc.usercenter.user.entity.UserEntity;
import com.lyj.dbc.usercenter.user.entity.UserRoleEntity;
import com.lyj.dbc.usercenter.user.mapper.UserMapper;
import com.lyj.dbc.usercenter.user.mapper.UserRoleMapper;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * 按用户角色并集解析数据范围。
 */
@Service
public class DataScopeService {

    private final UserMapper userMapper;
    private final UserRoleMapper userRoleMapper;
    private final RoleService roleService;
    private final DeptMapper deptMapper;
    private final DeptService deptService;

    public DataScopeService(UserMapper userMapper, UserRoleMapper userRoleMapper,
                            RoleService roleService, DeptMapper deptMapper, DeptService deptService) {
        this.userMapper = userMapper;
        this.userRoleMapper = userRoleMapper;
        this.roleService = roleService;
        this.deptMapper = deptMapper;
        this.deptService = deptService;
    }

    /**
     * 解析指定用户的数据权限。
     */
    public DataScopeVO resolve(Long userId) {
        UserEntity user = userMapper.selectById(userId);
        if (user == null) {
            return DataScopeVO.builder().all(false).deptIds(List.of()).build();
        }
        List<Long> roleIds = userRoleMapper.selectList(new LambdaQueryWrapper<UserRoleEntity>()
                        .eq(UserRoleEntity::getUserId, userId))
                .stream()
                .map(UserRoleEntity::getRoleId)
                .toList();
        List<RoleEntity> roles = roleService.listByIds(roleIds);

        Long deptId = user.getDeptId();
        String deptPath = null;
        if (deptId != null) {
            DeptEntity dept = deptMapper.selectById(deptId);
            if (dept != null) {
                deptPath = dept.getPath();
            }
        }

        Set<Long> visible = new LinkedHashSet<>();
        boolean all = false;
        for (RoleEntity role : roles) {
            DataScopeType scope;
            try {
                scope = DataScopeType.valueOf(role.getDataScope());
            } catch (Exception ex) {
                scope = DataScopeType.DEPT_AND_CHILDREN;
            }
            switch (scope) {
                case ALL -> all = true;
                case DEPT_ONLY -> {
                    if (deptId != null) {
                        visible.add(deptId);
                    }
                }
                case DEPT_AND_CHILDREN -> {
                    if (deptId != null) {
                        visible.addAll(deptService.listSelfAndDescendantIds(deptId));
                    }
                }
                case CUSTOM -> visible.addAll(roleService.listCustomDeptIds(role.getId()));
                default -> {
                }
            }
        }
        if (all) {
            return DataScopeVO.builder()
                    .all(true)
                    .deptIds(List.of())
                    .deptId(deptId)
                    .deptPath(deptPath)
                    .build();
        }
        return DataScopeVO.builder()
                .all(false)
                .deptIds(new ArrayList<>(visible))
                .deptId(deptId)
                .deptPath(deptPath)
                .build();
    }
}
