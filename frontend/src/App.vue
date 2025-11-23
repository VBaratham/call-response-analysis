<template>
  <div class="app">
    <header class="header">
      <h1>Call/Response Analysis</h1>
      <div class="header-actions">
        <button v-if="store.sessionId" @click="exportProject" class="btn btn-secondary">
          Export Project
        </button>
        <button v-if="store.sessionId" @click="newProject" class="btn btn-secondary">
          New Project
        </button>
      </div>
    </header>

    <main class="main-content">
      <!-- File Upload -->
      <FileUpload v-if="!store.sessionId" @uploaded="onFileUploaded" />

      <!-- Project Choice (after upload, before processing) -->
      <ProjectChoice
        v-else-if="store.isAwaitingProjectChoice"
        :session-id="store.sessionId"
        @start-processing="onStartProcessing"
        @project-imported="onProjectImported"
      />

      <!-- Processing Status -->
      <ProcessingStatus
        v-else-if="store.isProcessing"
        :status="store.processingStatus"
        :logs="store.processingLogs"
      />

      <!-- Reference Selection (after vocals ready, before segmentation) -->
      <InitialReferenceSelector
        v-else-if="store.isSelectingReferences"
        :audio-url="store.audioUrl"
        :duration="store.duration"
        :reference-sections="store.referenceSections"
        :has-known-references="!!store.knownReferences"
        @add-reference="onAddReference"
        @remove-reference="onRemoveReference"
        @run-segmentation="onRunSegmentation"
        @skip-references="onSkipReferences"
        @use-known-references="onUseKnownReferences"
      />

      <!-- Main Editor -->
      <div v-else-if="store.hasData" class="editor-container">
        <!-- Tab Navigation -->
        <div class="tabs">
          <button
            :class="['tab', { active: activeTab === 'segments' }]"
            @click="activeTab = 'segments'"
          >
            Segment Editor
          </button>
          <button
            :class="['tab', { active: activeTab === 'alignment' }]"
            @click="activeTab = 'alignment'"
          >
            Call/Response Alignment
          </button>
        </div>

        <!-- Segment Editor Tab -->
        <div v-show="activeTab === 'segments'" class="tab-content">
          <WaveformEditor
            :audio-url="store.audioUrl"
            :sections="store.sections"
            :duration="store.duration"
            @sections-updated="onSectionsUpdated"
          />
        </div>

        <!-- Pitch Alignment Tab -->
        <div v-show="activeTab === 'alignment'" class="tab-content">
          <div class="alignment-layout">
            <PairSelector
              :pairs="store.pairs"
              :current-pair="store.currentPairId"
              @select="onPairSelect"
            />
            <PitchViewer
              v-if="store.currentPair"
              :call-pitch="store.currentCallPitch"
              :response-pitch="store.currentResponsePitch"
              :offset="store.currentOffset"
              @offset-changed="onOffsetChanged"
            />
            <AlignmentControls
              v-if="store.currentPair"
              :pair="store.currentPair"
              :metrics="store.currentMetrics"
              :offset="store.currentOffset"
              @offset-changed="onOffsetChanged"
              @save-offset="onSaveOffset"
              @reset-offset="onResetOffset"
            />
          </div>
        </div>
      </div>

      <!-- Loading/Error State -->
      <div v-else class="loading">
        <p>Loading session data...</p>
      </div>
    </main>

    <footer class="footer">
      <p>Call/Response Analysis Tool</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useProjectStore } from './stores/project'
import FileUpload from './components/FileUpload.vue'
import ProjectChoice from './components/ProjectChoice.vue'
import ProcessingStatus from './components/ProcessingStatus.vue'
import WaveformEditor from './components/WaveformEditor.vue'
import PitchViewer from './components/PitchViewer.vue'
import AlignmentControls from './components/AlignmentControls.vue'
import PairSelector from './components/PairSelector.vue'
import InitialReferenceSelector from './components/InitialReferenceSelector.vue'

const store = useProjectStore()
const activeTab = ref('segments')

onMounted(async () => {
  // Check for saved session in localStorage
  const savedSession = localStorage.getItem('currentSession')
  if (savedSession) {
    try {
      await store.loadSession(savedSession)
    } catch (e) {
      localStorage.removeItem('currentSession')
    }
  }
})

async function onFileUploaded(sessionId) {
  localStorage.setItem('currentSession', sessionId)
  await store.loadSession(sessionId)
  // Show choice: start processing or import existing project
  store.setAwaitingProjectChoice(true)
}

async function onStartProcessing() {
  await store.startProcessing()
}

async function onProjectImported() {
  // Clear the choice screen and reload session to get imported data
  store.setAwaitingProjectChoice(false)
  await store.loadSession(store.sessionId)
}

function onSectionsUpdated(sections) {
  store.updateSections(sections)
}

function onPairSelect(pairId) {
  store.selectPair(pairId)
}

function onOffsetChanged(offset) {
  store.setCurrentOffset(offset)
}

async function onSaveOffset() {
  await store.saveCurrentOffset()
}

function onResetOffset() {
  store.resetCurrentOffset()
}

function onAddReference(section, label) {
  store.addReferenceSection(section, label)
}

function onRemoveReference(sectionId, label) {
  store.removeReferenceSection(sectionId, label)
}

async function onRunSegmentation() {
  await store.runSegmentation()
}

async function onSkipReferences() {
  // Skip reference selection and run auto-detection
  store.clearReferenceSections()
  await store.runSegmentation()
}

function onUseKnownReferences() {
  store.useKnownReferences()
}

async function exportProject() {
  await store.exportProject()
}

function newProject() {
  localStorage.removeItem('currentSession')
  store.reset()
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: #1a1a2e;
  color: #eee;
  min-height: 100vh;
}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
}

.header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #e94560;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.main-content {
  flex: 1;
  padding: 1.5rem;
  overflow: auto;
}

.footer {
  padding: 1rem;
  text-align: center;
  background: #16213e;
  border-top: 1px solid #0f3460;
  font-size: 0.85rem;
  color: #888;
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

.btn-primary:hover {
  background: #ff6b6b;
}

.btn-secondary {
  background: #0f3460;
  color: #eee;
  border: 1px solid #1a4b8c;
}

.btn-secondary:hover {
  background: #1a4b8c;
}

.editor-container {
  height: calc(100vh - 180px);
  display: flex;
  flex-direction: column;
}

.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.tab {
  padding: 0.75rem 1.5rem;
  background: #16213e;
  border: 1px solid #0f3460;
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  color: #888;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.tab:hover {
  color: #ccc;
}

.tab.active {
  background: #1a1a2e;
  color: #e94560;
  border-color: #e94560;
}

.tab-content {
  flex: 1;
  background: #16213e;
  border-radius: 0 8px 8px 8px;
  padding: 1rem;
  overflow: auto;
}

.alignment-layout {
  display: grid;
  grid-template-columns: 200px 1fr 300px;
  gap: 1rem;
  height: 100%;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
  color: #888;
}

@media (max-width: 1200px) {
  .alignment-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
  }
}
</style>
