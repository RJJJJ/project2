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

const candidateSummaryMap = computed(() => {
  const map = {}
  for (const summary of props.result?.candidate_summary || []) {
    if (summary?.raw_item_name) map[summary.raw_item_name] = summary
  }
  return map
})
const resolvedItems = computed(() => props.result?.resolved_items || [])
const ambiguousItems = computed(() => props.result?.ambiguous_items || [])
const notCoveredItems = computed(() => props.result?.not_covered_items || [])
const decisionResult = computed(() => props.result?.price_plan?.decision_result || null)
const bestPlan = computed(() => decisionResult.value?.best_recommendation || props.result?.price_plan?.best_plan || null)
const alternatives = computed(() => {
  const plans = decisionResult.value?.alternatives || []
  return plans.filter((plan) => plan && plan !== bestPlan.value).slice(0, 3)
})
const recommendedStoreText = computed(() => bestPlan.value ? storeNames(bestPlan.value) : '未有推薦')
const calculateSavings = computed(() => {
  if (!bestPlan.value) return '0.0'
  const totals = [bestPlan.value, ...(decisionResult.value?.alternatives || [])]
    .map((plan) => Number(plan?.estimated_total_mop || 0))
    .filter((value) => Number.isFinite(value) && value > 0)
  if (!totals.length) return '0.0'
  const savings = Math.max(...totals) - Number(bestPlan.value.estimated_total_mop || 0)
  return savings > 0 ? savings.toFixed(1) : '0.0'
})
const pricedItemCount = computed(() => bestPlan.value?.items?.length || 0)
const totalItemCount = computed(() => resolvedItems.value.length + ambiguousItems.value.length + notCoveredItems.value.length)
const coverageText = computed(() => `${pricedItemCount.value}/${totalItemCount.value || pricedItemCount.value || 0}`)

function formatMoney(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A'
  return props.isSenior ? `$${Number(value).toFixed(1)}` : `MOP ${Number(value).toFixed(2)}`
}
function summaryFor(rawItemName) { return candidateSummaryMap.value[rawItemName] || null }
function topCandidateName(rawItemName) { return summaryFor(rawItemName)?.top_candidates?.[0]?.product_name || '' }
function clarificationOptions(item) {
  if (item?.clarification_options?.length) return item.clarification_options
  return (item?.resolution?.intent_options || []).map((intentId) => ({ intent_id: intentId, label_zh: intentId }))
}
function isSelected(rawItemName, intentId) { return props.selectedClarifications?.[rawItemName]?.intent_id === intentId }
function selectOption(rawItemName, option) { emit('select-clarification', { rawItemName, option }) }
function storeNames(plan) {
  const names = plan?.supermarket_names || [plan?.supermarket_name]
  return names.filter(Boolean).join('、') || '未能確認店名'
}
function itemStoreName(item, plan) { return item?.selected_store_name || plan?.supermarket_name || storeNames(plan) }
function itemDisplayName(item) { return item?.selected_product_name || topCandidateName(item?.raw_item_name) || '待確認商品' }
function itemPrice(item) { return item?.subtotal_mop ?? item?.unit_price_mop }
function planDifference(plan) {
  if (!bestPlan.value?.estimated_total_mop || !plan?.estimated_total_mop) return 'N/A'
  return formatMoney(Number(plan.estimated_total_mop) - Number(bestPlan.value.estimated_total_mop))
}
</script>

