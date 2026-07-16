# Essentia Studio

Essentia Studio is the in-progress web successor to the Essentia Music Tagger: a local FastAPI/React application for reviewing genre and mood analysis, selectively writing approved tags, and managing Navidrome smart playlists.

The first release targets a trusted local network without authentication. Music enters through a read/write container mount at `/music`; application state lives under `/data`. The default image runs analysis on CPU, while a separate NVIDIA CUDA image is planned for compatible Linux and Windows/WSL2 hosts.

## Current development status

The cross-platform application foundation is available on the `feature/essentia-studio` branch. Analysis, safe tag writing, undo, complete smart-playlist integration, and delivery images are implemented in the subsequent roadmap stages.

- [Approved product design](docs/superpowers/specs/2026-07-16-essentia-studio-design.md)
- [Implementation roadmap](docs/superpowers/plans/2026-07-16-essentia-studio-roadmap.md)
- [Development on macOS, Windows, WSL2, and Linux](docs/development.md)
- [Contributor and AI-agent contract](AGENTS.md)

To run the current source checks:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
npm --prefix frontend install
python scripts/verify.py
python scripts/dev.py all
```

Open `http://localhost:5173` for development. See [docs/development.md](docs/development.md) for PowerShell commands and local path configuration.

## Legacy CLI: Essentia Music Tagger

The original command-line application remains present while its tested analysis and tagging behavior is extracted into the web architecture.

**Intelligent audio analysis and automatic genre/mood tagging for your music library**

