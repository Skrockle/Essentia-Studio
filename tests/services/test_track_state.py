import pytest

from essentia_studio.services.track_state import derive_processing_state


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        ({}, "new"),
        ({"analysis_exists": True, "analysis_matches": True}, "current"),
        ({"analysis_exists": True, "analysis_matches": False}, "changed"),
        (
            {
                "analysis_exists": True,
                "analysis_matches": False,
                "verified_write_matches": True,
            },
            "written",
        ),
        ({"latest_attempt_failed": True}, "failed"),
        (
            {
                "analysis_exists": True,
                "analysis_matches": True,
                "latest_attempt_failed": True,
            },
            "failed",
        ),
    ],
)
def test_processing_state_precedence(facts, expected) -> None:
    assert derive_processing_state(**facts) == expected
