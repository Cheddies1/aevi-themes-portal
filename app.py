import base64
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent
THEMES_DIR = Path(os.getenv("THEMES_DIR", BASE_DIR / "themes"))
PORTAL_DATA_DIR = Path(os.getenv("PORTAL_DATA_DIR", BASE_DIR / ".portal-data"))
MAX_LOGO_BYTES = int(os.getenv("MAX_LOGO_BYTES", str(1024 * 1024)))
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
AEVI_LOGO_PATH = BASE_DIR / "static" / "aevi-logo.svg"
SETTINGS_PATH = PORTAL_DATA_DIR / "settings.json"
METADATA_PATH = PORTAL_DATA_DIR / "theme-metadata.json"
DEFAULT_SORT_MODE = "name_asc"
SORT_MODES = {"name_asc", "created_desc", "updated_desc", "manual"}


app = FastAPI(title="Aevi Theme Portal")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
THEMES_DIR.mkdir(parents=True, exist_ok=True)
PORTAL_DATA_DIR.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "theme"


def safe_theme_path(file_name: str) -> Path:
    candidate = Path(file_name).name
    if candidate != file_name or not candidate.endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid file name.")
    return THEMES_DIR / candidate


def hex_to_argb_signed(color: str) -> int:
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        raise HTTPException(status_code=400, detail="Colour must be in #RRGGBB format.")
    rgb_value = int(color[1:], 16)
    unsigned_argb = (0xFF << 24) | rgb_value
    if unsigned_argb >= 0x80000000:
        return unsigned_argb - 0x100000000
    return unsigned_argb


def parse_checkbox(value: str | None) -> bool:
    return str(value).lower() in {"1", "true", "on", "yes"}


def validate_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Name is required.")
    return cleaned


def validate_logo(logo: UploadFile | None) -> str | None:
    if logo is None or not logo.filename:
        return None

    payload = logo.file.read()
    if len(payload) > MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Logo must be {MAX_LOGO_BYTES} bytes or smaller.",
        )
    if not payload.startswith(PNG_SIGNATURE):
        raise HTTPException(status_code=400, detail="Logo must be a PNG file.")

    return base64.b64encode(payload).decode("ascii")


def read_theme(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail="Theme not found.")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def list_theme_files() -> list[Path]:
    return sorted(THEMES_DIR.glob("*.json"))


def iso_utc(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat().replace("+00:00", "Z")


def parse_iso_utc(value: str | None) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, tz=UTC)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return datetime.fromtimestamp(0, tz=UTC)


