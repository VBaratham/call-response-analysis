<template>
  <div class="waveform-editor">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-group">
        <button class="btn btn-icon" @click="togglePlayback" :title="isPlaying ? 'Pause' : 'Play'">
          <svg v-if="!isPlaying" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5 3 19 12 5 21"/>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="4" width="4" height="16"/>
            <rect x="14" y="4" width="4" height="16"/>
          </svg>
        </button>
        <button class="btn btn-icon" @click="stopPlayback" title="Stop">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <rect x="4" y="4" width="16" height="16"/>
          </svg>
        </button>
        <span class="time-display">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
      </div>

      <div class="toolbar-group speed-controls">
        <span class="speed-label">Speed:</span>
        <button
          v-for="speed in playbackSpeeds"
          :key="speed"
          class="btn btn-speed"
          :class="{ active: currentSpeed === speed }"
          @click="setPlaybackSpeed(speed)"
        >
          {{ speed }}x
        </button>
      </div>

      <div class="toolbar-group">
        <button class="btn btn-icon" @click="zoomIn" title="Zoom In">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            <line x1="11" y1="8" x2="11" y2="14"/>
            <line x1="8" y1="11" x2="14" y2="11"/>
          </svg>
        </button>
        <button class="btn btn-icon" @click="zoomOut" title="Zoom Out">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            <line x1="8" y1="11" x2="14" y2="11"/>
          </svg>
        </button>
        <button class="btn btn-icon" @click="resetZoom" title="Reset Zoom">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          </svg>
        </button>
      </div>

      <div class="toolbar-group">
        <button class="btn btn-icon" @click="undo" :disabled="!canUndo" title="Undo (Cmd+Z)">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 7v6h6"/>
            <path d="M3 13a9 9 0 1 0 3-7.7L3 7"/>
          </svg>
        </button>
        <button class="btn btn-icon" @click="redo" :disabled="!canRedo" title="Redo (Cmd+Shift+Z)">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 7v6h-6"/>
            <path d="M21 13a9 9 0 1 1-3-7.7L21 7"/>
          </svg>
        </button>
      </div>

      <div class="toolbar-group">
        <button class="btn btn-small" @click="addSection" title="Add Section">
          + Add Section
        </button>
      </div>
    </div>

    <!-- Waveform Container -->
    <div class="waveform-container" ref="waveformContainer" @wheel="handleWheel"></div>

    <!-- Section Details Panel -->
    <div class="details-panel" v-if="selectedSection">
      <h3>Selected Section</h3>
      <div class="detail-row">
        <span class="label">Type:</span>
        <span :class="['value', 'label-' + selectedSection.label]">
          {{ selectedSection.label }}
        </span>
        <button class="btn btn-small" @click="toggleSelectedLabel">
          Toggle (T)
        </button>
      </div>
      <div class="detail-row">
        <span class="label">Start:</span>
        <span class="value">{{ formatTime(selectedSection.start) }}</span>
        <div class="adjust-buttons">
          <button @click="adjustStart(-1)" title="-1s">-1s</button>
          <button @click="adjustStart(-0.1)" title="-0.1s">-0.1</button>
          <button @click="adjustStart(0.1)" title="+0.1s">+0.1</button>
          <button @click="adjustStart(1)" title="+1s">+1s</button>
        </div>
      </div>
      <div class="detail-row">
        <span class="label">End:</span>
        <span class="value">{{ formatTime(selectedSection.end) }}</span>
        <div class="adjust-buttons">
          <button @click="adjustEnd(-1)" title="-1s">-1s</button>
          <button @click="adjustEnd(-0.1)" title="-0.1s">-0.1</button>
          <button @click="adjustEnd(0.1)" title="+0.1s">+0.1</button>
          <button @click="adjustEnd(1)" title="+1s">+1s</button>
        </div>
      </div>
      <div class="detail-row">
        <span class="label">Duration:</span>
        <span class="value">{{ (selectedSection.end - selectedSection.start).toFixed(2) }}s</span>
      </div>
      <div class="detail-row">
        <span class="label">Reference:</span>
        <input type="checkbox" :checked="selectedSection.is_reference" @change="toggleReference">
      </div>
      <div class="detail-actions">
        <button class="btn btn-small btn-danger" @click="deleteSelected">Delete (Del)</button>
        <button class="btn btn-small" @click="splitAtPlayhead">Split (S)</button>
      </div>
    </div>

    <!-- Help Panel -->
    <div class="help-panel">
      <h4>Shortcuts</h4>
      <ul>
        <li><kbd>Space</kbd> Play section / Pause</li>
        <li><kbd>Shift+Space</kbd> Play last 2s</li>
        <li><kbd>T</kbd> Toggle Call/Response</li>
        <li><kbd>Del</kbd> Delete Section</li>
        <li><kbd>S</kbd> Split at Playhead</li>
        <li><kbd>+/-</kbd> Zoom</li>
        <li><kbd>Shift+Scroll</kbd> Zoom</li>
        <li><kbd>Cmd+Z</kbd> Undo</li>
        <li><kbd>Cmd+Shift+Z</kbd> Redo</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import WaveSurfer from 'wavesurfer.js'
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js'
import { useProjectStore } from '../stores/project'

