<template>
  <section class="page" data-module="work-detail">
    <header class="page-head">
      <div>
        <h2>施工任务详情</h2>
        <p class="page-desc">与施工列表读取同一条记录，施工进度、完工日期口径一致；修改后保存即同步。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn ghost" to="/work">返回施工列表</RouterLink>
      </div>
    </header>

    <div v-if="entry" class="detail-card">
      <div class="detail-head">
        <strong>{{ entry['施工编号'] }}</strong>
        <span class="detail-status">{{ entry['施工状态'] ?? entry.status }}</span>
        <span class="detail-progress">施工进度 {{ entry['施工进度'] ?? 0 }}%</span>
      </div>

      <form class="detail-form" @submit.prevent="save">
        <label v-for="field in editableFields" :key="field" class="filter-item">
          <span>{{ field }}</span>
          <input v-model="form[field]" :placeholder="`请输入${field}`" />
        </label>
        <div class="detail-actions">
          <button class="btn primary" type="submit">保存修改</button>
          <button
            v-for="action in actions"
            :key="action"
            class="btn"
            type="button"
            @click="runAction(action)"
          >
            {{ action }}
          </button>
        </div>
      </form>
    </div>

    <footer class="page-foot">
      <span v-if="savedMessage" class="saved-text">{{ savedMessage }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/work'
const editableFields = ["关联计划", "承接单位", "开工日期", "完工日期", "完成工程量", "监理人员"]
const actions = ["确认开工", "提交验收", "确认完工"]

const route = useRoute()
const entry = ref<Row | null>(null)
const form = ref<Record<string, string>>({})
const savedMessage = ref('')
const errorMessage = ref('')

function applyEntry(data: Row) {
  entry.value = data
  const next: Record<string, string> = {}
  for (const field of editableFields) {
    next[field] = data[field] == null ? '' : String(data[field])
  }
  form.value = next
}

async function load() {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${route.params.id}`)
    if (!response.ok) {
      throw new Error('施工任务详情读取失败')
    }
    applyEntry(await response.json())
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '施工任务详情读取失败'
  }
}

async function save() {
  errorMessage.value = ''
  savedMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${route.params.id}`, {
      method: 'PUT',
      body: JSON.stringify({ values: form.value }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message ?? payload.detail ?? '施工任务保存失败')
    }
    if (payload.entry) {
      applyEntry(payload.entry)
    }
    savedMessage.value = payload.message ?? '施工任务已保存'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '施工任务保存失败'
  }
}

async function runAction(action: string) {
  errorMessage.value = ''
  savedMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${route.params.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message ?? '养护施工动作未生效，请稍后重试')
    }
    if (payload.entry) {
      applyEntry(payload.entry)
    }
    savedMessage.value = payload.message ?? `施工任务已${action}`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '养护施工操作失败'
  }
}

onMounted(load)
</script>

<style scoped>
.detail-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
.detail-head {
  display: flex;
  gap: 12px;
  align-items: baseline;
  margin-bottom: 12px;
}
.detail-status {
  color: var(--muted);
  font-size: 13px;
}
.detail-progress {
  color: var(--brand);
  font-size: 13px;
}
.detail-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-end;
}
.detail-actions {
  display: flex;
  gap: 8px;
}
.saved-text {
  color: #067647;
}
</style>
