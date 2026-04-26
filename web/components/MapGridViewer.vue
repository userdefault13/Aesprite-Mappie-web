<script setup lang="ts">
import type { Artifact } from '~/composables/useMappieApi'

const props = defineProps<{
  asciiArtifact?: Artifact
  csvArtifact?: Artifact
  artifactUrl: (artifact: Artifact) => string
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const loading = ref(false)
const error = ref('')
const asciiRows = ref<string[]>([])
const tileRows = ref<number[][]>([])
const zoom = ref(6)
const hovered = ref<{ x: number; y: number; char: string; tileId?: number } | null>(null)

const width = computed(() => asciiRows.value[0]?.length ?? 0)
const height = computed(() => asciiRows.value.length)
const canRender = computed(() => width.value > 0 && height.value > 0)

watch(
  () => [props.asciiArtifact?.url, props.csvArtifact?.url],
  () => loadMapData(),
  { immediate: true }
)

watch([asciiRows, tileRows, zoom], () => drawMap(), { deep: true })

async function loadMapData() {
  error.value = ''
  asciiRows.value = []
  tileRows.value = []
  hovered.value = null

  if (!props.asciiArtifact) return

  loading.value = true
  try {
    const asciiText = await fetch(props.artifactUrl(props.asciiArtifact)).then((response) => {
      if (!response.ok) throw new Error(`Could not load ASCII map (${response.status})`)
      return response.text()
    })
    asciiRows.value = asciiText.trimEnd().split(/\r?\n/)

    if (props.csvArtifact) {
      const csvText = await fetch(props.artifactUrl(props.csvArtifact)).then((response) => {
        if (!response.ok) throw new Error(`Could not load CSV map (${response.status})`)
        return response.text()
      })
      tileRows.value = csvText
        .trimEnd()
        .split(/\r?\n/)
        .map((line) => line.split(',').map((value) => Number(value)))
    }

  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : 'Could not load map viewer data.'
  } finally {
    loading.value = false
    await nextTick()
    drawMap()
  }
}

function drawMap() {
  const canvas = canvasRef.value
  if (!canvas || !canRender.value) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  canvas.width = width.value * zoom.value
  canvas.height = height.value * zoom.value
  ctx.imageSmoothingEnabled = false

  for (let y = 0; y < height.value; y += 1) {
    const row = asciiRows.value[y]
    for (let x = 0; x < width.value; x += 1) {
      ctx.fillStyle = colorForChar(row[x] ?? ' ')
      ctx.fillRect(x * zoom.value, y * zoom.value, zoom.value, zoom.value)
    }
  }

  if (hovered.value) {
    ctx.strokeStyle = '#f5f1e8'
    ctx.lineWidth = Math.max(1, Math.floor(zoom.value / 3))
    ctx.strokeRect(
      hovered.value.x * zoom.value + 0.5,
      hovered.value.y * zoom.value + 0.5,
      zoom.value - 1,
      zoom.value - 1
    )
  }
}

function colorForChar(char: string) {
  const colors: Record<string, string> = {
    G: '#68b24c',
    '.': '#68b24c',
    B: '#c2b280',
    L: '#78a0b4',
    R: '#648cc8',
    I: '#5a7846',
    '~': '#4884e0',
    '`': '#3060b4',
    T: '#2e6c36',
    F: '#1e4e28',
    P: '#b59866',
    S: '#fae45c',
    J: '#ffa14d',
    M: '#7d7e86',
    H: '#d67b49',
    C: '#c24c4c',
    D: '#f05f5f',
    N: '#56d0dc'
  }
  return colors[char] ?? '#111827'
}

function updateHover(event: MouseEvent) {
  const canvas = canvasRef.value
  if (!canvas || !canRender.value) return

  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const x = Math.floor(((event.clientX - rect.left) * scaleX) / zoom.value)
  const y = Math.floor(((event.clientY - rect.top) * scaleY) / zoom.value)

  if (x < 0 || y < 0 || x >= width.value || y >= height.value) {
    hovered.value = null
    drawMap()
    return
  }

  hovered.value = {
    x,
    y,
    char: asciiRows.value[y]?.[x] ?? ' ',
    tileId: tileRows.value[y]?.[x]
  }
  drawMap()
}
</script>

<template>
  <section class="map-viewer">
    <div class="map-viewer-header">
      <div>
        <p class="eyebrow">Browser Viewer</p>
        <h3>Generated Map Grid</h3>
      </div>
      <div class="map-viewer-controls">
        <label>
          Zoom
          <input v-model.number="zoom" type="range" min="2" max="14" step="1" />
        </label>
        <span v-if="canRender">{{ width }} x {{ height }}</span>
      </div>
    </div>

    <div v-if="loading" class="map-viewer-empty">Loading map grid...</div>
    <div v-else-if="error" class="map-viewer-error">{{ error }}</div>
    <div v-else-if="!asciiArtifact" class="map-viewer-empty">ASCII map artifact is not available yet.</div>
    <div v-else class="map-canvas-wrap">
      <canvas ref="canvasRef" @mousemove="updateHover" @mouseleave="hovered = null; drawMap()" />
    </div>

    <div class="map-viewer-footer">
      <span v-if="hovered">
        x={{ hovered.x }}, y={{ hovered.y }}, char="{{ hovered.char }}"
        <template v-if="hovered.tileId !== undefined">, tile={{ hovered.tileId }}</template>
      </span>
      <span v-else>Hover a tile to inspect it.</span>
    </div>
  </section>
</template>

<style scoped>
.map-viewer {
  margin: 18px 0;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: #0b0e14;
}

.map-viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.map-viewer-header h3 {
  margin: 0;
  font-size: 1.2rem;
}

.map-viewer-controls {
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--muted);
  font-family: "JetBrains Mono", monospace;
  font-size: 0.78rem;
}

.map-viewer-controls label {
  min-width: 180px;
}

.map-canvas-wrap {
  overflow: auto;
  max-height: 72vh;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #05070b;
}

canvas {
  display: block;
  image-rendering: pixelated;
}

.map-viewer-empty,
.map-viewer-error,
.map-viewer-footer {
  color: var(--muted);
  line-height: 1.6;
}

.map-viewer-error {
  color: var(--danger);
}

.map-viewer-footer {
  margin-top: 12px;
  font-family: "JetBrains Mono", monospace;
  font-size: 0.8rem;
}

@media (max-width: 720px) {
  .map-viewer-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
