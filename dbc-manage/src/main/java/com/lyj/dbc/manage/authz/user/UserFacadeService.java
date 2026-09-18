package com.lyj.dbc.manage.authz.user;

import com.lyj.dbc.client.common.InnerClientException;
import com.lyj.dbc.client.common.PageResult;
import com.lyj.dbc.client.usercenter.UserCenterInnerClient;
import com.lyj.dbc.client.usercenter.dto.UserSummary;
import com.lyj.dbc.manage.common.BizException;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

/**
 * 用户选人门面：经 usercenter inner 拉取，不要求 usercenter.user.view。
 */
@Service
public class UserFacadeService {

    private final UserCenterInnerClient userCenterInnerClient;

    public UserFacadeService(UserCenterInnerClient userCenterInnerClient) {
        this.userCenterInnerClient = userCenterInnerClient;
    }

    public PageResult<UserSummary> page(long page, long size, String username) {
        long p = page < 1 ? 1 : page;
        long s = size < 1 ? 10 : Math.min(size, 100);
        try {
            return userCenterInnerClient.pageUsers(p, s, StringUtils.hasText(username) ? username.trim() : null);
        } catch (InnerClientException e) {
            throw BizException.badRequest("拉取用户列表失败: " + e.getMessage());
        }
    }
}
