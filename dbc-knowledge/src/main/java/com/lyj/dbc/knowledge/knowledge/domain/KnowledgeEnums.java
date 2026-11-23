package com.lyj.dbc.knowledge.knowledge.domain;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public final class KnowledgeEnums {
    private KnowledgeEnums() {}

    public static final String ORIENT_VERTICAL = "VERTICAL";
    public static final String ORIENT_HORIZONTAL = "HORIZONTAL";
    /** 原文同时需要横向与纵向能力（非互斥） */
    public static final String ORIENT_BOTH = "BOTH";

    public static final String STATUS_DRAFT = "DRAFT";
    public static final String STATUS_PUBLISHED = "PUBLISHED";
    public static final String STATUS_DEPRECATED = "DEPRECATED";

    public static final String KIND_DOCUMENT = "DOCUMENT";
    public static final String KIND_SLICE = "SLICE";

    public static final String SOURCE_MANUAL = "MANUAL";
    public static final String SOURCE_MD_IMPORT = "MD_IMPORT";
    public static final String SOURCE_MCP = "MCP";
    public static final String SOURCE_REVIEW = "REVIEW";

    /** 新增；发布后无过期副作用 */
    public static final String UPDATE_CREATE = "CREATE";
    /** 整篇更新：过期目标原文及其全部切片 */
    public static final String UPDATE_REPLACE_DOCUMENT = "REPLACE_DOCUMENT";
    /** 切片更新：仅过期指定切片；工作草稿切片并入目标原文 */
    public static final String UPDATE_REPLACE_SLICES = "REPLACE_SLICES";

    public static boolean isValidUpdateMode(String mode) {
        return UPDATE_CREATE.equals(mode)
                || UPDATE_REPLACE_DOCUMENT.equals(mode)
                || UPDATE_REPLACE_SLICES.equals(mode);
    }

    public static boolean isValidSliceOrientation(String o) {
        return ORIENT_HORIZONTAL.equals(o) || ORIENT_VERTICAL.equals(o);
    }

    public static boolean isValidDocumentOrientation(String o) {
        return ORIENT_HORIZONTAL.equals(o) || ORIENT_VERTICAL.equals(o) || ORIENT_BOTH.equals(o);
    }

    /** 文档取向 → 期望的切片取向列表（BOTH 含两者） */
    public static List<String> documentOrientModes(String documentOrientation) {
        Set<String> set = new LinkedHashSet<>();
        if (documentOrientation == null || documentOrientation.isBlank() || ORIENT_BOTH.equals(documentOrientation)) {
            set.add(ORIENT_HORIZONTAL);
            set.add(ORIENT_VERTICAL);
            return new ArrayList<>(set);
        }
        String upper = documentOrientation.trim().toUpperCase(Locale.ROOT);
        if (upper.contains(",")) {
            for (String p : upper.split(",")) {
                String t = p.trim();
                if (ORIENT_HORIZONTAL.equals(t) || ORIENT_VERTICAL.equals(t)) {
                    set.add(t);
                }
            }
        } else if (ORIENT_HORIZONTAL.equals(upper) || ORIENT_VERTICAL.equals(upper)) {
            set.add(upper);
        } else {
            set.add(ORIENT_HORIZONTAL);
            set.add(ORIENT_VERTICAL);
        }
        if (set.isEmpty()) {
            set.add(ORIENT_HORIZONTAL);
            set.add(ORIENT_VERTICAL);
        }
        return new ArrayList<>(set);
    }

    public static String toDocumentOrientation(List<String> modes) {
        if (modes == null || modes.isEmpty()) {
            return ORIENT_BOTH;
        }
        boolean h = modes.contains(ORIENT_HORIZONTAL);
        boolean v = modes.contains(ORIENT_VERTICAL);
        if (h && v) {
            return ORIENT_BOTH;
        }
        if (v) {
            return ORIENT_VERTICAL;
        }
        return ORIENT_HORIZONTAL;
    }

    public static boolean wantsHorizontal(String documentOrientation) {
        return documentOrientModes(documentOrientation).contains(ORIENT_HORIZONTAL);
    }

    public static boolean wantsVertical(String documentOrientation) {
        return documentOrientModes(documentOrientation).contains(ORIENT_VERTICAL);
    }
}
