# Essentia Studio Platform Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the cross-platform FastAPI/React/SQLite application shell with settings, capability preflight, typed errors, migrations, and the approved studio navigation.

**Architecture:** A Python package under `backend/essentia_studio` owns configuration, database lifecycle, API routes, and production frontend serving. A Vite application under `frontend` talks to `/api`, while development commands remain runnable from POSIX shells, PowerShell, WSL2, and Apple Container hosts.

**Tech Stack:** Python 3.10, FastAPI 0.128.0, Pydantic 2, SQLAlchemy 2, pytest, React 19.2.7, TypeScript, Vite 8.1.5, Vitest, Testing Library, plain CSS design tokens.

## Global Constraints

- The product has no authentication and is intended only for a trusted local network.
- Python support is exactly `>=3.10,<3.11` because Essentia and the selected wheel are validated against Python 3.10.
- Runtime defaults are music root `/music`, data directory `/data`, database `/data/essentia-studio.db`, playlist directory `/music/SmartPlaylists`, and port `8000`.
- Client-visible paths are mount-relative POSIX paths; platform-native absolute paths stay server-side.
- The backend is importable and testable without Essentia installed; model dependencies enter only in the analysis plan and production image extras.
- Frontend copy is German; API identifiers and source code names are English.
- Source files use LF on every platform except explicit `.ps1`/`.cmd` launch helpers, which may use CRLF.
- `AGENTS.md` is canonical for humans and AI tools; hand-written Python/TypeScript complexity must not exceed 10 and every task ends by simplifying names, control flow, and module boundaries before commit.

---

## Planned file map

```text
backend/essentia_studio/
  __init__.py                 package version
  main.py                     application factory and production frontend mount
  config.py                   environment-backed immutable runtime paths
  errors.py                   typed application errors and FastAPI handler
  api/router.py               root API router
  api/routes/health.py        health and capability endpoints
  api/routes/settings.py      persisted setting endpoints
  db/engine.py                SQLite engine/session construction
  db/migrate.py               ordered SQL migration runner
  db/migrations/0001_core.sql initial settings schema
  repositories/settings.py    setting persistence boundary
  schemas/common.py           shared error and health response models
  schemas/settings.py         settings request/response models
  services/capabilities.py    filesystem/model/compute preflight
frontend/src/
  app/App.tsx                 route-free application shell
  api/client.ts               typed fetch wrapper
  api/types.ts                backend contract types
  components/AppNav.tsx       primary navigation
  features/settings/*         settings and about views
  styles/tokens.css           approved visual tokens
  styles/global.css           resets, layout, accessibility
scripts/dev.py                cross-platform backend/frontend launcher
tests/                        backend tests
frontend/src/**/*.test.tsx    frontend tests
```

### Task 0: Canonical human and AI collaboration guidance

**Files:**
- Create: `AGENTS.md`
- Create: `CLAUDE.md`
- Create: `GEMINI.md`
- Create: `.github/copilot-instructions.md`
- Create: `.cursor/rules/project.mdc`
- Create: `.windsurfrules`
- Create: `CONTRIBUTING.md`
- Create: `docs/architecture.md`
- Create: `tests/docs/test_agent_guidance.py`

**Interfaces:**
- Consumes: approved design and implementation roadmap.
- Produces: one canonical Codex/general collaboration contract and five thin tool-specific entry points with no duplicated rules.

- [ ] **Step 1: Write the failing canonical-source test**

```python
# tests/docs/test_agent_guidance.py
from pathlib import Path
import unittest


ENTRY_FILES = [
    "CLAUDE.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
    ".cursor/rules/project.mdc",
    ".windsurfrules",
]


class AgentGuidanceTest(unittest.TestCase):
    def test_every_ai_entry_points_to_canonical_contract_and_roadmap(self) -> None:
        self.assertTrue(Path("AGENTS.md").exists())
        for name in ENTRY_FILES:
            text = Path(name).read_text(encoding="utf-8")
            self.assertIn("AGENTS.md", text, name)
            self.assertIn(
                "docs/superpowers/plans/2026-07-16-essentia-studio-roadmap.md",
                text,
                name,
            )

    def test_canonical_contract_contains_safety_and_verification_sections(self) -> None:
        text = Path("AGENTS.md").read_text(encoding="utf-8")
        for heading in [
            "## Architecture",
            "## Safety invariants",
            "## Readability",
            "## Verification",
            "## Platform support",
        ]:
            self.assertIn(heading, text)
```

