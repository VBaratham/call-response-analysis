<template>
  <div class="choice-container">
    <h2>Audio Uploaded Successfully</h2>
    <p class="subtitle">What would you like to do?</p>

    <div class="choice-cards">
      <div class="choice-card" @click="$emit('start-processing')">
        <div class="card-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
        </div>
        <h3>Start Fresh</h3>
        <p>Process this audio file to detect call/response sections automatically.</p>
      </div>

      <div class="choice-card" @click="$refs.importInput.click()">
        <div class="card-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="12" y1="18" x2="12" y2="12"/>
            <line x1="9" y1="15" x2="12" y2="12"/>
            <line x1="15" y1="15" x2="12" y2="12"/>
          </svg>
        </div>
        <h3>Import Saved Project</h3>
        <p>Load sections and alignments from a previously exported project file.</p>
      </div>
    </div>

    <input
      ref="importInput"
      type="file"
      accept=".zip,.json"
      @change="handleImport"
      hidden
    />

    <div v-if="error" class="import-error">
      <p>{{ error }}</p>
      <button class="btn btn-secondary" @click="error = null">Dismiss</button>
    </div>

    <div v-if="isImporting" class="importing">
      <p>Importing project...</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../services/api'

const props = defineProps({
  sessionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['start-processing', 'project-imported'])

const importInput = ref(null)
const isImporting = ref(false)
const error = ref(null)

async function handleImport(event) {
  const file = event.target.files[0]
  if (!file) return

  error.value = null
  isImporting.value = true

  try {
    await api.importProject(props.sessionId, file)
    emit('project-imported')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to import project. Please check the file format.'
  } finally {
    isImporting.value = false
    // Reset input so same file can be selected again
    event.target.value = ''
  }
}
</script>

<style scoped>
.choice-container {
  max-width: 700px;
  margin: 2rem auto;
  text-align: center;
}

.choice-container h2 {
  color: #e94560;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #888;
  margin-bottom: 2rem;
}

.choice-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.choice-card {
  background: #16213e;
  border: 2px solid #0f3460;
  border-radius: 12px;
  padding: 2rem;
  cursor: pointer;
  transition: all 0.3s;
}

.choice-card:hover {
  border-color: #e94560;
  background: rgba(233, 69, 96, 0.05);
}

.card-icon {
  color: #e94560;
  margin-bottom: 1rem;
}

.choice-card h3 {
  color: #eee;
  margin-bottom: 0.75rem;
}

.choice-card p {
  color: #888;
  font-size: 0.9rem;
  line-height: 1.5;
}

.import-error {
  margin-top: 1.5rem;
  padding: 1rem;
  background: rgba(255, 100, 100, 0.1);
  border: 1px solid #ff6b6b;
  border-radius: 8px;
}

.import-error p {
  color: #ff6b6b;
  margin-bottom: 0.5rem;
}

.importing {
  margin-top: 1.5rem;
  color: #888;
}

@media (max-width: 600px) {
  .choice-cards {
    grid-template-columns: 1fr;
  }
}
</style>
