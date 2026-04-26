<script setup lang="ts">
import type { Artifact } from '~/composables/useMappieApi'

const props = defineProps<{
  paintedArtifact?: Artifact
  artifactUrl: (artifact: Artifact) => string
}>()

const zoom = ref(1)
const imageLoaded = ref(false)
</script>

<template>
  <section class="painted-viewer">
    <div class="painted-viewer-header">
      <div>
        <p class="eyebrow">Painted Viewer</p>
        <h3>Rendered Aseprite Map</h3>
      </div>
      <div class="painted-viewer-controls">
        <label>
          Zoom
          <input v-model.number="zoom" type="range" min="0.25" max="3" step="0.25" />
        </label>
        <span>{{ Math.round(zoom * 100) }}%</span>
      </div>
    </div>

    <div v-if="!paintedArtifact" class="painted-viewer-empty">
      Painted PNG will appear when Aseprite export is complete.
    </div>
    <div v-else class="painted-image-wrap">
      <img
        :src="artifactUrl(paintedArtifact)"
        alt="Painted generated map"
        :style="{ width: `${zoom * 100}%` }"
        @load="imageLoaded = true"
      />
      <div v-if="!imageLoaded" class="painted-viewer-empty">Loading painted map...</div>
    </div>
  </section>
</template>

<style scoped>
.painted-viewer {
  margin: 18px 0;
  padding: 18px;
  border: 1px solid rgba(123, 216, 143, 0.36);
  border-radius: 22px;
  background: #0b0e14;
}

.painted-viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.painted-viewer-header h3 {
  margin: 0;
  font-size: 1.2rem;
}

.painted-viewer-controls {
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--muted);
  font-family: "JetBrains Mono", monospace;
  font-size: 0.78rem;
}

.painted-viewer-controls label {
  min-width: 180px;
}

.painted-image-wrap {
  overflow: auto;
  max-height: 78vh;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #05070b;
}

.painted-image-wrap img {
  display: block;
  max-width: none;
  image-rendering: pixelated;
}

.painted-viewer-empty {
  color: var(--muted);
  line-height: 1.6;
}

@media (max-width: 720px) {
  .painted-viewer-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