const props = defineProps({
  audioUrl: String,
  sections: Array,
  duration: Number
})

const emit = defineEmits(['sections-updated'])

const store = useProjectStore()

const waveformContainer = ref(null)
let wavesurfer = null
let regionsPlugin = null

const isPlaying = ref(false)
const currentTime = ref(0)
const selectedSection = ref(null)
const selectedRegionId = ref(null)
const canUndo = ref(false)
const canRedo = ref(false)
const playbackSpeeds = [0.5, 1, 2, 4]
const currentSpeed = ref(1)

// Colors
const CALL_COLOR = 'rgba(233, 69, 96, 0.4)'
const RESPONSE_COLOR = 'rgba(79, 172, 254, 0.4)'
const SELECTED_CALL_COLOR = 'rgba(233, 69, 96, 0.7)'
const SELECTED_RESPONSE_COLOR = 'rgba(79, 172, 254, 0.7)'

onMounted(async () => {
  await initWaveSurfer()
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  if (wavesurfer) {
    wavesurfer.destroy()
  }
  window.removeEventListener('keydown', handleKeydown)
})

watch(() => props.audioUrl, async (newUrl) => {
  if (newUrl && wavesurfer) {
    await wavesurfer.load(newUrl)
  }
})

watch(() => props.sections, (newSections) => {
  if (regionsPlugin && newSections) {
    syncRegions()
    // Update selectedSection if it exists (e.g., after toggle)
    if (selectedSection.value) {
      const updated = newSections.find(s => s.id === selectedSection.value.id)
      if (updated) {
        selectedSection.value = updated
      } else {
        // Section was deleted
        selectedSection.value = null
        selectedRegionId.value = null
      }
    }
  }
}, { deep: true })

async function initWaveSurfer() {
  regionsPlugin = RegionsPlugin.create()

  wavesurfer = WaveSurfer.create({
    container: waveformContainer.value,
    waveColor: '#4a5568',
    progressColor: '#e94560',
    cursorColor: '#e94560',
    cursorWidth: 2,
    height: 150,
    normalize: true,
    plugins: [regionsPlugin]
  })

  // Events
  wavesurfer.on('ready', () => {
    syncRegions()
  })

  wavesurfer.on('play', () => {
    isPlaying.value = true
  })

  wavesurfer.on('pause', () => {
    isPlaying.value = false
  })

  wavesurfer.on('timeupdate', (time) => {
    currentTime.value = time
  })

  // Region events
  regionsPlugin.on('region-clicked', (region, e) => {
    e.stopPropagation()
    selectRegion(region)
  })

  regionsPlugin.on('region-updated', (region) => {
    updateSectionFromRegion(region)
  })

  regionsPlugin.on('region-created', (region) => {
    // Only handle user-created regions
    if (!region.id.startsWith('section_')) {
      // This is a new region created by user
      const newSection = {
        id: region.id,
        start: region.start,
        end: region.end,
        label: 'call',
        is_reference: false,
        confidence: null
      }
      const updatedSections = [...props.sections, newSection]
      emit('sections-updated', updatedSections)
    }
  })

  // Load audio
  if (props.audioUrl) {
    await wavesurfer.load(props.audioUrl)
  }
}

