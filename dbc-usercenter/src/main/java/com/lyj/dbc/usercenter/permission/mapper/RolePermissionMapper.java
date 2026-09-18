package com.lyj.dbc.usercenter.permission.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.lyj.dbc.usercenter.permission.entity.RolePermissionEntity;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;

/**
 * 角色-权限 Mapper。
 */
@Mapper
public interface RolePermissionMapper extends BaseMapper<RolePermissionEntity> {

    /**
     * 幂等插入：并发注册 / 种子重叠时忽略已存在绑定。
     */
    @Insert("""
            INSERT INTO t_usercenter_role_permission (role_id, permission_id, created_at)
            VALUES (#{roleId}, #{permissionId}, #{createdAt})
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """)
    int insertIgnore(RolePermissionEntity row);
}
