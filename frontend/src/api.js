const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request(path, options = {}) {
  const endpoint = `${API_BASE_URL}${path}`
  let response
  try {
    response = await fetch(endpoint, {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    })
  } catch (err) {
    const apiError = new Error(err?.message || 'Failed to fetch')
    apiError.endpoint = endpoint
    apiError.status = null
    apiError.isNetworkError = true
    throw apiError
  }

  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const detail = typeof data === 'object' && data !== null ? data.detail : data
    const apiError = new Error(detail || `API request failed: ${response.status}`)
    apiError.endpoint = endpoint
    apiError.status = response.status
    apiError.payload = data
    throw apiError
  }

  return data
}

export function fetchPoints() {
  return request('/api/points')
}

export function fetchHistoricalSignals({ pointCode, date = 'latest', lookbackDays = 30, topN = 5 }) {
  const params = new URLSearchParams({
    date,
    lookback_days: String(lookbackDays),
    top_n: String(topN),
  })
  return request(`/api/historical-signals/${encodeURIComponent(pointCode)}?${params.toString()}`)
}

export async function runShoppingAgent({
  query,
  pointCode = null,
  useLlm = false,
  includePricePlan = true,
  priceStrategy = 'cheapest_single_store',
  decisionPolicy = 'cheapest_single_store',
  decisionPolicyOptions = null,
  clarificationAnswers = undefined,
  plannerMode = 'rule',
  localLlmModel = null,
  localLlmEndpoint = null,
  retrievalMode = 'taxonomy',
  composerMode = 'template',
} = {}) {
  const trimmedQuery = String(query || '').trim()
  if (!trimmedQuery) {
    const apiError = new Error('請輸入購物清單')
    apiError.status = 400
    throw apiError
  }

  const data = await request('/api/agent/shopping', {
    method: 'POST',
    body: JSON.stringify({
      query: trimmedQuery,
      point_code: pointCode,
      use_llm: Boolean(useLlm),
      include_price_plan: Boolean(includePricePlan),
      price_strategy: priceStrategy,
      decision_policy: decisionPolicy,
      decision_policy_options: decisionPolicyOptions,
      ...(clarificationAnswers && Object.keys(clarificationAnswers).length
        ? { clarification_answers: clarificationAnswers }
        : {}),
      planner_mode: plannerMode,
      local_llm_model: localLlmModel,
      local_llm_endpoint: localLlmEndpoint,
      retrieval_mode: retrievalMode,
      composer_mode: composerMode,
    }),
  })

  if (!data || typeof data !== 'object' || typeof data.status !== 'string') {
    const apiError = new Error('後端回傳格式錯誤')
    apiError.status = null
    apiError.payload = data
    throw apiError
  }

  return data
}