- [ ] **Step 2: Run the test and verify missing files fail**

Run: `python -m unittest discover -s tests/docs -p test_agent_guidance.py -v`

Expected: FAIL because repository-local `AGENTS.md` and adapters do not exist.

- [ ] **Step 3: Write the canonical `AGENTS.md` contract**

The file contains these exact top-level sections:

```markdown
# Essentia Studio Contributor Contract

## Start here
Read the approved design and current roadmap before editing. Work from the current repository state, preserve unrelated changes, and keep the task checklist current.

## Architecture
The product is a modular FastAPI/React/SQLite monolith. Analysis is read-only; tag writing, playlists, persistence, and HTTP routes communicate through explicit service interfaces.

## Safety invariants
Resolve all media paths beneath the configured music root. Never write tags during analysis. Require an explicit selection and preview before writes. Verify managed tags after writes and fingerprints before undo. Serialize filesystem mutations.

## Readability
Prefer descriptive domain names and direct control flow. Keep one responsibility per module. Cyclomatic complexity may not exceed 10. Remove unnecessary wrappers and comments that merely restate code. Explain non-obvious safety decisions with concise comments.

## Platform support
Development must work on macOS with Apple Container, Windows 11 with PowerShell or Docker Desktop/WSL2, and Linux. Use pathlib and subprocess argument lists; do not depend on Bash for core development commands.

## Verification
Run `python scripts/verify.py` for the source gate. Run focused tests before the full gate. Container, browser, playlist-parity, and real CUDA checks are required when their corresponding files change.

## Git and scope
Use Conventional Commits. Do not force-push, rewrite user changes, commit secrets, or edit vendored/generated files by hand. Keep `upstream` read-only and reserve `origin` for the private repository.
```

Add a repository map and links to the design, roadmap, four plans, development guide, deployment guides, and licensing guide beneath these sections. Do not copy machine-specific global instructions into the repository.

- [ ] **Step 4: Add thin adapters and human guidance**

Each adapter is at most 12 nonblank lines. Its tool-specific front matter may identify scope, then it says to read root `AGENTS.md`, the roadmap, and the active plan before editing. Cursor uses `alwaysApply: true` front matter. Copilot uses a repository-wide instruction file. `CONTRIBUTING.md` explains the same design → plan → failing test → implementation → focused test → readability review → full verification → Conventional Commit workflow in human-facing language. `docs/architecture.md` contains the module dependency diagram and points to the design for normative requirements.

- [ ] **Step 5: Verify guidance, review duplication, and commit**

Run:

```bash
python -m unittest discover -s tests/docs -p test_agent_guidance.py -v
rg -n "Safety invariants|Cyclomatic complexity" CLAUDE.md GEMINI.md .github/copilot-instructions.md .cursor/rules/project.mdc .windsurfrules
```

Expected: tests PASS; the second command returns no matches because detailed rules exist only in `AGENTS.md`.

Readability review: confirm a new contributor can find architecture, safety, commands, and the active plan from any entry file without encountering duplicated or contradictory rules.

Commit:

```bash
git add AGENTS.md CLAUDE.md GEMINI.md .github/copilot-instructions.md .cursor/rules/project.mdc .windsurfrules CONTRIBUTING.md docs/architecture.md tests/docs/test_agent_guidance.py
git commit -m "docs: add multi-agent contributor guidance"
```

### Task 1: Repository hygiene and executable project skeleton

