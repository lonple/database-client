package com.lyj.dbc.knowledge.knowledge.service;

import com.lyj.dbc.knowledge.knowledge.domain.Relation;
import com.lyj.dbc.knowledge.knowledge.mapper.RelationMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class RelationService {
    private final RelationMapper relationMapper;

    public RelationService(RelationMapper relationMapper) {
        this.relationMapper = relationMapper;
    }

    @Transactional
    public List<Relation> createBatch(List<Map<String, Object>> items) {
        List<Relation> saved = new ArrayList<>();
        for (Map<String, Object> item : items) {
            Relation r = new Relation();
            r.setFromKind(String.valueOf(item.get("fromKind")));
            r.setFromId(toLong(item.get("fromId")));
            r.setToKind(String.valueOf(item.get("toKind")));
            r.setToId(toLong(item.get("toId")));
            r.setRelType(String.valueOf(item.get("relType")));
            r.setCreatedAt(OffsetDateTime.now());
            try {
                relationMapper.insert(r);
                saved.add(r);
            } catch (Exception ignored) {
                // unique conflict skip
            }
        }
        return saved;
    }

    private Long toLong(Object o) {
        if (o instanceof Number n) {
            return n.longValue();
        }
        return Long.parseLong(String.valueOf(o));
    }
}
