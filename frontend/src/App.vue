<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import { fetchHistoricalSignals, fetchPoints } from './api'
import ShoppingAgentBox from './components/ShoppingAgentBox.vue'

const isSeniorMode = ref(false)
const pointCode = ref('p001')
const points = ref([])
const loadingPoints = ref(false)
const pointsError = ref('')
const historicalSignals = ref(null)
const loadingHistoricalSignals = ref(false)
const historicalSignalsError = ref('')

const NOT_ENOUGH_HISTORY_WARNING = 'Not enough historical dates for historical comparison.'
const PROCESSED_DATA_MISSING_PREFIX = 'Processed data not found'

const districtGroups = [
  { key: 'north', label: '北區 / 黑沙環 / 關閘一帶' },
  { key: 'central', label: '中區 / 高士德 / 新馬路一帶' },
  { key: 'south', label: '南區 / 筷子基 / 下環一帶' },
  { key: 'islands', label: '離島 / 氹仔 / 路環' },
]

const selectedPoint = computed(() => points.value.find((point) => point.point_code === pointCode.value))
const selectedPointName = computed(() => selectedPoint.value?.name || pointCode.value)
const historicalSignalItems = computed(() => historicalSignals.value?.signals || [])
const historicalSignalWarnings = computed(() => historicalSignals.value?.warnings || [])

const dataFreshnessLabel = computed(() => {
  const day = new Date().getDay()
  return day === 4 || day === 5 ? '本週較近期監測資料' : '最近一期監測資料'
})

const historicalAvailability = computed(() => {
  const warnings = historicalSignalWarnings.value
  if (historicalSignalItems.value.length > 0) {
    return {
      status: 'enough_history',
      badge: '有足夠歷史資料',
      title: '歷史價格訊號',
      message: '目前僅部分採集點有足夠歷史價格資料；此區可顯示歷史價格訊號作為輔助參考。',
    }
  }
  if (warnings.some((warning) => String(warning).includes(NOT_ENOUGH_HISTORY_WARNING))) {
    return {
      status: 'insufficient_history',
      badge: '歷史資料不足',
      title: '歷史資料不足',
      message: '此地區暫未有足夠歷史價格資料，仍可使用當期格價功能。',
    }
  }
  if (warnings.some((warning) => String(warning).includes(PROCESSED_DATA_MISSING_PREFIX))) {
    return {
      status: 'not_tracking',
      badge: '尚未建立歷史追蹤',
      title: '尚未建立歷史追蹤',
      message: '此地區尚未建立歷史價格追蹤，仍可使用當期格價功能。',
    }
  }
  return {
    status: 'insufficient_history',
    badge: '歷史資料不足',
    title: '歷史資料暫未可用',
    message: '此地區暫未有可顯示的歷史價格訊號，仍可使用當期格價功能。',
  }
})

const pointGroups = computed(() => {
  const buckets = Object.fromEntries(districtGroups.map((group) => [group.key, []]))
  for (const point of points.value) buckets[classifyPoint(point)].push(point)
  return districtGroups
    .map((group) => ({
      ...group,
      points: buckets[group.key].slice().sort((a, b) => String(a.point_code).localeCompare(String(b.point_code))),
    }))
    .filter((group) => group.points.length)
})

function classifyPoint(point) {
  const lat = Number(point?.lat)
  if (Number.isFinite(lat)) {
    if (lat < 22.18) return 'islands'
    if (lat >= 22.203) return 'north'
    if (lat >= 22.193) return 'central'
    return 'south'
  }

  const text = `${point?.name || ''} ${point?.district || ''}`.toLowerCase()
  if (text.includes('taipa') || text.includes('coloane')) return 'islands'
  if (text.includes('north')) return 'north'
  if (text.includes('south')) return 'south'
  return 'central'
}

function money(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A'
  return isSeniorMode.value ? `$${Number(value).toFixed(1)}` : `MOP ${Number(value).toFixed(1)}`
}

function percent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A'
  return `${Math.abs(Number(value)).toFixed(1)}%`
}

function signalText(signalType) {
  return {
    near_historical_low: '接近歷史低位',
    below_average: '低於近期平均',
    unusual_high: '高於近期平均',
  }[signalType] || '歷史價格訊號'
}

function toggleMode() {
  isSeniorMode.value = !isSeniorMode.value
}

async function loadPoints() {
  loadingPoints.value = true
  pointsError.value = ''
  try {
    points.value = await fetchPoints()
    if (!points.value.some((point) => point.point_code === pointCode.value)) {
      pointCode.value = points.value[0]?.point_code || 'p001'
    }
  } catch (err) {
    pointsError.value = err?.message || '無法載入採集點清單'
  } finally {
    loadingPoints.value = false
  }
}

async function loadHistoricalSignals() {
  if (!pointCode.value) return
  loadingHistoricalSignals.value = true
  historicalSignalsError.value = ''
  try {
    historicalSignals.value = await fetchHistoricalSignals({ pointCode: pointCode.value, date: 'latest', lookbackDays: 30, topN: 5 })
  } catch (err) {
    historicalSignals.value = null
    historicalSignalsError.value = err?.message || '無法載入歷史價格訊號'
  } finally {
    loadingHistoricalSignals.value = false
  }
}