**Files:**
- Modify: `.gitignore`
- Create: `.gitattributes`
- Create: `pyproject.toml`
- Create: `backend/essentia_studio/__init__.py`
- Create: `backend/essentia_studio/config.py`
- Create: `tests/test_config.py`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/eslint.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/vite-env.d.ts`

**Interfaces:**
- Consumes: no project-local interface.
- Produces: `RuntimeConfig.from_env(env: Mapping[str, str] | None = None) -> RuntimeConfig`; importable Python and Node workspaces.

- [ ] **Step 1: Write the failing runtime-default test**

```python
# tests/test_config.py
from pathlib import Path

from essentia_studio.config import RuntimeConfig


def test_runtime_config_uses_container_defaults() -> None:
    config = RuntimeConfig.from_env({})

    assert config.music_root == Path("/music")
    assert config.data_dir == Path("/data")
    assert config.database_path == Path("/data/essentia-studio.db")
    assert config.playlist_dir == Path("/music/SmartPlaylists")
    assert config.host == "0.0.0.0"
    assert config.port == 8000
```

- [ ] **Step 2: Create the package metadata and verify the test fails at import**

```toml
# pyproject.toml
[build-system]
requires = ["hatchling>=1.27,<2"]
build-backend = "hatchling.build"

[project]
name = "essentia-studio"
version = "0.0.0"
requires-python = ">=3.10,<3.11"
dependencies = [
  "fastapi==0.128.0",
  "pydantic>=2.12,<3",
  "sqlalchemy>=2.0.46,<2.1",
  "uvicorn[standard]>=0.40,<0.41",
]

[project.optional-dependencies]
dev = [
  "httpx>=0.28,<0.29",
  "pytest>=9.0,<10",
  "pytest-cov>=7.0,<8",
  "pyyaml>=6.0,<7",
  "ruff>=0.15,<0.16",
  "yamllint>=1.37,<2",
]

[tool.hatch.build.targets.wheel]
packages = ["backend/essentia_studio"]

[tool.pytest.ini_options]
pythonpath = ["backend"]
testpaths = ["tests"]
markers = ["model: requires the installed Essentia models"]

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "C90"]

[tool.ruff.lint.mccabe]
max-complexity = 10
```

Run: `python -m pytest tests/test_config.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'essentia_studio.config'`.

- [ ] **Step 3: Implement immutable environment configuration**

```python
# backend/essentia_studio/config.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import os


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    music_root: Path
    data_dir: Path
    database_path: Path
    playlist_dir: Path
    frontend_dir: Path
    host: str
    port: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "RuntimeConfig":
        values = os.environ if env is None else env
        music_root = Path(values.get("ESSENTIA_MUSIC_ROOT", "/music"))
        data_dir = Path(values.get("ESSENTIA_DATA_DIR", "/data"))
        return cls(
            music_root=music_root,
            data_dir=data_dir,
            database_path=Path(
                values.get("ESSENTIA_DATABASE_PATH", str(data_dir / "essentia-studio.db"))
            ),
            playlist_dir=Path(
                values.get("ESSENTIA_PLAYLIST_DIR", str(music_root / "SmartPlaylists"))
            ),
            frontend_dir=Path(values.get("ESSENTIA_FRONTEND_DIR", "frontend/dist")),
            host=values.get("ESSENTIA_HOST", "0.0.0.0"),
            port=int(values.get("ESSENTIA_PORT", "8000")),
        )
