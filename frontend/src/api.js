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