Analyze your music collection using machine learning and write accurate genre and mood tags directly to your audio files. No internet required - all processing happens locally using [Essentia](https://essentia.upf.edu/), an advanced audio analysis library from the Music Technology Group.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Essentia](https://img.shields.io/badge/Essentia-2.1b6-green.svg)](https://essentia.upf.edu/)
 
---

## ✨ Features

- 🎯 **Audio-based analysis** - Analyzes actual audio content, not metadata lookups
- 🎼 **400 genre classifications** - Uses Discogs taxonomy for detailed genre tagging
- 😊 **Mood detection** - Detects moods like energetic, dark, happy, aggressive, etc.
- 🎚️ **Analysis mode selection** - Choose genres only, moods only, or both per run
- � **Default library path** - Save your library root; browse it with an arrow-key folder navigator on every run
- �🔄 **Batch processing** - Recursively process entire music libraries
- 🎛️ **Fully configurable** - Interactive prompts for all settings on each run
- 📝 **Comprehensive logging** - Detailed logs with confidence scores and predictions
- 🏷️ **Multiple tag formats** - Choose how genre tags are formatted
- 💾 **Wide format support** - Writes tags to FLAC, MP3, OGG, Opus, M4A/MP4, AAC, WMA, AIFF, WAV, WavPack, APE, Musepack, and DSF
- 🧪 **Dry run mode** - Test before making changes
- 🚀 **CPU-only** - No GPU required (though it helps!)
- 🐳 **Docker support** - Run with Docker, with optional GPU acceleration
- 🤖 **Automation support** - CLI arguments for scripted/automated workflows
- 🔄 **Picard integration** - Auto-tag files saved by MusicBrainz Picard.

---

## 🎵 How It Works

Unlike tools like MusicBrainz Picard or beets that look up metadata from online databases, **Essentia Music Tagger analyzes the actual audio waveform** using deep learning models:

1. **Loads audio** - Reads your music files
2. **Extracts features** - Analyzes spectral, tonal, and rhythmic characteristics
3. **Runs ML models** - Pre-trained neural networks predict genres and moods
4. **Writes tags** - Saves predictions to your music files

**No internet connection required after initial setup!**

### Example Predictions

**Input:** Alternative rock track  
**Output:**

🎸 Genres: Rock - Alternative Rock (32%), Rock - Indie Rock (23%), Rock - Brit Pop (22%) 😊 Moods: Energetic (2.3%), Dark (1.8%)

Tags written:

- `GENRE`: `Rock - Alternative Rock; Rock - Indie Rock; Rock - Brit Pop`
- `MOOD`: `Energetic; Dark`

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Linux** (Debian/Ubuntu recommended, also works on macOS)
- **~100MB disk space** for models
- **8GB+ RAM** recommended

### Installation

```bash
# 1. Clone the repository
cd /srv/dev-disk-by-uuid-dc4918d5-6597-465b-9567-ce442fbd8e2a/Github
git clone https://github.com/WB2024/Essentia-to-Metadata.git
cd Essentia-to-Metadata

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install essentia-tensorflow mutagen numpy

# 4. Download ML models (~87MB)
bash download_models.sh
```

### First Run

# Run the script

python tag_music.py

You'll be prompted for:

- 📂 **Music directory** to analyze
- 🎸 **Number of genres** to tag (1-10)
- 📊 **Confidence thresholds** for genre/mood
- 🎨 **Tag formatting** style
- 🧪 **Dry run mode** (test first!)
- And more...

**Recommendation:** Run in dry-run mode first to preview results!

---
## 🐳 Docker

### CPU mode

```bash
# Build the image
docker compose build essentia-tagger

# Process a music directory
MUSIC_DIR=/path/to/music docker compose run --rm essentia-tagger

# Dry run
MUSIC_DIR=/path/to/music docker compose run --rm essentia-tagger /music --auto --dry-run

# Process a single file
MUSIC_DIR=/path/to/music docker compose run --rm essentia-tagger /music/song.flac --auto --single-file
```

### GPU mode (NVIDIA)

Requires the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed on the host. Uses a dedicated `Dockerfile.gpu` based on `nvidia/cuda` with CUDA 11.2 + cuDNN 8 for actual GPU acceleration.

```bash
# Build the GPU image
docker compose build essentia-tagger-gpu

# Process with GPU acceleration
MUSIC_DIR=/path/to/music docker compose run --rm essentia-tagger-gpu
```

If no GPU is available on the host, use the CPU profile instead.

---

## 🤖 Command Line / Automation Mode

For scripting or integration with other tools, use CLI arguments:

```bash
# Basic automated mode
python tag_music.py /path/to/music --auto

# Process a single file (e.g., from a file watcher)
python tag_music.py /path/to/song.flac --auto --single-file

# Custom settings
python tag_music.py /path/to/music --auto \
    --genres 4 \
    --genre-threshold 20 \
    --mood-threshold 1 \
    --genre-format child_only \
    --overwrite

# Dry run for testing
python tag_music.py /path/to/music --auto --dry-run
```

### CLI Arguments Reference

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `--auto` | `-a` | Non-interactive mode | - |
| `--single-file` | `-f` | Process single file | - |
| `--genres N` | `-g` | Number of genres | 3 |
| `--genre-threshold PCT` | `-gt` | Genre confidence % | 15 |
| `--genre-format STYLE` | `-gf` | Format style | parent_child |
| `--no-genres` | - | Disable genre analysis | - |
| `--no-moods` | - | Disable mood analysis | - |
| `--mood-threshold PCT` | `-mt` | Mood confidence % | 0.5 |
| `--dry-run` | `-d` | Don't write tags | - |
| `--overwrite` | `-o` | Overwrite existing tags | - |
| `--quiet` | `-q` | Minimal output | - |
| `--log-dir DIR` | - | Log file directory | ./ |
| `--model-dir DIR` | - | Essentia models directory | ~/essentia_models |
| `--library DIR` | - | Set & save default library path | - |

> **Note:** `--no-genres` and `--no-moods` cannot be used together — at least one analysis type must be enabled.

> **Tip:** Use `--library /path/to/library` once to save your library root. It is stored in `~/.essentia_tagger.json` and used automatically in future interactive runs.

---

## 🎵 MusicBrainz Picard Automation

Automatically tag files whenever Picard saves them! Perfect for server setups.

See **[PICARD_AUTOMATION_SETUP.md](PICARD_AUTOMATION_SETUP.md)** for complete setup instructions.

**How it works:**
1. Picard (in Docker) saves files to your music directory
2. A file watcher (systemd service) detects new files
3. Essentia analyzes and tags the files automatically

**Included files for automation:**
- `essentia_watcher.sh` - File watcher script using inotifywait
- `essentia-tagger.service` - Systemd service file

---
## 📖 Detailed Usage

### Interactive Configuration

Every run prompts you to configure:

#### Default Library Path

The first setting lets you define (or update) a **default music library root path**, saved persistently to `~/.essentia_tagger.json`.

Once set, every subsequent run begins with a path selection menu:

| Option | Description |
|--------|-------------|
| **1. Scan entire library** (default) | Recursively scan from the library root |
| **2. Browse & select a folder** | Open the interactive folder browser to pick a sub-folder |
| **3. Enter a custom path** | Type a path manually (original behaviour) |

#### Interactive Folder Browser

Option 2 opens a full-screen CLI folder navigator:

```
   📂 Browsing: /2Pac
   📍 Full path: /srv/.../Music/Sources/Clean/2Pac
   Use ↑↓ arrows to navigate, Enter to select, 'q' to cancel
   ──────────────────────────────────────────────────
   ▶ ✅ SELECT THIS FOLDER
     ⬆️  ../ (go up)
     📁 [1994] Me Against the World
     📁 [1996] All Eyez on Me
     📁 [1996] The Don Killuminati
```

| Key | Action |
|-----|--------|
| ↑ / ↓ | Move selection up/down |
| Enter | Select folder or navigate into it |
| Backspace | Go up one directory |
| q | Cancel and return to path selection |

#### Analysis Mode

Choose what to analyse for each run:

| Option | Description |
|--------|-------------|
| **1. Both** (default) | Analyse and write both genre and mood tags |
| **2. Genres only** | Run only the genre model; skip mood analysis entirely |
| **3. Moods only** | Run only the mood model; skip genre analysis entirely |

Only the models that are needed are loaded, saving memory and time when running in a single-mode.

#### Genre Settings *(shown when mode is Both or Genres only)*

- **Number of genres** (1-10) - How many genre tags per song
- **Confidence threshold** (1-50%) - Minimum prediction confidence
- **Format style**:
  - `Rock - Alternative Rock` (parent - child) ← default
  - `Alternative Rock - Rock` (child - parent)
  - `Alternative Rock` (child only)
  - `Rock---Alternative Rock` (raw)

#### Mood Settings *(shown when mode is Both or Moods only)*

- **Confidence threshold** (0.1-20%) - Moods have lower confidence than genres

#### Other Options

- **Dry run mode** - Test without writing tags
- **Confidence tags** - Write detailed scores to custom tags
- **Overwrite existing** - Skip or replace existing genre/mood tags independently
- **Verbose output** - Show detailed predictions

### Example Session

$ python tag_music.py

🎸 ESSENTIA MUSIC TAGGER - INTERACTIVE MODE
══════════════════════════════════════════════════════════════════════

Enter the path to analyze: /music/2Pac

📂 Directory: /music/2Pac
🎵 Found ~45 audio files

⚙️  CONFIGURATION
──────────────────────────────────────────────────────────────────────
🧪 DRY RUN MODE
Enable dry run mode? [Y/n]: y

�️ ANALYSIS MODE
  1. Both genres and moods (default)
  2. Genres only
  3. Moods only
Select mode [1]: 1

🎸 GENRE SETTINGS
Number of genres to write [3]: 3
Genre threshold (%) [15]: 15
Genre format [1]: 1

😊 MOOD SETTINGS
Mood threshold (%) [0.5]: 0.5

🔄 Loading models...
✅ Models loaded successfully!

[1/45] 2Pac/Me Against the World/05 - Temptations.flac
     🎸 Raw: Hip-Hop---Gangsta (45.2%), Hip-Hop---East Coast Hip Hop (32.4%)
     🎸 Formatted: Hip-Hop - Gangsta, Hip-Hop - East Coast Hip Hop
     😊 Raw: energetic (2.3%), dark (1.8%)
     😊 Formatted: Energetic, Dark
     [DRY RUN] Would write: Genres: Hip-Hop - Gangsta, Hip-Hop - East Coast Hip Hop | Moods: Energetic, Dark

## 🎛️ Configuration Guide

### Confidence Thresholds

Understanding confidence scores:

**Genres:**

- Model predicts across **400 possible classes**
- Top prediction typically 15-40%
- **15% threshold** = balanced (recommended)
- **25% threshold** = strict (fewer genres)
- **5% threshold** = inclusive (more genres)

**Moods:**

- Naturally **much lower** than genres (0.1-5% range)
- **0.5% threshold** = good starting point
- **1-3%** = more selective

### Tag Formatting Examples

| Raw Prediction            | parent_child              | child_parent              | child_only         |
| ------------------------- | ------------------------- | ------------------------- | ------------------ |
| `Rock---Alternative Rock` | `Rock - Alternative Rock` | `Alternative Rock - Rock` | `Alternative Rock` |
| `Hip-Hop---Gangsta`       | `Hip-Hop - Gangsta`       | `Gangsta - Hip-Hop`       | `Gangsta`          |
| `Electronic---Techno`     | `Electronic - Techno`     | `Techno - Electronic`     | `Techno`           |

---

## 📁 Output

### Tags Written

Tags are written using the native tagging format for each container:

**FLAC / OGG Vorbis / OGG Opus** (Vorbis Comments):

- `GENRE` - Formatted genre tags (semicolon-separated)
- `MOOD` - Formatted mood tags (semicolon-separated)
- `ESSENTIA_GENRE` - Raw predictions with confidence scores (optional)
- `ESSENTIA_MOOD` - Raw mood predictions with scores (optional)

**MP3 / AIFF / WAV / DSF** (ID3v2):

- `TCON` (Genre) - Formatted genre tags
- `COMM` (Comment) - Confidence scores (optional)

**M4A / MP4 / AAC** (iTunes atoms):

- `©gen` - Formatted genre tags
- `©cmt` - Confidence scores (optional)
- `----:com.apple.iTunes:MOOD` - Mood tags (freeform atom)

**WMA** (ASF/Windows Media):

- `WM/Genre` - Formatted genre tags
- `WM/Mood` - Mood tags
- `WM/Provider` - Confidence scores (optional)

**WavPack / APE / Musepack** (APEv2):

- `Genre` - Formatted genre tags
- `Mood` - Mood tags
- `Essentia Genre` / `Essentia Mood` - Confidence scores (optional)

### Log Files

Each run creates a timestamped log: `essentia_tagger_YYYYMMDD_HHMMSS.log`

Example log content:

FILE: 2Pac/Me Against the World/05 - Temptations.flac
────────────────────────────────────────────────────────────────────────────
GENRES (raw predictions):
  • Hip-Hop---Gangsta: 45.23%
  • Hip-Hop---East Coast Hip Hop: 32.45%
  • Hip-Hop---Golden Age Hip Hop: 21.34%

GENRES (formatted for tags):
  • Hip-Hop - Gangsta
  • Hip-Hop - East Coast Hip Hop

ALL GENRE PREDICTIONS (top 10):
  • Hip-Hop---Gangsta: 45.23%
  • Hip-Hop---East Coast Hip Hop: 32.45%
  ...

MOODS (passed threshold - 2 total):
  • energetic: 2.34%
  • dark: 1.87%

## 🎓 Understanding the Models

### Genre Model: Discogs-400

- **Classes:** 400 genre/style categories from Discogs taxonomy
- **Architecture:** EfficientNet-based CNN
- **Training:** Supervised learning on Discogs-tagged releases
- **Strengths:** Very detailed genre classification
- **Example classes:** `Hip-Hop---Golden Age Hip Hop`, `Rock---Shoegaze`, `Electronic---Deep House`

### Mood Model: MTG-Jamendo

- **Classes:** Mood and theme tags (energetic, dark, happy, sad, etc.)
- **Architecture:** Multi-label classification
- **Training:** MTG-Jamendo dataset with crowd-sourced tags
- **Note:** Lower confidence than genres (this is normal!)

### Embedding Model: Discogs-Effnet

- **Purpose:** Extracts audio features for downstream tasks
- **Input:** 16kHz audio resampled from any format
- **Output:** High-dimensional embedding vectors

---

## ⚡ Performance

**Processing Speed** (CPU-only, Intel i3-4150T @ 3.00GHz):

- **~5-15 seconds** per track (varies by length and complexity)
- **~500 tracks** = 2-4 hours
- **~2000 tracks** = 8-16 hours

**Tips for faster processing:**

- Use newer/faster CPU
- Process in batches by artist/album
- Run overnight for large libraries
- GPU support (if available) can 10x speed

**Memory Usage:**

- **~2-3GB RAM** during processing
- Models loaded once, reused for all files

---

## 🛠️ Troubleshooting

### "Could not load model" errors

- Ensure models are downloaded: `bash download_models.sh`
- Check `~/essentia_models/` contains `.pb` and `.json` files

### "No moods above threshold"

- Moods have very low confidence (0.1-5%)
- Try lowering mood threshold to 0.3% or 0.1%
- Check log file for raw mood predictions

### TensorFlow warnings

Could not load dynamic library 'libcudart.so.11.0'

- **Safe to ignore** - means no GPU, will use CPU
- Performance is still good on CPU

### Out of memory

- Reduce batch processing
- Close other applications
- Upgrade RAM if processing very large files

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Ideas for contributions:

- GUI interface
- Progress bars
- Resume/checkpoint system for interrupted runs
- Custom model support
- Genre mapping/translation tables
- ALAC (Apple Lossless) support

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/copilot/c/LICENSE) file for details.