```

```python
# backend/essentia_studio/__init__.py
__version__ = "0.0.0"
```

- [ ] **Step 4: Add cross-platform Git and frontend configuration**

```gitattributes
# .gitattributes
* text=auto
*.py text eol=lf
*.ts text eol=lf
*.tsx text eol=lf
*.css text eol=lf
*.html text eol=lf
*.json text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
Dockerfile* text eol=lf
*.sh text eol=lf
*.nsp text eol=lf
*.ps1 text eol=crlf
*.cmd text eol=crlf
```

```json
{
  "name": "essentia-studio-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "engines": { "node": ">=24 <25" },
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "tsc -b && vite build",
    "test": "vitest run",
    "e2e": "playwright test",
    "typecheck": "tsc -b --pretty false",
    "lint": "eslint ."
  },
  "dependencies": {
    "react": "19.2.7",
    "react-dom": "19.2.7",
    "lucide-react": "1.24.0"
  },
  "devDependencies": {
    "@eslint/js": "10.0.1",
    "@playwright/test": "1.61.1",
    "@testing-library/jest-dom": "6.9.1",
    "@testing-library/react": "16.3.2",
    "@testing-library/user-event": "14.6.1",
    "@types/node": "24.13.3",
    "@types/react": "19.2.17",
    "@types/react-dom": "19.2.3",
    "@vitejs/plugin-react": "6.0.3",
    "eslint": "10.7.0",
    "eslint-plugin-react-hooks": "7.1.1",
    "eslint-plugin-react-refresh": "0.5.3",
    "globals": "17.7.0",
    "jsdom": "29.1.1",
    "typescript": "6.0.3",
    "typescript-eslint": "8.64.0",
    "vite": "8.1.5",
    "vitest": "4.1.10"
  }
}
```

Create the TypeScript and Vite configuration exactly as follows:

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
```

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
    "target": "ES2023",
    "lib": ["ES2023"],
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "types": ["node"],
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "skipLibCheck": true,
    "strict": true
  },
  "include": ["vite.config.ts", "vitest.config.ts", "eslint.config.js"]
}
```

```typescript
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:8000' } },
  },
})
```

```typescript
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    restoreMocks: true,
  },
})
```

Create `frontend/src/vite-env.d.ts` containing `/// <reference types="vite/client" />` and use this exact flat ESLint configuration:

```javascript
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'coverage'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { ecmaVersion: 2023, globals: globals.browser },
    plugins: { 'react-hooks': reactHooks, 'react-refresh': reactRefresh },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      complexity: ['error', 10],
    },
  },
)
```

Create `frontend/index.html` as:

