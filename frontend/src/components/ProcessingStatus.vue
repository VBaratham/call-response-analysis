<template>
  <div class="processing-container">
    <div class="processing-card">
      <div class="processing-icon" :class="{ error: status?.stage === 'error' }">
        <svg v-if="status?.stage !== 'error'" class="spinner" xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
          <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/>
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
      </div>

      <h2>{{ stageTitle }}</h2>
      <p class="message">{{ status?.message || 'Initializing...' }}</p>

      <div class="progress-container">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <span class="progress-text">{{ progressPercent }}%</span>
      </div>

      <div class="stages">
        <div
          v-for="stage in stages"
          :key="stage.id"
          class="stage"
          :class="{
            active: status?.stage === stage.id,
            completed: isStageCompleted(stage.id),
            error: status?.stage === 'error' && status?.error
          }"
        >
          <div class="stage-indicator">
            <!-- Completed: checkmark -->
            <svg v-if="isStageCompleted(stage.id)" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <!-- Active: spinner -->
            <svg v-else-if="status?.stage === stage.id" class="stage-spinner" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
              <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/>
            </svg>
            <!-- Pending: number -->
            <span v-else>{{ stage.number }}</span>
          </div>
          <span class="stage-label">{{ stage.label }}</span>
        </div>
      </div>

      <p v-if="status?.error" class="error-message">
        {{ status.error }}
      </p>

      <!-- Live Logs -->
      <div class="logs-container">
        <div class="logs-header">
          <h4>Processing Output</h4>
          <button class="btn-toggle" @click="showLogs = !showLogs">
            {{ showLogs ? 'Hide' : 'Show' }}
          </button>
        </div>
        <div class="logs-content" v-show="showLogs" ref="logsContainer">
          <div v-if="logs.length === 0" class="log-line log-waiting">Waiting for output...</div>
          <div v-for="(log, idx) in logs" :key="idx" class="log-line">
            {{ log }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  status: {
    type: Object,
    default: () => ({ stage: 'pending', progress: 0, message: '' })
  },
  logs: {
    type: Array,
    default: () => []
  }
})

const showLogs = ref(true)
const logsContainer = ref(null)

// Auto-scroll to bottom when new logs arrive
watch(() => props.logs.length, async () => {
  await nextTick()
  if (logsContainer.value && showLogs.value) {
    logsContainer.value.scrollTop = logsContainer.value.scrollHeight
  }
})

const stages = [
  { id: 'vocal_separation', number: 1, label: 'Separating Vocals' },
  { id: 'vocals_ready', number: 2, label: 'Vocals Ready' },
  { id: 'fingerprinting', number: 3, label: 'Detecting Sections' },
  { id: 'complete', number: 4, label: 'Complete' }
]

const stageOrder = ['pending', 'starting', 'vocal_separation', 'vocals_ready', 'fingerprinting', 'complete']

const stageTitle = computed(() => {
  const titles = {
    pending: 'Preparing...',
    starting: 'Starting Processing...',
    vocal_separation: 'Separating Vocals',
    vocals_ready: 'Vocals Ready!',
    fingerprinting: 'Detecting Call/Response Sections',
    pitch_estimation: 'Analyzing Pitch Contours',
    complete: 'Processing Complete!',
    error: 'Processing Error'
  }
  return titles[props.status?.stage] || 'Processing...'
})

const progressPercent = computed(() => {
  const stage = props.status?.stage
  const stageProgress = props.status?.progress || 0

  const stageWeights = {
    pending: 0,
    starting: 0,
    vocal_separation: 0.5,  // 0-50%
    vocals_ready: 0,        // 50%
    fingerprinting: 0.5,    // 50-100%
    complete: 0
  }

  const stageBases = {
    pending: 0,
    starting: 0,
    vocal_separation: 0,
    vocals_ready: 50,
    fingerprinting: 50,
    complete: 100
  }

  if (stage === 'complete') return 100
  if (stage === 'vocals_ready') return 50
  if (stage === 'error') return 0

  const base = stageBases[stage] || 0
  const weight = stageWeights[stage] || 0

  return Math.round(base + (stageProgress * weight * 100))
})

function isStageCompleted(stageId) {
  const currentIdx = stageOrder.indexOf(props.status?.stage)
  const stageIdx = stageOrder.indexOf(stageId)
  return stageIdx < currentIdx
}
</script>

<style scoped>
.processing-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.processing-card {
  background: #16213e;
  border-radius: 12px;
  padding: 3rem;
  text-align: center;
  max-width: 500px;
  width: 100%;
}

.processing-icon {
  color: #e94560;
  margin-bottom: 1.5rem;
}

.processing-icon.error {
  color: #ff6b6b;
}

.spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

h2 {
  margin-bottom: 0.5rem;
  color: #eee;
}

.message {
  color: #888;
  margin-bottom: 2rem;
}

.progress-container {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #0f3460;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #e94560, #ff6b6b);
  transition: width 0.5s ease;
}

.progress-text {
  font-size: 0.9rem;
  font-weight: 600;
  color: #e94560;
  min-width: 40px;
}

.stages {
  display: flex;
  justify-content: space-between;
}

.stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  opacity: 0.5;
  transition: opacity 0.3s;
}

.stage.active,
.stage.completed {
  opacity: 1;
}

.stage-indicator {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #0f3460;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  font-weight: 600;
  color: #888;
  transition: all 0.3s;
}

.stage.active .stage-indicator {
  background: #e94560;
  color: white;
}

.stage-spinner {
  animation: spin 1s linear infinite;
}

.stage.completed .stage-indicator {
  background: #4caf50;
  color: white;
}

.stage-label {
  font-size: 0.75rem;
  color: #888;
  max-width: 80px;
  text-align: center;
}

.stage.active .stage-label,
.stage.completed .stage-label {
  color: #ccc;
}

.error-message {
  margin-top: 1.5rem;
  padding: 1rem;
  background: rgba(255, 100, 100, 0.1);
  border-radius: 8px;
  color: #ff6b6b;
  font-size: 0.9rem;
}

.logs-container {
  margin-top: 2rem;
  text-align: left;
  border-top: 1px solid #0f3460;
  padding-top: 1rem;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.logs-header h4 {
  font-size: 0.9rem;
  color: #888;
  margin: 0;
}

.btn-toggle {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  background: #0f3460;
  border: 1px solid #1a4b8c;
  border-radius: 4px;
  color: #888;
  cursor: pointer;
}

.btn-toggle:hover {
  background: #1a4b8c;
  color: #ccc;
}

.logs-content {
  background: #0a0a1a;
  border-radius: 6px;
  padding: 0.75rem;
  max-height: 200px;
  overflow-y: auto;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.75rem;
  line-height: 1.4;
}

.log-line {
  color: #8a8;
  padding: 0.1rem 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-line:nth-child(even) {
  background: rgba(255, 255, 255, 0.02);
}

.log-waiting {
  color: #666;
  font-style: italic;
}
</style>
