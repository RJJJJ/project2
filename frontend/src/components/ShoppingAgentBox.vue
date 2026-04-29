<script setup>
import { computed, ref } from 'vue'

import { runShoppingAgent } from '../api'
import AgentResultPanel from './AgentResultPanel.vue'

const props = defineProps({
  pointCode: {
    type: String,
    default: '',
  },
  selectedPointName: {
    type: String,
    default: '',
  },
})

const copy = {
  title: '\u0041\u0049 \u63a1\u8cfc\u6c7a\u7b56 Agent\uff08\u6e2c\u8a66\u7248\uff09',
  subtitle: '\u8f38\u5165\u81ea\u7136\u8a9e\u8a00\u8cfc\u7269\u6e05\u55ae\uff0c\u7cfb\u7d71\u6703\u5148\u5224\u65b7\u5546\u54c1\u662f\u5426\u6e05\u695a\u3001\u662f\u5426\u5df2\u6536\u9304\uff0c\u518d\u5c0d\u5df2\u78ba\u8a8d\u5546\u54c1\u8a08\u7b97\u53ef\u6bd4\u8f03\u50f9\u683c\u3002',
  debug: 'Debug mode',
  pointPrefix: '\u76ee\u524d\u6bd4\u8f03\u5730\u5340\uff1a',
  pointFallback: '\uff08\u672a\u9078\u5730\u5340\u6642\u6703\u9810\u8a2d\u4f7f\u7528 p001\uff09',
  queryLabel: '\u8cfc\u7269\u6e05\u55ae',
  queryPlaceholder: '\u4f8b\u5982\uff1a\u5169\u5305\u9eb5 \u4e00\u5305\u85af\u689d \u56db\u5305\u85af\u7247 \u6cb9 \u7cd6 M&M',
  loading: '\u6b63\u5728\u5206\u6790\u8cfc\u7269\u6e05\u55ae...',
  submit: '\u7528 Agent \u5206\u6790',
  helper: '\u5f8c\u7aef\u6703\u76f4\u63a5\u8fd4\u56de structured result\uff0c\u50f9\u683c\u8a08\u7b97\u4ecd\u7531\u5f8c\u7aef deterministic \u8655\u7406\u3002',
  emptyQuery: '\u8acb\u5148\u8f38\u5165\u8cfc\u7269\u6e05\u55ae\u3002',
  inputError: '\u8f38\u5165\u5167\u5bb9\u6709\u554f\u984c\uff0c\u8acb\u6aa2\u67e5\u8cfc\u7269\u6e05\u55ae\u3002',
  networkError: '\u672a\u80fd\u9023\u7dda\u5230\u5f8c\u7aef\u670d\u52d9\uff0c\u8acb\u7a0d\u5f8c\u518d\u8a66\u3002',
  genericError: '\u5206\u6790\u6642\u767c\u751f\u932f\u8aa4\uff0c\u8acb\u7a0d\u5f8c\u518d\u8a66\u3002',
}

const query = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)
const debug = ref(false)
const selectedClarifications = ref({})
const lastSubmittedQuery = ref('')

const effectivePointCode = computed(() => props.pointCode || 'p001')
const selectedClarificationPayload = computed(() => {
  const payload = {}
  for (const [rawItemName, selection] of Object.entries(selectedClarifications.value)) {
    if (selection?.intent_id) {
      payload[rawItemName] = selection.intent_id
    }
  }
  return payload
})
const canRecalculate = computed(() => !loading.value && Object.keys(selectedClarificationPayload.value).length > 0)

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

  if (trimmedQuery !== lastSubmittedQuery.value) {
    selectedClarifications.value = {}
  }

  loading.value = true
  error.value = ''

  try {
    result.value = await runShoppingAgent({
      query: trimmedQuery,
      pointCode: effectivePointCode.value,
      useLlm: false,
      includePricePlan: true,
      priceStrategy: 'cheapest_single_store',
      clarificationAnswers: useClarifications ? selectedClarificationPayload.value : undefined,
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
    [rawItemName]: {
      intent_id: option.intent_id,
      label: option.label_zh || option.intent_id,
    },
  }
}
</script>

<template>
  <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 class="text-2xl font-semibold text-slate-950">{{ copy.title }}</h2>
        <p class="mt-2 text-base leading-7 text-slate-700">
          {{ copy.subtitle }}
        </p>
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

    <label class="mt-4 flex flex-col gap-2">
      <span class="text-base font-medium text-slate-800">{{ copy.queryLabel }}</span>
      <textarea
        v-model="query"
        rows="5"
        :placeholder="copy.queryPlaceholder"
        class="w-full resize-y rounded-xl border border-slate-300 px-4 py-3 text-base leading-7 text-slate-950 outline-none focus:border-slate-700"
      />
    </label>

    <div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
      <button
        type="button"
        class="min-h-12 rounded-xl bg-emerald-700 px-5 text-base font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
        :disabled="loading"
        @click="submitAgent()"
      >
        {{ loading ? copy.loading : copy.submit }}
      </button>
      <p class="text-sm text-slate-500">{{ copy.helper }}</p>
    </div>

    <div class="mt-6">
      <AgentResultPanel
        :result="result"
        :loading="loading"
        :error="error"
        :debug="debug"
        :selected-clarifications="selectedClarifications"
        :can-recalculate="canRecalculate"
        @select-clarification="selectClarification"
        @recalculate="submitAgent({ useClarifications: true })"
      />
    </div>
  </section>
</template>
