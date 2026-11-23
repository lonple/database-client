package com.lyj.dbc.graph.graphmeta;

import com.lyj.dbc.graph.common.api.BizException;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 解析库表关系导入 Markdown。
 * <p>
 * 约定：
 * <ul>
 *   <li>可选元数据：{@code - code: `default`} / YAML front matter</li>
 *   <li>外键表头含「子表」「父表」，列名可为「子列/列」「父列」「说明/子表说明」</li>
 *   <li>也支持行：{@code child.col -> parent.col}</li>
 * </ul>
 */
public final class TableRelationMdParser {
    private static final Pattern META_LINE = Pattern.compile(
            "^\\s*[-*]\\s*(code|name|summary|productName|product_name|bidirectional)\\s*[：:]\\s*(.+?)\\s*$",
            Pattern.CASE_INSENSITIVE);
    private static final Pattern ARROW_LINE = Pattern.compile(
            "^\\s*`?([A-Za-z_][\\w.]*)`?\\.`?([A-Za-z_][\\w]*)`?\\s*(?:->|→|=>)\\s*`?([A-Za-z_][\\w.]*)`?\\.`?([A-Za-z_][\\w]*)`?\\s*(?:#.*)?$");
    private static final Pattern H1 = Pattern.compile("^\\s*#\\s+(.+?)\\s*$");

    private TableRelationMdParser() {
    }

    public static Parsed parse(String markdown) {
        if (!StringUtils.hasText(markdown)) {
            throw new BizException("Markdown 内容不能为空");
        }
        String text = markdown.replace("\r\n", "\n").replace('\r', '\n');
        Map<String, String> meta = new HashMap<>();
        String body = stripFrontMatter(text, meta);
        String h1Name = null;
        List<FkRow> fks = new ArrayList<>();

        String[] lines = body.split("\n", -1);
        int i = 0;
        while (i < lines.length) {
            String raw = lines[i];
            String trimmed = raw == null ? "" : raw.trim();
            if (!StringUtils.hasText(trimmed)) {
                i++;
                continue;
            }
            Matcher h1m = H1.matcher(trimmed);
            if (h1m.matches() && h1Name == null) {
                h1Name = stripTicks(h1m.group(1));
                i++;
                continue;
            }
            Matcher mm = META_LINE.matcher(trimmed);
            if (mm.matches()) {
                putMeta(meta, mm.group(1), stripTicks(mm.group(2)));
                i++;
                continue;
            }
            if (trimmed.startsWith("|")) {
                TableBlock block = readTable(lines, i);
                i = block.nextIndex;
                fks.addAll(parseFkTable(block.header, block.rows));
                continue;
            }
            Matcher am = ARROW_LINE.matcher(trimmed);
            if (am.matches()) {
                fks.add(new FkRow(
                        bareTable(am.group(1)),
                        am.group(2),
                        bareTable(am.group(3)),
                        am.group(4),
                        ""));
            }
            i++;
        }

        if (fks.isEmpty()) {
            throw new BizException("未解析到外键行：请提供「子表|子列|父表|父列」表格，或 child.col -> parent.col 行");
        }

        Set<String> tables = new LinkedHashSet<>();
        for (FkRow fk : fks) {
            tables.add(fk.child());
            tables.add(fk.parent());
        }

        String code = firstNonBlank(meta.get("code"), "default");
        String name = firstNonBlank(meta.get("name"), h1Name, "导入表关系");
        String summary = firstNonBlank(meta.get("summary"),
                "库表外键导入：共 " + tables.size() + " 表 / " + fks.size() + " FK");
        String productName = firstNonBlank(meta.get("productName"), meta.get("product_name"), "dbc产品");
        boolean bidirectional = parseBool(meta.get("bidirectional"), true);

        return new Parsed(code, name, summary, productName, bidirectional, List.copyOf(tables), List.copyOf(fks));
    }

    private static String stripFrontMatter(String text, Map<String, String> meta) {
        String t = text.trim();
        if (!t.startsWith("---")) {
            return text;
        }
        int start = t.indexOf('\n');
        if (start < 0) {
            return text;
        }
        int end = t.indexOf("\n---", start + 1);
        if (end < 0) {
            return text;
        }
        String yaml = t.substring(start + 1, end);
        for (String line : yaml.split("\n")) {
            String s = line == null ? "" : line.trim();
            if (!StringUtils.hasText(s) || s.startsWith("#")) {
                continue;
            }
            int colon = s.indexOf(':');
            if (colon <= 0) {
                continue;
            }
            putMeta(meta, s.substring(0, colon).trim(), stripTicks(s.substring(colon + 1).trim()));
        }
        return t.substring(end + 4);
    }

    private static void putMeta(Map<String, String> meta, String key, String value) {
        if (!StringUtils.hasText(key) || !StringUtils.hasText(value)) {
            return;
        }
        String k = key.trim().toLowerCase(Locale.ROOT).replace("_", "");
        if ("productname".equals(k)) {
            meta.put("productName", value.trim());
        } else if ("bidirectional".equals(k)) {
            meta.put("bidirectional", value.trim());
        } else {
            meta.put(k, value.trim());
        }
    }

    private static TableBlock readTable(String[] lines, int start) {
        List<String> headerCells = splitRow(lines[start]);
        int i = start + 1;
        if (i < lines.length && isSeparatorRow(lines[i])) {
            i++;
        }
        List<List<String>> rows = new ArrayList<>();
        while (i < lines.length) {
            String t = lines[i] == null ? "" : lines[i].trim();
            if (!t.startsWith("|")) {
                break;
            }
            if (isSeparatorRow(t)) {
                i++;
                continue;
            }
            rows.add(splitRow(t));
            i++;
        }
        return new TableBlock(headerCells, rows, i);
    }

