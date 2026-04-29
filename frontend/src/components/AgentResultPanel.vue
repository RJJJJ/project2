<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  debug: { type: Boolean, default: false },
  selectedClarifications: { type: Object, default: () => ({}) },
  canRecalculate: { type: Boolean, default: false },
})

const emit = defineEmits(['select-clarification', 'recalculate'])

const copy = {
  statusMessages: {
    ok: '\u5df2\u6839\u64da\u76ee\u524d\u516c\u958b\u76e3\u6e2c\u50f9\u683c\uff0c\u751f\u6210\u53ef\u6bd4\u8f03\u65b9\u6848\u3002',
    needs_clarification: '\u90e8\u5206\u5546\u54c1\u9700\u8981\u4f60\u78ba\u8a8d\u985e\u578b\u3002\u4ee5\u4e0b\u50f9\u683c\u53ea\u5305\u542b\u5df2\u78ba\u8a8d\u5546\u54c1\u3002',
    partial: '\u90e8\u5206\u5546\u54c1\u5df2\u53ef\u8a08\u50f9\uff0c\u90e8\u5206\u5546\u54c1\u66ab\u672a\u6536\u9304\u6216\u9700\u8981\u78ba\u8a8d\u3002',
    not_covered: '\u76ee\u524d\u8f38\u5165\u7684\u5546\u54c1\u672a\u80fd\u5728\u516c\u958b\u76e3\u6e2c\u8cc7\u6599\u4e2d\u627e\u5230\u53ef\u6bd4\u8f03\u50f9\u683c\u3002',
    error: '\u5206\u6790\u6642\u767c\u751f\u932f\u8aa4\uff0c\u8acb\u7a0d\u5f8c\u518d\u8a66\u3002',
  },
  dataCoverageMessage: '\u672c\u7cfb\u7d71\u4f7f\u7528\u6fb3\u9580\u6d88\u8cbb\u8005\u59d4\u54e1\u6703\u516c\u958b\u76e3\u6e2c\u5546\u54c1\u8cc7\u6599\uff0c\u4e26\u975e\u6db5\u84cb\u6240\u6709\u8d85\u5e02\u5546\u54c1\u3002\u82e5\u986f\u793a\u300c\u66ab\u672a\u6536\u9304\u300d\uff0c\u4ee3\u8868\u76ee\u524d\u6c92\u6709\u516c\u958b\u53ef\u6bd4\u8f03\u50f9\u683c\u8cc7\u6599\uff0c\u4e0d\u4ee3\u8868\u8a72\u5546\u54c1\u4e0d\u5b58\u5728\u6216\u8d85\u5e02\u6c92\u6709\u552e\u8ce3\u3002',
  temporaryPricingMessage: '\u7531\u65bc\u90e8\u5206\u5546\u54c1\u4ecd\u9700\u78ba\u8a8d\uff0c\u4e0b\u65b9\u50f9\u683c\u53ea\u5305\u542b\u5df2\u78ba\u8a8d\u5546\u54c1\uff0c\u4e0d\u4ee3\u8868\u5b8c\u6574\u8cfc\u7269\u6e05\u55ae\u7e3d\u50f9\u3002',
  unresolvedCoverageMessage: '\u4ee5\u4e0b\u5546\u54c1\u76ee\u524d\u6c92\u6709\u516c\u958b\u53ef\u6bd4\u8f03\u50f9\u683c\u3002\u4f60\u53ef\u4ee5\u6539\u67e5\u76f8\u8fd1\u985e\u578b\uff0c\u6216\u5148\u7565\u904e\u9019\u4e9b\u5546\u54c1\u3002',
  ambiguityHint: '\u4ee5\u4e0b\u5546\u54c1\u6709\u591a\u7a2e\u53ef\u80fd\u610f\u601d\uff0c\u8acb\u9078\u64c7\u4f60\u60f3\u67e5\u7684\u985e\u578b\u3002',
  summaryTitle: '\u5206\u6790\u6458\u8981',
  resolvedTitle: '\u5df2\u7406\u89e3\u7684\u5546\u54c1',
  resolvedEmpty: '\u76ee\u524d\u672a\u6709\u5df2\u7406\u89e3\u5546\u54c1\u3002',
  resolvedAsPrefix: '\u5df2\u7406\u89e3\u70ba\u300c',
  resolvedAsSuffix: '\u300d',
  candidatePrefix: '\u5019\u9078\u5546\u54c1\uff1a',
  candidateCountPrefix: '\u5019\u9078\u6578\u91cf\uff1a',
  ambiguousTitle: '\u9700\u8981\u4f60\u78ba\u8a8d',
  recalculate: '\u6309\u4ee5\u4e0a\u9078\u64c7\u91cd\u65b0\u8a08\u7b97',
  notCoveredTitle: '\u66ab\u672a\u6536\u9304',
  pricePlanTitleDefault: '\u53ef\u8a08\u50f9\u65b9\u6848',
  bestPlanTitle: '\u6700\u4fbf\u5b9c\u65b9\u6848',
  temporaryPlanTitle: '\u5df2\u78ba\u8a8d\u5546\u54c1\u7684\u66ab\u6642\u8a08\u50f9',
  noPlan: '\u76ee\u524d\u672a\u80fd\u627e\u5230\u5b8c\u6574\u53ef\u8a08\u50f9\u65b9\u6848\u3002',
  storeLabel: '\u8d85\u5e02',
  totalLabel: '\u4f30\u7b97\u7e3d\u50f9',
  unknownStore: '\u672a\u63d0\u4f9b\u8d85\u5e02\u540d\u7a31',
  unknownProduct: '\u672a\u63d0\u4f9b\u5546\u54c1\u540d\u7a31',
  quantityLabel: '\u6578\u91cf\uff1a',
  unitPriceLabel: '\u55ae\u50f9\uff1a',
  packageLabel: '\u5305\u88dd\uff1a',
  packageFallback: '\u672a\u63d0\u4f9b',
  warningsTitle: '\u63d0\u9192',
  debugTitle: 'Debug \u8cc7\u8a0a',
  loading: '\u6b63\u5728\u5206\u6790\u8cfc\u7269\u6e05\u55ae...',
}

