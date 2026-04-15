# Aevi Theme Portal - Agent Context

## What this is
FastAPI proof-of-concept portal for creating, editing, deleting, listing, and serving Aevi theme configuration files.

Primary purpose:
- sales/demo support
- quick manual theme creation
- file-backed JSON output without a database

This is intentionally a small internal utility, not a production platform.

## Product direction
Current scope:
- create themes from a simple web form
- edit existing themes
- delete themes
- list stored themes
- serve raw theme JSON files
- expose a lightweight metadata API
- expose an app-facing config list endpoint

Out of scope:
- auth
- user management
- database storage
- S3/object storage implementation
- versioning/history
- bulk import/export
- frontend framework migration

## Theme file contract
Each stored theme must remain compatible with the Aevi app-facing JSON structure:

```json
{
  "name": "Jupico Green",
  "primaryColorArgb": -13762508,
  "useDefaultLogo": false,
  "colorDefaultLogo": true,
  "logoBytesBase64": "BASE64_ENCODED_PNG"
}
```

Rules:
- `name` is required and must be unique across saved themes
- filenames are slugified from the name, for example `Jupico Green` -> `jupico-green.json`
- `primaryColorArgb` is derived from `#RRGGBB` with full alpha and stored as a signed 32-bit integer
- `logoBytesBase64` is optional and only valid for PNG uploads
- if `logoBytesBase64` exists, omit `useDefaultLogo` and `colorDefaultLogo`
- if no custom logo exists, write `useDefaultLogo`
- only write `colorDefaultLogo` when `useDefaultLogo` is true

## Current behaviour
Implemented API routes:
- `GET /`
- `GET /ui/themes/{file_name}/edit`
- `POST /ui/themes`
- `POST /ui/themes/{file_name}`
- `POST /ui/themes/{file_name}/delete`
- `GET /themes`
- `GET /themes/configs`
- `GET /themes/{file_name}`
- `POST /themes`
- `PUT /themes/{file_name}`
- `DELETE /themes/{file_name}`
- `GET /health`

Important current API details:
- `GET /themes` returns absolute theme URLs built from the incoming request
- `GET /themes` also returns `lastModified` and `size`
- `GET /themes/configs` returns the stored theme JSON objects exactly, with stable filename order and no metadata fields injected
- create/update endpoints accept multipart form data
- update flows may include `removeCurrentLogo=true` to explicitly remove an existing custom logo

UI behaviour already in place:
- saved-theme cards show colour preview
- saved-theme cards show custom logo preview when present
- saved-theme cards show `Default logo` or `No logo` when no custom logo exists
- saved-theme cards include direct JSON link and clipboard copy action
- edit page includes explicit `Remove current logo`

## Storage
- default storage is local filesystem under [themes](themes)
- each theme is stored as `/themes/{slug}.json` on disk
- no database is used

## Branding
Current UI branding is intentionally restrained:
- Aevi Hero Green: `#33CC6B`
- Aevi Off-White: `#F7F6EF`
- Aevi Black: `#230211`

Current logo asset:
- [static/aevi-logo.svg](static/aevi-logo.svg)

Temporary brand references live in `temp/` and are not part of runtime behaviour:
- logo variants
- brand guidelines PDF

## Key files
- [app.py](app.py)
- [README.md](README.md)
- [requirements.txt](requirements.txt)
- [templates/base.html](templates/base.html)
- [templates/index.html](templates/index.html)
- [templates/edit.html](templates/edit.html)
- [static/styles.css](static/styles.css)
- [static/app.js](static/app.js)
- [static/aevi-logo.svg](static/aevi-logo.svg)
- [themes](themes)

## Architectural guardrails
- keep FastAPI and the current server-rendered approach
- keep file-backed storage as the default
- do not introduce auth or a database unless explicitly requested
- do not redesign the theme JSON format
- prefer small, targeted edits over re-architecture
- keep dependencies minimal
- use vanilla JS only for small client-side actions

## Constraints
- preserve PNG-only validation and configured max upload size
- preserve unique-name validation
- preserve slugified filenames
- preserve signed ARGB conversion semantics
- keep the portal usable as a fast internal demo tool

## Read first
- [README.md](README.md)
- [app.py](app.py)
- [templates/index.html](templates/index.html)
- [templates/edit.html](templates/edit.html)
- [static/styles.css](static/styles.css)
