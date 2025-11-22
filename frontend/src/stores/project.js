import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api'

export const useProjectStore = defineStore('project', () => {
  // State
  const sessionId = ref(null)
  const metadata = ref(null)
  const sections = ref([])
  const alignments = ref([])
  const hasFullPitch = ref(false)  // Whether full pitch data exists
  const currentPairId = ref(0)
  const currentOffset = ref(0)
  const currentCallPitch = ref([])
  const currentResponsePitch = ref([])
  const currentMetrics = ref(null)
  const processingStatus = ref(null)
  const processingLogs = ref([])
  const isProcessing = ref(false)
  const isSelectingReferences = ref(false)  // Whether user is selecting reference sections
  const referenceSections = ref({ call: [], response: [] })  // User-selected reference sections
  const knownReferences = ref(null)  // Pre-defined references for sample files

  // Undo/Redo stacks
  const undoStack = ref([])
  const redoStack = ref([])
  const maxUndoLevels = 50

  // Computed
  const hasData = computed(() => {
    return metadata.value && (metadata.value.has_sections || sections.value.length > 0)
  })

  const duration = computed(() => metadata.value?.duration || 0)

  const audioUrl = computed(() => {
    if (!sessionId.value) return null
    if (metadata.value?.has_vocals) {
      return `/audio/${sessionId.value}/vocals.wav`
    }
    return null
  })

  const pairs = computed(() => {
    const calls = sections.value.filter(s => s.label === 'call')
    const responses = sections.value.filter(s => s.label === 'response')
    const result = []

    for (let i = 0; i < Math.min(calls.length, responses.length); i++) {
      result.push({
        id: i,
        call: calls[i],
        response: responses[i]
      })
    }
    return result
  })

  const currentPair = computed(() => {
    return pairs.value.find(p => p.id === currentPairId.value) || null
  })

  // Actions
  async function loadSession(id) {
    sessionId.value = id

    try {
      // Load metadata
      const metaResponse = await api.getMetadata(id)
      metadata.value = metaResponse

      // Check for known references (sample files)
      if (metaResponse.known_references) {
        knownReferences.value = metaResponse.known_references
      } else {
        knownReferences.value = null
      }

      // Load sections if available
      if (metaResponse.has_sections) {
        const sectionsResponse = await api.getSections(id)
        sections.value = sectionsResponse
      }

      // Load alignments if available
      if (metaResponse.has_pitch) {
        const alignResponse = await api.getAlignments(id)
        alignments.value = alignResponse.alignments || []
        hasFullPitch.value = alignResponse.has_full_pitch || false

        // Load first pair's pitch data (if available)
        if (pairs.value.length > 0 && hasFullPitch.value) {
          await selectPair(0)
        }
      }
    } catch (error) {
      console.error('Failed to load session:', error)
      throw error
    }
  }

  async function startProcessing() {
    isProcessing.value = true
    processingStatus.value = { stage: 'starting', progress: 0, message: 'Starting processing...' }
    processingLogs.value = []

    let logIndex = 0

    try {
      // Poll status and logs while processing
      const pollStatusAndLogs = async () => {
        try {
          const [status, logsData] = await Promise.all([
            api.getProcessingStatus(sessionId.value),
            api.getProcessingLogs(sessionId.value, logIndex)
          ])

          processingStatus.value = status

          // Append new logs
          if (logsData.logs && logsData.logs.length > 0) {
            processingLogs.value = [...processingLogs.value, ...logsData.logs]
            logIndex = logsData.total
          }

          // Check for vocals_ready status (vocals done, ready for reference selection)
          return status.stage === 'vocals_ready' || status.stage === 'complete' || status.stage === 'error'
        } catch (e) {
          // Ignore polling errors
          return false
        }
      }

      // Start processing (don't await yet)
      const processPromise = api.startProcessing(sessionId.value)

      // Poll until vocals are ready (every 4 seconds)
      while (!(await pollStatusAndLogs())) {
        await new Promise(resolve => setTimeout(resolve, 4000))
      }

      // Wait for the actual request to finish
      await processPromise

      // Final log poll
      await pollStatusAndLogs()

      // Reload metadata
      const metaResponse = await api.getMetadata(sessionId.value)
      metadata.value = metaResponse

      // Enter reference selection mode
      if (processingStatus.value.stage === 'vocals_ready') {
        isSelectingReferences.value = true
        referenceSections.value = { call: [], response: [] }
      }
    } catch (error) {
      processingStatus.value = {
        stage: 'error',
        progress: 0,
        message: error.response?.data?.detail || error.message,
        error: error.response?.data?.detail || error.message
      }
    } finally {
      isProcessing.value = false
    }
  }

  async function runSegmentation() {
    isProcessing.value = true
    processingStatus.value = { stage: 'fingerprinting', progress: 0, message: 'Running segmentation...' }

    let logIndex = processingLogs.value.length

    try {
      // Prepare references
      const references = {
        call_references: referenceSections.value.call.map(s => ({ start: s.start, end: s.end })),
        response_references: referenceSections.value.response.map(s => ({ start: s.start, end: s.end }))
      }

      // Poll status and logs while segmenting
      const pollStatusAndLogs = async () => {
        try {
          const [status, logsData] = await Promise.all([
            api.getProcessingStatus(sessionId.value),
            api.getProcessingLogs(sessionId.value, logIndex)
          ])

          processingStatus.value = status

          // Append new logs
          if (logsData.logs && logsData.logs.length > 0) {
            processingLogs.value = [...processingLogs.value, ...logsData.logs]
            logIndex = logsData.total
          }

          return status.stage === 'complete' || status.stage === 'error'
        } catch (e) {
          return false
        }
      }

      // Start segmentation (don't await yet)
      const segmentPromise = api.runSegmentation(sessionId.value, references)

      // Poll until complete
      while (!(await pollStatusAndLogs())) {
        await new Promise(resolve => setTimeout(resolve, 2000))
      }

      // Wait for the actual request to finish
      await segmentPromise

      // Final log poll
      await pollStatusAndLogs()

      // Exit reference selection mode
      isSelectingReferences.value = false

      // Reload session data
      await loadSession(sessionId.value)
    } catch (error) {
      processingStatus.value = {
        stage: 'error',
        progress: 0,
        message: error.response?.data?.detail || error.message,
        error: error.response?.data?.detail || error.message
      }
    } finally {
      isProcessing.value = false
    }
  }

  function addReferenceSection(section, label) {
    referenceSections.value[label].push(section)
  }

  function removeReferenceSection(sectionId, label) {
    referenceSections.value[label] = referenceSections.value[label].filter(s => s.id !== sectionId)
  }

  function clearReferenceSections() {
    referenceSections.value = { call: [], response: [] }
  }

  function useKnownReferences() {
    if (!knownReferences.value) return

    // Convert known references to the format expected by referenceSections
    referenceSections.value = {
      call: knownReferences.value.call.map((r, i) => ({
        id: `known_call_${i}`,
        start: r.start,
        end: r.end
      })),
      response: knownReferences.value.response.map((r, i) => ({
        id: `known_resp_${i}`,
        start: r.start,
        end: r.end
      }))
    }
  }

  async function updateSections(newSections) {
    // Save to undo stack
    pushUndo()

    sections.value = newSections

    // Save to server
    try {
      await api.replaceSections(sessionId.value, newSections)
    } catch (error) {
      console.error('Failed to save sections:', error)
    }
  }

  async function addSection(section) {
    pushUndo()
    const response = await api.createSection(sessionId.value, section)
    sections.value.push(response)
    sections.value.sort((a, b) => a.start - b.start)
  }

  async function updateSection(sectionId, updates) {
    pushUndo()
    const response = await api.updateSection(sessionId.value, sectionId, updates)
    const idx = sections.value.findIndex(s => s.id === sectionId)
    if (idx !== -1) {
      sections.value[idx] = response
      sections.value.sort((a, b) => a.start - b.start)
    }
  }

  async function deleteSection(sectionId) {
    pushUndo()
    await api.deleteSection(sessionId.value, sectionId)
    sections.value = sections.value.filter(s => s.id !== sectionId)
  }

  async function toggleSectionLabel(sectionId) {
    pushUndo()
    const response = await api.toggleSectionLabel(sessionId.value, sectionId)
    const idx = sections.value.findIndex(s => s.id === sectionId)
    if (idx !== -1) {
      sections.value[idx] = response
    }
  }

  async function splitSection(sectionId, splitTime) {
    pushUndo()
    const response = await api.splitSection(sessionId.value, sectionId, splitTime)
    const idx = sections.value.findIndex(s => s.id === sectionId)
    if (idx !== -1) {
      sections.value.splice(idx, 1, ...response)
    }
  }

  async function mergeSections(sectionIds) {
    pushUndo()
    const response = await api.mergeSections(sessionId.value, sectionIds)
    sections.value = sections.value.filter(s => !sectionIds.includes(s.id))
    sections.value.push(response)
    sections.value.sort((a, b) => a.start - b.start)
  }

  async function selectPair(pairId) {
    currentPairId.value = pairId

    // Check if pitch data exists
    if (!hasFullPitch.value) {
      currentCallPitch.value = []
      currentResponsePitch.value = []
      currentMetrics.value = { error: 'Pitch data not available. Run processing first.' }
      return
    }

    try {
      const pitchData = await api.getPairPitch(sessionId.value, pairId)
      currentCallPitch.value = pitchData.call
      currentResponsePitch.value = pitchData.response

      // Get alignment info
      const alignment = alignments.value.find(a => a.pair_id === pairId)
      currentOffset.value = alignment?.custom_offset ?? alignment?.optimal_offset ?? 0

      // Calculate metrics
      await updateMetrics()
    } catch (error) {
      console.error('Failed to load pair:', error)
      currentCallPitch.value = []
      currentResponsePitch.value = []
      currentMetrics.value = { error: 'Failed to load pitch data' }
    }
  }

  function setCurrentOffset(offset) {
    currentOffset.value = offset
    updateMetrics()
  }

  async function updateMetrics() {
    try {
      const metrics = await api.getPairMetrics(
        sessionId.value,
        currentPairId.value,
        currentOffset.value
      )
      currentMetrics.value = metrics
    } catch (error) {
      console.error('Failed to calculate metrics:', error)
    }
  }

  async function saveCurrentOffset() {
    try {
      await api.updateAlignment(sessionId.value, currentPairId.value, currentOffset.value)

      // Update local alignments
      const idx = alignments.value.findIndex(a => a.pair_id === currentPairId.value)
      if (idx !== -1) {
        alignments.value[idx].custom_offset = currentOffset.value
      } else {
        alignments.value.push({
          pair_id: currentPairId.value,
          custom_offset: currentOffset.value
        })
      }
    } catch (error) {
      console.error('Failed to save offset:', error)
    }
  }

  function resetCurrentOffset() {
    const alignment = alignments.value.find(a => a.pair_id === currentPairId.value)
    currentOffset.value = alignment?.optimal_offset ?? 0
    updateMetrics()
  }

  // Undo/Redo
  function pushUndo() {
    undoStack.value.push(JSON.parse(JSON.stringify(sections.value)))
    if (undoStack.value.length > maxUndoLevels) {
      undoStack.value.shift()
    }
    redoStack.value = []
  }

  async function undo() {
    if (undoStack.value.length === 0) return

    redoStack.value.push(JSON.parse(JSON.stringify(sections.value)))
    const prevState = undoStack.value.pop()
    sections.value = prevState

    try {
      await api.replaceSections(sessionId.value, sections.value)
    } catch (error) {
      console.error('Failed to save undo:', error)
    }
  }

  async function redo() {
    if (redoStack.value.length === 0) return

    undoStack.value.push(JSON.parse(JSON.stringify(sections.value)))
    const nextState = redoStack.value.pop()
    sections.value = nextState

    try {
      await api.replaceSections(sessionId.value, sections.value)
    } catch (error) {
      console.error('Failed to save redo:', error)
    }
  }

  async function exportProject() {
    try {
      const data = await api.exportProject(sessionId.value)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${sessionId.value}_project.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to export:', error)
    }
  }

  async function importProject(file) {
    try {
      await api.importProject(sessionId.value, file)
      await loadSession(sessionId.value)
    } catch (error) {
      console.error('Failed to import:', error)
    }
  }

  function reset() {
    sessionId.value = null
    metadata.value = null
    sections.value = []
    alignments.value = []
    hasFullPitch.value = false
    currentPairId.value = 0
    currentOffset.value = 0
    currentCallPitch.value = []
    currentResponsePitch.value = []
    currentMetrics.value = null
    processingStatus.value = null
    processingLogs.value = []
    isProcessing.value = false
    isSelectingReferences.value = false
    referenceSections.value = { call: [], response: [] }
    knownReferences.value = null
    undoStack.value = []
    redoStack.value = []
  }

  return {
    // State
    sessionId,
    metadata,
    sections,
    alignments,
    hasFullPitch,
    currentPairId,
    currentOffset,
    currentCallPitch,
    currentResponsePitch,
    currentMetrics,
    processingStatus,
    processingLogs,
    isProcessing,
    isSelectingReferences,
    referenceSections,
    knownReferences,

    // Computed
    hasData,
    duration,
    audioUrl,
    pairs,
    currentPair,

    // Actions
    loadSession,
    startProcessing,
    runSegmentation,
    addReferenceSection,
    removeReferenceSection,
    clearReferenceSections,
    useKnownReferences,
    updateSections,
    addSection,
    updateSection,
    deleteSection,
    toggleSectionLabel,
    splitSection,
    mergeSections,
    selectPair,
    setCurrentOffset,
    saveCurrentOffset,
    resetCurrentOffset,
    undo,
    redo,
    exportProject,
    importProject,
    reset
  }
})
