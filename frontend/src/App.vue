<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { askBasket, fetchPoints, fetchSignals, fetchProductCandidates } from './api'

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
const loadingCandidates = ref(false)
const candidateGroups = ref([])
const selectedCandidateOids = ref({})

const planLabels = {
  cheapest_by_item: '單品最低價',
  cheapest_single_store: '推薦：只去一間店',
  cheapest_two_stores: '最多兩間店',
}

const selectedPoint = computed(() => points.value.find((point) => point.point_code === pointCode.value))

const selectedPlan = computed(() => {
  const plans = basketResult.value?.plans || []
  const recommended = plans.find((plan) => plan.plan_type === basketResult.value?.recommended_plan_type)
  return recommended || plans.find((plan) => plan.estimated_total_mop !== null && plan.estimated_total_mop !== undefined) || plans[0]
})

const otherPlans = computed(() => basketResult.value?.plans || [])
const signalItems = computed(() => signals.value?.largest_price_gap || [])
const hasPlan = computed(() => Boolean(selectedPlan.value?.items?.length))
const selectedProducts = computed(() =>
  candidateGroups.value
    .map((group) => ({
      keyword: group.keyword,
      product_oid: selectedCandidateOids.value[group.keyword],
    }))
    .filter((item) => item.product_oid !== null && item.product_oid !== undefined && item.product_oid !== ''),
)

function planLabel(planType) {
  return planLabels[planType] || '採購方案'
}

function money(value) {
  if (value === null || value === undefined) return 'N/A'
  return `${Number(value).toFixed(1)} MOP`
}

function percent(value) {
  if (value === null || value === undefined) return 'N/A'
  return `${Number(value).toFixed(1)}%`
}

