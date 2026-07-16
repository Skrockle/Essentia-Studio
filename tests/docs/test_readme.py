from pathlib import Path


def test_readme_covers_required_deployments_and_licenses() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    for phrase in [
        "Apple Container",
        "Windows 11",
        "WSL2",
        "Docker Compose",
        "NVIDIA CUDA",
        "/music",
        "/data",
        "kein Login",
        "CC BY-NC-ND 4.0",
        "nichtkommerziell",
        "Navidrome Smart Playlists",
        "Tags wiederherstellen",
    ]:
        assert phrase in text