def load_json_file(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def load_settings() -> dict[str, str]:
    payload = load_json_file(SETTINGS_PATH, {"sortMode": DEFAULT_SORT_MODE})
    sort_mode = payload.get("sortMode", DEFAULT_SORT_MODE)
    if sort_mode not in SORT_MODES:
        sort_mode = DEFAULT_SORT_MODE
    return {"sortMode": sort_mode}


def save_settings(settings: dict[str, str]) -> None:
    write_json_file(SETTINGS_PATH, settings)


def load_theme_metadata() -> dict[str, Any]:
    payload = load_json_file(METADATA_PATH, {"themes": {}})
    themes = payload.get("themes")
    if not isinstance(themes, dict):
        themes = {}
    return {"themes": themes}


def save_theme_metadata(metadata: dict[str, Any]) -> None:
    write_json_file(METADATA_PATH, metadata)


def get_theme_meta_entry(
    metadata: dict[str, Any],
    theme_path: Path,
    *,
    create_missing: bool = True,
) -> dict[str, Any]:
    themes_meta = metadata.setdefault("themes", {})
    entry = themes_meta.get(theme_path.name)
    if not isinstance(entry, dict):
        entry = {}
        if create_missing:
            themes_meta[theme_path.name] = entry

    if create_missing and "createdAt" not in entry:
        entry["createdAt"] = iso_utc(theme_path.stat().st_ctime)
    return entry


def get_next_display_order(metadata: dict[str, Any]) -> int:
    themes_meta = metadata.get("themes", {})
    display_orders = [
        value.get("displayOrder")
        for value in themes_meta.values()
        if isinstance(value, dict) and isinstance(value.get("displayOrder"), int)
    ]
    return (max(display_orders) + 100) if display_orders else 100


def cleanup_theme_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    existing_files = {theme_path.name for theme_path in list_theme_files()}
    themes_meta = metadata.get("themes", {})
    metadata["themes"] = {
        file_name: value
        for file_name, value in themes_meta.items()
        if file_name in existing_files and isinstance(value, dict)
    }
    return metadata


def build_theme_url(request: Request, file_name: str) -> str:
    return str(request.url_for("api_get_theme", file_name=file_name))


def serialize_theme(
    request: Request,
    theme_path: Path,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    data = read_theme(theme_path)
    stats = theme_path.stat()
    meta_entry = get_theme_meta_entry(metadata, theme_path)
    item = {
        "name": data["name"],
        "fileName": theme_path.name,
        "url": build_theme_url(request, theme_path.name),
        "lastModified": iso_utc(stats.st_mtime),
        "size": stats.st_size,
        "createdAt": str(meta_entry.get("createdAt", iso_utc(stats.st_ctime))),
        "displayOrder": meta_entry.get("displayOrder"),
    }
    return {**item, **theme_to_form_values(theme_path.name, data)}


def sort_theme_paths(
    theme_paths: list[Path],
    metadata: dict[str, Any],
    sort_mode: str,
) -> list[Path]:
    if sort_mode == "created_desc":
        return sorted(
            theme_paths,
            key=lambda path: (
                parse_iso_utc(get_theme_meta_entry(metadata, path).get("createdAt")).timestamp(),
                path.name.casefold(),
            ),
            reverse=True,
        )
    if sort_mode == "updated_desc":
        return sorted(
            theme_paths,
            key=lambda path: (path.stat().st_mtime, path.name.casefold()),
            reverse=True,
        )
    if sort_mode == "manual":
        return sorted(
            theme_paths,
            key=lambda path: (
                get_theme_meta_entry(metadata, path).get("displayOrder")
                if isinstance(get_theme_meta_entry(metadata, path).get("displayOrder"), int)
                else 10**9,
                read_theme(path)["name"].casefold(),
                path.name.casefold(),
            ),
        )
    return sorted(theme_paths, key=lambda path: read_theme(path)["name"].casefold())


def ordered_theme_paths() -> tuple[list[Path], dict[str, Any], str]:
    metadata = cleanup_theme_metadata(load_theme_metadata())
    settings = load_settings()
    ordered_paths = sort_theme_paths(list_theme_files(), metadata, settings["sortMode"])
    save_theme_metadata(metadata)
    return ordered_paths, metadata, settings["sortMode"]


def list_themes(request: Request) -> tuple[list[dict[str, Any]], str]:
    ordered_paths, metadata, sort_mode = ordered_theme_paths()
    return [serialize_theme(request, theme_path, metadata) for theme_path in ordered_paths], sort_mode


def list_theme_configs() -> list[dict[str, Any]]:
    ordered_paths, _, _ = ordered_theme_paths()
    return [read_theme(theme_path) for theme_path in ordered_paths]


def find_theme_by_name(name: str, exclude_file: str | None = None) -> Path | None:
    target_name = name.strip().casefold()
    for theme_path in list_theme_files():
        if exclude_file and theme_path.name == exclude_file:
            continue
        data = read_theme(theme_path)
        if str(data.get("name", "")).strip().casefold() == target_name:
            return theme_path
    return None


def build_theme_document(
    *,
    name: str,
    color: str,
    logo_base64: str | None,
    use_default_logo: bool,
    color_default_logo: bool,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "name": validate_name(name),
        "primaryColorArgb": hex_to_argb_signed(color),
    }

    if logo_base64:
        document["logoBytesBase64"] = logo_base64
        return document

    document["useDefaultLogo"] = use_default_logo
    if use_default_logo:
        document["colorDefaultLogo"] = color_default_logo

    return document


def write_theme(path: Path, document: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)


def theme_to_form_values(file_name: str, data: dict[str, Any]) -> dict[str, Any]:
    argb = int(data["primaryColorArgb"])
    rgb_hex = f"#{argb & 0x00FFFFFF:06X}"
    logo_base64 = data.get("logoBytesBase64")
    return {
        "file_name": file_name,
        "name": data["name"],
        "color": rgb_hex,
        "use_default_logo": bool(data.get("useDefaultLogo", False)),
        "color_default_logo": bool(data.get("colorDefaultLogo", False)),
        "has_custom_logo": bool(logo_base64),
        "logo_data_url": f"data:image/png;base64,{logo_base64}" if logo_base64 else None,
    }


def upsert_theme(
    *,
    current_file_name: str | None,
    name: str,
    color: str,
    logo: UploadFile | None,
    remove_current_logo_raw: str | None,
    use_default_logo_raw: str | None,
    color_default_logo_raw: str | None,
) -> tuple[str, dict[str, Any]]:
    validated_name = validate_name(name)

    existing_with_name = find_theme_by_name(validated_name, exclude_file=current_file_name)
    if existing_with_name is not None:
        raise HTTPException(status_code=400, detail="Theme name must be unique.")

    use_default_logo = parse_checkbox(use_default_logo_raw)
    color_default_logo = parse_checkbox(color_default_logo_raw)
    remove_current_logo = parse_checkbox(remove_current_logo_raw)
    logo_base64 = validate_logo(logo)

    existing_document: dict[str, Any] | None = None
    if current_file_name:
        current_path = safe_theme_path(current_file_name)
        if not current_path.exists():
            raise HTTPException(status_code=404, detail="Theme not found.")
        existing_document = read_theme(current_path)
        if (
            not logo_base64
            and not remove_current_logo
            and not use_default_logo
            and "logoBytesBase64" in existing_document
        ):
            logo_base64 = str(existing_document["logoBytesBase64"])

    document = build_theme_document(
        name=validated_name,
        color=color,
        logo_base64=logo_base64,
        use_default_logo=use_default_logo,
        color_default_logo=color_default_logo,
    )

    new_file_name = f"{slugify(validated_name)}.json"
    target_path = safe_theme_path(new_file_name)
    metadata = cleanup_theme_metadata(load_theme_metadata())
    settings = load_settings()

    if current_file_name:
        current_path = safe_theme_path(current_file_name)
        if not current_path.exists():
            raise HTTPException(status_code=404, detail="Theme not found.")
        if current_path != target_path and target_path.exists():
            raise HTTPException(status_code=400, detail="A theme with this file name already exists.")
        write_theme(target_path, document)
        if current_path != target_path and current_path.exists():
            existing_meta = metadata.get("themes", {}).pop(current_path.name, None)
            if isinstance(existing_meta, dict):
                metadata.setdefault("themes", {})[target_path.name] = existing_meta
            current_path.unlink()
        get_theme_meta_entry(metadata, target_path)
    else:
        if target_path.exists():
            raise HTTPException(status_code=400, detail="A theme with this file name already exists.")
        write_theme(target_path, document)
        new_entry = get_theme_meta_entry(metadata, target_path)
        if settings["sortMode"] == "manual" or not isinstance(new_entry.get("displayOrder"), int):
            new_entry["displayOrder"] = get_next_display_order(metadata)

    save_theme_metadata(metadata)

    return new_file_name, document


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    themes, sort_mode = list_themes(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "themes": themes,
            "sort_mode": sort_mode,
            "sort_mode_options": [
                {"value": "name_asc", "label": "Name"},
                {"value": "created_desc", "label": "Newest created"},
                {"value": "updated_desc", "label": "Recently updated"},
                {"value": "manual", "label": "Manual"},
            ],
            "max_logo_mb": MAX_LOGO_BYTES // (1024 * 1024),
            "error": None,
            "aevi_logo_path": "/static/aevi-logo.svg" if AEVI_LOGO_PATH.exists() else None,
            "form": {
                "name": "",
                "color": "#33CC6B",
                "use_default_logo": False,
                "color_default_logo": False,
            },
        },
    )


@app.get("/ui/themes/{file_name}/edit", response_class=HTMLResponse)
def edit_theme_page(request: Request, file_name: str) -> HTMLResponse:
    theme_path = safe_theme_path(file_name)
    form = theme_to_form_values(file_name, read_theme(theme_path))
    form["theme_url"] = build_theme_url(request, file_name)
    form["last_modified"] = iso_utc(theme_path.stat().st_mtime)
    form["size"] = theme_path.stat().st_size
    form["remove_current_logo"] = False
    return templates.TemplateResponse(
        request=request,
        name="edit.html",
        context={
            "form": form,
            "max_logo_mb": MAX_LOGO_BYTES // (1024 * 1024),
            "error": None,
            "aevi_logo_path": "/static/aevi-logo.svg" if AEVI_LOGO_PATH.exists() else None,
        },
    )


def render_index_with_error(request: Request, message: str, form: dict[str, Any]) -> HTMLResponse:
    themes, sort_mode = list_themes(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "themes": themes,
            "sort_mode": sort_mode,
            "sort_mode_options": [
                {"value": "name_asc", "label": "Name"},
                {"value": "created_desc", "label": "Newest created"},
                {"value": "updated_desc", "label": "Recently updated"},
                {"value": "manual", "label": "Manual"},
            ],
            "max_logo_mb": MAX_LOGO_BYTES // (1024 * 1024),
            "error": message,
            "aevi_logo_path": "/static/aevi-logo.svg" if AEVI_LOGO_PATH.exists() else None,
            "form": form,
        },
        status_code=400,
    )


