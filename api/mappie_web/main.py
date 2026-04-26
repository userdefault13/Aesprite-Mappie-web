from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import core_path, ensure_core_importable, resolve_aseprite_bin, upload_root
from .jobs import job_store
from .schemas import AssetUploadResponse, HealthResponse, JobResponse, JobStatus, MapRequest


app = FastAPI(title="Mappie Web API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ASSET_KEYS = {
    "grass_path",
    "shoreline_path",
    "lakesrivers_path",
    "water_path",
    "hill_path",
    "dirt_path",
    "trees_path",
}
ASSET_EXTENSIONS = {".png", ".aseprite", ".ase"}


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    core = core_path()
    core_importable = False
    try:
        ensure_core_importable()
        import tilemap_generator  # noqa: F401

        core_importable = True
    except Exception:
        core_importable = False

    aseprite_bin = resolve_aseprite_bin()
    return HealthResponse(
        ok=core.exists() and core_importable,
        core_path=str(core),
        core_importable=core_importable,
        aseprite_available=aseprite_bin is not None,
        aseprite_bin=aseprite_bin,
    )


@app.get("/api/presets")
def presets() -> list[dict]:
    return [
        {
            "id": "island-balanced",
            "name": "Balanced Island",
            "description": "Classic ocean-border map with moderate trees, water, POIs, and hills.",
            "settings": MapRequest().model_dump(),
        },
        {
            "id": "forest-continent",
            "name": "Forest Continent",
            "description": "Tree-heavy land map with fewer lakes and no ocean border.",
            "settings": MapRequest(
                map_mode="continent",
                tree_density=0.32,
                forest_density=0.78,
                water_density=0.06,
                hill_density=0.05,
            ).model_dump(),
        },
        {
            "id": "waterways",
            "name": "Waterways",
            "description": "Higher water density with shoreline erosion for rougher coasts.",
            "settings": MapRequest(
                water_density=0.18,
                tree_density=0.18,
                shoreline_erode_iterations=4,
                hill_density=0.03,
            ).model_dump(),
        },
    ]


@app.post("/api/assets/{asset_key}", response_model=AssetUploadResponse)
def upload_asset(asset_key: str, file: UploadFile = File(...)) -> AssetUploadResponse:
    if asset_key not in ASSET_KEYS:
        raise HTTPException(status_code=404, detail="Unknown asset key")

    source_name = Path(file.filename or "").name
    suffix = Path(source_name).suffix.lower()
    if suffix not in ASSET_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Upload a .png, .aseprite, or .ase file")

    safe_stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in Path(source_name).stem)
    filename = f"{uuid4().hex}_{safe_stem}{suffix}"
    target_dir = upload_root() / asset_key
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename

    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    return AssetUploadResponse(
        key=asset_key,
        filename=source_name,
        path=str(target),
        size_bytes=target.stat().st_size,
    )


@app.post("/api/jobs", response_model=JobResponse, status_code=202)
def create_job(request: MapRequest) -> JobResponse:
    if request.tree_density + request.water_density > 1:
        raise HTTPException(status_code=422, detail="tree_density + water_density cannot exceed 1.0")
    job = job_store.create(request)
    return job_store.to_response(job)


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_store.to_response(job)


@app.get("/api/jobs/{job_id}/artifacts/{filename}")
def download_artifact(job_id: str, filename: str) -> FileResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    response = job_store.to_response(job)
    if response.status not in (JobStatus.complete, JobStatus.failed):
        raise HTTPException(status_code=409, detail="Artifacts are not ready yet")
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid artifact name")
    path = job.directory / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path, filename=filename, headers={"Cache-Control": "no-store"})
