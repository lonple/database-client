import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { ASKDATA_BASE } from '@/modules/askdata/constants'

export interface AskdataAppConfig {
  dailyTokenLimit: number
  llmProvider: string
  concurrentChatLimit: number
  /** 单个测评任务内同时执行的用例数 */
  evalTaskConcurrency: number
}

export function getAskdataAppConfig() {
  return http.get(`${ASKDATA_BASE}/api/admin/app-config/askdata`) as Promise<
    ApiResponse<AskdataAppConfig>
  >
}

export function putAskdataAppConfig(data: Partial<AskdataAppConfig>) {
  return http.put(`${ASKDATA_BASE}/api/admin/app-config/askdata`, data) as Promise<
    ApiResponse<AskdataAppConfig>
  >
}
