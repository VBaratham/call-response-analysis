<template>
  <div class="reference-selector">
    <h3>Reference Sections</h3>
    <p class="description">
      Mark sections as references for improved fingerprinting accuracy.
      Select high-confidence examples of each type.
    </p>

    <!-- Call References -->
    <div class="reference-group">
      <h4>
        <span class="dot call"></span>
        Call References ({{ callReferences.length }})
      </h4>
      <div class="reference-list">
        <div
          v-for="section in callSections"
          :key="section.id"
          class="reference-item"
          :class="{ selected: section.is_reference }"
          @click="toggleReference(section)"
        >
          <div class="ref-info">
            <span class="ref-time">{{ formatTime(section.start) }} - {{ formatTime(section.end) }}</span>
            <span class="ref-duration">{{ (section.end - section.start).toFixed(1) }}s</span>
          </div>
          <div class="ref-confidence" v-if="section.confidence">
            {{ (section.confidence * 100).toFixed(0) }}%
          </div>
          <div class="ref-check">
            <svg v-if="section.is_reference" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Response References -->
    <div class="reference-group">
      <h4>
        <span class="dot response"></span>
        Response References ({{ responseReferences.length }})
      </h4>
      <div class="reference-list">
        <div
          v-for="section in responseSections"
          :key="section.id"
          class="reference-item"
          :class="{ selected: section.is_reference }"
          @click="toggleReference(section)"
        >
          <div class="ref-info">
            <span class="ref-time">{{ formatTime(section.start) }} - {{ formatTime(section.end) }}</span>
            <span class="ref-duration">{{ (section.end - section.start).toFixed(1) }}s</span>
          </div>
          <div class="ref-confidence" v-if="section.confidence">
            {{ (section.confidence * 100).toFixed(0) }}%
          </div>
          <div class="ref-check">
            <svg v-if="section.is_reference" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="actions">
      <button
        class="btn btn-primary"
        @click="rerunFingerprinting"
        :disabled="callReferences.length === 0 || responseReferences.length === 0"
      >
        Re-run Fingerprinting
      </button>
      <button class="btn btn-secondary" @click="autoSelectReferences">
        Auto-select Best
      </button>
    </div>

    <p class="hint" v-if="callReferences.length === 0 || responseReferences.length === 0">
      Select at least one reference for each type to re-run fingerprinting.
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useProjectStore } from '../stores/project'

const store = useProjectStore()

const callSections = computed(() =>
  store.sections.filter(s => s.label === 'call').sort((a, b) => a.start - b.start)
)

const responseSections = computed(() =>
  store.sections.filter(s => s.label === 'response').sort((a, b) => a.start - b.start)
)

const callReferences = computed(() =>
  callSections.value.filter(s => s.is_reference)
)

const responseReferences = computed(() =>
  responseSections.value.filter(s => s.is_reference)
)

function toggleReference(section) {
  store.updateSection(section.id, { is_reference: !section.is_reference })
}

function autoSelectReferences() {
  // Auto-select top 3 highest confidence sections for each type
  const topCalls = [...callSections.value]
    .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
    .slice(0, 3)

  const topResponses = [...responseSections.value]
    .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
    .slice(0, 3)

  // Clear existing references
  store.sections.forEach(s => {
    if (s.is_reference) {
      store.updateSection(s.id, { is_reference: false })
    }
  })

  // Set new references
  topCalls.forEach(s => store.updateSection(s.id, { is_reference: true }))
  topResponses.forEach(s => store.updateSection(s.id, { is_reference: true }))
}

async function rerunFingerprinting() {
  // This would call the API to re-run fingerprinting with new references
  // For now, just log
  console.log('Re-running fingerprinting with references:', {
    call: callReferences.value.map(s => [s.start, s.end]),
    response: responseReferences.value.map(s => [s.start, s.end])
  })

  // TODO: Call API endpoint to re-run fingerprinting
  alert('Re-run fingerprinting feature coming soon!')
}

function formatTime(seconds) {
  if (!seconds) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}
</script>

<style scoped>
.reference-selector {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1rem;
}

h3 {
  font-size: 1rem;
  color: #ccc;
  margin: 0 0 0.5rem 0;
}

.description {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 1rem;
  line-height: 1.4;
}

.reference-group {
  margin-bottom: 1.5rem;
}

.reference-group h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #888;
  margin-bottom: 0.75rem;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.call {
  background: #e94560;
}

.dot.response {
  background: #4facfe;
}

.reference-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.reference-item {
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

.reference-item:hover {
  border-color: #1a4b8c;
}

.reference-item.selected {
  background: rgba(76, 175, 80, 0.15);
  border-color: #4caf50;
}

.ref-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.ref-time {
  font-size: 0.85rem;
  font-family: monospace;
  color: #ccc;
}

.ref-duration {
  font-size: 0.75rem;
  color: #666;
}

.ref-confidence {
  font-size: 0.75rem;
  color: #888;
  background: #1a1a2e;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
}

.ref-check {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4caf50;
}

.actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.actions .btn {
  flex: 1;
  padding: 0.6rem;
  font-size: 0.85rem;
}

.hint {
  font-size: 0.8rem;
  color: #ff9800;
  text-align: center;
}
</style>
