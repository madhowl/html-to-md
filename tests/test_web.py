from __future__ import annotations

import io
import time
import zipfile

from fastapi.testclient import TestClient

from html2doc.web.app import app

client = TestClient(app)


def _post_archive(files: dict[str, tuple[str, bytes, str]]) -> str:
    response = client.post("/api/jobs", files=files)
    assert response.status_code == 202, response.text
    return response.json()["job_id"]


def _wait(job_id: str) -> dict[str, object]:
    for _ in range(200):
        status = client.get(f"/api/jobs/{job_id}").json()
        if status["status"] in {"done", "error"}:
            return status
        time.sleep(0.1)
    raise AssertionError("Задание не завершилось вовремя")


def test_web_upload_returns_zip_with_all_formats() -> None:
    buffer = io.BytesIO()
    markup = "<html><body><h1>Веб</h1><p>Текст</p></body></html>"
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("веб.htm", markup)
    job_id = _post_archive({"file": ("lectures.zip", buffer.getvalue(), "application/zip")})

    status = _wait(job_id)
    assert status["status"] == "done", status

    response = client.get(f"/api/jobs/{job_id}/result")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        names = zf.namelist()
    assert any(name.endswith("веб.md") for name in names)
    assert any(name.endswith("веб.pdf") for name in names)
    assert any(name.endswith("веб.docx") for name in names)
    assert any(name.endswith("conversion-report.json") for name in names)


def test_web_rejects_path_traversal() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("../evil.htm", "<html><body><p>x</p></body></html>")
    job_id = _post_archive({"file": ("evil.zip", buffer.getvalue(), "application/zip")})

    status = _wait(job_id)
    assert status["status"] == "error"
    assert "Недопустимый путь" in str(status["error"])