function readableError(err) {
  return '後端服務未啟動或資料尚未準備。'
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

async function findCandidates() {
  loadingCandidates.value = true
  error.value = ''
  basketResult.value = null
  candidateGroups.value = []
  selectedCandidateOids.value = {}
  try {
    const parsedResult = await askBasket({
      text: shoppingText.value,
      pointCode: pointCode.value,
    })
    const items = parsedResult.parsed_items || []
    const groups = await Promise.all(
      items.map(async (item) => {
        const response = await fetchProductCandidates({
          keyword: item.keyword,
          pointCode: pointCode.value,
          limit: 8,
        })
        return {
          keyword: item.keyword,
          quantity: item.quantity,
          candidates: response.candidates || [],
        }
      }),
    )
    const defaults = {}
    groups.forEach((group) => {
      const recommended = group.candidates.find((candidate) => candidate.is_recommended) || group.candidates[0]
      if (recommended) {
        defaults[group.keyword] = recommended.product_oid
      }
    })
    candidateGroups.value = groups
    selectedCandidateOids.value = defaults
    if (!groups.length) {
      error.value = '未能從輸入解析出商品，請嘗試使用米、洗頭水、紙巾等關鍵字。'
    }
    await loadSignals()
  } catch (err) {
    candidateGroups.value = []
    error.value = readableError(err)
  } finally {
    loadingCandidates.value = false
  }
}

async function generatePlanWithSelectedProducts() {
  loadingBasket.value = true
  error.value = ''
  try {
    basketResult.value = await askBasket({
      text: shoppingText.value,
      pointCode: pointCode.value,
      selectedProducts: selectedProducts.value,
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
        <p class="text-sm text-slate-500">資料範圍：所選採集點附近約 500 米。價格只供參考，以店內標示為準。</p>
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
              class="h-11 w-full rounded-md bg-slate-950 px-5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400 sm:w-auto"
              :disabled="loadingBasket || !shoppingText.trim() || !pointCode"
              @click="generatePlan"
            >
              {{ loadingBasket ? '生成中...' : '直接生成方案' }}
            </button>
            <button
              type="button"
              class="h-11 w-full rounded-md border border-slate-300 bg-white px-5 text-sm font-medium text-slate-900 disabled:cursor-not-allowed disabled:bg-slate-100 sm:w-auto"
              :disabled="loadingCandidates || loadingBasket || !shoppingText.trim() || !pointCode"
              @click="findCandidates"
            >
              {{ loadingCandidates ? '查找中...' : '先選商品規格' }}
            </button>
            <p v-if="error" class="text-sm text-red-700">{{ error }}</p>
          </div>
        </div>

        <aside class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 class="text-base font-semibold text-slate-950">本區價差訊號</h2>
          <p v-if="loadingSignals" class="mt-3 text-sm text-slate-500">載入中...</p>
          <div v-else-if="signalItems.length" class="mt-3 grid gap-3">
            <article
              v-for="item in signalItems"
              :key="`${item.product_oid}-${item.product_name}`"
              class="rounded-lg border border-slate-200 bg-slate-50 p-3"
            >
              <div class="flex items-start justify-between gap-3">
                <h3 class="text-sm font-medium leading-5 text-slate-950">{{ item.product_name }}</h3>
                <div class="shrink-0 rounded-md bg-red-50 px-2 py-1 text-base font-semibold text-red-700">
                  {{ percent(item.gap_percent) }}
                </div>
              </div>
              <div class="mt-3 grid grid-cols-2 gap-2 text-sm">
                <div class="rounded-md bg-white p-2">
                  <div class="text-xs text-slate-500">最低價</div>
                  <div class="mt-1 font-medium text-slate-950">{{ money(item.min_price_mop) }}</div>
                  <div class="mt-1 text-xs text-slate-600">{{ item.min_supermarket_name || 'N/A' }}</div>
                </div>
                <div class="rounded-md bg-white p-2">
                  <div class="text-xs text-slate-500">最高價</div>
                  <div class="mt-1 font-medium text-slate-950">{{ money(item.max_price_mop) }}</div>
                  <div class="mt-1 text-xs text-slate-600">{{ item.max_supermarket_name || 'N/A' }}</div>
                </div>
              </div>
            </article>
          </div>
          <p v-else class="mt-3 text-sm text-slate-500">暫無價差訊號。</p>
        </aside>
      </section>

      <section v-if="candidateGroups.length" class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div class="flex flex-col gap-3 border-b border-slate-100 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 class="text-lg font-semibold text-slate-950">確認商品 / 規格</h2>
            <p class="mt-1 text-sm text-slate-600">先選定具體商品，再用所選 product_oid 生成採購方案。</p>
          </div>
          <button
            type="button"
            class="h-11 rounded-md bg-emerald-700 px-5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
            :disabled="loadingBasket"
            @click="generatePlanWithSelectedProducts"
          >
            {{ loadingBasket ? '生成中...' : '使用所選商品生成方案' }}
          </button>
        </div>

        <div class="mt-4 grid gap-4">
          <article
            v-for="group in candidateGroups"
            :key="group.keyword"
            class="rounded-lg border border-slate-200 p-3"
          >
            <div class="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
              <h3 class="text-base font-semibold text-slate-950">{{ group.keyword }} x {{ group.quantity }}</h3>
              <p class="text-sm text-slate-500">候選 {{ group.candidates.length }} 個</p>
            </div>

            <div v-if="group.candidates.length" class="mt-3 grid gap-2">
              <label class="flex cursor-pointer gap-3 rounded-md border border-dashed border-slate-300 bg-slate-50 p-3 hover:bg-slate-100">
                <input
                  v-model="selectedCandidateOids[group.keyword]"
                  type="radio"
                  class="mt-1"
                  :name="`candidate-${group.keyword}`"
                  value=""
                />
                <div>
                  <div class="font-medium text-slate-950">不指定，讓系統推薦</div>
                  <div class="mt-1 text-sm text-slate-600">不傳入 product_oid，使用原有快速匹配與最低價方案。</div>
                </div>
              </label>

              <label
                v-for="candidate in group.candidates"
                :key="`${group.keyword}-${candidate.product_oid}`"
                class="flex cursor-pointer gap-3 rounded-md border p-3 hover:bg-slate-50"
                :class="candidate.is_recommended ? 'border-emerald-300 bg-emerald-50/50' : 'border-slate-200'"
              >
                <input
                  v-model="selectedCandidateOids[group.keyword]"
                  type="radio"
                  class="mt-1"
                  :name="`candidate-${group.keyword}`"
                  :value="candidate.product_oid"
                />
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <div class="font-medium text-slate-950">{{ candidate.product_name }}</div>
                    <span
                      v-if="candidate.is_recommended"
                      class="rounded-full bg-emerald-600 px-2 py-0.5 text-xs font-medium text-white"
                    >
                      系統推薦
                    </span>
                  </div>
                  <div v-if="candidate.is_recommended && candidate.recommendation_reason" class="mt-1 text-sm text-emerald-800">
                    {{ candidate.recommendation_reason }}
                  </div>
                  <div class="mt-1 grid gap-1 text-sm text-slate-600 sm:grid-cols-4">
                    <div>規格：{{ candidate.package_quantity || 'N/A' }}</div>
                    <div>類別：{{ candidate.category_name || 'N/A' }}</div>
                    <div>價格：{{ money(candidate.min_price_mop) }} - {{ money(candidate.max_price_mop) }}</div>
                    <div>覆蓋超市：{{ candidate.store_count }}</div>
                  </div>
                  <div class="mt-1 text-xs text-slate-500">
                    product_oid: {{ candidate.product_oid }}
                    <span v-if="candidate.sample_supermarkets?.length">
                      · {{ candidate.sample_supermarkets.join('、') }}
                    </span>
                  </div>
                </div>
              </label>
            </div>

            <p v-else class="mt-3 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
              暫時找不到候選商品，將由系統用原有方式嘗試匹配。
            </p>
          </article>
        </div>
      </section>

      <section v-if="basketResult" class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div v-if="!hasPlan" class="rounded-md bg-slate-50 p-4 text-sm text-slate-700">
          暫時找不到完整採購方案，請嘗試更換商品名稱或地區。
        </div>

        <div v-else class="border-b border-slate-100 pb-4">
          <div class="text-sm font-medium text-slate-500">推薦方案</div>
          <div class="mt-1 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 class="text-2xl font-semibold text-slate-950">{{ planLabel(selectedPlan?.plan_type) }}</h2>
              <p class="mt-2 text-sm text-slate-700">{{ basketResult.recommendation_reason || 'N/A' }}</p>
            </div>
            <div class="text-left sm:text-right">
              <div class="text-xs font-medium uppercase text-slate-500">預估總價</div>
              <div class="mt-1 text-3xl font-semibold text-slate-950">{{ money(selectedPlan?.estimated_total_mop) }}</div>
            </div>
          </div>
        </div>

        <div v-if="hasPlan" class="mt-4">
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

        <div v-if="hasPlan" class="mt-5">
          <h2 class="text-base font-semibold text-slate-950">每件商品</h2>
          <div class="mt-3 overflow-x-auto">
            <table class="min-w-[860px] w-full border-collapse text-left text-sm">
              <thead class="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th class="px-3 py-2 font-medium">商品名</th>
                  <th class="px-3 py-2 font-medium">Product OID</th>
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
                  <td class="px-3 py-3 text-slate-700">{{ item.product_oid || 'N/A' }}</td>
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

        <div v-if="basketResult.warnings?.length" class="mt-5 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
          <div class="font-medium">提示</div>
          <ul class="mt-1 list-disc pl-5">
            <li v-for="warning in basketResult.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </div>

        <div class="mt-5">
          <h2 class="text-base font-semibold text-slate-950">其他方案摘要</h2>
          <div class="mt-2 grid gap-2 sm:grid-cols-3">
            <article v-for="plan in otherPlans" :key="plan.plan_type" class="rounded-md border border-slate-200 p-3">
              <div class="text-sm font-medium text-slate-950">{{ planLabel(plan.plan_type) }}</div>
              <div class="mt-1 text-sm text-slate-600">{{ money(plan.estimated_total_mop) }}</div>
              <div class="mt-1 text-xs text-slate-500">超市數量：{{ plan.store_count ?? 0 }}</div>
            </article>
          </div>
        </div>
      </section>
    </div>
  </main>
</template>
