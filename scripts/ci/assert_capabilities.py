"""Assert a container capability response in CI."""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("response", type=Path)
    parser.add_argument("--variant", choices=["cpu", "cuda"], required=True)
    parser.add_argument("--compute", choices=["cpu", "cuda"], required=True)
    arguments = parser.parse_args()
    capabilities = json.loads(arguments.response.read_text(encoding="utf-8"))
    assert capabilities["image_variant"] == arguments.variant
    assert capabilities["available_compute"] == [arguments.compute]
    assert all(model["status"] == "ready" for model in capabilities["models"])


if __name__ == "__main__":
    main()
