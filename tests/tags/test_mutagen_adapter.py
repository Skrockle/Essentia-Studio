from mutagen.id3 import ID3

from essentia_studio.tags.mutagen_adapter import MutagenTagAdapter


class AudioDouble:
    def __init__(self, tags) -> None:
        self.tags = tags


def test_id3_managed_fields_replace_and_restore_exact_values() -> None:
    adapter = MutagenTagAdapter()
    audio = AudioDouble(ID3())
    original = {
        "genres": ["Rock"],
        "moods": [],
        "genre_confidence": ["Rock=0.8"],
        "mood_confidence": [],
    }

    adapter._replace_fields(audio, "id3", original)
    snapshot = adapter._read_fields(audio, "id3")
    adapter._replace_fields(
        audio,
        "id3",
        {
            "genres": ["Ambient"],
            "moods": ["Calm"],
            "genre_confidence": [],
            "mood_confidence": [],
        },
    )
    adapter._replace_fields(audio, "id3", snapshot)

    assert adapter._read_fields(audio, "id3") == original


def test_format_families_use_the_documented_managed_keys() -> None:
    adapter = MutagenTagAdapter()

    assert adapter._mapping("vorbis")["moods"] == "MOOD"
    assert adapter._mapping("mp4")["genres"] == "\xa9gen"
    assert adapter._mapping("asf")["moods"] == "WM/Mood"
    assert adapter._mapping("apev2")["genre_confidence"] == "Essentia Genre"
    assert adapter._encode_values(["Ambient"], "mp4", "\xa9gen") == ["Ambient"]
    assert adapter._encode_values(
        ["Calm"], "mp4", "----:com.apple.iTunes:MOOD"
    ) == [b"Calm"]
