<template>
  <div class="reference-selector">
    <div class="selector-header">
      <h2>Select Reference Sections</h2>
      <p class="instructions">
        Create sections on the waveform to define reference examples of "call" and "response" voices.
        The segmentation algorithm will use these to identify similar sections throughout the track.
      </p>
    </div>

    <div class="reference-summary">
      <div class="reference-group call">
        <h3>Call References ({{ referenceSections.call.length }})</h3>
        <div class="reference-list">
          <div v-if="referenceSections.call.length === 0" class="empty-hint">
            Click and drag on the waveform, then press C to add as call reference
          </div>
          <div
            v-for="section in referenceSections.call"
            :key="section.id"
            class="reference-item"
          >
            <span class="time">{{ formatTime(section.start) }} - {{ formatTime(section.end) }}</span>
            <button class="btn-remove" @click="$emit('remove-reference', section.id, 'call')">x</button>
          </div>
        </div>
      </div>

      <div class="reference-group response">
        <h3>Response References ({{ referenceSections.response.length }})</h3>
        <div class="reference-list">
          <div v-if="referenceSections.response.length === 0" class="empty-hint">
            Click and drag on the waveform, then press R to add as response reference
          </div>
          <div
            v-for="section in referenceSections.response"
            :key="section.id"
            class="reference-item"
          >
            <span class="time">{{ formatTime(section.start) }} - {{ formatTime(section.end) }}</span>
            <button class="btn-remove" @click="$emit('remove-reference', section.id, 'response')">x</button>
          </div>
        </div>
      </div>
    </div>

    <div class="waveform-container" ref="waveformContainer">
      <div id="waveform-ref"></div>
      <div id="timeline-ref"></div>
    </div>

    <div class="controls">
      <div class="playback-controls">
        <button class="btn btn-secondary" @click="togglePlay">
          {{ isPlaying ? 'Pause' : 'Play' }}
        </button>
        <button class="btn btn-secondary" @click="zoomIn">Zoom In (+)</button>
        <button class="btn btn-secondary" @click="zoomOut">Zoom Out (-)</button>
      </div>

      <div class="action-controls">
        <button
          class="btn btn-primary"
          :disabled="!canRunSegmentation"
          @click="$emit('run-segmentation')"
        >
          Run Segmentation
        </button>
        <button class="btn btn-secondary" @click="$emit('skip-references')">
          Skip (Auto-detect)
        </button>
      </div>
    </div>

    <div class="keyboard-hints">
      <span><kbd>C</kbd> Add selection as Call</span>
      <span><kbd>R</kbd> Add selection as Response</span>
      <span><kbd>Space</kbd> Play/Pause</span>
      <span><kbd>+/-</kbd> Zoom</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import WaveSurfer from 'wavesurfer.js'
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js'
import TimelinePlugin from 'wavesurfer.js/dist/plugins/timeline.esm.js'

const props = defineProps({
  audioUrl: {
    type: String,
    required: true
  },
  duration: {
    type: Number,
    default: 0
  },
  referenceSections: {
    type: Object,
    default: () => ({ call: [], response: [] })
  }
})

const emit = defineEmits(['add-reference', 'remove-reference', 'run-segmentation', 'skip-references'])

let wavesurfer = null
let regionsPlugin = null
const waveformContainer = ref(null)
const isPlaying = ref(false)
const pendingRegion = ref(null)

const canRunSegmentation = computed(() => {
  return props.referenceSections.call.length > 0 && props.referenceSections.response.length > 0
})

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function initWavesurfer() {
  if (wavesurfer) {
    wavesurfer.destroy()
  }

  regionsPlugin = RegionsPlugin.create()

  wavesurfer = WaveSurfer.create({
    container: '#waveform-ref',
    waveColor: '#4a9eff',
    progressColor: '#e94560',
    cursorColor: '#fff',
    height: 200,
    normalize: true,
    minPxPerSec: 50,
    plugins: [
      regionsPlugin,
      TimelinePlugin.create({
        container: '#timeline-ref',
        primaryLabelInterval: 10,
        secondaryLabelInterval: 5,
        style: {
          fontSize: '12px',
          color: '#888'
        }
      })
    ]
  })

  wavesurfer.load(props.audioUrl)

  wavesurfer.on('ready', () => {
    regionsPlugin.enableDragSelection({
      color: 'rgba(255, 255, 255, 0.2)'
    })
    renderReferences()
  })

  wavesurfer.on('play', () => {
    isPlaying.value = true
  })

  wavesurfer.on('pause', () => {
    isPlaying.value = false
  })

  regionsPlugin.on('region-created', (region) => {
    if (pendingRegion.value && pendingRegion.value.id !== region.id) {
      try {
        pendingRegion.value.remove()
      } catch (e) {}
    }
    pendingRegion.value = region
    region.setOptions({
      color: 'rgba(255, 255, 255, 0.3)'
    })
  })
}