```html
<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Essentia Studio</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Update `.gitignore` by replacing the global `*.json` rule with `essentia_models/*.json`, then add `.memsearch/`, `.superdesign/`, `.superpowers/`, `frontend/node_modules/`, `frontend/dist/`, `.pytest_cache/`, `.ruff_cache/`, `coverage/`, and `*.db*`.

- [ ] **Step 5: Install, test, and commit the skeleton**

Run:

```bash
python -m pip install -e ".[dev]"
python -m pytest tests/test_config.py -q
npm --prefix frontend install
npm --prefix frontend run typecheck
```

Expected: config test PASS; npm lockfile created; TypeScript exits 0 with `src/vite-env.d.ts` as the initial source input.

Commit:

```bash
git add .gitattributes .gitignore pyproject.toml backend frontend tests/test_config.py
git commit -m "feat: scaffold cross-platform application"
```

### Task 2: SQLite engine, ordered migrations, and persisted settings

**Files:**
- Create: `backend/essentia_studio/db/engine.py`
- Create: `backend/essentia_studio/db/migrate.py`
- Create: `backend/essentia_studio/db/migrations/__init__.py`
- Create: `backend/essentia_studio/db/migrations/0001_core.sql`
- Create: `backend/essentia_studio/repositories/settings.py`
- Create: `backend/essentia_studio/schemas/settings.py`
- Create: `tests/db/test_migrations.py`
- Create: `tests/repositories/test_settings.py`

**Interfaces:**
- Consumes: `RuntimeConfig.database_path`.
- Produces: `create_sqlite_engine(path: Path) -> Engine`; `apply_migrations(engine: Engine) -> None`; `SettingsRepository.get() -> AppSettings`; `SettingsRepository.replace(value: AppSettings) -> AppSettings`.

- [ ] **Step 1: Write migration and setting repository tests**

```python
# tests/db/test_migrations.py
from sqlalchemy import text

from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations


def test_migrations_are_idempotent(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    apply_migrations(engine)

    with engine.connect() as connection:
        versions = connection.execute(
            text("SELECT version FROM schema_migrations ORDER BY version")
        ).scalars().all()
    assert versions == [1]
```

```python
# tests/repositories/test_settings.py
from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.repositories.settings import SettingsRepository
from essentia_studio.schemas.settings import AppSettings


def test_settings_round_trip(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = SettingsRepository(engine)
    updated = AppSettings(worker_count=3, max_audio_seconds=180)

    assert repository.replace(updated) == updated
    assert repository.get() == updated
```

- [ ] **Step 2: Run the tests and verify missing modules fail**

Run: `python -m pytest tests/db/test_migrations.py tests/repositories/test_settings.py -q`

Expected: FAIL during collection because `essentia_studio.db.engine` does not exist.

- [ ] **Step 3: Implement the engine and migration runner**

```python
# backend/essentia_studio/db/engine.py
from pathlib import Path

from sqlalchemy import Engine, create_engine, event


def create_sqlite_engine(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}", future=True)

    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine
```

```python
# backend/essentia_studio/db/migrate.py
from importlib.resources import files

from sqlalchemy import Engine


def apply_migrations(engine: Engine) -> None:
    migration_dir = files("essentia_studio.db.migrations")
    scripts = sorted(item for item in migration_dir.iterdir() if item.name.endswith(".sql"))
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
        )
        applied = set(
            connection.exec_driver_sql("SELECT version FROM schema_migrations").scalars()
        )
        for script in scripts:
            version = int(script.name.split("_", 1)[0])
            if version in applied:
                continue
            for statement in script.read_text(encoding="utf-8").split("-- migrate:split"):
                if statement.strip():
                    connection.exec_driver_sql(statement)
            connection.exec_driver_sql(
                "INSERT INTO schema_migrations(version) VALUES (?)", (version,)
            )
```

```sql
-- backend/essentia_studio/db/migrations/0001_core.sql
CREATE TABLE app_settings (
  singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
  worker_count INTEGER NOT NULL CHECK (worker_count BETWEEN 1 AND 64),
  max_audio_seconds INTEGER NOT NULL CHECK (max_audio_seconds BETWEEN 1 AND 3600),
  genre_threshold REAL NOT NULL CHECK (genre_threshold BETWEEN 0 AND 1),
  mood_threshold REAL NOT NULL CHECK (mood_threshold BETWEEN 0 AND 1),
  genre_count INTEGER NOT NULL CHECK (genre_count BETWEEN 1 AND 20),
  write_confidence_tags INTEGER NOT NULL CHECK (write_confidence_tags IN (0, 1)),
  overwrite_existing INTEGER NOT NULL CHECK (overwrite_existing IN (0, 1)),
  compute_preference TEXT NOT NULL CHECK (compute_preference IN ('auto', 'cpu', 'cuda'))
);
-- migrate:split
INSERT INTO app_settings VALUES (1, 1, 300, 0.15, 0.005, 3, 1, 0, 'auto');
```

- [ ] **Step 4: Implement typed settings and repository serialization**

```python
# backend/essentia_studio/schemas/settings.py
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AppSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    worker_count: int = Field(default=1, ge=1, le=64)
    max_audio_seconds: int = Field(default=300, ge=1, le=3600)
    genre_threshold: float = Field(default=0.15, ge=0, le=1)
    mood_threshold: float = Field(default=0.005, ge=0, le=1)
    genre_count: int = Field(default=3, ge=1, le=20)
    write_confidence_tags: bool = True
    overwrite_existing: bool = False
    compute_preference: Literal["auto", "cpu", "cuda"] = "auto"
```

`SettingsRepository` must execute an explicit `SELECT` for the singleton row and one `UPDATE` inside `engine.begin()`. Convert SQLite integer booleans with `bool(row.write_confidence_tags)` and serialize booleans with `int(value.write_confidence_tags)`; return `AppSettings` from both methods.

- [ ] **Step 5: Verify and commit persistence**

Run: `python -m pytest tests/db/test_migrations.py tests/repositories/test_settings.py -q`

Expected: 2 PASS.

Commit:

```bash
git add backend/essentia_studio/db backend/essentia_studio/repositories backend/essentia_studio/schemas tests/db tests/repositories
git commit -m "feat: persist application settings"
```

### Task 3: FastAPI app factory, typed errors, health, and capability preflight

**Files:**
- Create: `backend/essentia_studio/errors.py`
- Create: `backend/essentia_studio/schemas/common.py`
- Create: `backend/essentia_studio/services/capabilities.py`
- Create: `backend/essentia_studio/api/dependencies.py`
- Create: `backend/essentia_studio/api/routes/health.py`
- Create: `backend/essentia_studio/api/routes/settings.py`
- Create: `backend/essentia_studio/api/router.py`
- Create: `backend/essentia_studio/main.py`
- Create: `tests/conftest.py`
- Create: `tests/api/test_health.py`
- Create: `tests/api/test_settings.py`

**Interfaces:**
- Consumes: foundation database and settings interfaces.
- Produces: `create_app(config: RuntimeConfig | None = None) -> FastAPI`; `CapabilityService.inspect() -> Capabilities`; `/health`, `/api/capabilities`, and `GET/PUT /api/settings`.

- [ ] **Step 1: Write app-factory API tests**

```python
# tests/api/test_health.py
from fastapi.testclient import TestClient

from essentia_studio.config import RuntimeConfig
from essentia_studio.main import create_app


def test_health_and_capabilities_report_missing_mount(tmp_path) -> None:
    config = RuntimeConfig.from_env({
        "ESSENTIA_MUSIC_ROOT": str(tmp_path / "missing-music"),
        "ESSENTIA_DATA_DIR": str(tmp_path / "data"),
        "ESSENTIA_FRONTEND_DIR": str(tmp_path / "missing-dist"),
    })

    with TestClient(create_app(config)) as client:
        assert client.get("/health").json() == {"status": "ok", "version": "0.0.0"}
        response = client.get("/api/capabilities")

    assert response.status_code == 200
    assert response.json()["music_root"]["status"] == "missing"
    assert response.json()["image_variant"] == "cpu"
```

```python
# tests/api/test_settings.py
def test_put_settings_rejects_cuda_in_cpu_image(client) -> None:
    response = client.put("/api/settings", json={"compute_preference": "cuda"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "compute_mode_unavailable"
```

- [ ] **Step 2: Run tests and confirm missing app factory**

Run: `python -m pytest tests/api/test_health.py tests/api/test_settings.py -q`

Expected: FAIL importing `essentia_studio.main`.

- [ ] **Step 3: Implement error and capability contracts**

```python
# backend/essentia_studio/errors.py
from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


async def app_error_handler(_request: Request, error: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message": error.message, "details": error.details}},
    )
```

```python
# backend/essentia_studio/services/capabilities.py
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from essentia_studio.config import RuntimeConfig


class PathCapability(BaseModel):
    path: str
    status: Literal["ready", "read_only", "missing"]


class Capabilities(BaseModel):
    image_variant: Literal["cpu", "cuda"]
    available_compute: list[Literal["cpu", "cuda"]]
    music_root: PathCapability
    data_dir: PathCapability
    playlist_dir: PathCapability
    models: list[dict[str, str]]


def inspect_path(path: Path) -> PathCapability:
    if not path.exists():
        return PathCapability(path=str(path), status="missing")
    probe_parent = path if path.is_dir() else path.parent
    return PathCapability(
        path=str(path), status="ready" if os.access(probe_parent, os.W_OK) else "read_only"
    )
```

Add `CapabilityService(config, image_variant)` and have `inspect()` call `inspect_path` for all roots. The CPU implementation returns `available_compute=["cpu"]` and `models=[]`; the analysis plan replaces the empty model inventory through dependency injection.

- [ ] **Step 4: Implement app lifespan and routes**

`create_app` must create the engine, apply migrations inside an `@asynccontextmanager` lifespan, store config/engine/services on `app.state`, register `AppError`, include the `/api` router, and call `app.frontend("/", directory=config.frontend_dir, fallback="index.html")` only when `frontend/index.html` exists. The health route returns `{"status": "ok", "version": __version__}`.

`tests/conftest.py` creates a temporary music directory and data directory, builds `RuntimeConfig` from those absolute paths, enters `TestClient(create_app(config))` as a context manager, yields it, and closes the client after each test so lifespan state never leaks.

The settings PUT route accepts a partial Pydantic update model, merges it with `repository.get().model_copy(update=payload.model_dump(exclude_unset=True))`, and raises:

```python
raise AppError(
    "compute_mode_unavailable",
    "CUDA ist in diesem Image nicht verfügbar.",
    409,
)
```

when the requested preference is not present in `available_compute` and is not `auto`.

- [ ] **Step 5: Verify API behavior and commit**

Run: `python -m pytest tests/api/test_health.py tests/api/test_settings.py -q`

Expected: all tests PASS and lifespan creates one migrated temporary database per fixture.

Commit:

```bash
git add backend/essentia_studio tests/api
git commit -m "feat: add application health and settings api"
```

### Task 4: Approved studio shell, navigation, Settings, and About

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app/App.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/components/AppNav.tsx`
- Create: `frontend/src/features/settings/SettingsView.tsx`
- Create: `frontend/src/features/settings/AboutView.tsx`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/global.css`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/app/App.test.tsx`

**Interfaces:**
- Consumes: `/health`, `/api/capabilities`, `GET/PUT /api/settings`.
- Produces: primary view IDs `workbench`, `playlists`, `jobs`, `settings`, `about`; reusable `apiRequest<T>()`.

- [ ] **Step 1: Write the failing navigation and capability test**

```tsx
// frontend/src/app/App.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'
import { App } from './App'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/api/capabilities')) {
      return new Response(JSON.stringify({
        image_variant: 'cpu', available_compute: ['cpu'], models: [],
        music_root: { path: '/music', status: 'ready' },
        data_dir: { path: '/data', status: 'ready' },
        playlist_dir: { path: '/music/SmartPlaylists', status: 'ready' },
      }))
    }
    return new Response(JSON.stringify({ worker_count: 1, compute_preference: 'auto' }))
  }))
})

test('opens settings and explains the active CPU image', async () => {
  render(<App />)
  await userEvent.click(screen.getByRole('button', { name: 'Einstellungen' }))
  expect(await screen.findByText('CPU-Image')).toBeInTheDocument()
  expect(screen.getByText('/music')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run the frontend test and verify it fails**

Run: `npm --prefix frontend test -- --run src/app/App.test.tsx`

Expected: FAIL because `src/app/App.tsx` does not exist.

- [ ] **Step 3: Implement the typed client and shell state**

```typescript
// frontend/src/api/client.ts
export class ApiError extends Error {
  constructor(public readonly code: string, message: string, public readonly details: unknown) {
    super(message)
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const body = await response.json()
  if (!response.ok) {
    throw new ApiError(body.error.code, body.error.message, body.error.details)
  }
  return body as T
}
```

`App.tsx` uses `useState<ViewId>('workbench')`, renders one `AppNav`, and keeps Workbench/Playlists/Jobs as intentional empty states that name the next implementation plan. Settings loads settings and capabilities with an async function inside `useEffect`, guards state updates with an `active` boolean, and shows explicit `ready`, `read_only`, and `missing` labels.

- [ ] **Step 4: Implement the approved design tokens and accessible navigation**

```css
/* frontend/src/styles/tokens.css */
:root {
  --paper: #f2f4f7;
  --surface: #ffffff;
  --ink: #12243a;
  --ink-muted: #667386;
  --line: #d9e0e8;
  --genre: #2f6fed;
  --mood: #7b4ce2;
  --signal: #ed7b2f;
  --success: #197a55;
  --danger: #b33a3a;
  --radius-sm: 8px;
  --radius-md: 14px;
  --shadow-panel: 0 18px 50px rgb(18 36 58 / 8%);
  font-family: Manrope, system-ui, sans-serif;
  color: var(--ink);
  background: var(--paper);
}

