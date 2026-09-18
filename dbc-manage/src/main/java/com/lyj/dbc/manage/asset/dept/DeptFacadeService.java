package com.lyj.dbc.manage.asset.dept;

import com.lyj.dbc.client.common.InnerClientException;
import com.lyj.dbc.client.usercenter.UserCenterInnerClient;
import com.lyj.dbc.client.usercenter.dto.DeptTreeNode;
import com.lyj.dbc.manage.asset.DataScopeSupport;
import com.lyj.dbc.manage.client.dto.DataScopeVO;
import com.lyj.dbc.manage.common.BizException;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * 部门树门面：经 usercenter inner 拉取，并按当前用户 data-scope 裁剪。
 */
@Service
public class DeptFacadeService {

    private final UserCenterInnerClient userCenterInnerClient;

    public DeptFacadeService(UserCenterInnerClient userCenterInnerClient) {
        this.userCenterInnerClient = userCenterInnerClient;
    }

    public List<DeptTreeNode> treeForCurrentUser() {
        List<DeptTreeNode> full;
        try {
            full = userCenterInnerClient.listDeptTree();
        } catch (InnerClientException e) {
            throw BizException.badRequest("拉取部门树失败: " + e.getMessage());
        }
        DataScopeVO scope = DataScopeSupport.current();
        if (DataScopeSupport.isAll(scope)) {
            return full == null ? List.of() : full;
        }
        Set<Long> allowed = DataScopeSupport.deptIds(scope);
        if (allowed.isEmpty()) {
            return List.of();
        }
        return filterTree(full == null ? List.of() : full, allowed);
    }

    private List<DeptTreeNode> filterTree(List<DeptTreeNode> nodes, Set<Long> allowed) {
        List<DeptTreeNode> result = new ArrayList<>();
        for (DeptTreeNode node : nodes) {
            List<DeptTreeNode> children = filterTree(
                    node.getChildren() == null ? List.of() : node.getChildren(), allowed);
            boolean selfOk = node.getId() != null && allowed.contains(node.getId());
            if (selfOk || !children.isEmpty()) {
                result.add(DeptTreeNode.builder()
                        .id(node.getId())
                        .name(node.getName())
                        .description(node.getDescription())
                        .parentId(node.getParentId())
                        .level(node.getLevel())
                        .path(node.getPath())
                        .children(children)
                        .build());
            }
        }
        return result;
    }
}
