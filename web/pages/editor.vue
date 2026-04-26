<script setup lang="ts">
type EditorTool = 'inspect' | 'paint' | 'erase'

const tools = [
  { id: 'inspect' as const, label: 'Inspect' },
  { id: 'paint' as const, label: 'Paint' },
  { id: 'erase' as const, label: 'Erase' }
] satisfies Array<{ id: EditorTool; label: string }>

const terrainTiles = [
  { id: 'grass', label: 'Grass', char: 'G', color: '#68b24c' },
  { id: 'water', label: 'Water', char: '~', color: '#4884e0' },
  { id: 'forest', label: 'Forest', char: 'F', color: '#1e4e28' },
  { id: 'path', label: 'Path', char: 'P', color: '#b59866' },
  { id: 'hill', label: 'Hill', char: 'H', color: '#d67b49' },
  { id: 'spawn', label: 'Spawn', char: 'S', color: '#fae45c' }
]

const activeTool = ref<EditorTool>('paint')
const selectedTile = ref(terrainTiles[0])

const exports = [
  { id: 'png', label: 'PNG', note: 'Available' },
  { id: 'ascii', label: 'ASCII', note: 'Future' },
  { id: 'csv', label: 'CSV', note: 'Future' },
  { id: 'aseprite', label: 'Aseprite', note: 'Future' }
]
</script>

<template>
  <main class="page-shell editor-shell">
    <section class="hero editor-hero">
      <div>
        <p class="eyebrow">Map Editor</p>
        <h1>Shape maps directly on a canvas workspace.</h1>
        <p class="hero-copy">
          Start from a blank grid now. Painting, sprites, imports, and export workflows can grow
          into this page without changing the generator flow.
        </p>
      </div>
      <NuxtLink class="ghost-button" to="/">Back to Generator</NuxtLink>
    </section>

    <section class="editor-layout">
      <aside class="panel editor-sidebar">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Tools</p>
            <h2>Editor Controls</h2>
          </div>
        </div>

        <div class="tool-list">
          <button
            v-for="tool in tools"
            :key="tool.id"
            type="button"
            class="tool-button"
            :class="{ active: activeTool === tool.id }"
            @click="activeTool = tool.id"
          >
            {{ tool.label }}
          </button>
        </div>

        <section class="editor-card">
          <p class="eyebrow">Palette</p>
          <h3>Terrain Tiles</h3>
          <div class="palette-grid" role="list" aria-label="Terrain tile palette">
            <button
              v-for="tile in terrainTiles"
              :key="tile.id"
              type="button"
              class="palette-button"
              :class="{ active: selectedTile.id === tile.id }"
              @click="selectedTile = tile; activeTool = 'paint'"
            >
              <span class="palette-swatch" :style="{ background: tile.color }" />
              <span>
                <strong>{{ tile.label }}</strong>
                <small>{{ tile.char }}</small>
              </span>
            </button>
          </div>
        </section>

        <section class="editor-card">
          <p class="eyebrow">Exports</p>
          <h3>Planned Formats</h3>
          <div class="export-list">
            <span v-for="item in exports" :key="item.id">
              <strong>{{ item.label }}</strong>
              <small>{{ item.note }}</small>
            </span>
          </div>
        </section>
      </aside>

      <section class="panel editor-workspace">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Canvas</p>
            <h2>Editable Grid</h2>
          </div>
          <span class="pill">Phase 2</span>
        </div>

        <MapEditorCanvas :active-tool="activeTool" :selected-tile="selectedTile" />
      </section>
    </section>
  </main>
</template>

<style scoped>
.editor-shell {
  max-width: 1600px;
}

.editor-hero {
  align-items: center;
}

.editor-layout {
  display: grid;
  grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.editor-sidebar,
.editor-workspace {
  width: 100%;
}

.tool-list {
  display: grid;
  gap: 10px;
  margin-bottom: 18px;
}

.tool-button {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 16px;
  color: var(--text);
  text-align: left;
  background: var(--panel-soft);
  cursor: pointer;
}

.tool-button.active {
  color: #07120a;
  background: var(--accent);
  cursor: pointer;
}

.editor-card {
  margin-top: 14px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: rgba(11, 14, 20, 0.58);
}

.editor-card h3 {
  margin: 0 0 8px;
}

.editor-card p:not(.eyebrow) {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
}

.palette-grid {
  display: grid;
  gap: 8px;
}

.palette-button {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  color: var(--text);
  text-align: left;
  background: var(--panel-soft);
  cursor: pointer;
}

.palette-button.active {
  border-color: rgba(123, 216, 143, 0.72);
  box-shadow: 0 0 0 1px rgba(123, 216, 143, 0.25);
}

.palette-swatch {
  width: 22px;
  height: 22px;
  flex: 0 0 auto;
  border: 1px solid rgba(245, 241, 232, 0.32);
  border-radius: 7px;
}

.palette-button span:last-child {
  display: grid;
  gap: 2px;
}

.palette-button small {
  color: var(--muted);
  font-family: "JetBrains Mono", monospace;
  font-size: 0.72rem;
}

.export-list {
  display: grid;
  gap: 8px;
}

.export-list span {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel-soft);
}

.export-list small {
  color: var(--muted);
  font-family: "JetBrains Mono", monospace;
  font-size: 0.75rem;
  text-transform: uppercase;
}

@media (max-width: 980px) {
  .editor-layout {
    grid-template-columns: 1fr;
  }
}
</style>
