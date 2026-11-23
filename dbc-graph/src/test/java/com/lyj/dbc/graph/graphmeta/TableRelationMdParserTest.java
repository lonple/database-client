package com.lyj.dbc.graph.graphmeta;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TableRelationMdParserTest {

    @Test
    void parseImportMdTable() {
        String md = """
                # company 表关系
                
                - code: `default`
                - name: `company 表关系`
                - summary: `demo`
                - bidirectional: `true`
                
                ## 外键
                
                | 子表 | 子列 | 父表 | 父列 | 说明 |
                | --- | --- | --- | --- | --- |
                | `att_leave` | `emp_id` | `hr_employee` | `id` | 请假人 |
                | att_leave | leave_type_id | att_leave_type | id | |
                """;
        TableRelationMdParser.Parsed p = TableRelationMdParser.parse(md);
        assertEquals("default", p.code());
        assertEquals("company 表关系", p.name());
        assertTrue(p.bidirectional());
        assertEquals(2, p.fks().size());
        assertEquals(3, p.tables().size());
        assertEquals("att_leave", p.fks().get(0).child());
        assertEquals("emp_id", p.fks().get(0).childCol());
        assertEquals("hr_employee", p.fks().get(0).parent());
    }

    @Test
    void parseLegacyHeaderAndArrow() {
        String md = """
                | 子表 | 列 | 父表 | 父列 | 子表说明 |
                |---|---|---|---|---|
                | `fin_reimburse` | `emp_id` | `hr_employee` | `id` | -
                
                sal_sales_order_item.order_id -> sal_sales_order.id
                """;
        TableRelationMdParser.Parsed p = TableRelationMdParser.parse(md);
        assertEquals(2, p.fks().size());
        assertEquals("fin_reimburse", p.fks().get(0).child());
        assertEquals("sal_sales_order_item", p.fks().get(1).child());
        assertEquals("order_id", p.fks().get(1).childCol());
    }
}