watch(pointCode, () => {
  loadHistoricalSignals()
})

onMounted(async () => {
  await loadPoints()
  await loadHistoricalSignals()
})
</script>

<template>
  <main
    :class="[
      'min-h-screen pb-16 antialiased transition-all duration-300',
      isSeniorMode ? 'bg-white text-[20px] text-[#1A1A1A]' : 'bg-[#FBFBFA] text-base text-[#44413A]',
    ]"
  >
    <header class="sticky top-0 z-50 border-b border-[#E4E1D8] bg-white/90 shadow-sm backdrop-blur-md">
      <div class="mx-auto flex max-w-4xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div>
          <p v-if="!isSeniorMode" class="text-xs font-semibold uppercase tracking-[0.18em] text-[#8A826F]">Macau Grocery Intelligence</p>
          <h1
            class="font-black tracking-tight transition-all duration-300"
            :class="isSeniorMode ? 'text-2xl text-[#FF6B00] sm:text-3xl' : 'text-xl text-[#44413A] sm:text-2xl'"
          >
            {{ isSeniorMode ? 'AI 採購查價助手' : '澳門超市格價助手' }}
          </h1>
        </div>

        <button
          type="button"
          class="inline-flex shrink-0 items-center gap-2 rounded-full border-2 px-4 py-2 font-black shadow-sm transition-all duration-300 active:scale-95"
          :class="isSeniorMode ? 'border-[#FF6B00] bg-[#FF6B00] text-white shadow-orange-200' : 'border-[#C4B997] bg-white text-[#8A826F] hover:bg-[#F2F1EC]'"
          @click="toggleMode"
        >
          <span :class="isSeniorMode ? 'text-base' : 'text-sm'">{{ isSeniorMode ? '切換標準模式' : '長者友善模式' }}</span>
        </button>
      </div>
    </header>

    <div class="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6">
      <section
        :class="[
          'mb-8 transition-all duration-300',
          isSeniorMode
            ? 'rounded-[2rem] border-4 border-slate-100 bg-slate-50 p-6 shadow-xl'
            : 'rounded-2xl border border-[#E4E1D8] bg-white p-4 shadow-sm sm:grid sm:grid-cols-[1fr_auto] sm:items-end sm:gap-5',
        ]"
      >
        <div class="flex flex-col gap-2">
          <label
            :class="[
              'font-black transition-all duration-300',
              isSeniorMode ? 'mb-2 text-2xl text-slate-900' : 'text-xs uppercase tracking-[0.18em] text-[#8A826F]',
            ]"
          >
            選擇採集點 / 地區
          </label>
          <select
            v-model="pointCode"
            :disabled="loadingPoints || !points.length"
            :class="[
              'w-full border bg-white outline-none transition-all duration-300 disabled:cursor-not-allowed disabled:bg-slate-100',
              isSeniorMode
                ? 'h-16 rounded-2xl border-4 border-slate-200 px-4 text-xl font-black text-slate-900 focus:border-[#FF6B00]'
                : 'h-11 rounded-xl border-[#E4E1D8] px-3 text-sm font-semibold text-[#44413A] focus:border-[#C4B997]',
            ]"
          >
            <optgroup v-for="group in pointGroups" :key="group.key" :label="group.label">
              <option v-for="point in group.points" :key="point.point_code" :value="point.point_code">
                {{ point.name }}（{{ point.point_code }}）
              </option>
            </optgroup>
          </select>
          <p v-if="pointsError" :class="isSeniorMode ? 'text-lg font-bold text-yellow-900' : 'text-sm text-[#A07A32]'">{{ pointsError }}</p>
        </div>

        <div
          :class="[
            'transition-all duration-300',
            isSeniorMode ? 'mt-5 flex items-center justify-between gap-4 border-t-2 border-slate-200 pt-5' : 'mt-4 text-left sm:mt-0 sm:text-right',
          ]"
        >
          <div>
            <span :class="isSeniorMode ? 'text-base font-bold text-slate-500' : 'text-xs font-semibold uppercase tracking-wide text-[#8A826F]'">資料更新節奏</span>
            <p :class="isSeniorMode ? 'text-xl font-black text-[#00875A]' : 'mt-1 text-sm font-bold text-[#00875A]'">{{ dataFreshnessLabel }}</p>
          </div>
          <span :class="isSeniorMode ? 'rounded-full bg-white px-4 py-2 text-lg font-black text-slate-700 shadow' : 'mt-2 inline-block rounded-full bg-[#F2F1EC] px-3 py-1 text-xs font-semibold text-[#6E685A]'">
            {{ selectedPointName }}
          </span>
        </div>
      </section>

      <ShoppingAgentBox :is-senior="isSeniorMode" :point-code="pointCode" :selected-point-name="selectedPointName" />

      <section
        :class="[
          'mt-10 transition-all duration-300',
          isSeniorMode ? 'rounded-[2rem] border-4 border-slate-100 bg-white p-6 shadow-2xl' : 'rounded-2xl border border-[#E4E1D8] bg-white p-5 shadow-sm',
        ]"
      >
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <h2 :class="isSeniorMode ? 'text-3xl font-black text-slate-900' : 'text-lg font-bold text-[#44413A]'">
                歷史價格訊號
              </h2>
              <span :class="[
                'rounded-full px-3 py-1 text-xs font-bold',
                historicalAvailability.status === 'enough_history'
                  ? 'bg-emerald-50 text-emerald-700'
                  : historicalAvailability.status === 'not_tracking'
                    ? 'bg-slate-100 text-slate-600'
                    : 'bg-amber-50 text-amber-700',
              ]">
                {{ historicalAvailability.badge }}
              </span>
            </div>
            <p :class="isSeniorMode ? 'mt-1 text-lg font-bold text-slate-600' : 'mt-1 text-sm leading-6 text-[#6E685A]'">
              歷史價格訊號屬輔助資訊，不影響主查價流程。{{ historicalAvailability.status !== 'enough_history' ? '目前僅部分採集點有足夠歷史價格資料。' : '' }}
            </p>
          </div>
          <button
            type="button"
            :class="[
              'font-black transition-all duration-300 active:scale-95 disabled:cursor-not-allowed disabled:bg-slate-300',
              isSeniorMode ? 'h-14 rounded-2xl bg-[#FF6B00] px-6 text-lg text-white shadow-lg hover:bg-[#E66000]' : 'h-10 rounded-xl bg-[#C4B997] px-4 text-sm text-white hover:bg-[#B5AA87]',
            ]"
            :disabled="loadingHistoricalSignals"
            @click="loadHistoricalSignals"
          >
            {{ loadingHistoricalSignals ? '更新中…' : '重新整理' }}
          </button>
        </div>

        <p v-if="loadingHistoricalSignals" :class="isSeniorMode ? 'mt-5 rounded-2xl bg-orange-50 p-4 text-xl font-bold text-[#FF6B00]' : 'mt-4 text-sm text-[#6E685A]'">正在載入歷史價格訊號…</p>
        <p v-else-if="historicalSignalsError" :class="isSeniorMode ? 'mt-5 rounded-2xl bg-yellow-50 p-4 text-xl font-bold text-yellow-900' : 'mt-4 rounded-xl bg-[#F2F1EC] p-3 text-sm text-[#A07A32]'">{{ historicalSignalsError }}</p>

        <div v-else-if="historicalSignalItems.length" :class="isSeniorMode ? 'mt-5 grid gap-4' : 'mt-5 overflow-hidden rounded-xl border border-[#E4E1D8]'">
          <template v-if="isSeniorMode">
            <article
              v-for="item in historicalSignalItems"
              :key="`historical-card-${item.signal_type}-${item.product_oid}`"
              class="rounded-3xl border-2 border-orange-100 bg-orange-50 p-5 shadow-lg"
            >
              <div class="flex items-start justify-between gap-4">
                <div>
                  <p class="text-xl font-black text-slate-900">{{ item.product_name }}</p>
                  <p class="mt-1 text-lg font-bold text-slate-600">{{ signalText(item.signal_type) }}，比近期平均低 {{ percent(item.discount_vs_avg_percent) }}</p>
                </div>
                <p class="shrink-0 text-4xl font-black tabular-nums text-[#FF6B00]">{{ money(item.current_min_price_mop) }}</p>
              </div>
            </article>
          </template>
          <table v-else class="min-w-full divide-y divide-[#E4E1D8] text-left text-sm">
            <thead class="bg-[#F2F1EC] text-xs font-semibold uppercase tracking-wide text-[#8A826F]">
              <tr>
                <th class="px-4 py-3">商品</th>
                <th class="px-4 py-3">訊號</th>
                <th class="px-4 py-3 text-right">當前低價</th>
                <th class="px-4 py-3 text-right">較平均低</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[#E4E1D8] text-[#44413A]">
              <tr v-for="item in historicalSignalItems" :key="`historical-row-${item.signal_type}-${item.product_oid}`" class="hover:bg-[#F2F1EC]/70">
                <td class="px-4 py-3 font-medium">{{ item.product_name }}</td>
                <td class="px-4 py-3 text-[#6E685A]">{{ signalText(item.signal_type) }}</td>
                <td class="px-4 py-3 text-right font-semibold tabular-nums text-[#C4B997]">{{ money(item.current_min_price_mop) }}</td>
                <td class="px-4 py-3 text-right tabular-nums">{{ percent(item.discount_vs_avg_percent) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else :class="isSeniorMode ? 'mt-5 rounded-2xl bg-slate-50 p-5 text-lg font-bold text-slate-600' : 'mt-4 rounded-xl bg-[#FBFBFA] p-4 text-sm leading-6 text-[#6E685A]'">
          <p class="font-semibold text-[#44413A]">{{ historicalAvailability.title }}</p>
          <p class="mt-2">{{ historicalAvailability.message }}</p>
        </div>
      </section>
    </div>
  </main>
</template>
