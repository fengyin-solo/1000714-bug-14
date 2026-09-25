<template>
  <section class="page" data-module="work">
    <header class="page-head">
      <div>
        <h2>养护施工管理</h2>
        <p class="page-desc">维护施工任务，围绕施工编号、关联计划、承接单位、开工日期做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记施工任务</button>
        <button class="btn" type="button" @click="exportRows">导出养护施工清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ displayCell(column, row) }}</td>
          <td class="row-actions">
            <button class="link" type="button" @click="openDetail(row)">详情</button>
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无养护施工数据，可先登记施工任务</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条养护施工记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <div v-if="detail" class="modal-mask" @click.self="closeDetail">
      <div class="modal-card">
        <header class="modal-head">
          <h3>施工任务详情</h3>
          <button class="link" type="button" @click="closeDetail">关闭</button>
        </header>
        <dl v-if="!editing" class="detail-grid">
          <div v-for="column in columns" :key="column" class="detail-item">
            <dt>{{ column }}</dt>
            <dd>{{ displayCell(column, detail) }}</dd>
          </div>
        </dl>
        <form v-else class="form-grid" @submit.prevent="saveEdit">
          <label v-for="field in editableFields" :key="field" class="form-item">
            <span>{{ field }}</span>
            <input v-model="editForm[field]" :placeholder="`请输入${field}`" />
          </label>
        </form>
        <footer class="modal-actions">
          <template v-if="!editing">
            <button class="btn primary" type="button" @click="startEdit">修改承接信息</button>
          </template>
          <template v-else>
            <button class="btn primary" type="button" @click="saveEdit">保存</button>
            <button class="btn ghost" type="button" @click="cancelEdit">取消</button>
          </template>
        </footer>
        <p v-if="detailError" class="error-text">{{ detailError }}</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/work'
const columns = ["施工编号", "关联计划", "承接单位", "开工日期", "完工日期", "完成工程量", "施工进度", "监理人员", "施工状态"]
const actions = ["确认开工", "提交验收", "确认完工"]
const editableFields = ["关联计划", "承接单位", "开工日期", "完工日期", "完成工程量", "监理人员"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)
const stats = ref([
  { label: '待开工施工', value: 0 },
  { label: '施工中单据', value: 0 },
  { label: '本月完工数', value: 0 },
])
const detail = ref<Row | null>(null)
const editing = ref(false)
const editForm = ref<Record<string, string>>({})
const detailError = ref('')

function displayCell(column: string, row: Row | null): string | number {
  const value = row?.[column]
  if (value === null || value === undefined || value === '') {
    return '—'
  }
  return column === '施工进度' ? `${value}%` : value
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '施工任务登记入口尚未接入审批流'
}

async function openDetail(row: Row) {
  detailError.value = ''
  editing.value = false
  try {
    const response = await request(`${ENDPOINT}/${row.id}`)
    if (!response.ok) {
      throw new Error('施工任务详情读取失败')
    }
    detail.value = await response.json()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '施工任务详情读取失败'
  }
}

function closeDetail() {
  detail.value = null
  editing.value = false
  detailError.value = ''
}

function startEdit() {
  const form: Record<string, string> = {}
  for (const field of editableFields) {
    const value = detail.value?.[field]
    form[field] = value === null || value === undefined ? '' : String(value)
  }
  editForm.value = form
  detailError.value = ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  detailError.value = ''
}

async function saveEdit() {
  if (!detail.value) {
    return
  }
  detailError.value = ''
  try {
    const response = await request(`${ENDPOINT}/${detail.value.id}`, {
      method: 'PUT',
      body: JSON.stringify({ values: editForm.value }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '承接单位保存未生效，请稍后重试')
    }
    detail.value = payload.entry ?? detail.value
    editing.value = false
    await reload()
  } catch (error) {
    detailError.value = error instanceof Error ? error.message : '施工任务保存失败'
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('养护施工动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '养护施工操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const [listResponse, statsResponse] = await Promise.all([
      request(`${ENDPOINT}?${query}`),
      request(`${ENDPOINT}/stats`),
    ])
    if (!listResponse.ok) {
      throw new Error('施工任务列表读取失败')
    }
    const payload = await listResponse.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    if (statsResponse.ok) {
      const statsPayload = await statsResponse.json()
      stats.value = statsPayload.items ?? stats.value
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '养护施工列表读取失败'
  }
}

onMounted(reload)
</script>
