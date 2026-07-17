def test_put_settings_rejects_cuda_in_cpu_image(client) -> None:
    response = client.put("/api/settings", json={"analysis": {"compute": "cuda"}})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "compute_mode_unavailable"


def test_put_settings_merges_and_persists_partial_update(client) -> None:
    response = client.put("/api/settings", json={"analysis": {"workers": 4}})

    assert response.status_code == 200
    assert response.json()["values"]["analysis"]["workers"] == 4
    assert response.json()["values"]["analysis"]["max_audio_seconds"] == 300
    assert response.json()["sources"]["analysis.workers"] == "file"
    assert client.get("/api/settings").json()["values"]["analysis"]["workers"] == 4
