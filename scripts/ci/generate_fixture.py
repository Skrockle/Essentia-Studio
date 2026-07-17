"""Create a deterministic mono WAV fixture for container smoke tests."""

import argparse
import math
import struct
import wave
from pathlib import Path


def write_tone(path: Path, seconds: int = 10) -> None:
    sample_rate = 16_000
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        for index in range(sample_rate * seconds):
            sample = int(12_000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            audio.writeframesraw(struct.pack("<h", sample))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--seconds", type=int, default=10)
    arguments = parser.parse_args()
    write_tone(arguments.output, arguments.seconds)


if __name__ == "__main__":
    main()
