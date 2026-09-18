<template>
  <div class="home">
    <!-- 个人空间首页 -->
    <template v-if="domain.isPersonal">
      <header class="hero">
        <div class="logo-mark">DBC</div>
        <div class="hero-text">
          <h1>个人空间</h1>
          <p>你好，{{ displayName }}。在此管理个人实例、连接与授权；与公司资产完全隔离。</p>
        </div>
      </header>

      <section class="panel">
        <div class="panel-hd">
          <h2>{{ personalWorkspace ? '进入个人空间' : '创建个人空间' }}</h2>
          <p>
            每位用户仅有一个个人工作空间。创建后可登记个人资产、挂载连接并邀请成员仅执行 SQL。
          </p>
        </div>

        <a-spin :spinning="personalLoading">
          <div v-if="personalWorkspace" class="personal-card">
            <div>
              <strong>{{ personalWorkspace.name }}</strong>
              <p class="muted">{{ personalWorkspace.description || '你的个人工作空间已就绪。' }}</p>
            </div>
            <a-space>
              <a-button type="primary" @click="go(`/manage/auth/workspaces/${personalWorkspace.id}`)">
                进入工作空间
              </a-button>
              <a-button @click="go('/manage/instances')">管理个人资产</a-button>
              <a-button v-if="canSqlwork" @click="go('/sqlwork')">SQL 工作台</a-button>
            </a-space>
          </div>
          <div v-else class="personal-card">
            <div>
              <strong>尚未创建个人空间</strong>
              <p class="muted">一键创建后即可登记实例与连接，并配置工作空间授权。</p>
            </div>
            <a-button type="primary" :loading="creatingPersonal" @click="onCreatePersonal">
              创建个人空间
            </a-button>
          </div>
        </a-spin>

        <ol class="guide-list" style="margin-top: 20px">
          <li><strong>个人资产</strong>：仅自己可见，只能挂载到本人个人空间。</li>
          <li><strong>邀请成员</strong>：被授权人只能通过 SQL 工作台执行，不能改你的资产与授权。</li>
          <li><strong>退出</strong>：顶栏「退出个人空间」回到公司域。</li>
        </ol>
      </section>
    </template>

    <!-- DATA_OPERATOR 公司域首页 -->
    <template v-else-if="isDataOperator">
      <header class="hero">
        <div class="logo-mark">DBC</div>
        <div class="hero-text">
          <h1>数据库客户端</h1>
          <p>你好，{{ displayName }}。你可直接进入 SQL 工作台；个人库请使用右上角「个人空间」。</p>
        </div>
      </header>

      <section class="panel">
        <div class="panel-hd">
          <h2>开始工作</h2>
          <p>公司侧你主要使用 SQL 工作台；个人实例与连接在个人空间中自助管理。</p>
        </div>
        <div class="shortcuts">
          <a-button v-if="canSqlwork" type="primary" @click="go('/sqlwork')">进入 SQL 工作台</a-button>
          <a-button v-if="canEnterPersonal" @click="enterPersonalHome">进入个人空间</a-button>
        </div>
        <ol class="guide-list" style="margin-top: 20px">
          <li><strong>SQL 工作台</strong>：选择已加入的工作空间执行 SQL。</li>
          <li><strong>个人空间</strong>：登记个人实例/连接，创建个人工作空间并授权同事只读或执行。</li>
        </ol>
      </section>
    </template>

    <!-- 管理员等默认公司首页 -->
    <template v-else>
      <header class="hero">
        <div class="logo-mark">DBC</div>
        <div class="hero-text">
          <h1>数据库客户端</h1>
          <p>
            你好，{{ displayName }}。统一登录与授权后，在工作空间内安全执行 SQL；浏览器不直连目标库。
          </p>
        </div>
      </header>

      <section class="panel">
        <div class="panel-hd">
          <h2>快速上手</h2>
          <p>按角色完成配置后即可执行；管理员先搭资产与授权，操作员直接进工作台。</p>
        </div>

        <div class="quick-flow" aria-label="快速上手流程图">
          <div class="qf-step">
            <span class="qf-num">1</span>
            <strong>登记资产</strong>
            <span>资产管理 → 实例 / 连接</span>
          </div>
          <div class="qf-arrow" aria-hidden="true">→</div>
          <div class="qf-step">
            <span class="qf-num">2</span>
            <strong>建工作空间</strong>
            <span>权限管控 → 工作空间授权</span>
          </div>
          <div class="qf-arrow" aria-hidden="true">→</div>
          <div class="qf-step">
            <span class="qf-num">3</span>
            <strong>挂载与授权</strong>
            <span>挂连接、选对象、授操作</span>
          </div>
          <div class="qf-arrow" aria-hidden="true">→</div>
          <div class="qf-step">
            <span class="qf-num">4</span>
            <strong>执行 SQL</strong>
            <span>SQL 工作台 → 选空间执行</span>
          </div>
        </div>

        <ol class="guide-list">
          <li>
            <strong>资产管理</strong>
            ：登记数据库实例与连接（密码加密存库，执行时由服务端解密建池）。
          </li>
          <li>
            <strong>权限管控 · 工作空间</strong>
            ：创建空间 → 挂载连接/对象 → 添加成员并授予 SELECT / DML / DDL 等操作。
          </li>
          <li>
            <strong>（可选）全局管控</strong>
            ：对指定操作配置阻断、告警或二次鉴权，叠加在空间授权之上。
          </li>
          <li>
            <strong>SQL 工作台</strong>
            ：选择自己所在空间 → 选连接 / 库 / schema → 编写并执行；下方查看「执行日志」与「结果」。
          </li>
          <li>
            <strong>个人空间</strong>
            ：右上角用户菜单可进入，管理个人资产（与公司隔离）。
          </li>
        </ol>

        <div class="shortcuts">
          <a-button v-if="canSqlwork" type="primary" @click="go('/sqlwork')">进入 SQL 工作台</a-button>
          <a-button v-if="canAuth" @click="go('/manage/auth/workspaces')">工作空间授权</a-button>
          <a-button v-if="canManage" @click="go('/manage/instances')">资产管理</a-button>
          <a-button v-if="canEnterPersonal" @click="enterPersonalHome">个人空间</a-button>
        </div>
      </section>

      <section class="panel">
        <div class="panel-hd">
          <h2>SQL 执行业务流程</h2>
          <p>一次可提交多条语句；系统会按顺序拆成单句校验与执行，某句失败则停止后续语句。</p>
        </div>

        <div class="flow-diagram" aria-label="SQL 执行业务流程图">
          <svg viewBox="0 0 920 220" role="img" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                <path d="M0,0 L8,4 L0,8 Z" fill="#8c8c8c" />
              </marker>
            </defs>

            <g class="node">
              <rect x="16" y="70" width="120" height="64" rx="8" />
              <text x="76" y="98" text-anchor="middle">编辑器提交</text>
              <text x="76" y="116" text-anchor="middle" class="sub">多语句 SQL</text>
            </g>
            <line x1="136" y1="102" x2="168" y2="102" stroke="#8c8c8c" stroke-width="1.5" marker-end="url(#arrow)" />

            <g class="node">
              <rect x="172" y="70" width="120" height="64" rx="8" />
              <text x="232" y="98" text-anchor="middle">语句拆分</text>
              <text x="232" y="116" text-anchor="middle" class="sub">按顺序拆成单句</text>
            </g>
            <line x1="292" y1="102" x2="324" y2="102" stroke="#8c8c8c" stroke-width="1.5" marker-end="url(#arrow)" />

            <g class="node accent">
              <rect x="328" y="70" width="140" height="64" rx="8" />
              <text x="398" y="98" text-anchor="middle">空间鉴权</text>
              <text x="398" y="116" text-anchor="middle" class="sub">对象 + 操作权限</text>
            </g>
            <line x1="468" y1="102" x2="500" y2="102" stroke="#8c8c8c" stroke-width="1.5" marker-end="url(#arrow)" />

            <g class="node accent">
              <rect x="504" y="70" width="140" height="64" rx="8" />
              <text x="574" y="98" text-anchor="middle">全局策略</text>
              <text x="574" y="116" text-anchor="middle" class="sub">阻断 / 告警 / 二次鉴权</text>
            </g>
            <line x1="644" y1="102" x2="676" y2="102" stroke="#8c8c8c" stroke-width="1.5" marker-end="url(#arrow)" />

            <g class="node">
              <rect x="680" y="70" width="120" height="64" rx="8" />
              <text x="740" y="98" text-anchor="middle">目标库执行</text>
              <text x="740" y="116" text-anchor="middle" class="sub">sqlwork 连接池</text>
            </g>
            <line x1="800" y1="102" x2="832" y2="102" stroke="#8c8c8c" stroke-width="1.5" marker-end="url(#arrow)" />

            <g class="node ok">
              <rect x="836" y="70" width="68" height="64" rx="8" />
              <text x="870" y="98" text-anchor="middle">日志</text>
              <text x="870" y="116" text-anchor="middle" class="sub">结果</text>
            </g>

            <path
              d="M398 134 L398 170 L574 170 L574 134"
              fill="none"
              stroke="#ff4d4f"
              stroke-width="1.5"
              stroke-dasharray="4 3"
              marker-end="url(#arrow)"
            />
            <text x="486" y="190" text-anchor="middle" class="deny-label">无权限 / 阻断 → 写入执行日志并停止后续语句</text>
          </svg>
        </div>

        <div class="flow-cards">
          <div class="flow-card">
            <h3>1. 提交与拆分</h3>
            <p>工作台一次可提交多条 SQL；系统按书写顺序拆成单句处理，单批有条数上限，遇错即停止后续语句。</p>
          </div>
          <div class="flow-card">
            <h3>2. 空间鉴权</h3>
            <p>
              校验你是否为空间成员、连接是否挂载、对象是否在授权范围内，以及是否具备该语句操作（如 SELECT）。
            </p>
          </div>
          <div class="flow-card">
            <h3>3. 全局策略</h3>
            <p>
              叠加全局管控：<em>阻断</em>不执行；<em>告警</em>仍执行但日志标红；<em>二次鉴权</em>需密码换短时票据。
            </p>
          </div>
          <div class="flow-card">
            <h3>4. 执行与回显</h3>
            <p>
              通过后由 sqlwork 经连接池访问目标库。成功结果在「结果」Tab；失败原因、缺失对象与权限在「执行日志」。
            </p>
          </div>
        </div>

        <div class="note">
          <strong>安全边界：</strong>
          浏览器与前端永不直连目标库；密码仅在服务端短暂解密用于建池；执行权限以「工作空间成员授权 + 全局策略」为准，与菜单功能权限相互独立。
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/modules/user-center/stores/auth'
import { useDomainStore } from '@/modules/user-center/stores/domain'
import { hasAnyPermission, hasPermission } from '@/common/permission/menu'
import { MANAGE_ANY_VIEW } from '@/modules/manage/routes'
import { AUTH_ANY_VIEW } from '@/modules/auth/routes'
import { SQLWORK_ANY_VIEW } from '@/modules/sqlwork/routes'
import * as workspaceApi from '@/modules/auth/api/workspace'

