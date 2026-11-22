<script setup lang="ts">
import { computed, ref } from 'vue'

withDefaults(defineProps<{ loading?: boolean }>(), {
  loading: false,
})

const emit = defineEmits<{ submit: [url: string] }>()

const url = ref('')
const touched = ref(false)

const isValid = computed(() => /^https?:\/\/\S+$/i.test(url.value.trim()))
const showError = computed(() => touched.value && !isValid.value)

function handleSubmit(): void {
  touched.value = true

  if (!isValid.value) {
    return
  }

  emit('submit', url.value.trim())
}
</script>

<template>
  <form class="url-form" novalidate @submit.prevent="handleSubmit">
    <label for="url">Page URL</label>
    <div class="row">
      <input
        id="url"
        v-model="url"
        type="url"
        inputmode="url"
        placeholder="https://example.com"
        autocomplete="url"
        :disabled="loading"
        :aria-invalid="showError"
        @blur="touched = true"
      />
      <button type="submit" :disabled="loading || !url.trim()">
        {{ loading ? 'Submitting…' : 'Start Scraping' }}
      </button>
    </div>
    <p v-if="showError" class="field-error">
      URL must start with http:// or https://
    </p>
  </form>
</template>

<style scoped>
.url-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

label {
  font-weight: 600;
  font-size: 0.95rem;
}

.row {
  display: flex;
  gap: 0.75rem;
}

.row button {
  white-space: nowrap;
}

.field-error {
  margin: 0;
  color: #b91c1c;
  font-size: 0.9rem;
}

@media (max-width: 560px) {
  .row {
    flex-direction: column;
  }
}
</style>
