<script setup lang="ts">
import type { AssetUploadResponse, HealthResponse, JobResponse, Preset } from '~/composables/useMappieApi'

const api = useMappieApi()

const settings = reactive({
  width: 128,
  height: 128,
  tree_density: 0.22,
  forest_density: 0.65,
  water_density: 0.1,
  hill_density: 0.04,
  spawn_count: 8,
  spawn_clearing_size: 15,
  join_point_count: 0,
  path_width_threshold: 3,
  path_perlin_scale: 14,
  path_perlin_weight: 1.8,
  mine_count: 4,
  shop_count: 3,
  creep_zone_count: 6,
  creep_zone_radius: 2,
  dead_end_count: 8,
  require_secret_npc_path: true,
  hide_path: false,
  map_mode: 'island',
  shoreline_erode_iterations: 2,
  preview_tile_size: 16,
  seed: 42,
  terrain_config: 'examples/terrain.bitmask.json',
  include_aseprite: true,
  asset_overrides: {
    grass_path: null as string | null,
    shoreline_path: null as string | null,
    lakesrivers_path: null as string | null,
    water_path: null as string | null,
    hill_path: null as string | null,
    dirt_path: null as string | null,
    trees_path: null as string | null
  }
})

const health = ref<HealthResponse | null>(null)
const presets = ref<Preset[]>([])
const job = ref<JobResponse | null>(null)
const loading = ref(false)
const error = ref('')
const generationProgress = ref(0)
const assetUploads = reactive<Record<string, AssetUploadResponse | undefined>>({})
const assetUploadErrors = reactive<Record<string, string | undefined>>({})
const uploadingAssets = reactive<Record<string, boolean>>({})
const showSuccessModal = ref(false)
const successModalJobId = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | undefined
let progressTimer: ReturnType<typeof setInterval> | undefined

const assetFields = [
  { key: 'grass_path', label: 'Grass', hint: 'Grass interior / variants sheet' },
  { key: 'trees_path', label: 'Trees', hint: 'Tree tileset for T/F cells' },
  { key: 'hill_path', label: 'Hills', hint: 'Hill cliff autotile sheet' },
  { key: 'lakesrivers_path', label: 'Lakes & Rivers', hint: 'Lake and river bank sheet' },
  { key: 'shoreline_path', label: 'Shoreline', hint: 'Ocean/continent shoreline sheet' },
  { key: 'water_path', label: 'Water', hint: 'Water tile or animated water sheet' },
  { key: 'dirt_path', label: 'Dirt Paths', hint: 'Path autotile sheet' }
]

const previewArtifact = computed(() =>
  job.value?.artifacts.find((artifact) => artifact.filename === 'preview.bmp') ||
  job.value?.artifacts.find((artifact) => artifact.filename === 'preview.png') ||
  job.value?.artifacts.find((artifact) =>
    artifact.filename.endsWith('.bmp') || artifact.filename.endsWith('.png')
  )
)

const asciiArtifact = computed(() =>
  job.value?.artifacts.find((artifact) => artifact.filename === 'map.txt')
)

const csvArtifact = computed(() =>
  job.value?.artifacts.find((artifact) => artifact.filename === 'map.csv')
)

const asepriteArtifact = computed(() =>
  job.value?.artifacts.find((artifact) => artifact.filename === 'map.aseprite')
)

const paintedArtifact = computed(() =>
  job.value?.artifacts.find((artifact) => artifact.filename === 'map.png')
)

const primaryDownload = computed(() =>
  paintedArtifact.value ||
  asepriteArtifact.value ||
  job.value?.artifacts.find((artifact) => artifact.filename === 'map.tiled.json') ||
  job.value?.artifacts[0]
)

const jobLooksComplete = computed(() => {
  if (!job.value) return false
  if (job.value.status === 'complete') return true
  const filenames = new Set(job.value.artifacts.map((artifact) => artifact.filename))
  const hasCoreOutputs = filenames.has('map.txt') && filenames.has('map.legend.json') && filenames.has('map.csv')
  return hasCoreOutputs && (!settings.include_aseprite || filenames.has('map.aseprite'))
})