const candidateSummaryMap = computed(() => {
  const map = {}
  for (const summary of props.result?.candidate_summary || []) {
    if (summary?.raw_item_name) map[summary.raw_item_name] = summary
  }
  return map
})
const diagnostics = computed(() => props.result?.diagnostics || {})
const composerDiagnostics = computed(() => props.result?.composer_diagnostics || {})
const resolvedItems = computed(() => props.result?.resolved_items || [])
const ambiguousItems = computed(() => props.result?.ambiguous_items || [])
const notCoveredItems = computed(() => props.result?.not_covered_items || [])
const bestPlan = computed(() => props.result?.price_plan?.best_plan || null)
const pricePlanTitle = computed(() => {
  if (props.result?.status === 'ok') return copy.bestPlanTitle
  if (props.result?.status === 'partial' || props.result?.status === 'needs_clarification') return copy.temporaryPlanTitle
  return copy.pricePlanTitleDefault
})
const debugJson = computed(() => JSON.stringify(props.result, null, 2))

function formatMoney(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A'
  return `MOP ${Number(value).toFixed(2)}`
}
function summaryFor(rawItemName) { return candidateSummaryMap.value[rawItemName] || null }
function resolvedLabel(item) { return item?.intent_display_name_zh || summaryFor(item?.raw_item_name)?.intent_display_name_zh || '' }
function topCandidateName(rawItemName) { return summaryFor(rawItemName)?.top_candidates?.[0]?.product_name || '' }
function candidateCount(rawItemName, fallbackCount) { return fallbackCount ?? summaryFor(rawItemName)?.candidates_count ?? null }
function clarificationOptions(item) {
  if (item?.clarification_options?.length) return item.clarification_options
  return (item?.resolution?.intent_options || []).map((intentId) => ({ intent_id: intentId, label_zh: intentId }))
}
function isSelected(rawItemName, intentId) { return props.selectedClarifications?.[rawItemName]?.intent_id === intentId }
function selectOption(rawItemName, option) { emit('select-clarification', { rawItemName, option }) }
</script>

