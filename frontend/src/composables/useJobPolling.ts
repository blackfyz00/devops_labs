import { onUnmounted, ref } from 'vue'
import axios from 'axios'

const POLL_INTERVAL_MS = 3000
const POLL_TIMEOUT_MS = 120_000

export interface Quote {
  text: string
  author: string
  tags?: string[]
}

export interface ScrapingResult {
  quotes?: Quote[]
  scraped_at?: string
  total_count?: number
  [key: string]: unknown
}

interface JobStatusPayload {
  id: string
  status: string
  error: string | null
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string' && detail.length > 0) {
      return detail
    }
    if (error.message) {
      return error.message
    }
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Unexpected error'
}

export function useJobPolling(apiUrl: string) {
  const jobId = ref<string | null>(null)
  const status = ref('idle')
  const result = ref<ScrapingResult | null>(null)
  const error = ref<string | null>(null)
  const isPolling = ref(false)

  let intervalId: ReturnType<typeof setInterval> | null = null
  let startedAt = 0
  let requestInFlight = false

  function stopPolling(): void {
    if (intervalId !== null) {
      clearInterval(intervalId)
      intervalId = null
    }
    isPolling.value = false
  }

  function reset(): void {
    stopPolling()
    jobId.value = null
    status.value = 'idle'
    result.value = null
    error.value = null
    requestInFlight = false
  }

  async function poll(): Promise<void> {
    if (!isPolling.value || jobId.value === null || requestInFlight) {
      return
    }

    if (Date.now() - startedAt >= POLL_TIMEOUT_MS) {
      error.value = 'Timeout'
      stopPolling()
      return
    }

    requestInFlight = true

    try {
      const { data } = await axios.get<JobStatusPayload>(`${apiUrl}/jobs/${jobId.value}`)
      status.value = data.status

      if (data.status === 'done') {
        const response = await axios.get<ScrapingResult>(
          `${apiUrl}/jobs/${jobId.value}/result`,
        )
        result.value = response.data
        stopPolling()
      } else if (data.status === 'failed') {
        error.value = data.error ?? 'Scraping failed'
        stopPolling()
      }
    } catch (err) {
      error.value = getErrorMessage(err)
      stopPolling()
    } finally {
      requestInFlight = false
    }
  }

  function startPolling(id: string): void {
    stopPolling()
    jobId.value = id
    status.value = 'queued'
    result.value = null
    error.value = null
    isPolling.value = true
    startedAt = Date.now()
    intervalId = setInterval(() => {
      void poll()
    }, POLL_INTERVAL_MS)
  }

  onUnmounted(stopPolling)

  return {
    jobId,
    status,
    result,
    error,
    isPolling,
    startPolling,
    stopPolling,
    reset,
  }
}
