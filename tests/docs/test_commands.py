from pathlib import Path

import yaml


def test_default_compose_uses_cpu_image_and_required_mounts() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    service = compose["services"]["essentia-studio"]
    assert service["image"].endswith(":latest-cpu")
    assert "${MUSIC_DIR}:/music" in service["volumes"]
    assert "${DATA_DIR}:/data" in service["volumes"]
    assert "gpus" not in service


def test_cuda_compose_is_explicit() -> None:
    compose = yaml.safe_load(Path("compose.cuda.yml").read_text(encoding="utf-8"))
    service = compose["services"]["essentia-studio"]
    assert service["image"].endswith(":latest-cuda")
    assert service["gpus"] == "all"


def test_windows_docs_include_wsl_and_powershell_paths() -> None:
    text = Path("docs/deployment/windows.md").read_text(encoding="utf-8")
    assert "wsl --update" in text
    assert "$env:MUSIC_DIR" in text
    assert "--gpus all" in text
