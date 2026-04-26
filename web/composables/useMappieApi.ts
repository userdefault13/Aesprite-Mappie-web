export type JobStatus = 'queued' | 'running' | 'complete' | 'failed'

export interface Artifact {
  name: string
  filename: string
  size_bytes: number
  url: string
}

export interface JobResponse {
  id: string
  status: JobStatus
  created_at: string
  updated_at: string
  message: string
  artifacts: Artifact[]
  error?: string | null
}

export interface Preset {
  id: string
  name: string
  description: string
  settings: Record<string, unknown>
}

export interface HealthResponse {
  ok: boolean
  core_path: string
  core_importable: boolean
  aseprite_available: boolean
  aseprite_bin?: string | null
}

export interface AssetUploadResponse {
  key: string
  filename: string
  path: string
  size_bytes: number
}

export function useMappieApi() {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase as string

  const artifactUrl = (artifact: Artifact) => `${apiBase}${artifact.url}`

  return {
    apiBase,
    artifactUrl,
    health: () => $fetch<HealthResponse>('/api/health', { baseURL: apiBase }),
    presets: () => $fetch<Preset[]>('/api/presets', { baseURL: apiBase }),
    uploadAsset: (assetKey: string, file: File) => {
      const body = new FormData()
      body.append('file', file)
      return $fetch<AssetUploadResponse>(`/api/assets/${assetKey}`, {
        baseURL: apiBase,
        method: 'POST',
        body
      })
    },
    createJob: (payload: Record<string, unknown>) =>
      $fetch<JobResponse>('/api/jobs', { baseURL: apiBase, method: 'POST', body: payload }),
    getJob: (jobId: string) => $fetch<JobResponse>(`/api/jobs/${jobId}`, { baseURL: apiBase })
  }
}
