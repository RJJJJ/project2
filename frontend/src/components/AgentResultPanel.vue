<script setup>
import { computed } from 'vue'

const props = defineProps({
  isSenior: { type: Boolean, default: false },
  result: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  selectedClarifications: { type: Object, default: () => ({}) },
  canRecalculate: { type: Boolean, default: false },
})

const emit = defineEmits(['select-clarification', 'recalculate'])

const diagnostics = computed(() => props.result?.diagnostics || {})
const routerDecision = computed(() => props.result?.query_router || {})
const queryType = computed(() => routerDecision.value.query_type || '')
const bestPlan = computed(() => props.result?.price_plan?.decision_result?.best_recommendation || props.result?.price_plan?.best_plan || null)
const alternatives = computed(() => (props.result?.price_plan?.decision_result?.alternatives || []).filter((plan) => plan && plan !== bestPlan.value).slice(0, 3))
const ambiguousItems = computed(() => props.result?.ambiguous_items || [])
const notCoveredItems = computed(() => props.result?.not_covered_items || [])
const unsupportedItems = computed(() => props.result?.unsupported_items || [])
const candidateSummary = computed(() => props.result?.candidate_summary || [])
const firstRagFeatures = computed(() => {
  for (const summary of candidateSummary.value) {
    for (const candidate of summary.top_candidates || []) {
      if (candidate.rag_features) return candidate.rag_features
    }
  }
  return null
})
const recommendedStoreText = computed(() => (bestPlan.value ? storeNames(bestPlan.value) : '未有推薦'))
const calculateSavings = computed(() => {
  if (!bestPlan.value) return '0.0'
  const totals = [bestPlan.value, ...(props.result?.price_plan?.decision_result?.alternatives || [])]
    .map((plan) => Number(plan?.estimated_total_mop || 0))
    .filter((value) => Number.isFinite(value) && value > 0)
  const savings = Math.max(...totals, 0) - Number(bestPlan.value.estimated_total_mop || 0)
  return savings > 0 ? savings.toFixed(1) : '0.0'
})

function formatMoney(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A'
  return props.isSenior ? `$${Number(value).toFixed(1)}` : `MOP ${Number(value).toFixed(2)}`
}
function storeNames(plan) {
  return (plan?.supermarket_names || [plan?.supermarket_name]).filter(Boolean).join(' / ') || '未知超市'
}
function itemStoreName(item, plan) {
  return item?.selected_store_name || plan?.supermarket_name || storeNames(plan)
}
function itemDisplayName(item) {
  return item?.selected_product_name || item?.raw_item_name || '已選商品'
}
function itemPrice(item) {
  return item?.subtotal_mop ?? item?.unit_price_mop
}
function clarificationOptions(item) {
  return item?.clarification_options || []
}
function isSelected(rawItemName, intentId) {
  return props.selectedClarifications?.[rawItemName]?.intent_id === intentId
}
function selectOption(rawItemName, option) {
  emit('select-clarification', { rawItemName, option })
}
function routerNoticeText() {
  if (queryType.value === 'brand_search') return '你沒有指定口味 / 規格，以下先列出目前收錄的相關品牌商品。'
  if (queryType.value === 'direct_product_search') return '已按你輸入的商品名稱查價。'
  if (queryType.value === 'partial_product_search') return '已找到相近商品並按保守規則查價。'
  if (queryType.value === 'subjective_recommendation' || queryType.value === 'unsupported_request') return '目前沒有口味 / 健康 / 評分資料；可以改為查最便宜、列出收錄款式，或指定品牌查價。'
  return ''
}
</script>

