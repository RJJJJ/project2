<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { askBasket, fetchPoints, fetchSignals } from './api'

const defaultText = '我想買一包米、兩支洗頭水、一包紙巾'

const points = ref([])
const pointCode = ref('p001')
const shoppingText = ref(defaultText)
const basketResult = ref(null)
const signals = ref(null)
const error = ref('')
const loadingPoints = ref(false)
const loadingBasket = ref(false)
const loadingSignals = ref(false)

const selectedPoint = computed(() => points.value.find((point) => point.point_code === pointCode.value))

const selectedPlan = computed(() => {
  const plans = basketResult.value?.plans || []
  const recommended = plans.find((plan) => plan.plan_type === basketResult.value?.recommended_plan_type)
  return recommended || plans.find((plan) => plan.estimated_total_mop !== null && plan.estimated_total_mop !== undefined) || plans[0]
})

const otherPlans = computed(() => basketResult.value?.plans || [])
const signalItems = computed(() => signals.value?.largest_price_gap || [])

function money(value) {
  if (value === null || value === undefined) return 'N/A'
  return `${Number(value).toFixed(1)} MOP`
}

function percent(value) {
  if (value === null || value === undefined) return 'N/A'
  return `${Number(value).toFixed(1)}%`
}

function readableError(err) {
  if (err instanceof Error) return err.message
  return String(err || '發生未知錯誤')
}

async function loadPoints() {
  loadingPoints.value = true
  error.value = ''
  try {
    points.value = await fetchPoints()
    if (!points.value.some((point) => point.point_code === pointCode.value) && points.value.length) {
      pointCode.value = points.value[0].point_code
    }
  } catch (err) {
    error.value = readableError(err)
  } finally {
    loadingPoints.value = false
  }
}

async function loadSignals() {
  if (!pointCode.value) return
  loadingSignals.value = true
  error.value = ''
  try {
    signals.value = await fetchSignals(pointCode.value, 5)
  } catch (err) {
    signals.value = null
    error.value = readableError(err)
  } finally {
    loadingSignals.value = false
  }
}

async function generatePlan() {
  loadingBasket.value = true
  error.value = ''
  try {
    basketResult.value = await askBasket({
      text: shoppingText.value,
      pointCode: pointCode.value,
    })
    await loadSignals()
  } catch (err) {
    basketResult.value = null
    error.value = readableError(err)
  } finally {
    loadingBasket.value = false
  }
}

watch(pointCode, () => {
  loadSignals()
})

onMounted(async () => {
  await loadPoints()
  await loadSignals()
})
</script>

