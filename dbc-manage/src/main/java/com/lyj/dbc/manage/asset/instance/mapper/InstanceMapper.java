package com.lyj.dbc.manage.asset.instance.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.lyj.dbc.manage.asset.instance.entity.InstanceEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface InstanceMapper extends BaseMapper<InstanceEntity> {

    /**
     * 公司域：数据范围内且 owner_scope=COMPANY 的实例。
     */
    @Select("""
            <script>
            SELECT i.*
            FROM t_manage_instance i
            WHERE i.deleted = 0
              AND i.owner_scope = 'COMPANY'
            <if test="allScope == false">
              AND i.dept_id IN
              <foreach collection="deptIds" item="d" open="(" separator="," close=")">#{d}</foreach>
            </if>
            ORDER BY i.id DESC
            </script>
            """)
    List<InstanceEntity> selectVisibleCompany(@Param("allScope") boolean allScope,
                                              @Param("deptIds") List<Long> deptIds);

    /**
     * 个人域：当前用户个人实例。
     */
    @Select("""
            SELECT i.*
            FROM t_manage_instance i
            WHERE i.deleted = 0
              AND i.owner_scope = 'PERSONAL'
              AND i.owner_user_id = #{ownerUserId}
            ORDER BY i.id DESC
            """)
    List<InstanceEntity> selectVisiblePersonal(@Param("ownerUserId") Long ownerUserId);

    /**
     * 公司域可选实例：数据范围内归属且启用。
     */
    @Select("""
            <script>
            SELECT i.*
            FROM t_manage_instance i
            WHERE i.deleted = 0 AND i.status = 1
              AND i.owner_scope = 'COMPANY'
            <if test="dbType != null and dbType != ''">
              AND i.db_type = #{dbType}
            </if>
            <if test="allScope == false">
              AND i.dept_id IN
              <foreach collection="deptIds" item="d" open="(" separator="," close=")">#{d}</foreach>
            </if>
            ORDER BY i.name ASC
            </script>
            """)
    List<InstanceEntity> selectSelectableCompany(@Param("allScope") boolean allScope,
                                                 @Param("deptIds") List<Long> deptIds,
                                                 @Param("dbType") String dbType);

    /**
     * 个人域可选实例。
     */
    @Select("""
            <script>
            SELECT i.*
            FROM t_manage_instance i
            WHERE i.deleted = 0 AND i.status = 1
              AND i.owner_scope = 'PERSONAL'
              AND i.owner_user_id = #{ownerUserId}
            <if test="dbType != null and dbType != ''">
              AND i.db_type = #{dbType}
            </if>
            ORDER BY i.name ASC
            </script>
            """)
    List<InstanceEntity> selectSelectablePersonal(@Param("ownerUserId") Long ownerUserId,
                                                  @Param("dbType") String dbType);
}