    private static List<FkRow> parseFkTable(List<String> header, List<List<String>> rows) {
        Map<String, Integer> idx = headerIndex(header);
        Integer child = idx.get("child");
        Integer childCol = idx.get("childCol");
        Integer parent = idx.get("parent");
        Integer parentCol = idx.get("parentCol");
        Integer desc = idx.get("desc");
        if (child == null || childCol == null || parent == null || parentCol == null) {
            return List.of();
        }
        List<FkRow> out = new ArrayList<>();
        for (List<String> row : rows) {
            String c = cell(row, child);
            String cc = cell(row, childCol);
            String p = cell(row, parent);
            String pc = cell(row, parentCol);
            if (!StringUtils.hasText(c) || !StringUtils.hasText(cc)
                    || !StringUtils.hasText(p) || !StringUtils.hasText(pc)) {
                continue;
            }
            out.add(new FkRow(bareTable(c), stripTicks(cc), bareTable(p), stripTicks(pc),
                    desc == null ? "" : cell(row, desc)));
        }
        return out;
    }

    private static Map<String, Integer> headerIndex(List<String> header) {
        Map<String, Integer> idx = new LinkedHashMap<>();
        for (int i = 0; i < header.size(); i++) {
            String h = normalizeHeader(header.get(i));
            if (h.isEmpty()) {
                continue;
            }
            if (h.equals("子表") || h.equals("child") || h.equals("childtable") || h.equals("fromtable")) {
                idx.putIfAbsent("child", i);
            } else if (h.equals("子列") || h.equals("列") || h.equals("childcol") || h.equals("fromcol")
                    || h.equals("column") || h.equals("fkcolumn")) {
                idx.putIfAbsent("childCol", i);
            } else if (h.equals("父表") || h.equals("parent") || h.equals("parenttable") || h.equals("totable")) {
                idx.putIfAbsent("parent", i);
            } else if (h.equals("父列") || h.equals("parentcol") || h.equals("tocol") || h.equals("pkcolumn")) {
                idx.putIfAbsent("parentCol", i);
            } else if (h.equals("说明") || h.equals("子表说明") || h.equals("description") || h.equals("desc")
                    || h.equals("remark")) {
                idx.putIfAbsent("desc", i);
            }
        }
        return idx;
    }

    private static String normalizeHeader(String raw) {
        String s = stripTicks(raw == null ? "" : raw);
        return s.toLowerCase(Locale.ROOT)
                .replace(" ", "")
                .replace("_", "")
                .replace("-", "");
    }

    private static List<String> splitRow(String line) {
        String t = line == null ? "" : line.trim();
        if (t.startsWith("|")) {
            t = t.substring(1);
        }
        if (t.endsWith("|")) {
            t = t.substring(0, t.length() - 1);
        }
        String[] parts = t.split("\\|", -1);
        List<String> cells = new ArrayList<>(parts.length);
        for (String p : parts) {
            cells.add(stripTicks(p));
        }
        return cells;
    }

    private static boolean isSeparatorRow(String line) {
        String t = line == null ? "" : line.trim();
        if (!t.contains("-")) {
            return false;
        }
        for (char c : t.toCharArray()) {
            if (!(c == '|' || c == '-' || c == ':' || c == ' ' || c == '\t')) {
                return false;
            }
        }
        return t.contains("|") || t.startsWith("---");
    }

    private static String cell(List<String> row, int i) {
        if (i < 0 || i >= row.size()) {
            return "";
        }
        return row.get(i) == null ? "" : row.get(i).trim();
    }

    private static String stripTicks(String s) {
        String t = s == null ? "" : s.trim();
        if (t.startsWith("`") && t.endsWith("`") && t.length() >= 2) {
            t = t.substring(1, t.length() - 1).trim();
        }
        if ((t.startsWith("\"") && t.endsWith("\"")) || (t.startsWith("'") && t.endsWith("'"))) {
            t = t.substring(1, t.length() - 1).trim();
        }
        return t;
    }

    private static String bareTable(String name) {
        String t = stripTicks(name);
        int dot = t.lastIndexOf('.');
        if (dot >= 0 && dot < t.length() - 1) {
            // schema.table → table（图谱节点用裸表名，与问数找表一致）
            return t.substring(dot + 1);
        }
        return t;
    }

    private static boolean parseBool(String raw, boolean defaultValue) {
        if (!StringUtils.hasText(raw)) {
            return defaultValue;
        }
        String v = raw.trim().toLowerCase(Locale.ROOT);
        if (v.equals("true") || v.equals("1") || v.equals("yes") || v.equals("y") || v.equals("是")) {
            return true;
        }
        if (v.equals("false") || v.equals("0") || v.equals("no") || v.equals("n") || v.equals("否")) {
            return false;
        }
        return defaultValue;
    }

    private static String firstNonBlank(String... values) {
        if (values == null) {
            return null;
        }
        for (String v : values) {
            if (StringUtils.hasText(v)) {
                return v.trim();
            }
        }
        return null;
    }

    private record TableBlock(List<String> header, List<List<String>> rows, int nextIndex) {
    }

    public record FkRow(String child, String childCol, String parent, String parentCol, String description) {
    }

    public record Parsed(
            String code,
            String name,
            String summary,
            String productName,
            boolean bidirectional,
            List<String> tables,
            List<FkRow> fks
    ) {
    }
}