<template>
  <div class="min-w-0 transition-all duration-300">
    <div v-if="loading" :class="isSenior ? 'rounded-[2rem] border-4 border-orange-100 bg-orange-50 p-6 text-2xl font-black text-[#FF6B00] shadow-xl' : 'rounded-2xl border border-[#E4E1D8] bg-white p-5 text-sm font-semibold text-[#6E685A] shadow-sm'">
      {{ isSenior ? '計緊數，請等一等...' : '正在分析購物任務...' }}
    </div>

    <div v-else-if="error" :class="isSenior ? 'rounded-[2rem] border-4 border-red-200 bg-red-50 p-6 text-2xl font-black text-red-700 shadow-xl' : 'rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700'">
      {{ error }}
    </div>

    <div v-else-if="!result" :class="isSenior ? 'rounded-[2rem] border-4 border-slate-100 bg-white p-8 text-center shadow-xl' : 'rounded-2xl border border-[#E4E1D8] bg-white p-6 shadow-sm'">
      <template v-if="isSenior">
        <p class="text-5xl">🧾</p>
        <h3 class="mt-3 text-3xl font-black text-slate-900">輸入清單後即刻幫你格價</h3>
        <p class="mt-3 text-xl font-bold leading-8 text-slate-600">會先顯示最推薦超市、總價和慳咗幾多。</p>
      </template>
      <template v-else>
        <p class="text-xs font-semibold uppercase tracking-[0.18em] text-[#8A826F]">Decision Workspace</p>
        <h3 class="mt-2 text-xl font-bold text-[#44413A]">等待購物任務</h3>
        <p class="mt-2 max-w-xl text-sm leading-6 text-[#6E685A]">普通模式會以表格和診斷摘要呈現，方便檢查查價依據。</p>
      </template>
    </div>

    <template v-else>
      <div :class="isSenior ? 'space-y-6' : 'space-y-5'">
        <section v-if="routerNoticeText()" :class="isSenior ? 'rounded-[2rem] border-4 border-orange-100 bg-orange-50 p-5 text-xl font-black text-slate-900 shadow-lg' : 'rounded-2xl border border-[#E4E1D8] bg-[#F2F1EC] p-4 text-sm font-semibold text-[#5F5A4D]'">
          {{ routerNoticeText() }}
        </section>

        <details v-if="!isSenior" class="rounded-2xl border border-[#E4E1D8] bg-white p-4 text-sm shadow-sm">
          <summary class="cursor-pointer font-semibold text-[#8A826F]">Debug: Router / RAG / Composer</summary>
          <div class="mt-3 grid gap-2 text-[#5F5A4D] sm:grid-cols-3">
            <div>query_type: {{ queryType }}</div>
            <div>confidence: {{ routerDecision.confidence }}</div>
            <div>llm_router_used: {{ diagnostics.llm_router_used || 'disabled' }}</div>
            <div>merge: {{ diagnostics.router_merge_decision || 'disabled' }}</div>
            <div>retrieval_mode: {{ diagnostics.retrieval_mode }}</div>
            <div>composer_used: {{ diagnostics.composer_used }}</div>
          </div>
          <pre v-if="firstRagFeatures" class="mt-3 overflow-auto rounded-xl bg-slate-50 p-3 text-xs">{{ firstRagFeatures }}</pre>
        </details>

        <section v-if="bestPlan && !isSenior" class="overflow-hidden rounded-2xl border border-[#E4E1D8] bg-white shadow-sm">
          <div class="flex flex-col gap-3 border-b border-[#E4E1D8] bg-[#F2F1EC] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.18em] text-[#8A826F]">Recommended Plan</p>
              <h3 class="mt-1 text-lg font-bold text-[#44413A]">推薦方案：{{ recommendedStoreText }}</h3>
            </div>
            <p class="text-2xl font-bold tabular-nums text-[#C4B997]">{{ formatMoney(bestPlan.estimated_total_mop) }}</p>
          </div>
          <table class="min-w-full divide-y divide-[#E4E1D8] text-left text-sm">
            <thead class="bg-[#FBFBFA] text-xs font-semibold uppercase tracking-wide text-[#8A826F]">
              <tr><th class="px-4 py-3">輸入</th><th class="px-4 py-3">商品</th><th class="px-4 py-3">超市</th><th class="px-4 py-3 text-right">價格</th></tr>
            </thead>
            <tbody class="divide-y divide-[#E4E1D8] text-[#44413A]">
              <tr v-for="item in bestPlan.items || []" :key="`${item.raw_item_name}-${item.selected_product_name}-${itemStoreName(item, bestPlan)}`">
                <td class="px-4 py-3 font-medium">{{ item.raw_item_name }}</td>
                <td class="px-4 py-3">{{ itemDisplayName(item) }}</td>
                <td class="px-4 py-3">{{ itemStoreName(item, bestPlan) }}</td>
                <td class="px-4 py-3 text-right font-semibold tabular-nums">{{ formatMoney(itemPrice(item)) }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section v-if="bestPlan && isSenior" class="relative overflow-hidden rounded-[2.5rem] border-8 border-[#00875A] bg-white p-6 shadow-2xl sm:p-8">
          <div class="absolute right-0 top-0 rounded-bl-3xl bg-[#00875A] px-6 py-3 text-lg font-black text-white">最推介方案</div>
          <p class="pr-28 text-xl font-black text-slate-500">去呢度買最平：</p>
          <h3 class="mt-3 text-4xl font-black leading-tight text-[#00875A] sm:text-5xl">{{ recommendedStoreText }}</h3>
          <div class="my-6 grid grid-cols-1 gap-4 rounded-3xl border-4 border-slate-100 bg-slate-50 p-5 sm:grid-cols-2">
            <div class="rounded-2xl bg-white p-5 text-center shadow-lg">
              <p class="text-lg font-black text-slate-500">預計總共要畀</p>
              <p class="mt-2 text-4xl font-black tabular-nums text-[#FF6B00] sm:text-5xl">{{ formatMoney(bestPlan.estimated_total_mop) }}</p>
            </div>
            <div class="rounded-2xl bg-[#FF6B00] p-5 text-center text-white shadow-lg">
              <p class="text-lg font-black">比起其他方案</p>
              <p class="mt-2 text-4xl font-black tabular-nums sm:text-5xl">慳咗 ${{ calculateSavings }}</p>
            </div>
          </div>
          <div class="mt-8 space-y-4">
            <h4 class="border-l-8 border-[#FF6B00] pl-4 text-2xl font-black text-slate-900">詳細清單</h4>
            <article v-for="item in bestPlan.items || []" :key="`senior-${item.raw_item_name}-${item.selected_product_name}`" class="rounded-3xl border-2 border-slate-100 bg-white p-5 shadow-lg">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <p class="text-xl font-black text-slate-900">{{ item.raw_item_name }}</p>
                  <p class="mt-1 text-lg font-bold leading-7 text-slate-600">{{ itemDisplayName(item) }}</p>
                </div>
                <p class="shrink-0 text-3xl font-black tabular-nums text-[#FF6B00]">{{ formatMoney(itemPrice(item)) }}</p>
              </div>
            </article>
          </div>
        </section>

        <section v-if="!bestPlan && (unsupportedItems.length || result.status === 'unsupported')" :class="isSenior ? 'rounded-[2rem] border-4 border-yellow-300 bg-yellow-50 p-6 shadow-xl' : 'rounded-2xl border border-yellow-200 bg-yellow-50 p-5 shadow-sm'">
          <h3 :class="isSenior ? 'text-2xl font-black text-yellow-900' : 'text-base font-bold text-yellow-900'">資料限制提示</h3>
          <p :class="isSenior ? 'mt-2 text-lg font-bold text-yellow-900' : 'mt-2 text-sm leading-6 text-yellow-900'">{{ result.user_message_zh }}</p>
        </section>

        <section v-if="ambiguousItems.length" :class="isSenior ? 'rounded-[2rem] border-4 border-yellow-400 bg-yellow-50 p-6 shadow-2xl' : 'rounded-2xl border border-[#D4C9A8] bg-[#F2F1EC] p-5 shadow-sm'">
          <h3 :class="isSenior ? 'text-3xl font-black text-yellow-900' : 'text-lg font-bold text-[#44413A]'">{{ isSenior ? '請確認商品類型' : '需要確認的商品' }}</h3>
          <div :class="isSenior ? 'mt-6 space-y-6' : 'mt-4 space-y-4'">
            <div v-for="item in ambiguousItems" :key="`ambiguous-${item.raw_item_name}`" :class="isSenior ? 'rounded-3xl bg-white p-5 shadow-lg' : 'rounded-xl bg-white p-4'">
              <p :class="isSenior ? 'text-2xl font-black text-slate-900' : 'font-semibold text-[#44413A]'">「{{ item.raw_item_name }}」係指：</p>
              <div :class="isSenior ? 'mt-4 grid gap-3' : 'mt-3 flex flex-wrap gap-2'">
                <button v-for="option in clarificationOptions(item)" :key="`${item.raw_item_name}-${option.intent_id}`" type="button" :class="['font-black transition-all duration-300 active:scale-95', isSenior ? 'h-16 w-full rounded-2xl border-4 px-4 text-xl shadow-lg' : 'rounded-full border px-4 py-2 text-sm', isSelected(item.raw_item_name, option.intent_id) ? 'border-yellow-500 bg-yellow-400 text-slate-950' : 'border-slate-100 bg-white text-slate-900 hover:border-yellow-400']" @click="selectOption(item.raw_item_name, option)">
                  {{ option.label_zh || option.intent_id }}
                </button>
              </div>
            </div>
          </div>
          <button type="button" :class="isSenior ? 'mt-5 h-20 w-full rounded-2xl bg-yellow-600 text-2xl font-black text-white shadow-lg' : 'mt-5 h-11 w-full rounded-xl bg-[#C4B997] text-sm font-black text-white'" :disabled="!canRecalculate" @click="emit('recalculate')">重新計算價格</button>
        </section>

        <section v-if="notCoveredItems.length" :class="isSenior ? 'rounded-[2rem] border-4 border-slate-100 bg-white p-6 shadow-xl' : 'rounded-2xl border border-[#E4E1D8] bg-white p-5 shadow-sm'">
          <h3 :class="isSenior ? 'text-2xl font-black text-slate-900' : 'text-base font-bold text-[#44413A]'">暫未收錄</h3>
          <div :class="isSenior ? 'mt-4 grid gap-3' : 'mt-3 flex flex-wrap gap-2'">
            <div v-for="item in notCoveredItems" :key="`not-covered-${item.raw_item_name}`" :class="isSenior ? 'rounded-2xl bg-slate-50 p-4 text-xl font-black text-slate-700' : 'rounded-full bg-[#F2F1EC] px-3 py-1 text-sm font-semibold text-[#6E685A]'">{{ item.raw_item_name }}</div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>