const displayedStatus = computed(() => {
  if (!job.value) return ''
  return jobLooksComplete.value ? 'complete' : job.value.status
})

const displayedProgress = computed(() => {
  if (!job.value) return 0
  if (displayedStatus.value === 'complete') return 100
  if (displayedStatus.value === 'failed') return 100
  return Math.max(5, Math.min(95, generationProgress.value))
})

const densityTotal = computed(() => settings.tree_density + settings.water_density)
const canSubmit = computed(() => densityTotal.value <= 1 && !loading.value)

watch(jobLooksComplete, (isComplete) => {
  if (!isComplete || !job.value || successModalJobId.value === job.value.id) return
  successModalJobId.value = job.value.id
  showSuccessModal.value = true
  if (pollTimer) clearInterval(pollTimer)
})

onMounted(async () => {
  await Promise.all([loadHealth(), loadPresets()])
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (progressTimer) clearInterval(progressTimer)
})

async function loadHealth() {
  try {
    health.value = await api.health()
  } catch {
    health.value = null
  }
}

async function loadPresets() {
  presets.value = await api.presets()
}

function applyPreset(preset: Preset) {
  const currentOverrides = { ...settings.asset_overrides }
  Object.assign(settings, preset.settings)
  settings.asset_overrides = { ...settings.asset_overrides, ...currentOverrides }
}

async function submitJob() {
  error.value = ''
  loading.value = true
  generationProgress.value = 5
  showSuccessModal.value = false
  successModalJobId.value = null
  try {
    job.value = await api.createJob({ ...settings })
    startPolling()
    startProgress()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : 'Could not create job.'
  } finally {
    loading.value = false
  }
}

async function uploadAsset(assetKey: string, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  assetUploadErrors[assetKey] = undefined
  uploadingAssets[assetKey] = true
  try {
    const uploaded = await api.uploadAsset(assetKey, file)
    assetUploads[assetKey] = uploaded
    settings.asset_overrides[assetKey as keyof typeof settings.asset_overrides] = uploaded.path
  } catch (caught) {
    assetUploadErrors[assetKey] = caught instanceof Error ? caught.message : 'Upload failed.'
  } finally {
    uploadingAssets[assetKey] = false
    input.value = ''
  }
}

function clearAsset(assetKey: string) {
  assetUploads[assetKey] = undefined
  assetUploadErrors[assetKey] = undefined
  settings.asset_overrides[assetKey as keyof typeof settings.asset_overrides] = null
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(refreshJob, 1500)
}

function startProgress() {
  if (progressTimer) clearInterval(progressTimer)
  progressTimer = setInterval(() => {
    if (!job.value || displayedStatus.value === 'complete' || displayedStatus.value === 'failed') {
      generationProgress.value = displayedStatus.value === 'failed' ? 100 : generationProgress.value
      if (progressTimer) clearInterval(progressTimer)
      return
    }

    const nextIncrement = generationProgress.value < 45 ? 8 : generationProgress.value < 75 ? 4 : 1
    generationProgress.value = Math.min(95, generationProgress.value + nextIncrement)
  }, 700)
}