function renderReferences() {
  if (!regionsPlugin) return
  regionsPlugin.clearRegions()

  props.referenceSections.call.forEach(section => {
    regionsPlugin.addRegion({
      id: section.id,
      start: section.start,
      end: section.end,
      color: 'rgba(233, 69, 96, 0.4)',
      drag: false,
      resize: false
    })
  })

  props.referenceSections.response.forEach(section => {
    regionsPlugin.addRegion({
      id: section.id,
      start: section.start,
      end: section.end,
      color: 'rgba(74, 158, 255, 0.4)',
      drag: false,
      resize: false
    })
  })
}

function handleKeydown(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return

  if (e.code === 'Space') {
    e.preventDefault()
    togglePlay()
  } else if (e.key === 'c' || e.key === 'C') {
    e.preventDefault()
    addPendingAsReference('call')
  } else if (e.key === 'r' || e.key === 'R') {
    e.preventDefault()
    addPendingAsReference('response')
  } else if (e.key === '=' || e.key === '+') {
    e.preventDefault()
    zoomIn()
  } else if (e.key === '-') {
    e.preventDefault()
    zoomOut()
  }
}

function addPendingAsReference(label) {
  if (!pendingRegion.value) return

  const section = {
    id: `ref_${Date.now()}`,
    start: pendingRegion.value.start,
    end: pendingRegion.value.end
  }

  emit('add-reference', section, label)

  try {
    pendingRegion.value.remove()
  } catch (e) {}
  pendingRegion.value = null
}

function togglePlay() {
  if (wavesurfer) {
    wavesurfer.playPause()
  }
}

function zoomIn() {
  if (wavesurfer) {
    const currentZoom = wavesurfer.options.minPxPerSec || 50
    wavesurfer.zoom(Math.min(500, currentZoom * 1.5))
  }
}

function zoomOut() {
  if (wavesurfer) {
    const currentZoom = wavesurfer.options.minPxPerSec || 50
    wavesurfer.zoom(Math.max(10, currentZoom / 1.5))
  }
}

watch(() => props.referenceSections, () => {
  renderReferences()
}, { deep: true })

onMounted(() => {
  initWavesurfer()
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (wavesurfer) {
    wavesurfer.destroy()
  }
})
</script>

<style scoped>
.reference-selector {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  height: 100%;
  padding: 1rem;
}

.selector-header {
  text-align: center;
}

.selector-header h2 {
  color: #e94560;
  margin-bottom: 0.5rem;
}

.instructions {
  color: #888;
  font-size: 0.9rem;
  max-width: 600px;
  margin: 0 auto;
}

.reference-summary {
  display: flex;
  gap: 2rem;
  justify-content: center;
}

.reference-group {
  background: #0f3460;
  border-radius: 8px;
  padding: 1rem;
  min-width: 200px;
}

.reference-group h3 {
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

.reference-group.call h3 {
  color: #e94560;
}

.reference-group.response h3 {
  color: #4a9eff;
}

.reference-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.empty-hint {
  font-size: 0.8rem;
  color: #666;
  font-style: italic;
}

.reference-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0.5rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.reference-item .time {
  font-family: monospace;
  font-size: 0.85rem;
}

.btn-remove {
  background: none;
  border: none;
  color: #888;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0 0.25rem;
}

.btn-remove:hover {
  color: #ff6b6b;
}

.waveform-container {
  background: #16213e;
  border-radius: 8px;
  padding: 1rem;
  flex: 1;
  min-height: 250px;
}

#waveform-ref {
  margin-bottom: 0.5rem;
}

.controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.playback-controls,
.action-controls {
  display: flex;
  gap: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background: #e94560;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #ff6b6b;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #0f3460;
  color: #eee;
  border: 1px solid #1a4b8c;
}

.btn-secondary:hover {
  background: #1a4b8c;
}

.keyboard-hints {
  display: flex;
  justify-content: center;
  gap: 2rem;
  font-size: 0.8rem;
  color: #666;
}

kbd {
  background: #0f3460;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  font-family: monospace;
  margin-right: 0.25rem;
}
</style>
