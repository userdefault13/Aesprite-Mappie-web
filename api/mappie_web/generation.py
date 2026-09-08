from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import shutil
from pathlib import Path

from .config import core_path, ensure_core_importable, resolve_aseprite_bin
from .schemas import MapRequest


def run_generation_job(request: MapRequest, output_dir: Path) -> None:
    ensure_core_importable()
    from tilemap_generator import aseprite_cli, map_gen_cli

    output_dir.mkdir(parents=True, exist_ok=True)
    ascii_path = output_dir / "map.txt"
    preview_path = output_dir / "preview.bmp"
    terrain_config = build_job_terrain_config(request, output_dir)

    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        profile_arg = resolve_profile_arg(request.profile)
        # When a profile is set, canvas/densities from the request act as overrides
        # (None would mean "use profile"; we still pass request values as explicit overrides).
        map_gen_cli.run_from_args(
            argparse.Namespace(
                profile=profile_arg or "",
                width=request.width,
                height=request.height,
                tree_density=request.tree_density,
                forest_density=request.forest_density,
                water_density=request.water_density,
                hill_density=request.hill_density,
                spawn_count=request.spawn_count,
                spawn_clearing_size=make_odd(request.spawn_clearing_size),
                join_point_count=request.join_point_count,
                path_width_threshold=request.path_width_threshold,
                path_perlin_scale=request.path_perlin_scale,
                path_perlin_weight=request.path_perlin_weight,
                mine_count=request.mine_count,
                shop_count=request.shop_count,
                creep_zone_count=request.creep_zone_count,
                creep_zone_radius=request.creep_zone_radius,
                dead_end_count=request.dead_end_count,
                require_secret_npc_path=request.require_secret_npc_path,
                hide_path=request.hide_path,
                seed=request.seed,
                map_mode=request.map_mode,
                water_border_width=2 if request.map_mode == "island" else 0,
                height_noise_scale=12.0,
                hill_threshold=0.65,
                beach_height_max=0.45,
                shoreline_erode_iterations=request.shoreline_erode_iterations,
                shoreline_expand_depth=0,
                out=str(ascii_path),
                terrain_config=str(terrain_config),
                legend_out="",
                preview_out=str(preview_path),
                preview_tile_size=request.preview_tile_size,
                preview_in_aseprite=False,
                preview_layered=False,
                aseprite_bin="",
            )
        )
        if not request.include_aseprite:
            write_browser_painted_png(preview_path, output_dir / "map.png")

        if request.include_aseprite:
            aseprite_bin = resolve_aseprite_bin()
            if aseprite_bin is None:
                raise FileNotFoundError(
                    "Aseprite CLI was requested but not found. Set ASEPRITE_BIN or install aseprite in PATH."
                )
            aseprite_path = output_dir / "map.aseprite"
            layer_dir = output_dir / "paint_layers"
            previous_layer_dir = os.environ.get("MAPPIE_LAYER_EXPORT_DIR")
            previous_timeout = os.environ.get("MAPPIE_ASEPRITE_PAINT_TIMEOUT")
            previous_allow_timeout = os.environ.get("MAPPIE_ALLOW_ASEPRITE_PAINT_TIMEOUT")
            os.environ["MAPPIE_LAYER_EXPORT_DIR"] = str(layer_dir)
            os.environ["MAPPIE_ASEPRITE_PAINT_TIMEOUT"] = "15"
            os.environ["MAPPIE_ALLOW_ASEPRITE_PAINT_TIMEOUT"] = "1"
            try:
                aseprite_cli.main(
                    [
                        "--aseprite-bin",
                        aseprite_bin,
                        "paint",
                        "--ascii",
                        str(ascii_path),
                        "--out",
                        str(aseprite_path),
                        "--tile-size",
                        str(request.preview_tile_size),
                        "--terrain-config",
                        str(terrain_config),
                        "--no-open",
                        "--no-export-map",
                    ]
                )
            finally:
                if previous_layer_dir is None:
                    os.environ.pop("MAPPIE_LAYER_EXPORT_DIR", None)
                else:
                    os.environ["MAPPIE_LAYER_EXPORT_DIR"] = previous_layer_dir
                if previous_timeout is None:
                    os.environ.pop("MAPPIE_ASEPRITE_PAINT_TIMEOUT", None)
                else:
                    os.environ["MAPPIE_ASEPRITE_PAINT_TIMEOUT"] = previous_timeout
                if previous_allow_timeout is None:
                    os.environ.pop("MAPPIE_ALLOW_ASEPRITE_PAINT_TIMEOUT", None)
                else:
                    os.environ["MAPPIE_ALLOW_ASEPRITE_PAINT_TIMEOUT"] = previous_allow_timeout
            composite_painted_layers(layer_dir, output_dir / "map.png")

    (output_dir / "job.log").write_text(log.getvalue(), encoding="utf-8")
    copy_sidecar_outputs(output_dir, ascii_path)