async function refreshJob() {
  if (!job.value) return
  try {
    job.value = await api.getJob(job.value.id)
    if (job.value.status === 'complete' || job.value.status === 'failed' || jobLooksComplete.value) {
      if (pollTimer) clearInterval(pollTimer)
      if (progressTimer) clearInterval(progressTimer)
      generationProgress.value = 100
    }
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : 'Could not refresh job status.'
  }
}

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <main class="page-shell">
    <section class="hero">
      <div>
        <p class="eyebrow">Aseprite Mappie Web</p>
        <h1>Generate game-ready tilemaps from a polished web workflow.</h1>
        <p class="hero-copy">
          Tune terrain, paths, POIs, and exports from Nuxt while FastAPI runs the Python
          generator and Aseprite worker in the background.
        </p>
      </div>
      <div class="health-card">
        <span class="status-dot" :class="{ ok: health?.ok }" />
        <div>
          <strong>{{ health?.ok ? 'Backend ready' : 'Backend unavailable' }}</strong>
          <small>
            Aseprite:
            {{ health?.aseprite_available ? 'available' : 'not found' }}
          </small>
        </div>
      </div>
    </section>

    <section class="layout-grid">
      <form class="panel controls" @submit.prevent="submitJob">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Generator</p>
            <h2>Map Settings</h2>
          </div>
          <button class="primary" type="submit" :disabled="!canSubmit">
            {{ loading ? 'Starting...' : 'Generate Map' }}
          </button>
        </div>

        <div class="preset-row">
          <button v-for="preset in presets" :key="preset.id" type="button" @click="applyPreset(preset)">
            <strong>{{ preset.name }}</strong>
            <span>{{ preset.description }}</span>
          </button>
        </div>

        <div v-if="densityTotal > 1" class="error-box">
          Tree density + water density must be 1.0 or lower.
        </div>
        <div v-if="error" class="error-box">{{ error }}</div>

        <section class="asset-upload-section">
          <div class="subsection-header">
            <div>
              <p class="eyebrow">Tileset Assets</p>
              <h3>Upload Custom PNGs</h3>
            </div>
            <p>
              Optional overrides for this generation. Leave blank to use `examples/terrain.bitmask.json`.
            </p>
          </div>
          <div class="asset-grid">
            <div v-for="field in assetFields" :key="field.key" class="asset-card">
              <div>
                <strong>{{ field.label }}</strong>
                <small>{{ field.hint }}</small>
              </div>
              <label class="asset-upload-button">
                {{ uploadingAssets[field.key] ? 'Uploading...' : 'Choose file' }}
                <input
                  type="file"
                  accept=".png,.aseprite,.ase,image/png"
                  :disabled="uploadingAssets[field.key]"
                  @change="uploadAsset(field.key, $event)"
                />
              </label>
              <div v-if="assetUploads[field.key]" class="asset-uploaded">
                <span>{{ assetUploads[field.key]?.filename }}</span>
                <button type="button" @click="clearAsset(field.key)">Clear</button>
              </div>
              <p v-if="assetUploadErrors[field.key]" class="asset-error">
                {{ assetUploadErrors[field.key] }}
              </p>
            </div>
          </div>
        </section>

        <div class="field-grid">
          <label>
            Width
            <input v-model.number="settings.width" type="number" min="8" max="512" />
          </label>
          <label>
            Height
            <input v-model.number="settings.height" type="number" min="8" max="512" />
          </label>
          <label>
            Seed
            <input v-model.number="settings.seed" type="number" min="0" />
          </label>
          <label>
            Mode
            <select v-model="settings.map_mode">
              <option value="island">Island</option>
              <option value="continent">Continent</option>
            </select>
          </label>
        </div>

        <div class="slider-grid">
          <label>
            <span>Tree density {{ settings.tree_density }}</span>
            <input v-model.number="settings.tree_density" type="range" min="0" max="1" step="0.01" />
          </label>
          <label>
            <span>Forest density {{ settings.forest_density }}</span>
            <input v-model.number="settings.forest_density" type="range" min="0" max="1" step="0.01" />
          </label>
          <label>
            <span>Water density {{ settings.water_density }}</span>
            <input v-model.number="settings.water_density" type="range" min="0" max="1" step="0.01" />
          </label>
          <label>
            <span>Hill density {{ settings.hill_density }}</span>
            <input v-model.number="settings.hill_density" type="range" min="0" max="1" step="0.01" />
          </label>
        </div>

        <div class="field-grid">
          <label>
            Spawns
            <input v-model.number="settings.spawn_count" type="number" min="1" max="32" />
          </label>
          <label>
            Clearing size
            <input v-model.number="settings.spawn_clearing_size" type="number" min="3" max="31" />
          </label>
          <label>
            Mines
            <input v-model.number="settings.mine_count" type="number" min="0" max="20" />
          </label>
          <label>
            Shops
            <input v-model.number="settings.shop_count" type="number" min="0" max="16" />
          </label>
          <label>
            Creep zones
            <input v-model.number="settings.creep_zone_count" type="number" min="0" max="24" />
          </label>
          <label>
            Dead ends
            <input v-model.number="settings.dead_end_count" type="number" min="0" max="32" />
          </label>
        </div>

        <div class="toggles">
          <label>
            <input v-model="settings.require_secret_npc_path" type="checkbox" />
            Secret NPC path
          </label>
          <label>
            <input v-model="settings.hide_path" type="checkbox" />
            Hide paths
          </label>
          <label>
            <input v-model="settings.include_aseprite" type="checkbox" />
            Build .aseprite output
          </label>
        </div>
      </form>

      <aside class="panel results">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Output</p>
            <h2>Job Status</h2>
          </div>
          <div class="status-actions">
            <button v-if="job" class="ghost-button" type="button" @click="refreshJob">
              Refresh
            </button>
            <span v-if="job" class="pill" :class="displayedStatus">{{ displayedStatus }}</span>
          </div>
        </div>

        <div v-if="!job" class="empty-state">
          Generate a map to see previews and downloads here.
        </div>

        <template v-else>
          <p class="job-message">{{ job.message }}</p>
          <div class="generation-progress" role="progressbar" :aria-valuenow="displayedProgress" aria-valuemin="0" aria-valuemax="100">
            <div class="generation-progress-header">
              <span>{{ displayedStatus === 'complete' ? 'Generation complete' : displayedStatus === 'failed' ? 'Generation failed' : 'Generating map' }}</span>
              <strong>{{ displayedProgress }}%</strong>
            </div>
            <div class="generation-progress-track">
              <div class="generation-progress-fill" :style="{ width: `${displayedProgress}%` }" />
            </div>
          </div>
          <p v-if="job.error" class="error-box">{{ job.error }}</p>

          <div v-if="previewArtifact" class="preview-frame">
            <img :src="api.artifactUrl(previewArtifact)" alt="Generated map preview" />
          </div>

          <PaintedMapViewer
            v-if="settings.include_aseprite"
            :painted-artifact="paintedArtifact"
            :artifact-url="api.artifactUrl"
          />

          <MapGridViewer
            v-if="asciiArtifact"
            :ascii-artifact="asciiArtifact"
            :csv-artifact="csvArtifact"
            :artifact-url="api.artifactUrl"
          />

          <div class="artifact-list">
            <a
              v-for="artifact in job.artifacts"
              :key="artifact.filename"
              :href="api.artifactUrl(artifact)"
              target="_blank"
              rel="noreferrer"
            >
              <span>
                <strong>{{ artifact.name }}</strong>
                <small>{{ artifact.filename }}</small>
              </span>
              <em>{{ formatBytes(artifact.size_bytes) }}</em>
            </a>
          </div>
        </template>
      </aside>
    </section>

    <Teleport to="body">
      <div v-if="showSuccessModal && job" class="modal-backdrop" role="presentation">
        <section class="success-modal" role="dialog" aria-modal="true" aria-labelledby="success-title">
          <button class="modal-close" type="button" aria-label="Close success modal" @click="showSuccessModal = false">
            x
          </button>
          <p class="eyebrow">Generation Complete</p>
          <h2 id="success-title">Your map is ready.</h2>
          <p>
            Mappie generated {{ job.artifacts.length }} artifact{{ job.artifacts.length === 1 ? '' : 's' }},
            including your preview and downloads.
          </p>
          <div class="modal-actions">
            <a
              v-if="primaryDownload"
              class="primary modal-primary"
              :href="api.artifactUrl(primaryDownload)"
              target="_blank"
              rel="noreferrer"
            >
              Download {{ primaryDownload.name }}
            </a>
            <button class="ghost-button" type="button" @click="showSuccessModal = false">
              View all artifacts
            </button>
          </div>
        </section>
      </div>
    </Teleport>
  </main>
</template>