:focus-visible { outline: 3px solid color-mix(in srgb, var(--genre), white 35%); outline-offset: 3px; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; } }
```

Use `"Space Grotesk", "Avenir Next", sans-serif` for headings and `"IBM Plex Mono", "Cascadia Mono", monospace` for paths/versions. Do not fetch fonts from an internet CDN; the first release intentionally uses installed-system fallbacks and ships no font files.

- [ ] **Step 5: Verify frontend and commit**

Run:

```bash
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Expected: navigation test PASS, no TypeScript errors, and `frontend/dist/index.html` exists.

Commit:

```bash
git add frontend
git commit -m "feat: add studio application shell"
```

### Task 5: Cross-platform developer launcher and foundation verification

**Files:**
- Create: `scripts/dev.py`
- Create: `scripts/verify.py`
- Create: `tests/scripts/test_dev.py`
- Create: `docs/development.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `essentia_studio.main:create_app`, frontend npm scripts.
- Produces: `python scripts/dev.py [backend|frontend|all]`; `python scripts/verify.py`.

- [ ] **Step 1: Write launcher command-construction tests**

```python
# tests/scripts/test_dev.py
from scripts.dev import commands_for


def test_commands_are_shell_independent() -> None:
    commands = commands_for("all", python="python", npm="npm")
    assert commands == [
        ["python", "-m", "uvicorn", "essentia_studio.main:create_app", "--factory", "--reload", "--port", "8000"],
        ["npm", "--prefix", "frontend", "run", "dev"],
    ]