def render_edit_with_error(
    request: Request,
    file_name: str,
    message: str,
    form: dict[str, Any],
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="edit.html",
        context={
            "form": {**form, "file_name": file_name},
            "max_logo_mb": MAX_LOGO_BYTES // (1024 * 1024),
            "error": message,
            "aevi_logo_path": "/static/aevi-logo.svg" if AEVI_LOGO_PATH.exists() else None,
        },
        status_code=400,
    )


@app.post("/ui/themes")
def create_theme_from_ui(
    request: Request,
    name: str = Form(...),
    color: str = Form(...),
    logo: UploadFile | None = File(default=None),
    removeCurrentLogo: str | None = Form(default=None),
    useDefaultLogo: str | None = Form(default=None),
    colorDefaultLogo: str | None = Form(default=None),
) -> Response:
    try:
        upsert_theme(
            current_file_name=None,
            name=name,
            color=color,
            logo=logo,
            remove_current_logo_raw=removeCurrentLogo,
            use_default_logo_raw=useDefaultLogo,
            color_default_logo_raw=colorDefaultLogo,
        )
    except HTTPException as exc:
        return render_index_with_error(
            request,
            str(exc.detail),
            {
                "name": name,
                "color": color,
                "remove_current_logo": parse_checkbox(removeCurrentLogo),
                "use_default_logo": parse_checkbox(useDefaultLogo),
                "color_default_logo": parse_checkbox(colorDefaultLogo),
            },
        )
    return RedirectResponse("/", status_code=303)