const auth = useAuthStore()
const domain = useDomainStore()
const router = useRouter()
const displayName = computed(() => auth.user?.username || '用户')
const permissions = computed(() => auth.user?.permissions || [])

const canSqlwork = computed(() => hasAnyPermission(permissions.value, SQLWORK_ANY_VIEW))
const canAuth = computed(() => hasAnyPermission(permissions.value, AUTH_ANY_VIEW))
const canManage = computed(() => hasAnyPermission(permissions.value, MANAGE_ANY_VIEW))
const canEnterPersonal = computed(() => hasPermission(permissions.value, 'usercenter.personal.space.view'))

const isDataOperator = computed(() => {
  const roles = auth.user?.roles || []
  if (!roles.some((r) => r.code === 'DATA_OPERATOR')) return false
  // 同时具备公司管理权限时走管理员首页
  return !canManage.value && !canAuth.value
})

const personalLoading = ref(false)
const creatingPersonal = ref(false)
const personalWorkspace = ref<{ id: number; name: string; description?: string | null } | null>(null)

async function loadPersonal() {
  if (!domain.isPersonal) return
  personalLoading.value = true
  try {
    const resp = await workspaceApi.getPersonalWorkspace()
    personalWorkspace.value = resp.data || null
  } catch {
    personalWorkspace.value = null
  } finally {
    personalLoading.value = false
  }
}

