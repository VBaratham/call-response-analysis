<template>
  <div class="pitch-viewer">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

Chart.register(
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Title,
  Tooltip,
  Legend
)

const props = defineProps({
  callPitch: Array,
  responsePitch: Array,
  offset: Number
})

const chartCanvas = ref(null)
let chart = null

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  if (chart) {
    chart.destroy()
  }
})

watch([() => props.callPitch, () => props.responsePitch, () => props.offset], () => {
  updateChart()
}, { deep: true })

function initChart() {
  const ctx = chartCanvas.value.getContext('2d')

  chart = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [
        {
          label: 'Call',
          data: [],
          borderColor: '#e94560',
          backgroundColor: 'rgba(233, 69, 96, 0.1)',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.1,
          fill: false
        },
        {
          label: 'Response',
          data: [],
          borderColor: '#4facfe',
          backgroundColor: 'rgba(79, 172, 254, 0.1)',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.1,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            color: '#ccc',
            font: { size: 12 }
          }
        },
        title: {
          display: true,
          text: 'Pitch Contours',
          color: '#ccc',
          font: { size: 14, weight: '500' }
        },
        tooltip: {
          backgroundColor: '#16213e',
          titleColor: '#ccc',
          bodyColor: '#ccc',
          borderColor: '#0f3460',
          borderWidth: 1,
          callbacks: {
            label: (context) => {
              const value = context.parsed.y
              if (value === null) return null
              return `${context.dataset.label}: ${value.toFixed(1)} semitones`
            }
          }
        }
      },
      scales: {
        x: {
          type: 'linear',
          title: {
            display: true,
            text: 'Time (seconds)',
            color: '#888'
          },
          ticks: { color: '#666' },
          grid: { color: '#2a2a4a' }
        },
        y: {
          type: 'linear',
          title: {
            display: true,
            text: 'Pitch (semitones from A4)',
            color: '#888'
          },
          ticks: { color: '#666' },
          grid: { color: '#2a2a4a' }
        }
      }
    }
  })

  updateChart()
}

function updateChart() {
  if (!chart) return

  // Process call pitch data
  const callData = processContour(props.callPitch, 0)

  // Process response pitch data with offset
  const responseData = processContour(props.responsePitch, props.offset || 0)

  chart.data.datasets[0].data = callData
  chart.data.datasets[1].data = responseData

  chart.update('none')
}

function processContour(pitchData, timeOffset) {
  if (!pitchData || !Array.isArray(pitchData)) return []

  return pitchData
    .filter(p => p.semitones !== null)
    .map(p => ({
      x: (p.relative_time || p.time) + timeOffset,
      y: p.semitones
    }))
}
</script>

<style scoped>
.pitch-viewer {
  height: 100%;
  min-height: 300px;
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1rem;
}

canvas {
  width: 100% !important;
  height: 100% !important;
}
</style>
