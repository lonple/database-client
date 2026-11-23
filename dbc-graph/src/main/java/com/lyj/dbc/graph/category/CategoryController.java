package com.lyj.dbc.graph.category;

import com.lyj.dbc.graph.category.dto.CategoryCreateRequest;
import com.lyj.dbc.graph.category.dto.CategoryTreeNode;
import com.lyj.dbc.graph.category.entity.GraphCategoryEntity;
import com.lyj.dbc.graph.common.api.ApiResponse;
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

    public CategoryController(CategoryService categoryService) {
        this.categoryService = categoryService;
    }

    @GetMapping("/tree")
    public ApiResponse<List<CategoryTreeNode>> tree() {
        return ApiResponse.ok(categoryService.tree());
    }

    @PostMapping
    public ApiResponse<GraphCategoryEntity> create(@RequestBody CategoryCreateRequest req) {
        return ApiResponse.ok(categoryService.create(req));
    }

    @PatchMapping("/{id}")
    public ApiResponse<GraphCategoryEntity> rename(@PathVariable Long id, @RequestBody Map<String, String> body) {
        return ApiResponse.ok(categoryService.rename(id, body.get("name")));
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        categoryService.delete(id);
        return ApiResponse.ok(null);
    }
}
