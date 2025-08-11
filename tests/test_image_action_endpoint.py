import time
from pathlib import Path

from PIL import Image

from MOTEUR.scraping.server.flask_server import FlaskBridgeServer


def _make_image(path: Path, color: str) -> None:
    img = Image.new("RGB", (10, 10), color)
    img.save(path)


def test_image_action_endpoint(tmp_path):
    _make_image(tmp_path / "a.png", "red")
    _make_image(tmp_path / "b.jpg", "blue")

    srv = FlaskBridgeServer()
    srv.api_key = "k"
    client = srv.app.test_client()

    payload = {
        "source": {"folder": str(tmp_path)},
        "operations": [{"op": "resize", "width": 5, "height": 5, "keep_ratio": True}],
        "target_subdir": "out",
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
    assert data["progress"]["downloaded"] == 2
    out_dir = Path(data["output_dir"])
    assert (out_dir / "a.png").exists()
    assert (out_dir / "b.jpg").exists()
