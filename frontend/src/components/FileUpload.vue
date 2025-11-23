<template>
  <div class="upload-container">
    <!-- App Description -->
    <div class="app-description">
      <h2>Call/Response Analysis Tool</h2>
      <p>
        Analyze call-and-response vocal patterns in audio recordings.
        This tool separates vocals, automatically detects call/response sections,
        and lets you compare pitch contours to study how responses mirror the original call.
      </p>
    </div>

    <div
      class="upload-dropzone"
      :class="{ 'drag-over': isDragOver }"
      @dragover.prevent="isDragOver = true"
      @dragleave.prevent="isDragOver = false"
      @drop.prevent="handleDrop"
    >
      <div class="upload-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
      </div>
      <h2>Upload Audio File</h2>
      <p>Drag and drop an audio file here, or click to select</p>
      <p class="formats">Supported formats: WAV, MP3, FLAC, OGG, M4A</p>

      <input
        ref="fileInput"
        type="file"
        accept=".wav,.mp3,.flac,.ogg,.m4a,.aiff"
        @change="handleFileSelect"
        hidden
      />

      <div class="upload-buttons">
        <button class="btn btn-primary" @click="$refs.fileInput.click()">
          Select File
        </button>
        <button class="btn btn-secondary" @click="useSampleFile" :disabled="isLoadingSample">
          {{ isLoadingSample ? 'Loading...' : 'Use Sample: Om Namah Shivaya' }}
        </button>
      </div>
    </div>

    <div v-if="isUploading" class="upload-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
      </div>
      <p>Uploading {{ fileName }}... {{ uploadProgress }}%</p>
    </div>

    <div v-if="error" class="upload-error">
      <p>{{ error }}</p>
      <button class="btn btn-secondary" @click="error = null">Dismiss</button>
    </div>

    <!-- Import hint -->
    <div class="import-hint">
      <p>Have a saved project? Upload the audio first, then you'll be able to import your project file.</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../services/api'

const emit = defineEmits(['uploaded'])

const fileInput = ref(null)
const isDragOver = ref(false)
const isUploading = ref(false)
const isLoadingSample = ref(false)
const uploadProgress = ref(0)
const fileName = ref('')
const error = ref(null)

async function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    await uploadFile(file)
  }
}

async function handleDrop(event) {
  isDragOver.value = false
  const file = event.dataTransfer.files[0]
  if (file) {
    await uploadFile(file)
  }
}

async function uploadFile(file) {
  // Validate file type
  const allowedTypes = ['audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/flac', 'audio/ogg', 'audio/x-m4a', 'audio/aiff']
  const allowedExtensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aiff']

  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!allowedExtensions.includes(ext)) {
    error.value = `Unsupported file format: ${ext}. Please use WAV, MP3, FLAC, OGG, or M4A.`
    return
  }

  isUploading.value = true
  fileName.value = file.name
  uploadProgress.value = 0
  error.value = null

  try {
    // Simulate progress (axios doesn't give us real progress for small files)
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10
      }
    }, 200)

    const response = await api.uploadFile(file)

    clearInterval(progressInterval)
    uploadProgress.value = 100

    // Brief delay to show 100%
    await new Promise(resolve => setTimeout(resolve, 500))

    emit('uploaded', response.session_id)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to upload file. Please try again.'
  } finally {
    isUploading.value = false
    uploadProgress.value = 0
    fileName.value = ''
  }
}

async function useSampleFile() {
  isLoadingSample.value = true
  error.value = null

  try {
    // Fetch sample file from server
    const response = await fetch('/api/sample/om-namah-shivaya')
    if (!response.ok) {
      throw new Error('Sample file not available')
    }
    const data = await response.json()
    emit('uploaded', data.session_id)
  } catch (err) {
    error.value = 'Sample file not available. Please upload your own audio file.'
  } finally {
    isLoadingSample.value = false
  }
}
</script>

<style scoped>
.upload-container {
  max-width: 600px;
  margin: 2rem auto;
}

.app-description {
  text-align: center;
  margin-bottom: 2rem;
}

.app-description h2 {
  color: #e94560;
  margin-bottom: 0.75rem;
}

.app-description p {
  color: #aaa;
  line-height: 1.6;
}

.upload-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

.upload-dropzone {
  border: 2px dashed #0f3460;
  border-radius: 12px;
  padding: 3rem;
  text-align: center;
  transition: all 0.3s;
  background: #16213e;
}

.upload-dropzone:hover,
.upload-dropzone.drag-over {
  border-color: #e94560;
  background: rgba(233, 69, 96, 0.05);
}

.upload-icon {
  color: #e94560;
  margin-bottom: 1rem;
}

.upload-dropzone h2 {
  margin-bottom: 0.5rem;
  color: #eee;
}

.upload-dropzone p {
  color: #888;
  margin-bottom: 0.5rem;
}

.upload-dropzone .formats {
  font-size: 0.85rem;
  margin-bottom: 1.5rem;
}

.upload-progress {
  margin-top: 1.5rem;
  text-align: center;
}

.progress-bar {
  height: 8px;
  background: #0f3460;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #e94560, #ff6b6b);
  transition: width 0.3s;
}

.upload-error {
  margin-top: 1.5rem;
  padding: 1rem;
  background: rgba(255, 100, 100, 0.1);
  border: 1px solid #ff6b6b;
  border-radius: 8px;
  text-align: center;
}

.upload-error p {
  color: #ff6b6b;
  margin-bottom: 0.5rem;
}

.import-hint {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #0f3460;
  text-align: center;
}

.import-hint p {
  font-size: 0.9rem;
  color: #666;
}
</style>
