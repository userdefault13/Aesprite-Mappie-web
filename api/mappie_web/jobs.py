from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread
from uuid import uuid4

from .config import artifact_root
from .generation import composite_painted_layers, run_generation_job
from .schemas import Artifact, JobResponse, JobStatus, MapRequest


ARTIFACT_NAMES = {
    "map.txt": "ASCII Map",
    "map.legend.json": "Legend JSON",
    "map.csv": "Tile CSV",
    "map.tiled.json": "Tiled JSON",
    "preview.bmp": "Preview BMP",
    "map.aseprite": "Aseprite Map",
    "map.png": "Painted Map PNG",
    "map.json": "Painted Map Metadata",
    "map.hill.json": "Hill Debug JSON",
}


@dataclass
class JobRecord:
    id: str
    request: MapRequest
    status: JobStatus = JobStatus.running
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message: str = "Starting generation"
    error: str | None = None

    @property
    def directory(self) -> Path:
        return artifact_root() / self.id


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()

    def create(self, request: MapRequest) -> JobRecord:
        job = JobRecord(id=uuid4().hex, request=request)
        with self._lock:
            self._jobs[job.id] = job
        Thread(target=self._run, args=(job.id,), daemon=True).start()
        return job

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                return job
        directory = artifact_root() / job_id
        if not directory.exists() or not directory.is_dir():
            return None

        job = JobRecord(
            id=job_id,
            request=MapRequest(include_aseprite=(directory / "map.aseprite").exists()),
            message="Recovered generated artifacts",
        )
        with self._lock:
            return self._jobs.setdefault(job_id, job)

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        message: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if status is not None:
                job.status = status
            if message is not None:
                job.message = message
            if error is not None:
                job.error = error
            job.updated_at = datetime.now(timezone.utc)

    def to_response(self, job: JobRecord) -> JobResponse:
        status = infer_status_from_artifacts(job)
        if status == JobStatus.complete and job.status != JobStatus.complete:
            self.update(job.id, status=JobStatus.complete, message="Complete")
            job = self.get(job.id) or job
        return JobResponse(
            id=job.id,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            message=job.message,
            artifacts=list_artifacts(job) if job.status in (JobStatus.complete, JobStatus.failed) else [],
            error=job.error,
        )

    def _run(self, job_id: str) -> None:
        job = self.get(job_id)
        if job is None:
            return
        try:
            self.update(job_id, status=JobStatus.running, message="Generating map artifacts")
            run_generation_job(job.request, job.directory)
            self.update(job_id, status=JobStatus.complete, message="Complete")
        except Exception as exc:  # noqa: BLE001 - job errors are returned to the UI.
            log_path = job.directory / "error.log"
            job.directory.mkdir(parents=True, exist_ok=True)
            log_path.write_text(traceback.format_exc(), encoding="utf-8")
            self.update(job_id, status=JobStatus.failed, message="Generation failed", error=str(exc))


def list_artifacts(job: JobRecord) -> list[Artifact]:
    if not job.directory.exists():
        return []
    artifacts: list[Artifact] = []
    for path in sorted(job.directory.iterdir()):
        if not path.is_file():
            continue
        name = ARTIFACT_NAMES.get(path.name, path.name)
        artifacts.append(
            Artifact(
                name=name,
                filename=path.name,
                size_bytes=path.stat().st_size,
                url=f"/api/jobs/{job.id}/artifacts/{path.name}",
            )
        )
    return artifacts


def infer_status_from_artifacts(job: JobRecord) -> JobStatus:
    if job.status in (JobStatus.complete, JobStatus.failed):
        return job.status
    if not job.directory.exists():
        return job.status

    filenames = {path.name for path in job.directory.iterdir() if path.is_file()}
    has_core_outputs = {"map.txt", "map.legend.json", "map.csv", "preview.bmp"}.issubset(filenames)
    if not has_core_outputs:
        return job.status
    if job.request.include_aseprite and "map.aseprite" in filenames and "map.png" not in filenames:
        layer_dir = job.directory / "paint_layers"
        if layer_dir.exists():
            composite_painted_layers(layer_dir, job.directory / "map.png")
            filenames = {path.name for path in job.directory.iterdir() if path.is_file()}
    if job.request.include_aseprite and not {"map.aseprite", "map.png"}.issubset(filenames):
        return job.status
    return JobStatus.complete


job_store = JobStore()
