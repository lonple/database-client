import type { RouteRecordRaw } from 'vue-router'

export const askdataRoutes: RouteRecordRaw[] = [
  {
    path: '/askdata',
    component: () => import('@/layouts/WorkbenchLayout.vue'),
    meta: { module: 'askdata' },
    children: [
      {
        path: '',
        component: () => import('@/modules/askdata/layouts/AskdataShellLayout.vue'),
        meta: { module: 'askdata', fullContent: true },
        children: [
          {
            path: '',
            redirect: { name: 'askdata-spaces' },
          },
          {
            path: 'spaces',
            name: 'askdata-spaces',
            component: () => import('@/modules/askdata/views/AskdataSpaceHubView.vue'),
            meta: {
              module: 'askdata',
              title: '问数空间',
              permission: 'askdata.use',
              fullContent: true,
            },
          },
          {
            path: 'knowledge',
            name: 'askdata-knowledge',
            component: () => import('@/modules/askdata/views/AskdataKnowledgeListView.vue'),
            meta: {
              module: 'askdata',
              title: '知识库',
              permission: 'askdata.use',
              fullContent: true,
            },
          },
          {
            path: 'documents',
            name: 'askdata-documents',
            component: () => import('@/modules/askdata/views/AskdataDocumentListView.vue'),
            meta: {
              module: 'askdata',
              title: '文档管理',
              permission: 'askdata.use',
              fullContent: true,
            },
          },
          {
            path: 'documents/:id',
            name: 'askdata-document-detail',
            component: () => import('@/modules/askdata/views/AskdataDocumentDetailView.vue'),
            meta: {
              module: 'askdata',
              title: '文档详情',
              permission: 'askdata.use',
              fullContent: true,
            },
          },
          {
            path: 'graphs/:graphId',
            name: 'askdata-graph-editor',
            component: () => import('@/modules/askdata/graph/views/GraphEditorView.vue'),
            meta: {
              module: 'askdata',
              title: '图谱画布',
              permission: 'askdata.use',
              fullContent: true,
            },
          },
          {
            path: 'table-relations',
            name: 'askdata-table-relations',
            component: () => import('@/modules/askdata/views/AskdataTableRelationView.vue'),
            meta: {
              module: 'askdata',
              title: '库表关系',
              permission: 'askdata.use',
              fullContent: true,
            },
          },
          {
            path: 'ws/:workspaceId',
            name: 'askdata-workbench',
            component: () => import('@/modules/askdata/views/AskdataWorkbenchView.vue'),
            meta: {
              module: 'askdata',
              title: '智能问数工作台',
              permission: 'askdata.use',
              fullContent: true,
            },
          },
          {
            path: 'ws/:workspaceId/eval',
            name: 'askdata-eval',
            component: () => import('@/modules/askdata/views/AskdataEvalSpaceView.vue'),
            meta: {
              module: 'askdata',
              title: '测评空间',
              permission: 'askdata.use',
              fullContent: true,
            },
          },
          {
            path: 'ws/:workspaceId/eval/tasks',
            name: 'askdata-eval-tasks',
            component: () => import('@/modules/askdata/views/AskdataEvalTasksView.vue'),
            meta: {
              module: 'askdata',
              title: '测评任务',
              permission: 'askdata.use',
              fullContent: true,
            },
          },
          {
            path: 'ws/:workspaceId/eval/tasks/:taskId',
            name: 'askdata-eval-task-detail',
            component: () => import('@/modules/askdata/views/AskdataEvalTaskDetailView.vue'),
            meta: {
              module: 'askdata',
              title: '测评任务详情',
              permission: 'askdata.use',
              fullContent: true,
            },
          },
        ],
      },
    ],
  },
]

export const ASKDATA_ANY_VIEW = ['askdata.use']
