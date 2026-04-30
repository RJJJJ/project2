<script setup>
import { computed, onMounted, ref } from 'vue'

import { runShoppingAgent } from '../api'
import AgentResultPanel from './AgentResultPanel.vue'

const props = defineProps({
  isSenior: { type: Boolean, default: false },
  pointCode: { type: String, default: '' },
  selectedPointName: { type: String, default: '' },
})

const query = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)
const selectedClarifications = ref({})
const lastSubmittedQuery = ref('')
const showDeveloperControls = ref(false)
const showDeveloperSettings = ref(false)

const retrievalMode = ref('rag_v2')
const composerMode = ref('template')
const llmRouterEnabled = ref(true)
const llmRouterProvider = ref('gemini')
const llmRouterModel = ref('')

const effectivePointCode = computed(() => props.pointCode || 'p001')
const selectedClarificationPayload = computed(() => {
  const payload = {}
  for (const [rawItemName, selection] of Object.entries(selectedClarifications.value)) {
    if (selection?.intent_id) payload[rawItemName] = selection.intent_id
  }
  return payload
})
const canRecalculate = computed(() => !loading.value && Object.keys(selectedClarificationPayload.value).length > 0)

const effectiveSettings = computed(() => {
  if (!showDeveloperControls.value) {
    return {
      retrievalMode: 'rag_v2',
      composerMode: 'template',
      llmRouterEnabled: true,
      llmRouterProvider: 'gemini',
      llmRouterModel: null,
    }
  }
  return {
    retrievalMode: retrievalMode.value,
    composerMode: composerMode.value,
    llmRouterEnabled: llmRouterEnabled.value,
    llmRouterProvider: llmRouterProvider.value,
    llmRouterModel: llmRouterModel.value || null,
  }
})

function detectDebugMode() {
  if (typeof window === 'undefined') return false
  const urlDebug = new URLSearchParams(window.location.search).get('debug') === '1'
  const storageDebug = window.localStorage.getItem('project2_debug') === '1'
  return urlDebug || storageDebug
}

function readableAgentError(err) {
  if (err?.status === 400) return err.message || '查詢格式有誤，請調整後再試。'
  if (err?.isNetworkError || err?.message?.includes('Failed to fetch')) return '目前無法連線到查價服務，請稍後再試。'
  return err?.message || '查價時發生未預期問題，請稍後再試。'
}

function setQuickQuery(value) {
  query.value = value
}

async function submitAgent({ useClarifications = false } = {}) {
  const trimmedQuery = query.value.trim()
  if (!trimmedQuery) {
    error.value = '請先輸入想購買的商品、品牌或購物清單。'
    result.value = null
    return
  }
  if (trimmedQuery !== lastSubmittedQuery.value) selectedClarifications.value = {}
  loading.value = true
  error.value = ''
  try {
    result.value = await runShoppingAgent({
      query: trimmedQuery,
      pointCode: effectivePointCode.value,
      includePricePlan: true,
      priceStrategy: 'cheapest_single_store',
      decisionPolicy: 'cheapest_single_store',
      clarificationAnswers: useClarifications ? selectedClarificationPayload.value : undefined,
      plannerMode: 'rule',
      retrievalMode: effectiveSettings.value.retrievalMode,
      composerMode: effectiveSettings.value.composerMode,
      llmRouterEnabled: effectiveSettings.value.llmRouterEnabled,
      llmRouterProvider: effectiveSettings.value.llmRouterProvider,
      llmRouterModel: effectiveSettings.value.llmRouterModel,
    })
    lastSubmittedQuery.value = trimmedQuery
  } catch (err) {
    result.value = null
    error.value = readableAgentError(err)
  } finally {
    loading.value = false
  }
}

function selectClarification({ rawItemName, option }) {
  selectedClarifications.value = {
    ...selectedClarifications.value,
    [rawItemName]: { intent_id: option.intent_id, label: option.label_zh || option.intent_id },
  }
}

