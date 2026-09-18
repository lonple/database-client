package com.lyj.dbc.client.audit;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class AuditLogAspectNormalizeSpelTest {

    @Test
    void rewrite_hashService_to_atBean() {
        assertThat(AuditLogAspect.normalizeBeanSpel("#userService.getById(#id)"))
                .isEqualTo("@userService.getById(#id)");
        assertThat(AuditLogAspect.normalizeBeanSpel("#instanceService.getById(#id)"))
                .isEqualTo("@instanceService.getById(#id)");
    }

    @Test
    void keep_rootMethod_and_atBean() {
        assertThat(AuditLogAspect.normalizeBeanSpel("getById(#id)")).isEqualTo("getById(#id)");
        assertThat(AuditLogAspect.normalizeBeanSpel("@roleService.getById(#roleId)"))
                .isEqualTo("@roleService.getById(#roleId)");
    }
}
