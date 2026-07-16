import re
from pathlib import Path

import yaml

WORKFLOW_DIR = Path(".github/workflows")


def test_required_workflows_exist() -> None:
    for name in ["ci.yml", "gpu-smoke.yml", "release.yml"]:
        assert (WORKFLOW_DIR / name).is_file(), name


def test_actions_are_sha_pinned() -> None:
    for workflow in WORKFLOW_DIR.glob("*.yml"):
        for line in workflow.read_text(encoding="utf-8").splitlines():
            if "uses:" not in line or line.lstrip().startswith("#"):
                continue
            reference = line.split("uses:", 1)[1].strip()
            if reference.startswith("./"):
                continue
            assert re.search(r"@[0-9a-f]{40}(?:\s+#.*)?$", reference), (workflow, line)


def test_pull_request_jobs_have_read_only_permissions() -> None:
    workflow = yaml.safe_load((WORKFLOW_DIR / "ci.yml").read_text(encoding="utf-8"))
    assert workflow["permissions"] == {"contents": "read"}
    assert "packages: write" not in (WORKFLOW_DIR / "ci.yml").read_text(encoding="utf-8")


def test_source_matrix_covers_supported_development_hosts() -> None:
    text = (WORKFLOW_DIR / "ci.yml").read_text(encoding="utf-8")
    for runner in ["ubuntu-latest", "macos-latest", "windows-latest"]:
        assert runner in text


def test_release_workflow_publishes_all_required_tags() -> None:
    text = (WORKFLOW_DIR / "release.yml").read_text(encoding="utf-8")
    for tag in [
        "latest",
        "latest-cpu",
        "latest-cuda",
        "${{ needs.release.outputs.tag_name }}",
        "${{ needs.release.outputs.tag_name }}-cpu",
        "${{ needs.release.outputs.tag_name }}-cuda",
    ]:
        assert tag in text
    assert "release_created" in text
    assert "packages: write" in text
    assert "provenance: mode=max" in text
    assert "sbom: true" in text