onMounted(() => {
  showDeveloperControls.value = detectDebugMode()
})
</script>

<template>
  <section :class="['grid transition-all duration-300', isSenior ? 'gap-8' : 'gap-6']">
    <div
      :class="[
        'transition-all duration-300',
        isSenior
          ? 'rounded-[2rem] border-4 border-slate-100 bg-white p-6 shadow-2xl'
          : 'rounded-2xl border border-[#E4E1D8] bg-white p-5 shadow-sm',
      ]"
    >
      <div :class="['flex flex-wrap items-start justify-between gap-3', isSenior ? 'mb-5' : 'mb-4']">
        <div>
          <p v-if="!isSenior" class="text-xs font-semibold uppercase tracking-[0.18em] text-[#8A826F]">Shopping Mission Analyzer</p>
          <h2 :class="['font-black transition-all duration-300', isSenior ? 'text-3xl text-slate-900' : 'mt-1 text-xl text-[#44413A]']">
            輸入購物需求
          </h2>
          <p :class="isSenior ? 'mt-2 text-lg font-bold text-slate-600' : 'mt-2 text-sm leading-6 text-[#6E685A]'">
            可輸入購物清單、品牌或部分商品名，系統會自動判斷是否需要澄清，並根據公開價格資料生成採購方案。
          </p>
        </div>
        <span :class="isSenior ? 'rounded-full bg-slate-100 px-4 py-2 text-lg font-bold text-slate-700' : 'rounded-full bg-[#F2F1EC] px-3 py-1 text-xs font-semibold text-[#6E685A]'">
          {{ selectedPointName || effectivePointCode }}
        </span>
      </div>

      <label class="block">
        <span :class="isSenior ? 'mb-3 block text-xl font-black text-slate-900' : 'mb-2 block text-sm font-semibold text-[#5F5A4D]'">
          {{ isSenior ? '購物查詢' : '購物查詢 / Query' }}
        </span>
        <textarea
          v-model="query"
          :rows="isSenior ? 5 : 4"
          placeholder="例如：我想買砂糖、牙膏同洗頭水"
          :class="[
            'w-full resize-y outline-none transition-all duration-300 focus:bg-white',
            isSenior
              ? 'min-h-[190px] rounded-2xl border-4 border-slate-200 bg-slate-50 p-5 text-2xl font-bold leading-9 text-slate-900 shadow-inner placeholder:text-slate-400 focus:border-[#FF6B00]'
              : 'min-h-[120px] rounded-xl border border-[#E4E1D8] bg-[#FBFBFA] px-4 py-3 text-base leading-7 text-[#44413A] placeholder:text-[#8A826F] focus:border-[#C4B997]',
          ]"
        />
      </label>

      <div :class="isSenior ? 'mt-4 flex flex-wrap items-center gap-3' : 'mt-3 flex flex-wrap items-center gap-2'">
        <span :class="isSenior ? 'text-lg font-black text-slate-500' : 'text-xs font-semibold uppercase tracking-wide text-[#8A826F]'">快速示例</span>
        <button type="button" :class="isSenior ? 'rounded-full bg-orange-50 px-4 py-2 text-lg font-black text-[#FF6B00] shadow transition active:scale-95' : 'rounded-full bg-[#F2F1EC] px-3 py-1 text-xs font-semibold text-[#6E685A] hover:bg-[#E4E1D8]'" @click="setQuickQuery('我想買砂糖同洗頭水')">砂糖 + 洗頭水</button>
        <button type="button" :class="isSenior ? 'rounded-full bg-orange-50 px-4 py-2 text-lg font-black text-[#FF6B00] shadow transition active:scale-95' : 'rounded-full bg-[#F2F1EC] px-3 py-1 text-xs font-semibold text-[#6E685A] hover:bg-[#E4E1D8]'" @click="setQuickQuery('出前一丁麻油味')">出前一丁麻油味</button>
        <button type="button" :class="isSenior ? 'rounded-full bg-orange-50 px-4 py-2 text-lg font-black text-[#FF6B00] shadow transition active:scale-95' : 'rounded-full bg-[#F2F1EC] px-3 py-1 text-xs font-semibold text-[#6E685A] hover:bg-[#E4E1D8]'" @click="setQuickQuery('BB用嘅濕紙巾')">BB 用濕紙巾</button>
      </div>

      <div v-if="showDeveloperControls" class="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 class="text-sm font-bold text-slate-800 sm:text-base">開發者設定</h3>
            <p class="mt-1 text-xs leading-5 text-slate-600 sm:text-sm">只在 debug 模式顯示，可覆蓋預設智能查價設定與查看診斷資訊。</p>
          </div>
          <button type="button" class="text-sm font-bold text-slate-700 underline" @click="showDeveloperSettings = !showDeveloperSettings">
            {{ showDeveloperSettings ? '收起技術設定' : '顯示技術設定' }}
          </button>
        </div>

        <div v-if="showDeveloperSettings" class="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <label class="grid gap-1 font-bold text-slate-700">
            Retrieval Mode
            <select v-model="retrievalMode" class="rounded-xl border border-slate-200 bg-white px-3 py-2 font-medium">
              <option value="taxonomy">Taxonomy</option>
              <option value="rag_assisted">RAG v1</option>
              <option value="rag_v2">RAG v2</option>
            </select>
          </label>
          <label class="grid gap-1 font-bold text-slate-700">
            Composer
            <select v-model="composerMode" class="rounded-xl border border-slate-200 bg-white px-3 py-2 font-medium">
              <option value="template">Template</option>
              <option value="gemini">Gemini</option>
            </select>
          </label>
          <label class="flex items-center gap-2 font-bold text-slate-700">
            <input v-model="llmRouterEnabled" type="checkbox" class="h-5 w-5" />
            Use AI router
          </label>
          <label class="grid gap-1 font-bold text-slate-700">
            Router Provider
            <select v-model="llmRouterProvider" class="rounded-xl border border-slate-200 bg-white px-3 py-2 font-medium">
              <option value="gemini">Gemini</option>
              <option value="local_llm">Local LLM</option>
            </select>
          </label>
          <label class="grid gap-1 font-bold text-slate-700 sm:col-span-2">
            Router Model (optional)
            <input v-model="llmRouterModel" class="rounded-xl border border-slate-200 bg-white px-3 py-2 font-medium" placeholder="gemini-2.5-flash / qwen3:4b" />
          </label>
        </div>
      </div>

      <p class="mt-4 text-xs leading-5 text-[#8A826F]">
        AI 理解不可用時，系統會自動使用本地規則與 RAG v2 fallback。
      </p>

      <button
        type="button"
        :class="[
          'mt-6 w-full font-black transition-all duration-300 active:scale-[0.98] disabled:cursor-not-allowed disabled:bg-slate-400',
          isSenior
            ? 'h-20 rounded-[1.5rem] bg-[#FF6B00] text-3xl text-white shadow-[0_8px_0_0_#CC5600] active:translate-y-1 active:shadow-none hover:bg-[#E66000]'
            : 'h-12 rounded-xl bg-[#C4B997] text-base text-white shadow-lg hover:bg-[#B5AA87]',
        ]"
        :disabled="loading"
        @click="submitAgent()"
      >
        {{ loading ? (isSenior ? '分析中…' : '查價中…') : '開始查價' }}
      </button>
    </div>

    <AgentResultPanel
      :is-senior="isSenior"
      :result="result"
      :loading="loading"
      :error="error"
      :selected-clarifications="selectedClarifications"
      :can-recalculate="canRecalculate"
      :show-debug-panel="showDeveloperControls"
      @select-clarification="selectClarification"
      @recalculate="submitAgent({ useClarifications: true })"
    />
  </section>
</template>
