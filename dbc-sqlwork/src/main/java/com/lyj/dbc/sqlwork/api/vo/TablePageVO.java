package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 表分页结果。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TablePageVO {

    private List<TableItemVO> items;
    private long total;
    private int page;
    private int size;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TableItemVO {
        private String schema;
        private String name;
        private String objectType;
        /** 表注释 / 中文说明，可能为空 */
        private String comment;

        public TableItemVO(String schema, String name, String objectType) {
            this(schema, name, objectType, null);
        }
    }
}