def resolve_profile_arg(raw: str | None) -> str | None:
    """Resolve optional profile path/id to an absolute path under the Mappie core repo."""
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    candidate = Path(text).expanduser()
    if candidate.is_file():
        return str(candidate.resolve())
    core = core_path()
    # id like moba_3lane_lunacia → profiles/<id>.json
    for rel in (text, f"profiles/{text}", f"profiles/{text}.json", f"{text}.json"):
        p = (core / rel).resolve()
        if p.is_file():
            return str(p)
    # Allow relative to core even if missing — map_gen will error clearly
    return str((core / text).resolve())



def resolve_core_relative_path(raw: str) -> Path:
    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        return candidate
    return (core_path() / candidate).resolve()


def build_job_terrain_config(request: MapRequest, output_dir: Path) -> Path:
    base_path = resolve_core_relative_path(request.terrain_config)
    overrides = request.asset_overrides.model_dump(exclude_none=True)
    if not overrides:
        return base_path

    if not base_path.exists():
        raise FileNotFoundError(f"Terrain config not found: {base_path}")

    data = json.loads(base_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Terrain config must be a JSON object")

    for key, raw_path in overrides.items():
        data[key] = str(Path(raw_path).expanduser().resolve())

    out_path = output_dir / "terrain.web.json"
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return out_path


def make_odd(value: int) -> int:
    return value if value % 2 else max(3, value - 1)


def write_browser_painted_png(source_path: Path, target_path: Path) -> None:
    from PIL import Image

    if not source_path.exists():
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        image.save(target_path)


def composite_painted_layers(layer_dir: Path, target_path: Path) -> None:
    from PIL import Image

    layer_order = [
        "water_deep.png",
        "water_shallow.png",
        "water_lake.png",
        "water_river.png",
        "grass.png",
        "lakebank.png",
        "shoreline.png",
        "hill.png",
        "dirt.png",
        "trees.png",
        "poi.png",
        "poi_spawn.png",
        "poi_join.png",
        "poi_mine.png",
        "poi_shop.png",
        "poi_creep.png",
        "poi_deadend.png",
        "poi_secret.png",
    ]
    base: Image.Image | None = None
    for layer_name in layer_order:
        path = layer_dir / layer_name
        if not path.exists():
            continue
        with Image.open(path) as raw:
            layer = raw.convert("RGBA")
            if base is None:
                base = Image.new("RGBA", layer.size, (0, 0, 0, 0))
            base.alpha_composite(layer)
    if base is None:
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(target_path)


def copy_sidecar_outputs(output_dir: Path, ascii_path: Path) -> None:
    """Normalize sidecar files generated beside the ASCII map into known artifact names."""
    hill_path = ascii_path.with_suffix(".hill.json")
    if hill_path.exists():
        target = output_dir / "map.hill.json"
        if hill_path != target:
            shutil.copy2(hill_path, target)
