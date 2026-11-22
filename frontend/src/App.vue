<script setup lang="ts">
import { computed, ref } from 'vue'
import axios from 'axios'

import UrlForm from './components/UrlForm.vue'
import JobStatus from './components/JobStatus.vue'
import ResultView from './components/ResultView.vue'
import { getErrorMessage, useJobPolling } from './composables/useJobPolling'

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const { jobId, status, result, error, isPolling, startPolling, reset } =
  useJobPolling(apiUrl)

const isSubmitting = ref(false)
const submitError = ref<string | null>(null)

type Phase = 'idle' | 'processing' | 'result'

const phase = computed<Phase>(() => {
  if (result.value !== null || error.value !== null) {
    return 'result'
  }
  if (jobId.value !== null) {
    return 'processing'
  }
  return 'idle'
})

async function handleSubmit(url: string): Promise<void> {
  isSubmitting.value = true
  submitError.value = null

  try {
    const response = await axios.post<{ job_id: string; status: string }>(
      `${apiUrl}/jobs`,
      { url },
    )
    startPolling(response.data.job_id)
  } catch (err) {
    submitError.value = getErrorMessage(err)
  } finally {
    isSubmitting.value = false
  }
}

function handleReset(): void {
  submitError.value = null
  reset()
}
</script>

<template>
  <main class="app">
    <header class="hero">
      <h1>Quotes Scraper</h1>
      <p>Submit any page URL and get the scraped content asynchronously.</p>
    </header>

    <section v-if="phase === 'idle'" class="card">
      <UrlForm :loading="isSubmitting" @submit="handleSubmit" />
      <p v-if="submitError" class="form-error">{{ submitError }}</p>
    </section>

    <section v-else-if="phase === 'processing'" class="card">
      <JobStatus :status="status" :error="error" />
      <p class="hint">Job ID: <code>{{ jobId }}</code></p>
      <p v-if="isPolling" class="hint">Checking status every 3 seconds…</p>
    </section>

    <section v-else class="card">
      <JobStatus :status="status" :error="error" />
      <ResultView v-if="result" :result="result" />
      <button class="secondary" type="button" @click="handleReset">
        Scrape another URL
      </button>
    </section>
  </main>
</template>

<style scoped>
.app {
  max-width: 960px;
  margin: 0 auto;
  padding: 3rem 1.25rem 4rem;
}

.hero {
  margin-bottom: 2rem;
  text-align: center;
}

.hero h1 {
  margin: 0 0 0.5rem;
  font-size: clamp(2rem, 5vw, 2.6rem);
  letter-spacing: -0.03em;
}

.hero p {
  margin: 0;
  color: #64748b;
}

.card {
  background: #fff;
  border-radius: 16px;
  padding: 1.75rem;
  box-shadow: 0 18px 40px -24px rgb(15 23 42 / 35%);
}

.form-error {
  margin: 1rem 0 0;
  color: #b91c1c;
  font-size: 0.95rem;
}

.hint {
  margin: 0.9rem 0 0;
  color: #64748b;
  font-size: 0.95rem;
  overflow-wrap: anywhere;
}

.card > button {
  margin-top: 1.5rem;
}
</style>
