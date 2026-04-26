<script setup lang="ts">
type EditorTool = 'inspect' | 'paint' | 'erase'

interface TerrainTile {
  id: string
  label: string
  char: string
  color: string
}

const props = defineProps<{
  activeTool: EditorTool
  selectedTile: TerrainTile
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const zoom = ref(8)
const gridWidth = ref(64)
const gridHeight = ref(64)
const hovered = ref<{ x: number; y: number; tile?: TerrainTile } | null>(null)
const tiles = ref<(TerrainTile | null)[][]>(createBlankTiles(gridWidth.value, gridHeight.value))
const isDrawing = ref(false)

const canvasWidth = computed(() => gridWidth.value * zoom.value)
const canvasHeight = computed(() => gridHeight.value * zoom.value)

watch([zoom, hovered, tiles], () => drawGrid(), { deep: true })

watch([gridWidth, gridHeight], ([width, height], [oldWidth, oldHeight]) => {
  if (width === oldWidth && height === oldHeight) return
  resizeTiles(width, height)
  drawGrid()
})

onMounted(() => {
  drawGrid()
})

async function resetGrid() {
  gridWidth.value = 64
  gridHeight.value = 64
  zoom.value = 8
  hovered.value = null
  tiles.value = createBlankTiles(64, 64)
  await nextTick()
  drawGrid()
}

function createBlankTiles(width: number, height: number) {
  return Array.from({ length: height }, () => Array.from<TerrainTile | null>({ length: width }).fill(null))
}

function resizeTiles(width: number, height: number) {
  const previous = tiles.value
  tiles.value = Array.from({ length: height }, (_, y) =>
    Array.from({ length: width }, (_, x) => previous[y]?.[x] ?? null)
  )
}

function drawGrid() {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  canvas.width = canvasWidth.value
  canvas.height = canvasHeight.value
  ctx.imageSmoothingEnabled = false
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  for (let y = 0; y < gridHeight.value; y += 1) {
    for (let x = 0; x < gridWidth.value; x += 1) {
      const tile = tiles.value[y]?.[x]
      ctx.fillStyle = tile?.color ?? ((x + y) % 2 === 0 ? '#111827' : '#0f1722')
      ctx.fillRect(x * zoom.value, y * zoom.value, zoom.value, zoom.value)
    }
  }

  drawGridLines(ctx)
  drawHover(ctx)
}

function drawGridLines(ctx: CanvasRenderingContext2D) {
  if (zoom.value < 6) return

  ctx.strokeStyle = 'rgba(166, 173, 187, 0.16)'
  ctx.lineWidth = 1

  for (let x = 0; x <= gridWidth.value; x += 1) {
    const px = x * zoom.value + 0.5
    ctx.beginPath()
    ctx.moveTo(px, 0)
    ctx.lineTo(px, canvasHeight.value)
    ctx.stroke()
  }

  for (let y = 0; y <= gridHeight.value; y += 1) {
    const py = y * zoom.value + 0.5
    ctx.beginPath()
    ctx.moveTo(0, py)
    ctx.lineTo(canvasWidth.value, py)
    ctx.stroke()
  }
}

function drawHover(ctx: CanvasRenderingContext2D) {
  if (!hovered.value) return

  ctx.strokeStyle = '#f5f1e8'
  ctx.lineWidth = Math.max(1, Math.floor(zoom.value / 4))
  ctx.strokeRect(
    hovered.value.x * zoom.value + 0.5,
    hovered.value.y * zoom.value + 0.5,
    zoom.value - 1,
    zoom.value - 1
  )
}

function updateHover(event: PointerEvent) {
  const position = tilePositionFromEvent(event)
  hovered.value = position
  if (isDrawing.value && props.activeTool !== 'inspect') {
    applyTool(position)
  }
}

function startDrawing(event: PointerEvent) {
  const position = tilePositionFromEvent(event)
  hovered.value = position
  if (!position || props.activeTool === 'inspect') return
  isDrawing.value = true
  applyTool(position)
}

function stopDrawing() {
  isDrawing.value = false
}

function tilePositionFromEvent(event: PointerEvent) {
  const canvas = canvasRef.value
  if (!canvas) return null

  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const x = Math.floor(((event.clientX - rect.left) * scaleX) / zoom.value)
  const y = Math.floor(((event.clientY - rect.top) * scaleY) / zoom.value)

  if (x < 0 || y < 0 || x >= gridWidth.value || y >= gridHeight.value) {
    return null
  }

  return { x, y, tile: tiles.value[y]?.[x] ?? undefined }
}

function applyTool(position: { x: number; y: number } | null) {
  if (!position) return

  const row = tiles.value[position.y]
  if (!row) return

  row[position.x] = props.activeTool === 'erase' ? null : { ...props.selectedTile }
  hovered.value = { ...position, tile: row[position.x] ?? undefined }
}

function exportPng() {
  const exportTileSize = 16
  const exportCanvas = document.createElement('canvas')
  exportCanvas.width = gridWidth.value * exportTileSize
  exportCanvas.height = gridHeight.value * exportTileSize

  const ctx = exportCanvas.getContext('2d')
  if (!ctx) return

  ctx.imageSmoothingEnabled = false
  ctx.clearRect(0, 0, exportCanvas.width, exportCanvas.height)

  for (let y = 0; y < gridHeight.value; y += 1) {
    for (let x = 0; x < gridWidth.value; x += 1) {
      const tile = tiles.value[y]?.[x]
      if (!tile) continue
      ctx.fillStyle = tile.color
      ctx.fillRect(x * exportTileSize, y * exportTileSize, exportTileSize, exportTileSize)
    }
  }

  const url = exportCanvas.toDataURL('image/png')
  const link = document.createElement('a')
  link.href = url
  link.download = `mappie-editor-${gridWidth.value}x${gridHeight.value}.png`
  link.click()
}
</script>

<template>
  <section class="map-editor-canvas">
    <div class="editor-canvas-controls">
      <label>
        Zoom
        <input v-model.number="zoom" type="range" min="4" max="24" step="1" />
      </label>
      <label>
        Width
        <input v-model.number="gridWidth" type="number" min="8" max="256" />
      </label>
      <label>
        Height
        <input v-model.number="gridHeight" type="number" min="8" max="256" />
      </label>
      <button class="ghost-button" type="button" @click="exportPng">Download PNG</button>
      <button class="ghost-button" type="button" @click="resetGrid">Reset Blank Grid</button>
    </div>

    <div class="editor-canvas-wrap">
      <canvas
        ref="canvasRef"
        aria-label="Blank map editor grid"
        @pointerdown="startDrawing"
        @pointermove="updateHover"
        @pointerup="stopDrawing"
        @pointerleave="hovered = null; stopDrawing()"
      />
    </div>

    <div class="editor-canvas-footer">
      <span>{{ gridWidth }} x {{ gridHeight }} tiles</span>
      <span>
        Tool={{ activeTool }}
        <template v-if="activeTool === 'paint'">, tile={{ selectedTile.label }}</template>
      </span>
      <span v-if="hovered">
        x={{ hovered.x }}, y={{ hovered.y }}
        <template v-if="hovered.tile">, {{ hovered.tile.label }}</template>
      </span>
      <span v-else>Hover a tile to inspect coordinates.</span>
    </div>
  </section>
</template>

<style scoped>
.map-editor-canvas {
  display: grid;
  gap: 14px;
}

.editor-canvas-controls {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) repeat(2, minmax(120px, 160px)) auto auto;
  gap: 12px;
  align-items: end;
}

.editor-canvas-wrap {
  overflow: auto;
  max-height: 72vh;
  border: 1px solid var(--line);
  border-radius: 18px;
  background:
    radial-gradient(circle at center, rgba(123, 216, 143, 0.08), transparent 28rem),
    #05070b;
}

canvas {
  display: block;
  image-rendering: pixelated;
  cursor: crosshair;
  touch-action: none;
}

.editor-canvas-footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  color: var(--muted);
  font-family: "JetBrains Mono", monospace;
  font-size: 0.8rem;
}

@media (max-width: 980px) {
  .editor-canvas-controls {
    grid-template-columns: 1fr;
  }
}
</style>
