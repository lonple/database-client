package com.lyj.dbc.usercenter.common;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 分页结果。
 *
 * @param <T> 记录类型
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PageResult<T> {

    /** 当前页记录 */
    private List<T> records;

    /** 总记录数 */
    private long total;

    /** 当前页码（从1开始） */
    private long page;

    /** 每页大小 */
    private long size;
}