@app.post("/ui/themes/{file_name}")
def update_theme_from_ui(
    request: Request,
    file_name: str,
    name: str = Form(...),
    color: str = Form(...),
    logo: UploadFile | None = File(default=None),
    removeCurrentLogo: str | None = Form(default=None),
    useDefaultLogo: str | None = Form(default=None),
    colorDefaultLogo: str | None = Form(default=None),
) -> Response:
    try:
        new_file_name, _ = upsert_theme(
            current_file_name=file_name,
            name=name,
            color=color,
            logo=logo,
            remove_current_logo_raw=removeCurrentLogo,
            use_default_logo_raw=useDefaultLogo,
            color_default_logo_raw=colorDefaultLogo,
        )
    except HTTPException as exc:
        return render_edit_with_error(
            request,
            file_name,
            str(exc.detail),
            {
                "name": name,
                "color": color,
                "remove_current_logo": parse_checkbox(removeCurrentLogo),
                "use_default_logo": parse_checkbox(useDefaultLogo),
                "color_default_logo": parse_checkbox(colorDefaultLogo),
                "has_custom_logo": False,
                "logo_data_url": None,
                "theme_url": build_theme_url(request, file_name),
            },
        )
    return RedirectResponse(f"/ui/themes/{new_file_name}/edit", status_code=303)


@app.post("/ui/themes/{file_name}/delete")
def delete_theme_from_ui(file_name: str) -> RedirectResponse:
    theme_path = safe_theme_path(file_name)
    if theme_path.exists():
        theme_path.unlink()
    metadata = cleanup_theme_metadata(load_theme_metadata())
    metadata.get("themes", {}).pop(file_name, None)
    save_theme_metadata(metadata)
    return RedirectResponse("/", status_code=303)


@app.get("/themes")
def api_list_themes(request: Request) -> list[dict[str, Any]]:
    themes, _ = list_themes(request)
    return [
        {
            "name": item["name"],
            "fileName": item["fileName"],
            "url": item["url"],
            "lastModified": item["lastModified"],
            "size": item["size"],
        }
        for item in themes
    ]


@app.get("/themes/configs")
def api_list_theme_configs() -> list[dict[str, Any]]:
    return list_theme_configs()


@app.get("/themes/{file_name}")
def api_get_theme(file_name: str) -> Response:
    theme_path = safe_theme_path(file_name)
    with theme_path.open("r", encoding="utf-8") as handle:
        payload = handle.read()
    return Response(content=payload, media_type="application/json")


