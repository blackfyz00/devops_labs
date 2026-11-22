<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string; error?: string | null }>()

const isActive = computed(
  () => props.status === 'queued' || props.status === 'running',
)

const statusClass = computed(() => `badge--${props.status}`)
</script>

<template>
  <div class="job-status">
    <span class="badge" :class="statusClass">
      <span v-if="isActive" class="spinner" aria-hidden="true" />
      {{ status }}
    </span>
    <p v-if="error" class="status-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.job-status {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  width: fit-content;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: capitalize;
}

.badge--queued {
  background: #e5e7eb;
  color: #374151;
}

.badge--running {
  background: #dbeafe;
  color: #1d4ed8;
}

.badge--done {
  background: #dcfce7;
  color: #166534;
}

.badge--failed {
  background: #fee2e2;
  color: #b91c1c;
}

.spinner {
  width: 0.85rem;
  height: 0.85rem;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}

.status-error {
  margin: 0;
  color: #b91c1c;
  overflow-wrap: anywhere;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
