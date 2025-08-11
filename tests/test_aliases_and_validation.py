import time
from pathlib import Path
import os, sys

sys.path.append(os.getcwd())

from PIL import Image

from MOTEUR.scraping.server.flask_server import FlaskBridgeServer


def _make_image(path: Path) -> None:
    img = Image.new("RGB", (10, 10), "red")
    img.save(path)


def test_aliases_and_image_edit(tmp_path):
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    _make_image(img_dir / "a.png")

    srv = FlaskBridgeServer()
    srv.api_key = "k"
    client = srv.app.test_client()

    resp = client.get("/aliases", headers={"X-API-KEY": "k"})
    assert resp.status_code == 200
    assert resp.get_json() == {"sample_folder": ""}

    resp = client.post(
        "/aliases",
        json={"sample_folder": str(img_dir)},
        headers={"X-API-KEY": "k"},
    )
    assert resp.status_code == 200

    payload = {
        "source": {"folder": "sample_folder"},
        "operations": [{"op": "resize", "width": 5, "height": 5}],
    }
    resp = client.post(
        "/actions/image-edit", json=payload, headers={"X-API-KEY": "k"}
    )
    assert resp.status_code == 202
    job_id = resp.get_json()["job_id"]

    for _ in range(30):
        data = client.get(
            f"/jobs/{job_id}", headers={"X-API-KEY": "k"}
        ).get_json()
        if data["status"] in {"done", "error"}:
            break
        time.sleep(0.1)
    assert data["status"] == "done"
    assert data["progress"]["downloaded"] == 1


def test_image_edit_validation_errors(tmp_path):
    srv = FlaskBridgeServer()
    srv.api_key = "k"
    client = srv.app.test_client()

    payload = {
        "source": {"folder": str(tmp_path / "missing")},
        "operations": [{"op": "resize", "width": 5, "height": 5}],
    }
    resp = client.post(
        "/actions/image-edit", json=payload, headers={"X-API-KEY": "k"}
    )
    assert resp.status_code == 400
    assert "source not found" in resp.get_json()["detail"]

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    payload["source"] = {"folder": str(empty_dir)}
    resp = client.post(
        "/actions/image-edit", json=payload, headers={"X-API-KEY": "k"}
    )
    assert resp.status_code == 400
    assert "no images" in resp.get_json()["detail"]

    payload["source"] = {"folder": ""}
    resp = client.post(
        "/actions/image-edit", json=payload, headers={"X-API-KEY": "k"}
    )
    assert resp.status_code == 400
    assert resp.get_json()["detail"] == "source.folder is empty"