<template>
  <div class="min-w-0 transition-all duration-300">
    <div
      v-if="loading"
      :class="isSenior ? 'rounded-[2rem] border-4 border-orange-100 bg-orange-50 p-6 text-2xl font-black text-[#FF6B00] shadow-xl' : 'rounded-2xl border border-[#E4E1D8] bg-white p-5 text-sm font-semibold text-[#6E685A] shadow-sm'"
    >
      {{ isSenior ? '正在幫你格價，請稍等...' : '正在分析購物任務與價格方案...' }}
    </div>

    <div
      v-else-if="error"
      :class="isSenior ? 'rounded-[2rem] border-4 border-red-200 bg-red-50 p-6 text-2xl font-black text-red-700 shadow-xl' : 'rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700'"
    >
      {{ error }}
    </div>

    <div
      v-else-if="!result"
      :class="isSenior ? 'rounded-[2rem] border-4 border-slate-100 bg-white p-8 text-center shadow-xl' : 'rounded-2xl border border-[#E4E1D8] bg-white p-6 shadow-sm'"
    >
      <template v-if="isSenior">
        <p class="text-5xl">👆</p>
        <h3 class="mt-3 text-3xl font-black text-slate-900">輸入清單後，即刻睇最抵方案</h3>
        <p class="mt-3 text-xl font-bold leading-8 text-slate-600">結果會用大字顯示推薦超市、總價同慳咗幾多錢。</p>
      </template>
      <template v-else>
        <p class="text-xs font-semibold uppercase tracking-[0.18em] text-[#8A826F]">Decision Workspace</p>
        <h3 class="mt-2 text-xl font-bold text-[#44413A]">等待購物任務</h3>
        <p class="mt-2 max-w-xl text-sm leading-6 text-[#6E685A]">提交清單後，這裡會以結構化資料面板呈現推薦超市、總價、商品明細與替代方案。</p>
      </template>
    </div>

    <template v-else>
      <div :class="isSenior ? 'space-y-6' : 'space-y-5'">
        <template v-if="!isSenior">
          <section class="overflow-hidden rounded-2xl border border-[#E4E1D8] bg-white shadow-sm">
            <div class="flex flex-col gap-3 border-b border-[#E4E1D8] bg-[#F2F1EC] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.18em] text-[#8A826F]">Recommended Plan</p>
                <h3 class="mt-1 text-lg font-bold text-[#44413A]">推薦方案：{{ recommendedStoreText }}</h3>
              </div>
              <div class="text-left sm:text-right">
                <p class="text-xs font-semibold uppercase tracking-wide text-[#8A826F]">Estimated total</p>
                <p class="text-2xl font-bold tabular-nums text-[#C4B997]">{{ formatMoney(bestPlan?.estimated_total_mop) }}</p>
              </div>
            </div>

            <div class="grid gap-px bg-[#E4E1D8] text-sm sm:grid-cols-4">
              <div class="bg-white px-4 py-3">
                <p class="text-xs font-semibold uppercase tracking-wide text-[#8A826F]">Coverage</p>
                <p class="mt-1 font-bold text-[#44413A]">{{ coverageText }}</p>
              </div>
              <div class="bg-white px-4 py-3">
                <p class="text-xs font-semibold uppercase tracking-wide text-[#8A826F]">Stores</p>
                <p class="mt-1 font-bold text-[#44413A]">{{ bestPlan?.store_count || (bestPlan ? 1 : 'N/A') }}</p>
              </div>
              <div class="bg-white px-4 py-3">
                <p class="text-xs font-semibold uppercase tracking-wide text-[#8A826F]">Savings range</p>
                <p class="mt-1 font-bold tabular-nums text-[#00875A]">{{ formatMoney(calculateSavings) }}</p>
              </div>
              <div class="bg-white px-4 py-3">
                <p class="text-xs font-semibold uppercase tracking-wide text-[#8A826F]">Status</p>
                <p class="mt-1 font-bold text-[#44413A]">{{ result.status || 'ok' }}</p>
              </div>
            </div>

            <div v-if="bestPlan" class="overflow-x-auto">
              <table class="min-w-full divide-y divide-[#E4E1D8] text-left text-sm">
                <thead class="bg-[#FBFBFA] text-xs font-semibold uppercase tracking-wide text-[#8A826F]">
                  <tr>
                    <th class="px-4 py-3">輸入商品</th>
                    <th class="px-4 py-3">比對商品</th>
                    <th class="px-4 py-3">超市</th>
                    <th class="px-4 py-3 text-right">單價/小計</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[#E4E1D8] text-[#44413A]">
                  <tr v-for="item in bestPlan.items || []" :key="`best-plan-default-${item.raw_item_name}-${item.selected_product_name}-${itemStoreName(item, bestPlan)}`" class="hover:bg-[#F2F1EC]/70">
                    <td class="px-4 py-3 font-medium">{{ item.raw_item_name }}</td>
                    <td class="min-w-64 px-4 py-3 text-[#5F5A4D]">{{ itemDisplayName(item) }}</td>
                    <td class="px-4 py-3 text-[#6E685A]">{{ itemStoreName(item, bestPlan) }}</td>
                    <td class="px-4 py-3 text-right font-semibold tabular-nums text-[#44413A]">{{ formatMoney(itemPrice(item)) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <p v-else class="px-5 py-4 text-sm text-[#6E685A]">暫時未能計出完整推薦方案。</p>
          </section>
        </template>

        <template v-else>
          <section v-if="bestPlan" class="relative overflow-hidden rounded-[2.5rem] border-8 border-[#00875A] bg-white p-6 shadow-2xl sm:p-8">
            <div class="absolute right-0 top-0 rounded-bl-3xl bg-[#00875A] px-6 py-3 text-lg font-black text-white">最推介方案</div>

            <p class="pr-28 text-xl font-black text-slate-500">經過計算，最推薦去：</p>
            <h3 class="mt-3 text-4xl font-black leading-tight text-[#00875A] sm:text-5xl">{{ recommendedStoreText }}</h3>

            <div class="my-6 grid grid-cols-1 gap-4 rounded-3xl border-4 border-slate-100 bg-slate-50 p-5 sm:grid-cols-2">
              <div class="rounded-2xl bg-white p-5 text-center shadow-lg">
                <p class="text-lg font-black text-slate-500">總計約需</p>
                <p class="mt-2 text-4xl font-black tabular-nums text-[#FF6B00] sm:text-5xl">{{ formatMoney(bestPlan.estimated_total_mop) }}</p>
              </div>
              <div class="rounded-2xl bg-[#FF6B00] p-5 text-center text-white shadow-lg">
                <p class="text-lg font-black">比起其他方案</p>
                <p class="mt-2 text-4xl font-black tabular-nums sm:text-5xl">慳咗 ${{ calculateSavings }}</p>
              </div>
            </div>

            <div class="grid gap-3 sm:grid-cols-3">
              <div class="rounded-2xl bg-green-50 p-4 text-center">
                <p class="text-base font-bold text-slate-500">已格價商品</p>
                <p class="text-2xl font-black text-[#00875A]">{{ coverageText }}</p>
              </div>
              <div class="rounded-2xl bg-green-50 p-4 text-center">
                <p class="text-base font-bold text-slate-500">需去店舖</p>
                <p class="text-2xl font-black text-[#00875A]">{{ bestPlan.store_count || 1 }} ?</p>
              </div>
              <div class="rounded-2xl bg-green-50 p-4 text-center">
                <p class="text-base font-bold text-slate-500">資料狀態</p>
                <p class="text-2xl font-black text-[#00875A]">{{ result.status || 'ok' }}</p>
              </div>
            </div>

            <div class="mt-8 space-y-4">
              <h4 class="border-l-8 border-[#FF6B00] pl-4 text-2xl font-black text-slate-900">詳細購物清單</h4>
              <article
                v-for="item in bestPlan.items || []"
                :key="`best-plan-senior-${item.raw_item_name}-${item.selected_product_name}-${itemStoreName(item, bestPlan)}`"
                class="rounded-3xl border-2 border-slate-100 bg-white p-5 shadow-lg"
              >
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="text-xl font-black text-slate-900">{{ item.raw_item_name }}</p>
                    <p class="mt-1 text-lg font-bold leading-7 text-slate-600">{{ itemDisplayName(item) }}</p>
                    <p class="mt-2 inline-flex rounded-full bg-slate-100 px-4 py-2 text-base font-black text-slate-700">{{ itemStoreName(item, bestPlan) }}</p>
                  </div>
                  <p class="shrink-0 text-3xl font-black tabular-nums text-[#FF6B00]">{{ formatMoney(itemPrice(item)) }}</p>
                </div>
              </article>
            </div>
          </section>

          <section v-else class="rounded-[2rem] border-4 border-yellow-300 bg-yellow-50 p-6 shadow-xl">
            <h3 class="text-2xl font-black text-yellow-900">暫時未能計出完整推薦方案</h3>
            <p class="mt-2 text-lg font-bold text-yellow-800">可以先回答下面問題，或者換一個更清楚的商品名稱再試。</p>
          </section>
        </template>

        <section
          v-if="ambiguousItems.length"
          :class="isSenior ? 'rounded-[2rem] border-4 border-yellow-400 bg-yellow-50 p-6 shadow-2xl' : 'rounded-2xl border border-[#D4C9A8] bg-[#F2F1EC] p-5 shadow-sm'"
        >
          <h3 :class="isSenior ? 'text-3xl font-black text-yellow-900' : 'text-lg font-bold text-[#44413A]'">{{ isSenior ? '請問你想買邊款？' : '需要澄清的商品' }}</h3>
          <p :class="isSenior ? 'mt-2 text-xl font-bold text-yellow-800' : 'mt-1 text-sm leading-6 text-[#6E685A]'">揀清楚之後，系統會重新計算推薦方案。</p>

          <div :class="isSenior ? 'mt-6 space-y-6' : 'mt-4 space-y-4'">
            <div v-for="item in ambiguousItems" :key="`ambiguous-${item.raw_item_name}`" :class="isSenior ? 'rounded-3xl bg-white p-5 shadow-lg' : 'rounded-xl bg-white p-4'">
              <p :class="isSenior ? 'text-2xl font-black text-slate-900' : 'font-semibold text-[#44413A]'">「{{ item.raw_item_name }}」係指：</p>
              <p v-if="item.message_zh" :class="isSenior ? 'mt-2 text-lg font-bold text-slate-600' : 'mt-1 text-sm text-[#6E685A]'">{{ item.message_zh }}</p>
              <div :class="isSenior ? 'mt-4 grid gap-3' : 'mt-3 flex flex-wrap gap-2'">
                <button
                  v-for="option in clarificationOptions(item)"
                  :key="`${item.raw_item_name}-${option.intent_id}`"
                  type="button"
                  :class="[
                    'font-black transition-all duration-300 active:scale-95',
                    isSenior
                      ? 'h-16 w-full rounded-2xl border-4 px-4 text-xl shadow-lg'
                      : 'rounded-full border px-4 py-2 text-sm',
                    isSelected(item.raw_item_name, option.intent_id)
                      ? (isSenior ? 'border-yellow-500 bg-yellow-400 text-slate-950' : 'border-[#C4B997] bg-[#C4B997] text-white')
                      : (isSenior ? 'border-slate-100 bg-white text-slate-900 hover:border-yellow-400' : 'border-[#E4E1D8] bg-white text-[#44413A] hover:border-[#C4B997]'),
                  ]"
                  @click="selectOption(item.raw_item_name, option)"
                >
                  {{ option.label_zh || option.intent_id }}
                </button>
              </div>
            </div>
          </div>

          <button
            type="button"
            :class="[
              'mt-5 w-full font-black transition-all duration-300 active:scale-95 disabled:cursor-not-allowed disabled:bg-slate-300',
              isSenior ? 'h-20 rounded-2xl bg-yellow-600 text-2xl text-white shadow-lg hover:bg-yellow-700' : 'h-11 rounded-xl bg-[#C4B997] text-sm text-white hover:bg-[#B5AA87]',
            ]"
            :disabled="!canRecalculate"
            @click="emit('recalculate')"
          >
            重新計算價格
          </button>
        </section>

        <section v-if="alternatives.length" :class="isSenior ? 'rounded-[2rem] border-4 border-slate-100 bg-white p-6 shadow-xl' : 'rounded-2xl border border-[#E4E1D8] bg-white p-5 shadow-sm'">
          <h3 :class="isSenior ? 'text-2xl font-black text-slate-900' : 'text-base font-bold text-[#44413A]'">其他方案參考</h3>
          <div :class="isSenior ? 'mt-4 grid gap-4' : 'mt-4 overflow-hidden rounded-xl border border-[#E4E1D8]'">
            <template v-if="isSenior">
              <article v-for="(plan, index) in alternatives" :key="`alt-card-${storeNames(plan)}-${plan.estimated_total_mop}`" class="rounded-3xl bg-slate-50 p-5 shadow">
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <p class="text-lg font-black text-slate-500">方案 {{ index + 2 }}</p>
                    <p class="text-xl font-black text-slate-900">{{ storeNames(plan) }}</p>
                  </div>
                  <div class="text-right">
                    <p class="text-2xl font-black text-[#FF6B00]">{{ formatMoney(plan.estimated_total_mop) }}</p>
                    <p class="text-base font-bold text-slate-500">貴 {{ planDifference(plan) }}</p>
                  </div>                </div>
              </article>
            </template>
            <table v-else class="min-w-full divide-y divide-[#E4E1D8] text-left text-sm">
              <thead class="bg-[#F2F1EC] text-xs font-semibold uppercase tracking-wide text-[#8A826F]">
                <tr>
                  <th class="px-4 py-3">Rank</th>
                  <th class="px-4 py-3">Stores</th>
                  <th class="px-4 py-3 text-right">Total</th>
                  <th class="px-4 py-3 text-right">Diff</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[#E4E1D8] text-[#44413A]">
                <tr v-for="(plan, index) in alternatives" :key="`alt-row-${storeNames(plan)}-${plan.estimated_total_mop}`" class="hover:bg-[#F2F1EC]/70">
                  <td class="px-4 py-3 text-[#6E685A]">{{ index + 2 }}</td>
                  <td class="px-4 py-3 font-medium">{{ storeNames(plan) }}</td>
                  <td class="px-4 py-3 text-right tabular-nums">{{ formatMoney(plan.estimated_total_mop) }}</td>
                  <td class="px-4 py-3 text-right tabular-nums text-[#6E685A]">{{ planDifference(plan) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-if="notCoveredItems.length" :class="isSenior ? 'rounded-[2rem] border-4 border-slate-100 bg-white p-6 shadow-xl' : 'rounded-2xl border border-[#E4E1D8] bg-white p-5 shadow-sm'">
          <h3 :class="isSenior ? 'text-2xl font-black text-slate-900' : 'text-base font-bold text-[#44413A]'">以下商品暫時未有足夠價格資料</h3>
          <div :class="isSenior ? 'mt-4 grid gap-3' : 'mt-3 flex flex-wrap gap-2'">
            <div v-for="item in notCoveredItems" :key="`not-covered-${item.raw_item_name}`" :class="isSenior ? 'rounded-2xl bg-slate-50 p-4 text-xl font-black text-slate-700' : 'rounded-full bg-[#F2F1EC] px-3 py-1 text-sm font-semibold text-[#6E685A]'">
              {{ item.raw_item_name }}
            </div>
          </div>
        </section>

        <section v-if="result.price_plan?.warnings?.length" :class="isSenior ? 'rounded-[2rem] border-4 border-yellow-200 bg-yellow-50 p-6 shadow-xl' : 'rounded-2xl border border-yellow-200 bg-yellow-50 p-5 shadow-sm'">
          <h3 :class="isSenior ? 'text-2xl font-black text-yellow-900' : 'text-base font-bold text-yellow-900'">溫馨提示</h3>
          <ul :class="isSenior ? 'mt-3 list-disc space-y-2 pl-6 text-lg font-bold leading-8 text-yellow-900' : 'mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-yellow-900'">
            <li v-for="warning in result.price_plan.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </section>
      </div>
    </template>
  </div>
</template>
