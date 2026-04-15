# Aevi Theme Portal POC

Simple FastAPI web portal for creating, editing, deleting, listing, and serving Aevi theme configuration files.

## Features

- Server-rendered UI for theme CRUD operations
- File-based storage under `./themes`
- API endpoints for list, fetch, create, update, and delete
- Absolute theme URLs in the list API
- Simple health endpoint at `GET /health`
- JSON link and copy-to-clipboard action in the UI
- Explicit custom logo removal on edit
- Validation for unique names, PNG-only uploads, safe file names, and colour conversion
- JSON output matching the required theme structure

## Requirements

- Python 3.10+

## Run

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
uvicorn app:app --reload
```

4. Open `http://127.0.0.1:8000`

## Configuration

- `THEMES_DIR`: override the storage directory. Default is `./themes`
- `MAX_LOGO_BYTES`: maximum allowed PNG size in bytes. Default is `1048576`

## API

- `GET /themes` returns theme metadata including absolute `url`, `lastModified`, and `size`
- `GET /themes/configs` returns a list of raw theme configuration objects for app ingestion
- `GET /themes/{fileName}` returns the raw JSON config
- `GET /health` returns `{ "status": "ok" }`
- `POST /themes` creates a theme from multipart form-data
- `PUT /themes/{fileName}` updates a theme from multipart form-data
- `DELETE /themes/{fileName}` removes a theme

Example `GET /themes` item:

```json
{
  "name": "Jupico Green",
  "fileName": "jupico-green.json",
  "url": "http://127.0.0.1:8000/themes/jupico-green.json",
  "lastModified": "2026-04-15T10:12:34Z",
  "size": 1234
}
```

Example `GET /themes/configs` response:

```json
[
  {
    "name": "Jupico Green",
    "primaryColorArgb": -16734053,
    "useDefaultLogo": true,
    "colorDefaultLogo": false
  },
  {
    "name": "Visa Blue",
    "primaryColorArgb": -12345678,
    "logoBytesBase64": "BASE64..."
  }
]
```

Update requests may include `removeCurrentLogo=true` to explicitly remove an existing custom logo.

## Notes

- Colour input accepts `#RRGGBB` and is converted to a signed 32-bit ARGB integer with full opacity.
- If a custom logo is uploaded, the JSON omits `useDefaultLogo` and `colorDefaultLogo`.
- If no custom logo is uploaded, `useDefaultLogo` is always written and `colorDefaultLogo` is only written when `useDefaultLogo` is true.
- When editing, `removeCurrentLogo` removes `logoBytesBase64` instead of silently retaining the previous logo.
- The UI uses the bundled Aevi logo asset at `static/aevi-logo.svg`.
