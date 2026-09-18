package com.lyj.dbc.usercenter.config;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.usercenter.role.entity.RoleEntity;
import com.lyj.dbc.usercenter.role.mapper.RoleMapper;
import com.lyj.dbc.usercenter.user.entity.UserEntity;
import com.lyj.dbc.usercenter.user.entity.UserRoleEntity;
import com.lyj.dbc.usercenter.user.mapper.UserMapper;
import com.lyj.dbc.usercenter.user.mapper.UserRoleMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;

/**
 * 启动时幂等写入内置 admin 账号。
 */
@Component
public class AdminUserInitializer implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(AdminUserInitializer.class);

    private final UserMapper userMapper;
    private final RoleMapper roleMapper;
    private final UserRoleMapper userRoleMapper;
    private final PasswordEncoder passwordEncoder;

    public AdminUserInitializer(UserMapper userMapper, RoleMapper roleMapper,
                                UserRoleMapper userRoleMapper, PasswordEncoder passwordEncoder) {
        this.userMapper = userMapper;
        this.roleMapper = roleMapper;
        this.userRoleMapper = userRoleMapper;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    public void run(ApplicationArguments args) {
        RoleEntity superAdmin = roleMapper.selectOne(new LambdaQueryWrapper<RoleEntity>()
                .eq(RoleEntity::getCode, "SUPER_ADMIN"));
        if (superAdmin == null) {
            log.warn("SUPER_ADMIN role missing, skip admin seed");
            return;
        }
        OffsetDateTime now = OffsetDateTime.now();
        UserEntity admin = userMapper.selectOne(new LambdaQueryWrapper<UserEntity>()
                .eq(UserEntity::getUsername, "admin"));
        if (admin == null) {
            admin = new UserEntity();
            admin.setUsername("admin");
            admin.setPasswordHash(passwordEncoder.encode("admin"));
            admin.setDescription("内置账号");
            admin.setStatus(1);
            admin.setBuiltin(1);
            admin.setDeleted(0);
            admin.setCreatedAt(now);
            admin.setUpdatedAt(now);
            userMapper.insert(admin);
            log.info("Seeded builtin admin user");
        }

        Long linked = userRoleMapper.selectCount(new LambdaQueryWrapper<UserRoleEntity>()
                .eq(UserRoleEntity::getUserId, admin.getId())
                .eq(UserRoleEntity::getRoleId, superAdmin.getId()));
        if (linked == null || linked == 0) {
            UserRoleEntity link = new UserRoleEntity();
            link.setUserId(admin.getId());
            link.setRoleId(superAdmin.getId());
            link.setCreatedAt(now);
            userRoleMapper.insert(link);
            log.info("Bound SUPER_ADMIN role to admin user");
        }
    }
}
