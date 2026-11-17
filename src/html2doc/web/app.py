"""Web API и интерфейс загрузки ZIP."""

from __future__ import annotations

import shutil
import stat
import tempfile
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from html2doc.errors import ArchiveValidationError
from html2doc.options import ConvertOptions
from html2doc.pipeline import convert_batch

MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_MEMBERS = 500
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
JOB_TTL_SECONDS = 3600

app = FastAPI(title="html2doc", version="0.1.0")
_PACKAGE_DIR = Path(__file__).parent
_STATIC_DIR = _PACKAGE_DIR / "static"
_TEMPLATES_DIR = _PACKAGE_DIR / "templates"
_TEMP_ROOT = Path(tempfile.gettempdir()) / "html2doc-jobs"
_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@dataclass(slots=True)
class Job:
    id: str
    work_dir: Path
    created: float = field(default_factory=time.time)
    status: str = "queued"
    message: str = "В очереди"
    current: int = 0
    total: int = 0
    logs: list[dict[str, str]] = field(default_factory=list)
    error: str | None = None
    result_path: Path | None = None


_jobs: dict[str, Job] = {}


def _append_log(job: Job, level: str, message: str) -> None:
    job.logs.append({"level": level, "message": message})
    if len(job.logs) > 500:
        del job.logs[:-500]


def _safe_extract(archive: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(archive) as zf:
            members = zf.infolist()
            if len(members) > MAX_MEMBERS:
                raise ArchiveValidationError("Слишком много файлов в архиве")
            total_size = sum(item.file_size for item in members)
            if total_size > MAX_UNCOMPRESSED_BYTES:
                raise ArchiveValidationError("Слишком большой распакованный объём")
            root = destination.resolve()
            for item in members:
                name = item.filename
                if not name or name.endswith("/"):
                    continue
                if name.startswith(("/", "\\")) or "\\" in name:
                    raise ArchiveValidationError(f"Недопустимый путь в архиве: {name}")
                parts = Path(name).parts
                if ".." in parts or any(part.startswith("/") for part in parts):
                    raise ArchiveValidationError(f"Недопустимый путь в архиве: {name}")
                mode = item.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ArchiveValidationError(f"Символические ссылки запрещены: {name}")
                target = (destination / name).resolve()
                if not str(target).startswith(str(root)):
                    raise ArchiveValidationError(f"Путь вышел за пределы каталога: {name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(item) as source, target.open("wb") as sink:
                    shutil.copyfileobj(source, sink)
    except zipfile.BadZipFile as exc:
        raise ArchiveValidationError(f"Повреждённый ZIP-архив: {exc}") from exc


def _cleanup_jobs() -> None:
    now = time.time()
    for job_id, job in list(_jobs.items()):
        if job.status in {"queued", "running", "building"}:
            continue
        if now - job.created > JOB_TTL_SECONDS:
            shutil.rmtree(job.work_dir, ignore_errors=True)
            del _jobs[job_id]


def _process_job(job_id: str) -> None:
    job = _jobs[job_id]
    try:
        job.status = "running"
        job.message = "Распаковка архива"
        source_dir = job.work_dir / "input"
        source_dir.mkdir(parents=True, exist_ok=True)
        _safe_extract(job.work_dir / "input.zip", source_dir)

        job.message = "Конвертация"
        output_dir = job.work_dir / "output"

        def on_progress(current: int, total: int, source: Path, ok: bool) -> bool:
            job.current = current
            job.total = total
            _append_log(job, "info", f"{current}/{total} {source.name}: {'готово' if ok else 'ошибка'}")
            return True

        results = convert_batch(source_dir, output_dir, ConvertOptions(), on_progress)
        for result in results:
            for warning in result.warnings:
                _append_log(job, warning.severity, f"{result.source.name}: {warning.message}")

        job.status = "building"
        job.message = "Упаковка результата"
        result_zip = job.work_dir / "result.zip"
        with zipfile.ZipFile(result_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(output_dir.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(output_dir))

        job.result_path = result_zip
        job.status = "done"
        job.message = f"Готово файлов: {len(results)}"
    except Exception as exc:
        job.status = "error"
        job.error = str(exc)
        job.message = "Ошибка обработки"
        _append_log(job, "error", str(exc))


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    markup = (_TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(markup)


@app.post("/api/jobs")
async def create_job(file: UploadFile = File(...)) -> JSONResponse:
    _cleanup_jobs()
    filename = file.filename or ""
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Ожидается ZIP-архив")
    payload = await file.read(MAX_ARCHIVE_BYTES + 1)
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise HTTPException(status_code=413, detail="Архив слишком большой")

    job_id = uuid.uuid4().hex
    work_dir = _TEMP_ROOT / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "input.zip").write_bytes(payload)
    _jobs[job_id] = Job(id=job_id, work_dir=work_dir)

    thread = threading.Thread(target=_process_job, args=(job_id,), daemon=True)
    thread.start()
    return JSONResponse({"job_id": job_id, "status": "queued"}, status_code=202)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    _cleanup_jobs()
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    return {
        "job_id": job.id,
        "status": job.status,
        "message": job.message,
        "current": job.current,
        "total": job.total,
        "logs": job.logs,
        "error": job.error,
        "has_result": job.result_path is not None and job.result_path.is_file(),
    }


@app.get("/api/jobs/{job_id}/result")
def get_result(job_id: str) -> FileResponse:
    _cleanup_jobs()
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    if job.result_path is None or not job.result_path.is_file():
        raise HTTPException(status_code=409, detail="Результат ещё не готов")
    return FileResponse(job.result_path, filename="html2doc-result.zip", media_type="application/zip")