async function onCreatePersonal() {
  creatingPersonal.value = true
  try {
    const resp = await workspaceApi.ensurePersonalWorkspace()
    message.success('个人空间已创建')
    personalWorkspace.value = resp.data
      ? { id: resp.data.id, name: resp.data.name, description: null }
      : null
    await loadPersonal()
  } catch (e: any) {
    message.error(e?.message || '创建失败')
  } finally {
    creatingPersonal.value = false
  }
}

function enterPersonalHome() {
  domain.enterPersonal()
  router.push('/home')
}

function go(path: string) {
  router.push(path)
}

watch(
  () => domain.domain,
  () => {
    loadPersonal()
  },
)

onMounted(() => {
  loadPersonal()
})
</script>

<style scoped>
.home {
  min-height: calc(100vh - 56px);
  padding: 28px 32px 48px;
  background:
    radial-gradient(ellipse at 12% 0%, rgba(22, 119, 255, 0.07), transparent 42%),
    radial-gradient(ellipse at 88% 8%, rgba(22, 119, 255, 0.05), transparent 40%),
    #f5f5f5;
}

.hero {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.logo-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  height: 36px;
  padding: 0 12px;
  border-radius: 8px;
  background: #1677ff;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

.hero-text h1 {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.88);
}

.hero-text p {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: rgba(0, 0, 0, 0.45);
}