@app.post("/themes", status_code=201)
def api_create_theme(
    name: str = Form(...),
    color: str = Form(...),
    logo: UploadFile | None = File(default=None),
    removeCurrentLogo: str | None = Form(default=None),
    useDefaultLogo: str | None = Form(default=None),
    colorDefaultLogo: str | None = Form(default=None),
) -> dict[str, Any]:
    file_name, document = upsert_theme(
        current_file_name=None,
        name=name,
        color=color,
        logo=logo,
        remove_current_logo_raw=removeCurrentLogo,
        use_default_logo_raw=useDefaultLogo,
        color_default_logo_raw=colorDefaultLogo,
    )
    return {"fileName": file_name, "theme": document}


@app.put("/themes/{file_name}")
def api_update_theme(
    file_name: str,
    name: str = Form(...),
    color: str = Form(...),
    logo: UploadFile | None = File(default=None),
    removeCurrentLogo: str | None = Form(default=None),
    useDefaultLogo: str | None = Form(default=None),
    colorDefaultLogo: str | None = Form(default=None),
) -> dict[str, Any]:
    new_file_name, document = upsert_theme(
        current_file_name=file_name,
        name=name,
        color=color,
        logo=logo,
        remove_current_logo_raw=removeCurrentLogo,
        use_default_logo_raw=useDefaultLogo,
        color_default_logo_raw=colorDefaultLogo,
    )
    return {"fileName": new_file_name, "theme": document}


@app.delete("/themes/{file_name}", status_code=204)
def api_delete_theme(file_name: str) -> Response:
    theme_path = safe_theme_path(file_name)
    if not theme_path.exists():
        raise HTTPException(status_code=404, detail="Theme not found.")
    theme_path.unlink()
    metadata = cleanup_theme_metadata(load_theme_metadata())
    metadata.get("themes", {}).pop(file_name, None)
    save_theme_metadata(metadata)
    return Response(status_code=204)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ui/settings/sort-mode")
def update_sort_mode(sortMode: str = Form(...)) -> RedirectResponse:
    if sortMode not in SORT_MODES:
        raise HTTPException(status_code=400, detail="Invalid sort mode.")

    settings = load_settings()
    settings["sortMode"] = sortMode
    save_settings(settings)

    if sortMode == "manual":
        ordered_paths, metadata, _ = ordered_theme_paths()
        for index, path in enumerate(ordered_paths, start=1):
            entry = get_theme_meta_entry(metadata, path)
            if not isinstance(entry.get("displayOrder"), int):
                entry["displayOrder"] = index * 100
        save_theme_metadata(metadata)

    return RedirectResponse("/", status_code=303)


def move_theme(file_name: str, direction: int) -> None:
    settings = load_settings()
    if settings["sortMode"] != "manual":
        return

    ordered_paths, metadata, _ = ordered_theme_paths()
    file_names = [path.name for path in ordered_paths]
    if file_name not in file_names:
        raise HTTPException(status_code=404, detail="Theme not found.")

    current_index = file_names.index(file_name)
    target_index = current_index + direction
    if target_index < 0 or target_index >= len(file_names):
        return

    current_path = ordered_paths[current_index]
    target_path = ordered_paths[target_index]
    current_entry = get_theme_meta_entry(metadata, current_path)
    target_entry = get_theme_meta_entry(metadata, target_path)
    current_order = current_entry.get("displayOrder")
    target_order = target_entry.get("displayOrder")
    if not isinstance(current_order, int) or not isinstance(target_order, int):
        for index, path in enumerate(ordered_paths, start=1):
            get_theme_meta_entry(metadata, path)["displayOrder"] = index * 100
        current_order = get_theme_meta_entry(metadata, current_path)["displayOrder"]
        target_order = get_theme_meta_entry(metadata, target_path)["displayOrder"]

    current_entry["displayOrder"], target_entry["displayOrder"] = target_order, current_order
    save_theme_metadata(metadata)


@app.post("/ui/themes/{file_name}/move-up")
def move_theme_up(file_name: str) -> RedirectResponse:
    move_theme(file_name, -1)
    return RedirectResponse("/", status_code=303)


@app.post("/ui/themes/{file_name}/move-down")
def move_theme_down(file_name: str) -> RedirectResponse:
    move_theme(file_name, 1)
    return RedirectResponse("/", status_code=303)
