from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"


class AssetOverrides(BaseModel):
    grass_path: str | None = None
    shoreline_path: str | None = None
    lakesrivers_path: str | None = None
    water_path: str | None = None
    hill_path: str | None = None
    dirt_path: str | None = None
    trees_path: str | None = None


class MapRequest(BaseModel):
    width: int = Field(default=128, ge=8, le=512)
    height: int = Field(default=128, ge=8, le=512)
    tree_density: float = Field(default=0.22, ge=0, le=1)
    forest_density: float = Field(default=0.65, ge=0, le=1)
    water_density: float = Field(default=0.10, ge=0, le=1)
    hill_density: float = Field(default=0.04, ge=0, le=1)
    spawn_count: int = Field(default=8, ge=1, le=32)
    spawn_clearing_size: int = Field(default=15, ge=3, le=31)
    join_point_count: int = Field(default=0, ge=0, le=16)
    path_width_threshold: int = Field(default=3, ge=1, le=8)
    path_perlin_scale: float = Field(default=14.0, ge=4.0, le=24.0)
    path_perlin_weight: float = Field(default=1.8, ge=0.5, le=4.0)
    mine_count: int = Field(default=4, ge=0, le=20)
    shop_count: int = Field(default=3, ge=0, le=16)
    creep_zone_count: int = Field(default=6, ge=0, le=24)
    creep_zone_radius: int = Field(default=2, ge=1, le=6)
    dead_end_count: int = Field(default=8, ge=0, le=32)
    require_secret_npc_path: bool = True
    hide_path: bool = False
    map_mode: Literal["island", "continent"] = "island"
    shoreline_erode_iterations: int = Field(default=2, ge=0, le=6)
    preview_tile_size: int = Field(default=16, ge=2, le=32)
    seed: int = Field(default=42, ge=0, le=999_999_999)
    terrain_config: str = "examples/terrain.bitmask.json"
    include_aseprite: bool = True
    asset_overrides: AssetOverrides = Field(default_factory=AssetOverrides)


class Artifact(BaseModel):
    name: str
    filename: str
    size_bytes: int
    url: str


class JobResponse(BaseModel):
    id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    message: str
    artifacts: list[Artifact] = []
    error: str | None = None


class HealthResponse(BaseModel):
    ok: bool
    core_path: str
    core_importable: bool
    aseprite_available: bool
    aseprite_bin: str | None


class AssetUploadResponse(BaseModel):
    key: str
    filename: str
    path: str
    size_bytes: int
