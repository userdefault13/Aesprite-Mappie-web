# Aseprite Mappie Web

Web UI and API wrapper for the Python Mappie map generator.

## Structure

- `api/` - FastAPI backend that runs Mappie generation jobs and serves artifacts.
- `web/` - Nuxt 3 frontend for map settings, job status, previews, and downloads.

The backend expects the existing Python project to be available at:

```bash
/Users/juliuswong/Dev/Aseprite-Mappie
```

Override this with `MAPPIE_CORE_PATH` if needed.

## Backend Dev

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -e /Users/juliuswong/Dev/Aseprite-Mappie
pip install -e .
uvicorn mappie_web.main:app --reload --port 8000
```

Optional:

```bash
export ASEPRITE_BIN="/Applications/Aseprite.app/Contents/MacOS/aseprite"
```

## Frontend Dev

```bash
cd web
npm install
npm run dev
```

The frontend proxies API calls to `http://localhost:8000`.
