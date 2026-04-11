import api from './index'

export const getAiTravelRecommendations = (payload) =>
  api.post('/api/ai-travel/recommend', payload, {
    timeout: 90000,
  })

/**
 * Streaming follow-up chat with Doubao via SSE.
 * @param {object} payload - { location_summary, query, history }
 * @param {object} callbacks - { onChunk, onDone, onError }
 */
export async function streamAiTravelChat(payload, { onChunk, onDone, onError } = {}) {
  const token = localStorage.getItem('token')
  const response = await fetch('/api/ai-travel/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errText = await response.text().catch(() => '')
    throw new Error(errText || `HTTP ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6).trim()
        if (data === '[DONE]') {
          onDone?.()
          return
        }
        try {
          const parsed = JSON.parse(data)
          if (parsed.content) onChunk?.(parsed.content)
          if (parsed.error) onError?.(parsed.error)
        } catch {
          // ignore malformed chunks
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
  onDone?.()
}
