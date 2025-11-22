<template>
  <div class="alignment-controls">
    <h3>Alignment</h3>

    <!-- Metrics Display -->
    <div class="metrics-panel">
      <div class="metric">
        <span class="metric-label">Correlation</span>
        <span class="metric-value" :class="getCorrelationClass(metrics?.correlation)">
          {{ formatMetric(metrics?.correlation) }}
        </span>
      </div>
      <div class="metric">
        <span class="metric-label">Unaligned</span>
        <span class="metric-value muted">
          {{ formatMetric(metrics?.correlation_unaligned) }}
        </span>
      </div>
      <div class="metric">
        <span class="metric-label">Cosine Sim</span>
        <span class="metric-value" :class="getCorrelationClass(metrics?.cosine_similarity)">
          {{ formatMetric(metrics?.cosine_similarity) }}
        </span>
      </div>
    </div>

    <!-- Offset Slider -->
    <div class="offset-control">
      <label>Time Offset</label>
      <div class="slider-container">
        <input
          type="range"
          :value="offset"
          @input="onSliderChange"
          min="-2"
          max="2"
          step="0.01"
          class="slider"
        />
        <div class="slider-labels">
          <span>-2s</span>
          <span>0</span>
          <span>+2s</span>
        </div>
      </div>
      <div class="offset-value">
        <input
          type="number"
          :value="offset.toFixed(3)"
          @change="onInputChange"
          step="0.01"
          min="-2"
          max="2"
          class="offset-input"
        />
        <span class="unit">seconds</span>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="action-buttons">
      <button class="btn btn-primary" @click="$emit('save-offset')">
        Save Offset
      </button>
      <button class="btn btn-secondary" @click="$emit('reset-offset')">
        Reset to Optimal
      </button>
    </div>

    <!-- Pair Info -->
    <div class="pair-info" v-if="pair">
      <h4>Pair Details</h4>
      <div class="info-row">
        <span class="label">Call:</span>
        <span class="value">{{ formatTime(pair.call.start) }} - {{ formatTime(pair.call.end) }}</span>
      </div>
      <div class="info-row">
        <span class="label">Response:</span>
        <span class="value">{{ formatTime(pair.response.start) }} - {{ formatTime(pair.response.end) }}</span>
      </div>
    </div>

    <!-- Audio Playback -->
    <div class="playback-controls">
      <h4>Playback</h4>
      <div class="playback-buttons">
        <button class="btn btn-small" @click="playCall">Play Call</button>
        <button class="btn btn-small" @click="playResponse">Play Response</button>
        <button class="btn btn-small" @click="playBoth">Play Both</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useProjectStore } from '../stores/project'

const props = defineProps({
  pair: Object,
  metrics: Object,
  offset: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['offset-changed', 'save-offset', 'reset-offset'])

const store = useProjectStore()

let audioContext = null
let currentSource = null

function onSliderChange(e) {
  emit('offset-changed', parseFloat(e.target.value))
}

function onInputChange(e) {
  const value = parseFloat(e.target.value)
  if (!isNaN(value) && value >= -2 && value <= 2) {
    emit('offset-changed', value)
  }
}

function formatMetric(value) {
  if (value === null || value === undefined) return 'N/A'
  return value.toFixed(3)
}

function getCorrelationClass(value) {
  if (value === null || value === undefined) return ''
  if (value >= 0.7) return 'high'
  if (value >= 0.4) return 'medium'
  return 'low'
}

function formatTime(seconds) {
  if (!seconds) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

async function playCall() {
  await playSegment('call')
}

async function playResponse() {
  await playSegment('response')
}

async function playBoth() {
  // Play both segments with offset alignment
  await playSegment('both')
}

async function playSegment(type) {
  if (!store.audioUrl || !props.pair) return

  try {
    // Stop any current playback
    if (currentSource) {
      currentSource.stop()
      currentSource = null
    }

    // Create audio context if needed
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)()
    }

    // Fetch audio
    const response = await fetch(store.audioUrl)
    const arrayBuffer = await response.arrayBuffer()
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)

    const sampleRate = audioBuffer.sampleRate

    if (type === 'call') {
      const start = props.pair.call.start
      const end = props.pair.call.end
      playBufferSegment(audioBuffer, start, end)
    } else if (type === 'response') {
      const start = props.pair.response.start
      const end = props.pair.response.end
      playBufferSegment(audioBuffer, start, end)
    } else {
      // Play both - for simplicity, play call then response
      // In a full implementation, you'd mix them with offset
      const callStart = props.pair.call.start
      const callEnd = props.pair.call.end
      playBufferSegment(audioBuffer, callStart, callEnd)
    }
  } catch (error) {
    console.error('Playback error:', error)
  }
}

function playBufferSegment(buffer, startTime, endTime) {
  const source = audioContext.createBufferSource()
  source.buffer = buffer
  source.connect(audioContext.destination)

  const startOffset = startTime
  const duration = endTime - startTime

  currentSource = source
  source.start(0, startOffset, duration)

  source.onended = () => {
    currentSource = null
  }
}
</script>

<style scoped>
.alignment-controls {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

h3 {
  font-size: 1.1rem;
  color: #ccc;
  margin: 0;
}

h4 {
  font-size: 0.9rem;
  color: #888;
  margin: 0 0 0.75rem 0;
}

.metrics-panel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.metric {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-label {
  font-size: 0.85rem;
  color: #888;
}

.metric-value {
  font-size: 1rem;
  font-weight: 600;
  font-family: monospace;
}

.metric-value.high {
  color: #4caf50;
}

.metric-value.medium {
  color: #ff9800;
}

.metric-value.low {
  color: #f44336;
}

.metric-value.muted {
  color: #666;
}

.offset-control {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.offset-control label {
  font-size: 0.85rem;
  color: #888;
}

.slider-container {
  padding: 0 0.5rem;
}

.slider {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  background: #0f3460;
  border-radius: 3px;
  outline: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: #e94560;
  border-radius: 50%;
  cursor: pointer;
}

.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: #e94560;
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #666;
  margin-top: 0.25rem;
}

.offset-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;
}

.offset-input {
  width: 80px;
  padding: 0.4rem;
  background: #0f3460;
  border: 1px solid #1a4b8c;
  border-radius: 4px;
  color: #ccc;
  font-family: monospace;
  text-align: center;
}

.unit {
  font-size: 0.85rem;
  color: #666;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
}

.action-buttons .btn {
  flex: 1;
  padding: 0.6rem;
  font-size: 0.85rem;
}

.pair-info {
  padding-top: 1rem;
  border-top: 1px solid #0f3460;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.info-row .label {
  color: #888;
}

.info-row .value {
  color: #ccc;
  font-family: monospace;
}

.playback-controls {
  padding-top: 1rem;
  border-top: 1px solid #0f3460;
}

.playback-buttons {
  display: flex;
  gap: 0.5rem;
}

.playback-buttons .btn {
  flex: 1;
  padding: 0.5rem;
  font-size: 0.8rem;
}
</style>
