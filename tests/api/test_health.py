from fastapi.testclient import TestClient

from essentia_studio.config import RuntimeConfig
from essentia_studio.main import create_app


def test_health_and_capabilities_report_missing_mount(tmp_path) -> None:
    config = RuntimeConfig.from_env(
        {
            "ESSENTIA_MUSIC_ROOT": str(tmp_path / "missing-music"),
            "ESSENTIA_DATA_DIR": str(tmp_path / "data"),
            "ESSENTIA_FRONTEND_DIR": str(tmp_path / "missing-dist"),
        }
    )

    with TestClient(create_app(config)) as client:
        assert client.get("/health").json() == {"status": "ok", "version": "0.0.0"}
        response = client.get("/api/capabilities")

    assert response.status_code == 200
    assert response.json()["music_root"]["status"] == "missing"
    assert response.json()["image_variant"] == "cpu"
