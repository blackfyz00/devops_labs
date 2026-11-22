<script setup lang="ts">
import { computed } from 'vue'

import type { Quote, ScrapingResult } from '../composables/useJobPolling'

const props = defineProps<{ result: ScrapingResult }>()

const quotes = computed<Quote[]>(() =>
  Array.isArray(props.result.quotes) ? props.result.quotes : [],
)

const hasQuotesArray = computed(() => Array.isArray(props.result.quotes))

const totalCount = computed<number | null>(() => {
  if (typeof props.result.total_count === 'number') {
    return props.result.total_count
  }
  if (Array.isArray(props.result.quotes)) {
    return props.result.quotes.length
  }
  return null
})

const scrapedAt = computed<string | null>(() => {
  const value = props.result.scraped_at

  if (typeof value !== 'string' || value.length === 0) {
    return null
  }

  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
})

const prettyJson = computed(() => JSON.stringify(props.result, null, 2))
</script>

<template>
  <div class="result">
    <div v-if="scrapedAt !== null || totalCount !== null" class="result-meta">
      <span v-if="totalCount !== null">Total: {{ totalCount }}</span>
      <span v-if="scrapedAt !== null">Scraped: {{ scrapedAt }}</span>
    </div>

    <table v-if="hasQuotesArray">
      <thead>
        <tr>
          <th>Text</th>
          <th>Author</th>
          <th>Tags</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(quote, index) in quotes" :key="index">
          <td>{{ quote.text }}</td>
          <td>{{ quote.author }}</td>
          <td>{{ quote.tags?.join(', ') ?? '' }}</td>
        </tr>
        <tr v-if="quotes.length === 0">
          <td colspan="3" class="empty">No quotes found.</td>
        </tr>
      </tbody>
    </table>

    <pre v-else>{{ prettyJson }}</pre>
  </div>
</template>

<style scoped>
.result {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
  color: #64748b;
  font-size: 0.9rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
}

th,
td {
  padding: 0.65rem 0.75rem;
  text-align: left;
  vertical-align: top;
  border-bottom: 1px solid #e2e8f0;
}

th {
  background: #f8fafc;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
}

td:first-child {
  min-width: 16rem;
}

.empty {
  color: #64748b;
  text-align: center;
}

pre {
  margin: 0;
  padding: 1rem;
  border-radius: 10px;
  background: #0f172a;
  color: #e2e8f0;
  overflow: auto;
  font-size: 0.85rem;
}

@media (max-width: 640px) {
  table {
    display: block;
    overflow-x: auto;
  }
}
</style>
