<script setup>
import { computed, ref } from 'vue'

import { runShoppingAgent } from '../api'
import AgentResultPanel from './AgentResultPanel.vue'

const props = defineProps({
  pointCode: { type: String, default: '' },
  selectedPointName: { type: String, default: '' },
})

const copy = {
  title: '\u0041\u0049\u0020\u63a1\u8cfc\u6c7a\u7b56\u0020\u0041\u0067\u0065\u006e\u0074\uff08\u6e2c\u8a66\u7248\uff09',
  subtitle: '\u8f38\u5165\u81ea\u7136\u8a9e\u8a00\u8cfc\u7269\u6e05\u55ae\uff0c\u7cfb\u7d71\u6703\u5148\u5224\u65b7\u5546\u54c1\u662f\u5426\u6e05\u695a\u3001\u662f\u5426\u5df2\u6536\u9304\uff0c\u518d\u5c0d\u5df2\u78ba\u8a8d\u5546\u54c1\u8a08\u7b97\u53ef\u6bd4\u8f03\u50f9\u683c\u3002',
  debug: 'Debug mode',
  pointPrefix: '\u76ee\u524d\u63d0\u8ca8\u9ede\uff1a',
  pointFallback: '\u672a\u9078\u6642\u6703\u9810\u8a2d\u4f7f\u7528 p001\u3002',
  queryLabel: '\u8cfc\u7269\u6e05\u55ae',
  queryPlaceholder: '\u4f8b\u5982\uff1a\u5169\u5305\u9eb5 \u4e00\u5305\u85af\u689d \u56db\u5305\u85af\u7247 \u6cb9 \u7cd6 M&M',
  loading: '\u6b63\u5728\u5206\u6790\u8cfc\u7269\u6e05\u55ae...',
  submit: '\u7528 Agent \u5206\u6790',
  helper: '\u5f8c\u7aef\u6703\u8fd4\u56de structured result\uff0c\u50f9\u683c\u4ecd\u7531 deterministic price planner \u8a08\u7b97\u3002',
  emptyQuery: '\u8acb\u5148\u8f38\u5165\u8cfc\u7269\u6e05\u55ae\u3002',
  inputError: '\u8acb\u6aa2\u67e5\u8f38\u5165\u5167\u5bb9\u5f8c\u518d\u8a66\u3002',
  networkError: '\u66ab\u6642\u7121\u6cd5\u9023\u7dda\u5230\u5f8c\u7aef\u670d\u52d9\u3002',
  genericError: '\u5206\u6790\u6642\u767c\u751f\u932f\u8aa4\uff0c\u8acb\u7a0d\u5f8c\u518d\u8a66\u3002',
  advancedTitle: '\u9032\u968e\u8a2d\u5b9a',
  advancedHint: '\u9810\u8a2d\u6703\u4f7f\u7528\u5b89\u5168\u6a21\u5f0f\uff1b\u5373\u4f7f Local LLM / Gemini \u5931\u6557\uff0c\u7cfb\u7d71\u4e5f\u6703\u81ea\u52d5 fallback\u3002',
  plannerMode: 'Planner Mode',
  retrievalMode: 'Retrieval Mode',
  composerMode: 'Composer Mode',
  decisionPolicy: '採購策略 / Decision Policy',
  thresholdLabel: '兩店方案便宜不超過多少 MOP 時，仍建議一間店',
  penaltyLabel: '每多去一間店，視作額外成本 MOP',
}

const query = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)
const debug = ref(false)
const selectedClarifications = ref({})
const lastSubmittedQuery = ref('')
const plannerMode = ref('rule')
const retrievalMode = ref('taxonomy')
const composerMode = ref('template')
const decisionPolicy = ref('cheapest_single_store')
const singleStoreThresholdMop = ref(5)
const extraStorePenaltyMop = ref(5)

const effectivePointCode = computed(() => props.pointCode || 'p001')
const selectedClarificationPayload = computed(() => {
  const payload = {}
  for (const [rawItemName, selection] of Object.entries(selectedClarifications.value)) {
    if (selection?.intent_id) payload[rawItemName] = selection.intent_id
  }
  return payload
})
const canRecalculate = computed(() => !loading.value && Object.keys(selectedClarificationPayload.value).length > 0)
const decisionPolicyOptions = computed(() => {
  if (decisionPolicy.value === 'single_store_preferred') return { single_store_threshold_mop: Number(singleStoreThresholdMop.value) || 5 }
  if (decisionPolicy.value === 'balanced') return { extra_store_penalty_mop: Number(extraStorePenaltyMop.value) || 5 }
  return null
})

function readableAgentError(err) {
  if (err?.status === 400) return err.message || copy.inputError
  if (err?.isNetworkError || err?.message?.includes('Failed to fetch')) return copy.networkError
  return err?.message || copy.genericError
}

