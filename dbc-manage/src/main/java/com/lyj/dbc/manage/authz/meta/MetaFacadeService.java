package com.lyj.dbc.manage.authz.meta;

import com.lyj.dbc.manage.authz.WorkspaceAdminService;
import com.lyj.dbc.manage.authz.meta.vo.MetaTablePageVO;
import com.lyj.dbc.manage.client.SqlworkMetaClient;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 工作空间授权选表：校验空间维护权后，代理 sqlwork inner 元数据。
 */
@Service
public class MetaFacadeService {

    private final WorkspaceAdminService workspaceAdminService;
    private final SqlworkMetaClient sqlworkMetaClient;

    public MetaFacadeService(WorkspaceAdminService workspaceAdminService,
                             SqlworkMetaClient sqlworkMetaClient) {
        this.workspaceAdminService = workspaceAdminService;
        this.sqlworkMetaClient = sqlworkMetaClient;
    }

    public List<String> listDatabases(Long workspaceId, Long connectionId) {
        workspaceAdminService.assertMetaBrowseAccess(workspaceId, connectionId);
        return sqlworkMetaClient.listDatabases(connectionId);
    }

    public List<String> listSchemas(Long workspaceId, Long connectionId, String database) {
        workspaceAdminService.assertMetaBrowseAccess(workspaceId, connectionId);
        return sqlworkMetaClient.listSchemas(connectionId, database);
    }

    public MetaTablePageVO listTables(Long workspaceId, Long connectionId, String database,
                                      String schema, String keyword, int page, int size) {
        workspaceAdminService.assertMetaBrowseAccess(workspaceId, connectionId);
        return sqlworkMetaClient.listTables(connectionId, database, schema, keyword, page, size);
    }
}