.panel {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  padding: 24px 28px 28px;
  margin-bottom: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
}

.panel-hd h2 {
  margin: 0 0 6px;
  font-size: 17px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.88);
}

.panel-hd p {
  margin: 0 0 20px;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.45);
  line-height: 1.6;
}

.personal-card {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
}

.personal-card strong {
  display: block;
  font-size: 15px;
  color: rgba(0, 0, 0, 0.88);
  margin-bottom: 4px;
}

.muted {
  margin: 0;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.45);
}

.quick-flow {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 8px;
  margin-bottom: 20px;
  padding: 16px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
}

.qf-step {
  flex: 1 1 140px;
  min-width: 140px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid #e6f4ff;
  border-radius: 8px;
}

.qf-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #1677ff;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
}

.qf-step strong {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.88);
}

.qf-step span {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  line-height: 1.5;
}

.qf-arrow {
  display: flex;
  align-items: center;
  color: #91caff;
  font-size: 18px;
  font-weight: 600;
  padding: 0 2px;
  user-select: none;
}

.guide-list {
  margin: 0 0 20px;
  padding-left: 20px;
  color: rgba(0, 0, 0, 0.65);
  font-size: 14px;
  line-height: 1.85;
}

.guide-list strong {
  color: rgba(0, 0, 0, 0.88);
}

.shortcuts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.flow-diagram {
  overflow-x: auto;
  margin-bottom: 20px;
  padding: 12px 8px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
}

.flow-diagram svg {
  display: block;
  width: 100%;
  min-width: 760px;
  height: auto;
}

.flow-diagram .node rect {
  fill: #fff;
  stroke: #d9d9d9;
  stroke-width: 1.2;
}

.flow-diagram .node.accent rect {
  fill: #e6f4ff;
  stroke: #91caff;
}

.flow-diagram .node.ok rect {
  fill: #f6ffed;
  stroke: #b7eb8f;
}

.flow-diagram text {
  fill: rgba(0, 0, 0, 0.88);
  font-size: 13px;
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.flow-diagram text.sub {
  fill: rgba(0, 0, 0, 0.45);
  font-size: 11px;
}

.flow-diagram .deny-label {
  fill: #cf1322;
  font-size: 12px;
}

.flow-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.flow-card {
  padding: 14px 16px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fff;
}

.flow-card h3 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.88);
}

.flow-card p {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: rgba(0, 0, 0, 0.55);
}

.flow-card em {
  font-style: normal;
  color: #1677ff;
  font-weight: 600;
}

.note {
  padding: 12px 14px;
  border-radius: 8px;
  background: #fffbe6;
  border: 1px solid #ffe58f;
  font-size: 13px;
  line-height: 1.7;
  color: rgba(0, 0, 0, 0.65);
}

.note strong {
  color: rgba(0, 0, 0, 0.88);
}

@media (max-width: 1100px) {
  .flow-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .home {
    padding: 20px 16px 32px;
  }

  .qf-arrow {
    display: none;
  }

  .flow-cards {
    grid-template-columns: 1fr;
  }
}
</style>