async function submitAgent({ useClarifications = false } = {}) {
  const trimmedQuery = query.value.trim()
  if (!trimmedQuery) {
    error.value = copy.emptyQuery
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
      useLlm: false,
      includePricePlan: true,
      priceStrategy: 'cheapest_single_store',
      decisionPolicy: decisionPolicy.value,
      decisionPolicyOptions: decisionPolicyOptions.value,
      clarificationAnswers: useClarifications ? selectedClarificationPayload.value : undefined,
      plannerMode: plannerMode.value,
      retrievalMode: retrievalMode.value,
      composerMode: composerMode.value,
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
</script>

<template>
  <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 class="text-2xl font-semibold text-slate-950">{{ copy.title }}</h2>
        <p class="mt-2 text-base leading-7 text-slate-700">{{ copy.subtitle }}</p>
      </div>
      <label class="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-sm text-slate-700">
        <input v-model="debug" type="checkbox" class="h-4 w-4" />
        {{ copy.debug }}
      </label>
    </div>

    <div class="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
      {{ copy.pointPrefix }}{{ selectedPointName || effectivePointCode }}
      <span v-if="!pointCode" class="text-slate-500">{{ copy.pointFallback }}</span>
    </div>

    <details class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <summary class="cursor-pointer text-sm font-semibold text-slate-900">{{ copy.advancedTitle }}</summary>
      <p class="mt-2 text-sm text-slate-600">{{ copy.advancedHint }}</p>
      <div class="mt-4 grid gap-4 md:grid-cols-4">
        <label class="flex flex-col gap-2 text-sm text-slate-700">
          <span class="font-medium">{{ copy.plannerMode }}</span>
          <select v-model="plannerMode" class="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-950">
            <option value="rule">Rule parser</option>
            <option value="local_llm">Local LLM planner</option>
          </select>
        </label>
        <label class="flex flex-col gap-2 text-sm text-slate-700">
          <span class="font-medium">{{ copy.retrievalMode }}</span>
          <select v-model="retrievalMode" class="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-950">
            <option value="taxonomy">Taxonomy</option>
            <option value="rag_assisted">RAG-assisted</option>
          </select>
        </label>
        <label class="flex flex-col gap-2 text-sm text-slate-700">
          <span class="font-medium">{{ copy.composerMode }}</span>
          <select v-model="composerMode" class="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-950">
            <option value="template">Template</option>
            <option value="gemini">Gemini</option>
          </select>
        </label>
        <label class="flex flex-col gap-2 text-sm text-slate-700">
          <span class="font-medium">{{ copy.decisionPolicy }}</span>
          <select v-model="decisionPolicy" class="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-950">
            <option value="cheapest_single_store">最平一間店</option>
            <option value="cheapest_two_stores">最平最多兩間店</option>
            <option value="single_store_preferred">優先一間店</option>
            <option value="balanced">平衡價格與少走路</option>
          </select>
        </label>
      </div>
      <div v-if="decisionPolicy === 'single_store_preferred'" class="mt-4 max-w-xl">
        <label class="flex flex-col gap-2 text-sm text-slate-700">
          <span class="font-medium">{{ copy.thresholdLabel }}</span>
          <input v-model.number="singleStoreThresholdMop" type="number" min="0" step="0.5" class="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-950" />
        </label>
      </div>
      <div v-if="decisionPolicy === 'balanced'" class="mt-4 max-w-xl">
        <label class="flex flex-col gap-2 text-sm text-slate-700">
          <span class="font-medium">{{ copy.penaltyLabel }}</span>
          <input v-model.number="extraStorePenaltyMop" type="number" min="0" step="0.5" class="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-950" />
        </label>
      </div>
    </details>

    <label class="mt-4 flex flex-col gap-2">
      <span class="text-base font-medium text-slate-800">{{ copy.queryLabel }}</span>
      <textarea v-model="query" rows="5" :placeholder="copy.queryPlaceholder" class="w-full resize-y rounded-xl border border-slate-300 px-4 py-3 text-base leading-7 text-slate-950 outline-none focus:border-slate-700" />
    </label>

    <div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
      <button type="button" class="min-h-12 rounded-xl bg-emerald-700 px-5 text-base font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400" :disabled="loading" @click="submitAgent()">{{ loading ? copy.loading : copy.submit }}</button>
      <p class="text-sm text-slate-500">{{ copy.helper }}</p>
    </div>

    <div class="mt-6">
      <AgentResultPanel :result="result" :loading="loading" :error="error" :debug="debug" :selected-clarifications="selectedClarifications" :can-recalculate="canRecalculate" @select-clarification="selectClarification" @recalculate="submitAgent({ useClarifications: true })" />
    </div>
  </section>
</template>
