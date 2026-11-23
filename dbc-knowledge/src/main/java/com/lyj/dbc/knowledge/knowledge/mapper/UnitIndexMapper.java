package com.lyj.dbc.knowledge.knowledge.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.lyj.dbc.knowledge.knowledge.domain.UnitIndex;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface UnitIndexMapper extends BaseMapper<UnitIndex> {

    @Delete("""
            DELETE FROM t_knowledge_unit_index
            WHERE document_id = #{documentId}
               OR (kind = 'DOCUMENT' AND ref_id = #{documentId})
            """)
    int deleteByDocumentId(@Param("documentId") Long documentId);

    @Delete("""
            DELETE FROM t_knowledge_unit_index
            WHERE kind = #{kind} AND ref_id = #{refId}
            """)
    int deleteByKindAndRef(@Param("kind") String kind, @Param("refId") Long refId);
}
