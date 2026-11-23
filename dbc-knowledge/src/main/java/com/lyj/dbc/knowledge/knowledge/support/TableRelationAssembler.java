package com.lyj.dbc.knowledge.knowledge.support;

import com.lyj.dbc.knowledge.knowledge.dto.TableRelationEdgeVo;
import com.lyj.dbc.knowledge.knowledge.dto.TableRelationVo;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 把图谱 neighbors 整理成与 search/tables 相同的关联结构。
 */
public final class TableRelationAssembler {
    private static final Pattern JOIN_TEXT = Pattern.compile(
            "^(.+?)\\.([A-Za-z_][A-Za-z0-9_]*)\\s+关联\\s+(.+?)\\.([A-Za-z_][A-Za-z0-9_]*)$");

    private TableRelationAssembler() {
    }

    @SuppressWarnings("unchecked")
    public static List<TableRelationVo> fromNeighbors(String fromTable, Object neighborsObj) {
        List<TableRelationVo> relations = new ArrayList<>();
        if (!(neighborsObj instanceof List<?> neighbors) || !StringUtils.hasText(fromTable)) {
            return relations;
        }
        for (Object item : neighbors) {
            if (!(item instanceof Map<?, ?> m)) {
                continue;
            }
            String neighbor = String.valueOf(m.get("table") == null ? "" : m.get("table")).trim();
            if (!StringUtils.hasText(neighbor) || neighbor.equalsIgnoreCase(fromTable)) {
                continue;
            }
            List<Map<String, Object>> joins = m.get("joins") instanceof List<?> jl
                    ? (List<Map<String, Object>>) jl
                    : List.of();
            List<String> joinTexts = m.get("joinTexts") instanceof List<?> jt
                    ? (List<String>) jt
                    : List.of();
            TableRelationVo rel = new TableRelationVo();
            rel.setFromTable(fromTable);
            rel.setToTable(neighbor);
            rel.setJoins(joins);
            rel.setJoinTexts(joinTexts);
            rel.setEdges(edgesFrom(joins, joinTexts));
            rel.setPathLength(joins.isEmpty() ? (joinTexts.isEmpty() ? 0 : 1) : joins.size());
            relations.add(rel);
        }
        return relations;
    }

    static List<TableRelationEdgeVo> edgesFrom(List<Map<String, Object>> joins, List<String> joinTexts) {
        List<TableRelationEdgeVo> edges = new ArrayList<>();
        if (joins != null) {
            for (Map<String, Object> join : joins) {
                if (join == null) {
                    continue;
                }
                TableRelationEdgeVo edge = edge(
                        str(join.get("leftTable")),
                        str(join.get("leftColumn")),
                        str(join.get("rightTable")),
                        str(join.get("rightColumn")));
                if (edge != null) {
                    edges.add(edge);
                }
            }
        }
        if (!edges.isEmpty() || joinTexts == null) {
            return edges;
        }
        for (String text : joinTexts) {
            if (!StringUtils.hasText(text)) {
                continue;
            }
            Matcher matcher = JOIN_TEXT.matcher(text.trim());
            if (!matcher.matches()) {
                continue;
            }
            TableRelationEdgeVo edge = edge(matcher.group(1), matcher.group(2), matcher.group(3), matcher.group(4));
            if (edge != null) {
                edges.add(edge);
            }
        }
        return edges;
    }

    private static TableRelationEdgeVo edge(String fromTable, String fromColumn, String toTable, String toColumn) {
        if (!StringUtils.hasText(fromTable) || !StringUtils.hasText(fromColumn)
                || !StringUtils.hasText(toTable) || !StringUtils.hasText(toColumn)) {
            return null;
        }
        TableRelationEdgeVo edge = new TableRelationEdgeVo();
        edge.setFromTable(fromTable.trim());
        edge.setFromColumn(fromColumn.trim());
        edge.setToTable(toTable.trim());
        edge.setToColumn(toColumn.trim());
        return edge;
    }

    private static String str(Object raw) {
        if (raw == null) {
            return "";
        }
        return String.valueOf(raw).trim();
    }
}
