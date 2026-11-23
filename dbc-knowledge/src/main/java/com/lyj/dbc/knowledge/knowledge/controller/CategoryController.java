package com.lyj.dbc.knowledge.knowledge.controller;

import com.lyj.dbc.knowledge.common.api.ApiResponse;
import com.lyj.dbc.knowledge.knowledge.domain.Category;
import com.lyj.dbc.knowledge.knowledge.dto.CategoryCreateRequest;
import com.lyj.dbc.knowledge.knowledge.dto.CategoryTreeNode;
import com.lyj.dbc.knowledge.knowledge.service.CategoryRecommendService;
import com.lyj.dbc.knowledge.knowledge.service.CategoryService;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/categories")
public class CategoryController {
    private final CategoryService categoryService;
    private final CategoryRecommendService recommendService;

    public CategoryController(CategoryService categoryService, CategoryRecommendService recommendService) {
        this.categoryService = categoryService;
        this.recommendService = recommendService;
    }

    @GetMapping("/tree")
    public ApiResponse<List<CategoryTreeNode>> tree() {
        return ApiResponse.ok(categoryService.tree());
    }

    @PostMapping
    public ApiResponse<Category> create(@RequestBody CategoryCreateRequest req) {
        return ApiResponse.ok(categoryService.create(req));
    }

    @PatchMapping("/{id}")
    public ApiResponse<Category> rename(@PathVariable Long id, @RequestBody Map<String, String> body) {
        return ApiResponse.ok(categoryService.rename(id, body.get("name")));
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        categoryService.delete(id);
        return ApiResponse.ok(null);
    }

    @PostMapping("/recommend")
    public ApiResponse<Map<String, Object>> recommend(@RequestBody Map<String, String> body) {
        String desc = body.get("description");
        if (desc == null || desc.isBlank()) {
            desc = body.get("summary");
        }
        return ApiResponse.ok(recommendService.recommend(
                body.get("title"), desc, body.get("body")));
    }
}