function syncRegions() {
  if (!regionsPlugin) return

  // Clear existing regions
  regionsPlugin.clearRegions()

  // Add regions for sections
  props.sections.forEach(section => {
    const isSelected = selectedRegionId.value === section.id
    const color = section.label === 'call'
      ? (isSelected ? SELECTED_CALL_COLOR : CALL_COLOR)
      : (isSelected ? SELECTED_RESPONSE_COLOR : RESPONSE_COLOR)

    regionsPlugin.addRegion({
      id: section.id,
      start: section.start,
      end: section.end,
      color: color,
      drag: true,
      resize: true
    })
  })
}

function selectRegion(region) {
  selectedRegionId.value = region.id
  selectedSection.value = props.sections.find(s => s.id === region.id)
  syncRegions() // Update colors
}

function updateSectionFromRegion(region) {
  const updatedSections = props.sections.map(s => {
    if (s.id === region.id) {
      return {
        ...s,
        start: region.start,
        end: region.end
      }
    }
    return s
  })
  emit('sections-updated', updatedSections)
}

function togglePlayback() {
  if (wavesurfer) {
    wavesurfer.playPause()
  }
}

function stopPlayback() {
  if (wavesurfer) {
    wavesurfer.stop()
  }
}

function setPlaybackSpeed(speed) {
  currentSpeed.value = speed
  if (wavesurfer) {
    wavesurfer.setPlaybackRate(speed)
  }
}

function zoomIn() {
  if (wavesurfer) {
    const currentZoom = wavesurfer.options.minPxPerSec || 50
    wavesurfer.zoom(currentZoom * 1.5)
  }
}

function zoomOut() {
  if (wavesurfer) {
    const currentZoom = wavesurfer.options.minPxPerSec || 50
    wavesurfer.zoom(Math.max(10, currentZoom / 1.5))
  }
}

function resetZoom() {
  if (wavesurfer) {
    wavesurfer.zoom(50)
  }
}

function handleWheel(e) {
  // Zoom if Ctrl/Cmd or Shift is held, otherwise allow normal scroll
  if (e.ctrlKey || e.metaKey || e.shiftKey) {
    e.preventDefault()
    if (wavesurfer) {
      const currentZoom = wavesurfer.options.minPxPerSec || 50
      // Slower zoom factor (was 0.8/1.25, now 0.95/1.05)
      const delta = e.deltaY > 0 ? 0.95 : 1.05  // Scroll down = zoom out, up = zoom in
      const newZoom = Math.max(10, Math.min(500, currentZoom * delta))
      wavesurfer.zoom(newZoom)
    }
  }
}

async function undo() {
  await store.undo()
}

async function redo() {
  await store.redo()
}

function addSection() {
  const time = currentTime.value
  const newSection = {
    start: time,
    end: Math.min(time + 5, props.duration),
    label: 'call',
    is_reference: false
  }
  store.addSection(newSection)
}

function toggleSelectedLabel() {
  if (selectedSection.value) {
    store.toggleSectionLabel(selectedSection.value.id)
  }
}

function adjustStart(delta) {
  if (selectedSection.value) {
    const newStart = Math.max(0, selectedSection.value.start + delta)
    if (newStart < selectedSection.value.end) {
      store.updateSection(selectedSection.value.id, { start: newStart })
    }
  }
}

function adjustEnd(delta) {
  if (selectedSection.value) {
    const newEnd = Math.min(props.duration, selectedSection.value.end + delta)
    if (newEnd > selectedSection.value.start) {
      store.updateSection(selectedSection.value.id, { end: newEnd })
    }
  }
}

function toggleReference() {
  if (selectedSection.value) {
    store.updateSection(selectedSection.value.id, {
      is_reference: !selectedSection.value.is_reference
    })
  }
}

function deleteSelected() {
  if (selectedSection.value) {
    store.deleteSection(selectedSection.value.id)
    selectedSection.value = null
    selectedRegionId.value = null
  }
}

function splitAtPlayhead() {
  if (selectedSection.value) {
    const time = currentTime.value
    if (time > selectedSection.value.start && time < selectedSection.value.end) {
      store.splitSection(selectedSection.value.id, time)
      selectedSection.value = null
      selectedRegionId.value = null
    }
  }
}

function playSelectedSection() {
  if (!wavesurfer || !selectedSection.value) return

  const section = selectedSection.value
  wavesurfer.setTime(section.start)
  wavesurfer.play()

  // Stop at end of section
  const stopAtEnd = () => {
    if (wavesurfer.getCurrentTime() >= section.end) {
      wavesurfer.pause()
      wavesurfer.un('timeupdate', stopAtEnd)
    }
  }
  wavesurfer.on('timeupdate', stopAtEnd)
}

