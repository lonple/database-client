package com.lyj.dbc.manage.asset.instance;

import com.lyj.dbc.manage.asset.instance.dto.InstanceCreateRequest;
import com.lyj.dbc.manage.asset.instance.dto.InstanceUpdateRequest;
import com.lyj.dbc.manage.asset.instance.vo.InstanceVO;
import com.lyj.dbc.manage.common.ApiResponse;
import com.lyj.dbc.manage.security.RequirePermission;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * 实例管理接口。
 */
@Validated
@RestController
@RequestMapping("/instances")
public class InstanceController {

    private final InstanceService instanceService;

    public InstanceController(InstanceService instanceService) {
        this.instanceService = instanceService;
    }

    @GetMapping
    @RequirePermission("manage.instance.view")
    public ApiResponse<List<InstanceVO>> list() {
        return ApiResponse.ok(instanceService.list());
    }

    /**
     * 创建连接时可选实例（数据范围内归属且启用）。
     */
    @GetMapping("/selectable")
    @RequirePermission("manage.connection.view")
    public ApiResponse<List<InstanceVO>> selectable(@RequestParam(required = false) String dbType) {
        return ApiResponse.ok(instanceService.listSelectable(dbType));
    }

    @GetMapping("/{id}")
    @RequirePermission("manage.instance.view")
    public ApiResponse<InstanceVO> detail(@PathVariable @Min(1) Long id) {
        return ApiResponse.ok(instanceService.getById(id));
    }

    @PostMapping
    @RequirePermission("manage.instance.operate")
    public ApiResponse<InstanceVO> create(@Valid @RequestBody InstanceCreateRequest request) {
        return ApiResponse.ok(instanceService.create(request));
    }

    @PutMapping("/{id}")
    @RequirePermission("manage.instance.operate")
    public ApiResponse<InstanceVO> update(@PathVariable @Min(1) Long id,
                                          @Valid @RequestBody InstanceUpdateRequest request) {
        return ApiResponse.ok(instanceService.update(id, request));
    }

    @DeleteMapping("/{id}")
    @RequirePermission("manage.instance.operate")
    public ApiResponse<Void> delete(@PathVariable @Min(1) Long id) {
        instanceService.delete(id);
        return ApiResponse.ok(null);
    }

    @PostMapping(value = "/{id}/driver", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @RequirePermission("manage.instance.operate")
    public ApiResponse<InstanceVO> uploadDriver(@PathVariable @Min(1) Long id,
                                                @RequestPart("file") MultipartFile file) {
        return ApiResponse.ok(instanceService.uploadDriver(id, file));
    }
}
