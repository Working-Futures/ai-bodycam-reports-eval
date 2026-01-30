const API_BASE = '/api'

export async function loadVideos() {
  const response = await fetch(`${API_BASE}/videos`)
  if (!response.ok) throw new Error('Failed to load videos')
  return response.json()
}

export async function loadNarrative(narrativeId) {
  const response = await fetch(`${API_BASE}/narrative/${narrativeId}`)
  if (!response.ok) throw new Error('Failed to load narrative')
  return response.text()
}

export async function loadAtomicFacts(videoId) {
  const response = await fetch(`${API_BASE}/atomic-facts/${videoId}`)
  if (!response.ok) throw new Error('Failed to load atomic facts')
  const data = await response.json()
  return data.facts
}

export async function loadUserResponses(username) {
  const response = await fetch(`${API_BASE}/responses/${username}`)
  if (!response.ok) {
    if (response.status === 404) return {}
    throw new Error('Failed to load user responses')
  }
  return response.json()
}

export async function saveUserResponse(username, videoId, responses) {
  const response = await fetch(`${API_BASE}/responses/${username}/${videoId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(responses)
  })
  if (!response.ok) throw new Error('Failed to save response')
  return response.json()
}
