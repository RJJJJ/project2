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

export function askBasket({ text, pointCode, selectedProducts = null }) {
  return request('/api/basket/ask', {
    method: 'POST',
    body: JSON.stringify({
      text,
      point_code: pointCode,
      date: 'latest',
      ...(selectedProducts ? { selected_products: selectedProducts } : {}),
    }),
  })
}

export function fetchProductCandidates({ keyword, pointCode, limit = 8 }) {
  const params = new URLSearchParams({
    keyword,
    point_code: pointCode,
    date: 'latest',
    limit: String(limit),
  })
  return request(`/api/products/candidates?${params.toString()}`)
}

export function fetchSignals(pointCode, topN = 5) {
  return request(`/api/signals/${encodeURIComponent(pointCode)}?date=latest&top_n=${topN}`)
}

export function fetchHistoricalSignals({ pointCode, date = 'latest', lookbackDays = 30, topN = 5 }) {
  const params = new URLSearchParams({
    date,
    lookback_days: String(lookbackDays),
    top_n: String(topN),
  })
  return request(`/api/historical-signals/${encodeURIComponent(pointCode)}?${params.toString()}`)
}

export function fetchWatchlistSignals({ pointCode, items, date = 'latest', lookbackDays = 30 }) {
  return request('/api/watchlist/signals', {
    method: 'POST',
    body: JSON.stringify({
      point_code: pointCode,
      date,
      lookback_days: lookbackDays,
      items,
    }),
  })
}

export function fetchWatchlistAlerts({ pointCode, items, date = 'latest', lookbackDays = 30 }) {
  return request('/api/watchlist/alerts', {
    method: 'POST',
    body: JSON.stringify({
      point_code: pointCode,
      date,
      lookback_days: lookbackDays,
      items,
    }),
  })
}

export function fetchUserWatchlist(userToken) {
  const params = new URLSearchParams({ user_token: userToken })
  return request(`/api/user/watchlist?${params.toString()}`)
}

export function addUserWatchlistItem(userToken, item) {
  return request('/api/user/watchlist', {
    method: 'POST',
    body: JSON.stringify({ user_token: userToken, item }),
  })
}

export function removeUserWatchlistItem(userToken, productOid, pointCode) {
  const params = new URLSearchParams({ user_token: userToken, point_code: pointCode })
  return request(`/api/user/watchlist/${encodeURIComponent(productOid)}?${params.toString()}`, {
    method: 'DELETE',
  })
}

export function fetchUserAlertHistory(userToken) {
  const params = new URLSearchParams({ user_token: userToken })
  return request(`/api/user/alert-history?${params.toString()}`)
}

export function setUserAlertStatus(userToken, alert) {
  return request('/api/user/alert-history', {
    method: 'POST',
    body: JSON.stringify({ user_token: userToken, alert }),
  })
}

export function clearUserAlertHistory(userToken) {
  const params = new URLSearchParams({ user_token: userToken })
  return request(`/api/user/alert-history?${params.toString()}`, {
    method: 'DELETE',
  })
}

export async function runShoppingAgent({
  query,
  pointCode = null,
  useLlm = false,
  includePricePlan = true,
  priceStrategy = 'cheapest_single_store',
  clarificationAnswers = undefined,
  plannerMode = 'rule',
  localLlmModel = null,
  localLlmEndpoint = null,
  retrievalMode = 'taxonomy',
  composerMode = 'template',
} = {}) {
  const trimmedQuery = String(query || '').trim()
  if (!trimmedQuery) {
    const apiError = new Error('\u8acb\u5148\u8f38\u5165\u8cfc\u7269\u6e05\u55ae\u3002')
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
    const apiError = new Error('\u5f8c\u7aef\u56de\u50b3\u683c\u5f0f\u4e0d\u6b63\u78ba\u3002')
    apiError.status = null
    apiError.payload = data
    throw apiError
  }

  return data
}