<template>
  <div class="grid gap-4">
    <article v-if="loading" class="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-700">{{ copy.loading }}</article>
    <article v-else-if="error" class="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-800">{{ error }}</article>

    <template v-else-if="result">
      <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 class="text-lg font-semibold text-slate-950">{{ copy.summaryTitle }}</h3>
            <p class="mt-2 text-sm leading-6 text-slate-700">{{ copy.statusMessages[result.status] || copy.statusMessages.error }}</p>
            <p v-if="result.user_message_zh" class="mt-2 text-sm leading-6 text-slate-600">{{ result.user_message_zh }}</p>
          </div>
          <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium uppercase tracking-wide text-slate-600">{{ result.status || 'unknown' }}</span>
        </div>
        <p class="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">{{ copy.dataCoverageMessage }}</p>
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 class="text-lg font-semibold text-slate-950">{{ copy.resolvedTitle }}</h3>
        <div v-if="resolvedItems.length" class="mt-4 grid gap-3">
          <article v-for="item in resolvedItems" :key="`resolved-${item.raw_item_name}-${item.intent_id}`" class="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4">
            <div class="text-base font-semibold text-slate-950">{{ item.raw_item_name }}</div>
            <p v-if="resolvedLabel(item)" class="mt-1 text-sm text-slate-700">{{ copy.resolvedAsPrefix }}{{ resolvedLabel(item) }}{{ copy.resolvedAsSuffix }}</p>
            <p v-if="topCandidateName(item.raw_item_name)" class="mt-2 text-sm text-slate-700">{{ copy.candidatePrefix }}{{ topCandidateName(item.raw_item_name) }}</p>
            <p v-if="candidateCount(item.raw_item_name, item.candidates_count) !== null" class="mt-1 text-xs text-slate-500">{{ copy.candidateCountPrefix }}{{ candidateCount(item.raw_item_name, item.candidates_count) }}</p>
          </article>
        </div>
        <p v-else class="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">{{ copy.resolvedEmpty }}</p>
      </article>

      <article v-if="ambiguousItems.length" class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 class="text-lg font-semibold text-slate-950">{{ copy.ambiguousTitle }}</h3>
        <p class="mt-2 text-sm leading-6 text-slate-700">{{ copy.ambiguityHint }}</p>
        <div class="mt-4 grid gap-4">
          <article v-for="item in ambiguousItems" :key="`ambiguous-${item.raw_item_name}`" class="rounded-xl border border-amber-200 bg-amber-50/70 p-4">
            <div class="text-base font-semibold text-slate-950">{{ item.raw_item_name }}</div>
            <p v-if="item.message_zh" class="mt-1 text-sm text-slate-700">{{ item.message_zh }}</p>
            <div class="mt-3 flex flex-wrap gap-2">
              <button v-for="option in clarificationOptions(item)" :key="`${item.raw_item_name}-${option.intent_id}`" type="button" class="rounded-full border px-4 py-2 text-sm font-medium transition" :class="isSelected(item.raw_item_name, option.intent_id) ? 'border-emerald-700 bg-emerald-700 text-white' : 'border-slate-300 bg-white text-slate-800 hover:bg-slate-50'" @click="selectOption(item.raw_item_name, option)">{{ option.label_zh || option.intent_id }}</button>
            </div>
          </article>
        </div>
        <button type="button" class="mt-5 min-h-11 rounded-xl bg-emerald-700 px-5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400" :disabled="!canRecalculate" @click="emit('recalculate')">{{ copy.recalculate }}</button>
      </article>

      <article v-if="notCoveredItems.length" class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 class="text-lg font-semibold text-slate-950">{{ copy.notCoveredTitle }}</h3>
        <p class="mt-2 text-sm leading-6 text-slate-700">{{ copy.unresolvedCoverageMessage }}</p>
        <ul class="mt-4 grid gap-2 text-sm text-slate-800">
          <li v-for="item in notCoveredItems" :key="`not-covered-${item.raw_item_name}`" class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">{{ item.raw_item_name }}</li>
        </ul>
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 class="text-lg font-semibold text-slate-950">{{ pricePlanTitle }}</h3>
        <p v-if="result.status === 'needs_clarification' || result.status === 'partial'" class="mt-2 rounded-xl bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">{{ copy.temporaryPricingMessage }}</p>
        <div v-if="bestPlan" class="mt-4 grid gap-4">
          <div class="rounded-xl bg-emerald-50 p-4">
            <div class="text-sm font-medium text-emerald-800">{{ copy.storeLabel }}</div>
            <div class="mt-1 text-xl font-semibold text-slate-950">{{ bestPlan.supermarket_name || copy.unknownStore }}</div>
            <div class="mt-3 text-sm font-medium text-emerald-800">{{ copy.totalLabel }}</div>
            <div class="mt-1 text-3xl font-bold text-slate-950">{{ formatMoney(bestPlan.estimated_total_mop) }}</div>
          </div>
          <div class="grid gap-3">
            <article v-for="item in bestPlan.items || []" :key="`best-plan-${item.raw_item_name}-${item.selected_product_name}`" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div class="text-base font-semibold text-slate-950">{{ item.raw_item_name }}</div>
                  <div class="mt-1 text-sm text-slate-700">{{ item.selected_product_name || copy.unknownProduct }}</div>
                </div>
                <div class="text-sm font-semibold text-slate-900">{{ formatMoney(item.subtotal_mop) }}</div>
              </div>
              <div class="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-3">
                <div>{{ copy.quantityLabel }}{{ item.quantity || 1 }}</div>
                <div>{{ copy.unitPriceLabel }}{{ formatMoney(item.unit_price_mop) }}</div>
                <div>{{ copy.packageLabel }}{{ item.package_quantity || copy.packageFallback }}</div>
              </div>
            </article>
          </div>
        </div>
        <p v-else class="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">{{ copy.noPlan }}</p>
        <div v-if="result.price_plan?.warnings?.length" class="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">
          <div class="font-semibold">{{ copy.warningsTitle }}</div>
          <ul class="mt-2 list-disc pl-5"><li v-for="warning in result.price_plan.warnings" :key="warning">{{ warning }}</li></ul>
        </div>
      </article>

      <details v-if="debug" class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <summary class="cursor-pointer text-sm font-semibold text-slate-900">{{ copy.debugTitle }}</summary>
        <div class="mt-4 grid gap-3 text-sm text-slate-700 sm:grid-cols-2 lg:grid-cols-3">
          <div class="rounded-xl bg-slate-50 p-3">status: {{ result.status }}</div>
          <div class="rounded-xl bg-slate-50 p-3">price_plan.status: {{ result.price_plan?.status || 'N/A' }}</div>
          <div class="rounded-xl bg-slate-50 p-3">planner_used: {{ diagnostics.planner_used || 'N/A' }}</div>
          <div class="rounded-xl bg-slate-50 p-3">retrieval_mode: {{ diagnostics.retrieval_mode || 'N/A' }}</div>
          <div class="rounded-xl bg-slate-50 p-3">composer_used: {{ diagnostics.composer_used || composerDiagnostics.composer_used || 'N/A' }}</div>
          <div class="rounded-xl bg-slate-50 p-3">composer_mode: {{ composerDiagnostics.composer_mode || diagnostics.composer_mode || 'N/A' }}</div>
        </div>
        <div v-if="(diagnostics.planner_errors || []).length || (composerDiagnostics.composer_errors || []).length" class="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">
          <div class="font-semibold">Fallback / errors</div>
          <ul class="mt-2 list-disc pl-5">
            <li v-for="item in diagnostics.planner_errors || []" :key="`planner-${item}`">planner: {{ item }}</li>
            <li v-for="item in composerDiagnostics.composer_errors || []" :key="`composer-${item}`">composer: {{ item }}</li>
          </ul>
        </div>
        <pre class="mt-4 overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">{{ debugJson }}</pre>
      </details>
    </template>
  </div>
</template>
