const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const detail = typeof data === 'object' && data !== null ? data.detail : data
    throw new Error(detail || `API request failed: ${response.status}`)
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
