import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

export default {
  // Upload
  async uploadFile(file) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await client.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  // Session/Metadata
  async getMetadata(sessionId) {
    const response = await client.get(`/sessions/${sessionId}/metadata`)
    return response.data
  },

  async getAudioInfo(sessionId) {
    const response = await client.get(`/sessions/${sessionId}/audio-info`)
    return response.data
  },

  async listSessions() {
    const response = await client.get('/sessions')
    return response.data
  },

  async deleteSession(sessionId) {
    const response = await client.delete(`/sessions/${sessionId}`)
    return response.data
  },

  // Processing
  async startProcessing(sessionId) {
    const response = await client.post(`/sessions/${sessionId}/process`)
    return response.data
  },

  async getProcessingStatus(sessionId) {
    const response = await client.get(`/sessions/${sessionId}/status`)
    return response.data
  },

  async getProcessingLogs(sessionId, since = 0) {
    const response = await client.get(`/sessions/${sessionId}/logs`, {
      params: { since }
    })
    return response.data
  },

  async separateVocals(sessionId) {
    const response = await client.post(`/sessions/${sessionId}/separate-vocals`)
    return response.data
  },

  async detectSections(sessionId) {
    const response = await client.post(`/sessions/${sessionId}/detect-sections`)
    return response.data
  },

  async runSegmentation(sessionId, references = null) {
    const response = await client.post(`/sessions/${sessionId}/segment`, references)
    return response.data
  },

  async estimatePitch(sessionId) {
    const response = await client.post(`/sessions/${sessionId}/estimate-pitch`)
    return response.data
  },

  // Sections
  async getSections(sessionId) {
    const response = await client.get(`/sessions/${sessionId}/sections`)
    return response.data
  },

  async createSection(sessionId, section) {
    const response = await client.post(`/sessions/${sessionId}/sections`, section)
    return response.data
  },

  async updateSection(sessionId, sectionId, updates) {
    const response = await client.put(`/sessions/${sessionId}/sections/${sectionId}`, updates)
    return response.data
  },

  async deleteSection(sessionId, sectionId) {
    const response = await client.delete(`/sessions/${sessionId}/sections/${sectionId}`)
    return response.data
  },

  async toggleSectionLabel(sessionId, sectionId) {
    const response = await client.post(`/sessions/${sessionId}/sections/${sectionId}/toggle-label`)
    return response.data
  },

  async splitSection(sessionId, sectionId, splitTime) {
    const response = await client.post(
      `/sessions/${sessionId}/sections/${sectionId}/split`,
      null,
      { params: { split_time: splitTime } }
    )
    return response.data
  },

  async mergeSections(sessionId, sectionIds) {
    const response = await client.post(`/sessions/${sessionId}/sections/merge`, sectionIds)
    return response.data
  },

  async replaceSections(sessionId, sections) {
    const response = await client.put(`/sessions/${sessionId}/sections`, sections)
    return response.data
  },

  // Alignment
  async getPairs(sessionId) {
    const response = await client.get(`/sessions/${sessionId}/pairs`)
    return response.data
  },

  async getPairPitch(sessionId, pairId) {
    const response = await client.get(`/sessions/${sessionId}/pairs/${pairId}/pitch`)
    return response.data
  },

  async getAlignments(sessionId) {
    const response = await client.get(`/sessions/${sessionId}/alignments`)
    return response.data
  },

  async updateAlignment(sessionId, pairId, customOffset) {
    const response = await client.put(
      `/sessions/${sessionId}/alignments/${pairId}`,
      null,
      { params: { custom_offset: customOffset } }
    )
    return response.data
  },

  async getPairMetrics(sessionId, pairId, offset) {
    const response = await client.get(
      `/sessions/${sessionId}/pairs/${pairId}/metrics`,
      { params: { offset } }
    )
    return response.data
  },

  async getPairAudio(sessionId, pairId, source) {
    const response = await client.get(`/sessions/${sessionId}/pairs/${pairId}/audio/${source}`)
    return response.data
  },

  // Export/Import
  async exportProject(sessionId) {
    const response = await client.get(`/sessions/${sessionId}/export`, {
      responseType: 'blob'
    })
    return response
  },

  async importProject(sessionId, file) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await client.post(`/sessions/${sessionId}/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  async exportSections(sessionId) {
    const response = await client.get(`/sessions/${sessionId}/export/sections`)
    return response.data
  },

  async exportAlignments(sessionId) {
    const response = await client.get(`/sessions/${sessionId}/export/alignments`)
    return response.data
  }
}
