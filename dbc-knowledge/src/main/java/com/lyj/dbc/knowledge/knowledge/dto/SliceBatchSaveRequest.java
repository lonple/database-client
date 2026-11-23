package com.lyj.dbc.knowledge.knowledge.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class SliceBatchSaveRequest {
    @NotNull
    @Valid
    private List<SliceSaveItem> slices = new ArrayList<>();
}
