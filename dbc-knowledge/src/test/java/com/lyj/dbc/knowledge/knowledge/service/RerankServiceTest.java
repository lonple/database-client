package com.lyj.dbc.knowledge.knowledge.service;

import com.lyj.dbc.knowledge.llm.model.RerankHit;
import com.lyj.dbc.knowledge.knowledge.dto.SearchHit;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;

class RerankServiceTest {

    @Test
    void applyRerankOrder_reordersAndWritesScores() {
        SearchHit a = hit("a");
        SearchHit b = hit("b");
        SearchHit c = hit("c");
        List<SearchHit> ordered = RerankService.applyRerankOrder(
                List.of(a, b, c),
                List.of(new RerankHit(2, 0.9), new RerankHit(0, 0.4), new RerankHit(1, 0.1)));
        assertEquals(List.of("c", "a", "b"), ordered.stream().map(SearchHit::getTitle).toList());
        assertEquals(0.9, ordered.get(0).getScore());
        assertEquals(0.4, ordered.get(1).getScore());
        assertEquals(0.1, ordered.get(2).getScore());
    }

    @Test
    void applyRerankOrder_appendsMissingIndices() {
        SearchHit a = hit("a");
        SearchHit b = hit("b");
        SearchHit c = hit("c");
        List<SearchHit> ordered = RerankService.applyRerankOrder(
                List.of(a, b, c),
                List.of(new RerankHit(1, 0.8)));
        assertEquals(List.of("b", "a", "c"), ordered.stream().map(SearchHit::getTitle).toList());
        assertSame(b, ordered.get(0));
    }

    @Test
    void toDocument_joinsTitleDescriptionBodySummary() {
        SearchHit hit = hit("标题");
        hit.setDescription("说明");
        hit.setBodySummary("正文摘要");
        assertEquals("标题\n说明\n正文摘要", RerankService.toDocument(hit));
    }

    private static SearchHit hit(String title) {
        SearchHit h = new SearchHit();
        h.setTitle(title);
        h.setScore(0.0);
        return h;
    }
}
