package com.lyj.dbc.knowledge.knowledge.support;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;

public final class ExpireSliceIdsSupport {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private ExpireSliceIdsSupport() {
    }

    public static String toJson(List<Long> ids) {
        try {
            return MAPPER.writeValueAsString(ids == null ? List.of() : ids);
        } catch (Exception e) {
            return "[]";
        }
    }

    public static List<Long> fromJson(String json) {
        if (!StringUtils.hasText(json)) {
            return new ArrayList<>();
        }
        try {
            List<Long> list = MAPPER.readValue(json, new TypeReference<>() {
            });
            return list == null ? new ArrayList<>() : new ArrayList<>(list);
        } catch (Exception e) {
            return new ArrayList<>();
        }
    }
}
