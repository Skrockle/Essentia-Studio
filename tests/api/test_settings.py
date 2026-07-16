def test_put_settings_rejects_cuda_in_cpu_image(client) -> None:
    response = client.put("/api/settings", json={"compute_preference": "cuda"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "compute_mode_unavailable"


def test_put_settings_merges_and_persists_partial_update(client) -> None:
    response = client.put("/api/settings", json={"worker_count": 4})

    assert response.status_code == 200
    assert response.json()["worker_count"] == 4
    assert response.json()["max_audio_seconds"] == 300
    assert client.get("/api/settings").json()["worker_count"] == 4