```

- [ ] **Step 2: Run the launcher test and verify it fails**

Run: `python -m pytest tests/scripts/test_dev.py -q`

Expected: FAIL because `scripts.dev` does not exist.

- [ ] **Step 3: Implement subprocess-list launchers without shell syntax**

```python
# scripts/dev.py
from __future__ import annotations

import argparse
import subprocess
import sys


def commands_for(target: str, python: str = sys.executable, npm: str = "npm") -> list[list[str]]:
    backend = [python, "-m", "uvicorn", "essentia_studio.main:create_app", "--factory", "--reload", "--port", "8000"]
    frontend = [npm, "--prefix", "frontend", "run", "dev"]
    return {"backend": [backend], "frontend": [frontend], "all": [backend, frontend]}[target]
```

The `main()` function starts each command with `subprocess.Popen(command)`, waits until interrupted, then calls `terminate()` and `wait(timeout=10)` for every child. It never passes `shell=True`.

`scripts/verify.py` runs, in order, `python -m pytest -q`, `python -m ruff check backend tests scripts`, `npm --prefix frontend run lint`, `npm --prefix frontend test`, `npm --prefix frontend run typecheck`, and `npm --prefix frontend run build`, returning the first nonzero exit code.

- [ ] **Step 4: Document macOS, Windows, and Linux foundation development**

`docs/development.md` must contain copy-paste commands for:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
npm --prefix frontend install
python scripts/dev.py all
```

and the POSIX/WSL2 equivalent using `python3.10 -m venv`, `source .venv/bin/activate`, and the same Python/npm launcher commands. Explain that a WSL2 clone should live under `~/src`, not `/mnt/c`, for watcher and mount performance.

- [ ] **Step 5: Run the complete foundation gate and commit**

Run: `python scripts/verify.py`

Expected: backend tests, Ruff, frontend tests, TypeScript, and frontend build all exit 0 on macOS; the same command is the Windows CI contract.

Commit:

```bash
git add scripts tests/scripts docs/development.md README.md
git commit -m "docs: add cross-platform development workflow"
```

## Foundation completion evidence

- `python scripts/verify.py` passes from a clean environment.
- `GET /health`, `GET /api/capabilities`, and settings round-trip tests pass.
- The browser shows the approved navigation and correctly reports CPU capability and mount health.
- The same non-container verification command is runnable from PowerShell and POSIX shells.