<template>
  <main class="min-h-screen">
    <div class="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
      <header class="flex flex-col gap-1 border-b border-slate-200 pb-4">
        <h1 class="text-2xl font-semibold text-slate-950 sm:text-3xl">澳門採購決策 Agent MVP</h1>
        <p class="text-sm text-slate-600">本地採購方案與本區價差訊號</p>
      </header>

      <section class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div class="grid gap-4 md:grid-cols-[260px_minmax(0,1fr)]">
            <label class="flex flex-col gap-2">
              <span class="text-sm font-medium text-slate-700">地區</span>
              <select
                v-model="pointCode"
                class="h-11 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 outline-none focus:border-slate-700"
                :disabled="loadingPoints"
              >
                <option v-for="point in points" :key="point.point_code" :value="point.point_code">
                  {{ point.name }} / {{ point.district }}
                </option>
              </select>
            </label>

            <div class="rounded-md bg-slate-50 p-3 text-sm text-slate-700">
              <div class="font-medium text-slate-900">{{ selectedPoint?.name || pointCode }}</div>
              <div>{{ selectedPoint?.district || 'N/A' }}</div>
            </div>
          </div>

          <label class="mt-4 flex flex-col gap-2">
            <span class="text-sm font-medium text-slate-700">購物清單</span>
            <textarea
              v-model="shoppingText"
              rows="5"
              class="w-full resize-y rounded-md border border-slate-300 px-3 py-2 text-base text-slate-950 outline-none focus:border-slate-700"
            />
          </label>

          <div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              type="button"
              class="h-11 rounded-md bg-slate-950 px-5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
              :disabled="loadingBasket || !shoppingText.trim() || !pointCode"
              @click="generatePlan"
            >
              {{ loadingBasket ? '生成中...' : '生成採購方案' }}
            </button>
            <p v-if="error" class="text-sm text-red-700">{{ error }}</p>
          </div>
        </div>

        <aside class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 class="text-base font-semibold text-slate-950">本區價差訊號</h2>
          <p v-if="loadingSignals" class="mt-3 text-sm text-slate-500">載入中...</p>
          <div v-else-if="signalItems.length" class="mt-3 flex flex-col divide-y divide-slate-100">
            <article v-for="item in signalItems" :key="`${item.product_oid}-${item.product_name}`" class="py-3 first:pt-0">
              <h3 class="text-sm font-medium text-slate-950">{{ item.product_name }}</h3>
              <dl class="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-600">
                <dt>最低價</dt>
                <dd class="text-right text-slate-900">{{ money(item.min_price_mop) }}</dd>
                <dt>最高價</dt>
                <dd class="text-right text-slate-900">{{ money(item.max_price_mop) }}</dd>
                <dt>價差</dt>
                <dd class="text-right text-slate-900">{{ percent(item.gap_percent) }}</dd>
                <dt>最低價超市</dt>
                <dd class="text-right text-slate-900">{{ item.min_supermarket_name || 'N/A' }}</dd>
                <dt>最高價超市</dt>
                <dd class="text-right text-slate-900">{{ item.max_supermarket_name || 'N/A' }}</dd>
              </dl>
            </article>
          </div>
          <p v-else class="mt-3 text-sm text-slate-500">暫無價差訊號。</p>
        </aside>
      </section>

      <section v-if="basketResult" class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div class="grid gap-3 border-b border-slate-100 pb-4 md:grid-cols-3">
          <div>
            <div class="text-xs font-medium uppercase text-slate-500">推薦方案類型</div>
            <div class="mt-1 text-base font-semibold text-slate-950">{{ basketResult.recommended_plan_type || 'N/A' }}</div>
          </div>
          <div>
            <div class="text-xs font-medium uppercase text-slate-500">推薦原因</div>
            <div class="mt-1 text-sm text-slate-800">{{ basketResult.recommendation_reason || 'N/A' }}</div>
          </div>
          <div>
            <div class="text-xs font-medium uppercase text-slate-500">預估總價</div>
            <div class="mt-1 text-base font-semibold text-slate-950">{{ money(selectedPlan?.estimated_total_mop) }}</div>
          </div>
        </div>

        <div class="mt-4">
          <h2 class="text-base font-semibold text-slate-950">建議超市</h2>
          <div class="mt-2 flex flex-wrap gap-2">
            <span
              v-for="store in selectedPlan?.stores || []"
              :key="store.supermarket_oid"
              class="rounded-md bg-slate-100 px-3 py-1 text-sm text-slate-800"
            >
              {{ store.supermarket_name || store.supermarket_oid }}
            </span>
            <span v-if="!(selectedPlan?.stores || []).length" class="text-sm text-slate-500">N/A</span>
          </div>
        </div>

        <div class="mt-5">
          <h2 class="text-base font-semibold text-slate-950">每件商品</h2>
          <div class="mt-3 overflow-x-auto">
            <table class="min-w-[760px] w-full border-collapse text-left text-sm">
              <thead class="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th class="px-3 py-2 font-medium">商品名</th>
                  <th class="px-3 py-2 font-medium">規格</th>
                  <th class="px-3 py-2 font-medium">數量</th>
                  <th class="px-3 py-2 font-medium">單價</th>
                  <th class="px-3 py-2 font-medium">小計</th>
                  <th class="px-3 py-2 font-medium">超市</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="item in selectedPlan?.items || []" :key="`${item.keyword}-${item.product_oid}`">
                  <td class="px-3 py-3 text-slate-950">{{ item.product_name || item.keyword }}</td>
                  <td class="px-3 py-3 text-slate-700">{{ item.package_quantity || 'N/A' }}</td>
                  <td class="px-3 py-3 text-slate-700">{{ item.requested_quantity }}</td>
                  <td class="px-3 py-3 text-slate-700">{{ money(item.unit_price_mop) }}</td>
                  <td class="px-3 py-3 text-slate-700">{{ money(item.subtotal_mop) }}</td>
                  <td class="px-3 py-3 text-slate-700">{{ item.supermarket_name || 'N/A' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="mt-5">
          <h2 class="text-base font-semibold text-slate-950">其他方案摘要</h2>
          <div class="mt-2 grid gap-2 sm:grid-cols-3">
            <article v-for="plan in otherPlans" :key="plan.plan_type" class="rounded-md border border-slate-200 p-3">
              <div class="text-sm font-medium text-slate-950">{{ plan.plan_type }}</div>
              <div class="mt-1 text-sm text-slate-600">{{ money(plan.estimated_total_mop) }}</div>
              <div class="mt-1 text-xs text-slate-500">超市數量：{{ plan.store_count ?? 0 }}</div>
            </article>
          </div>
        </div>
      </section>
    </div>
  </main>
</template>