function playLastTwoSeconds() {
  if (!wavesurfer) return

  const current = wavesurfer.getCurrentTime()
  const startTime = Math.max(0, current - 2)
  wavesurfer.setTime(startTime)
  wavesurfer.play()

  // Stop at original position
  const stopAtEnd = () => {
    if (wavesurfer.getCurrentTime() >= current) {
      wavesurfer.pause()
      wavesurfer.un('timeupdate', stopAtEnd)
    }
  }
  wavesurfer.on('timeupdate', stopAtEnd)
}

function handleKeydown(e) {
  // Ignore if typing in input
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return

  switch (e.key) {
    case ' ':
      e.preventDefault()
      if (isPlaying.value) {
        // If playing, always pause first
        togglePlayback()
      } else if (e.shiftKey) {
        // Shift+Space: play last 2 seconds
        playLastTwoSeconds()
      } else if (selectedSection.value) {
        // Space with selected section: play that section
        playSelectedSection()
      } else {
        // Space without selection: toggle playback
        togglePlayback()
      }
      break
    case 't':
    case 'T':
      toggleSelectedLabel()
      break
    case 'Delete':
    case 'Backspace':
      deleteSelected()
      break
    case 's':
    case 'S':
      splitAtPlayhead()
      break
    case '+':
    case '=':
      zoomIn()
      break
    case '-':
    case '_':
      zoomOut()
      break
    case '0':
      resetZoom()
      break
    case 'z':
      if (e.metaKey || e.ctrlKey) {
        e.preventDefault()
        if (e.shiftKey) {
          redo()
        } else {
          undo()
        }
      }
      break
    case 'y':
      if (e.metaKey || e.ctrlKey) {
        e.preventDefault()
        redo()
      }
      break
  }
}

function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}
</script>

<style scoped>
.waveform-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.toolbar {
  display: flex;
  gap: 1rem;
  padding: 0.75rem;
  background: #1a1a2e;
  border-radius: 8px;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-icon {
  width: 36px;
  height: 36px;
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
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-small {
  padding: 0.4rem 0.8rem;
  font-size: 0.85rem;
  background: #0f3460;
  border: 1px solid #1a4b8c;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
}

.btn-small:hover {
  background: #1a4b8c;
}

.btn-danger {
  border-color: #e94560;
  color: #e94560;
}

.btn-danger:hover {
  background: rgba(233, 69, 96, 0.2);
}

.time-display {
  font-family: monospace;
  font-size: 0.9rem;
  color: #888;
  min-width: 100px;
}

.speed-controls {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.speed-label {
  font-size: 0.8rem;
  color: #888;
  margin-right: 0.25rem;
}

.btn-speed {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  background: #0f3460;
  border: 1px solid #1a4b8c;
  border-radius: 4px;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-speed:hover {
  background: #1a4b8c;
  color: #ccc;
}

.btn-speed.active {
  background: #e94560;
  border-color: #e94560;
  color: white;
}

.waveform-container {
  flex: 1;
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1rem;
  min-height: 180px;
}

.details-panel {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1rem;
  margin-top: 1rem;
}

.details-panel h3 {
  font-size: 1rem;
  margin-bottom: 1rem;
  color: #ccc;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.detail-row .label {
  color: #888;
  width: 80px;
}

.detail-row .value {
  font-weight: 500;
  min-width: 80px;
}

.label-call {
  color: #e94560;
}

.label-response {
  color: #4facfe;
}

.adjust-buttons {
  display: flex;
  gap: 0.25rem;
}

.adjust-buttons button {
  padding: 0.2rem 0.4rem;
  font-size: 0.75rem;
  background: #0f3460;
  border: 1px solid #1a4b8c;
  border-radius: 3px;
  color: #888;
  cursor: pointer;
}

.adjust-buttons button:hover {
  background: #1a4b8c;
  color: #ccc;
}

.detail-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #0f3460;
}

.help-panel {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1rem;
  margin-top: 1rem;
}

.help-panel h4 {
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
  color: #888;
}

.help-panel ul {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.help-panel li {
  font-size: 0.85rem;
  color: #666;
}

.help-panel kbd {
  background: #0f3460;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.8rem;
  color: #ccc;
  margin-right: 0.3rem;
}
</style>
