<template>
  <div class="pair-selector">
    <h3>Pairs</h3>

    <!-- Navigation -->
    <div class="nav-buttons">
      <button
        class="btn btn-icon"
        @click="prevPair"
        :disabled="currentPair <= 0"
        title="Previous Pair"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </button>
      <span class="pair-indicator">{{ currentPair + 1 }} / {{ pairs.length }}</span>
      <button
        class="btn btn-icon"
        @click="nextPair"
        :disabled="currentPair >= pairs.length - 1"
        title="Next Pair"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </button>
    </div>

    <!-- Pair List -->
    <div class="pair-list">
      <div
        v-for="pair in pairs"
        :key="pair.id"
        class="pair-item"
        :class="{ active: pair.id === currentPair }"
        @click="$emit('select', pair.id)"
      >
        <div class="pair-number">{{ pair.id + 1 }}</div>
        <div class="pair-details">
          <div class="pair-times">
            <span class="call-time">{{ formatTime(pair.call.start) }}</span>
            <span class="separator">→</span>
            <span class="response-time">{{ formatTime(pair.response.start) }}</span>
          </div>
          <div class="pair-duration">
            {{ formatDuration(pair.call.end - pair.call.start) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Keyboard hints -->
    <div class="hints">
      <span><kbd>←</kbd> Prev</span>
      <span><kbd>→</kbd> Next</span>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'

const props = defineProps({
  pairs: {
    type: Array,
    default: () => []
  },
  currentPair: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['select'])

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

function handleKeydown(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return

  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    prevPair()
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    nextPair()
  }
}

function prevPair() {
  if (props.currentPair > 0) {
    emit('select', props.currentPair - 1)
  }
}

function nextPair() {
  if (props.currentPair < props.pairs.length - 1) {
    emit('select', props.currentPair + 1)
  }
}

function formatTime(seconds) {
  if (!seconds) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function formatDuration(seconds) {
  if (!seconds) return '0s'
  return `${seconds.toFixed(1)}s`
}
</script>

<style scoped>
.pair-selector {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  height: 100%;
}

h3 {
  font-size: 1rem;
  color: #ccc;
  margin: 0 0 1rem 0;
}

.nav-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.btn-icon {
  width: 32px;
  height: 32px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f3460;
  border: 1px solid #1a4b8c;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-icon:hover:not(:disabled) {
  background: #1a4b8c;
  color: white;
}

.btn-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pair-indicator {
  font-size: 0.9rem;
  color: #888;
  min-width: 60px;
  text-align: center;
}

.pair-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.pair-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem;
  background: #0f3460;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.pair-item:hover {
  border-color: #1a4b8c;
}

.pair-item.active {
  background: rgba(233, 69, 96, 0.15);
  border-color: #e94560;
}

.pair-number {
  width: 24px;
  height: 24px;
  background: #1a1a2e;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  color: #888;
}

.pair-item.active .pair-number {
  background: #e94560;
  color: white;
}

.pair-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.pair-times {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.8rem;
  font-family: monospace;
}

.call-time {
  color: #e94560;
}

.response-time {
  color: #4facfe;
}

.separator {
  color: #666;
  font-size: 0.7rem;
}

.pair-duration {
  font-size: 0.7rem;
  color: #666;
}

.hints {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #0f3460;
}

.hints span {
  font-size: 0.75rem;
  color: #666;
}

.hints kbd {
  background: #0f3460;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.7rem;
  color: #888;
  margin-right: 0.2rem;
}
</style>
