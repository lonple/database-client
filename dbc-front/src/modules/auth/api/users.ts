import http from '@/common/api/http'
import type { ApiResponse, PageResult } from '@/common/api/types'
import { MANAGE_BASE } from '@/modules/manage/constants'

/** 工作空间选人等场景用的用户摘要（经 manage 门面，不要求 usercenter.user.view） */
export interface ManageUserSummary {
  id: number
  username: string
  status?: number
  deptId?: number | null
  deptName?: string | null
}

export function fetchUsersForWorkspace(params: {
  page: number
  size: number
  username?: string
}) {
  return http.get(`${MANAGE_BASE}/users`, { params }) as Promise<
    ApiResponse<PageResult<ManageUserSummary>>
  >
}
