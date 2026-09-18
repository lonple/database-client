package com.lyj.dbc.manage.authz.policy.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.lyj.dbc.manage.authz.policy.entity.GlobalPolicyEntity;
import org.apache.ibatis.annotations.Mapper;

/**
 * 全局管控策略 Mapper。
 */
@Mapper
public interface GlobalPolicyMapper extends BaseMapper<GlobalPolicyEntity> {
}
