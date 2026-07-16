from datetime import datetime, timezone

import pytest

from essentia_studio.domain.analysis import AnalysisResult, Prediction
from essentia_studio.domain.tracks import ScannedTrack, TrackFingerprint


@pytest.fixture
def seeded_results(client):
    tracks = client.app.state.track_repository
    results = client.app.state.result_repository
    scanned = [
        ScannedTrack(
            f"Artist/song-{index:02}.flac",
            ".flac",
            TrackFingerprint(size=index + 1, mtime_ns=index + 100),
        )
        for index in range(63)
    ]
    tracks.replace_scan(scanned, datetime.now(timezone.utc))
    result_ids = []
    for track in scanned:
        stored = results.save(
            tracks.get_by_path(track.relative_path),
            AnalysisResult(
                genres=[Prediction("Electronic---House", 0.9)],
                moods=[Prediction("moodtheme---happy", 0.8)],
            ),
            ["Electronic; House"],
            ["Happy"],
        )
        result_ids.append(stored.id)
    return result_ids


def test_query_selection_selects_all_matching_rows_not_only_page(client, seeded_results) -> None:
    response = client.post(
        "/api/results/selection",
        json={
            "selection": {
                "mode": "query",
                "query": {"mood": "Happy"},
                "excluded_ids": [],
            },
            "selected": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"affected": 63}
    page = client.get("/api/results", params={"mood": "Happy", "page_size": 20}).json()
    assert page["total"] == 63
    assert page["selected_count"] == 63
    assert len(page["items"]) == 20


def test_patch_draft_normalizes_manual_tags(client, seeded_results) -> None:
    response = client.patch(
        f"/api/results/{seeded_results[0]}/draft",
        json={"genres": [" House ", "house", "Ambient"], "moods": ["Calm"]},
    )

    assert response.status_code == 200
    assert response.json()["draft"]["genres"] == ["House", "Ambient"]


def test_bulk_add_genre_changes_only_selected_drafts(client, seeded_results) -> None:
    response = client.post(
        "/api/results/bulk-draft",
        json={
            "selection": {"mode": "ids", "ids": seeded_results[:2]},
            "operation": "add_genre",
            "value": "Ambient",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"affected": 2}
    first = client.get("/api/results", params={"genre": "Ambient"}).json()
    assert first["total"] == 2