**Note:** Essentia library itself is licensed under AGPL-3.0. Pre-trained models from MTG are available under CC BY-NC-ND 4.0 for non-commercial use.

---

## 🙏 Credits

### Built With

- **[Essentia](https://essentia.upf.edu/)** - Audio analysis library by Music Technology Group
- **[Mutagen](https://mutagen.readthedocs.io/)** - Python library for audio metadata
- **[NumPy](https://numpy.org/)** - Numerical computing

### Models

Pre-trained models provided by:

- **[Music Technology Group (MTG)](https://www.upf.edu/web/mtg)** - Universitat Pompeu Fabra
- Trained on public datasets: Discogs, MTG-Jamendo, AcousticBrainz

### Inspiration

- [AcousticBrainz](https://acousticbrainz.org/) - Crowdsourced acoustic analysis
- [beets](https://beets.io/) - Music library management
- [MusicBrainz Picard](https://picard.musicbrainz.org/) - Music tagger

---

## 📚 Further Reading

- [Essentia Documentation](https://essentia.upf.edu/documentation.html)
- [MTG Models Repository](https://essentia.upf.edu/models.html)
- [Discogs Genre Taxonomy](https://www.discogs.com/help/doc/submission-guidelines-release-genres-styles)
- [Music Information Retrieval](https://musicinformationretrieval.com/)

---

## 💬 Support

- **Issues:** [GitHub Issues](https://github.com/WB2024/Essentia-to-Metadata/issues)
- **Discussions:** [GitHub Discussions](https://github.com/WB2024/Essentia-to-Metadata/discussions)

---

## 🎶 Example Use Cases

### 1. Organize Your Music Library

Tag your entire collection with accurate genres for better browsing in music players.

### 2. DJ / Producer Workflow

Quickly find tracks by mood/energy for mixing and production.

### 3. Music Research

Analyze genre distributions in music collections.

### 4. Playlist Generation

Use mood tags to create dynamic playlists (energetic workout mixes, relaxing evening music, etc.).

---

## 📋 Changelog

### v2.0.0 (Latest)

#### New Features

- **Analysis mode selection** — New 3-way mode menu in interactive mode lets you choose to run genres only, moods only, or both. The corresponding ML models are only loaded when needed, reducing memory usage when running in single-mode. CLI equivalents: `--no-genres` and `--no-moods`.
- **Default library path & folder browser** — Set a default music library root path (saved to `~/.essentia_tagger.json`). On each interactive run you can scan the whole library, drill into a subfolder using an arrow-key folder browser, or type a custom path. No more copying and pasting long paths. CLI equivalent: `--library /path/to/library`.
- **Wide audio format support** — Tag writing now covers 12 audio container formats via native tag systems:
  - Vorbis Comments: FLAC, OGG Vorbis, OGG Opus
  - ID3v2: MP3, AIFF, WAV, DSF
  - iTunes atoms: M4A, MP4, AAC
  - ASF: WMA
  - APEv2: WavPack (`.wv`), Monkey's Audio (`.ape`), Musepack (`.mpc`)
- **Per-tag-type overwrite logic** — Genre and mood tags are now checked and potentially skipped independently. Previously, if a genre tag existed and overwrite was disabled the entire file was skipped, including moods.

#### Bug Fixes

- Fixed MP3 mood tags never being written when genres were disabled — mood writing was incorrectly nested inside the genres block.
- Fixed bare `except:` clause in MP3 tag writing replaced with `except Exception:` to avoid swallowing system exits and keyboard interrupts.
- Fixed `mood_threshold` config default mismatch — the internal default was `0.01` while the CLI help text advertised `0.5%` (0.005). Both are now consistently `0.005`.
- Removed unused imports (`re`, `from mutagen.mp3 import MP3`).

---

**Made with ❤️ for music lovers and data nerds**

*If this project helps you, consider ⭐ starring the repo!*
