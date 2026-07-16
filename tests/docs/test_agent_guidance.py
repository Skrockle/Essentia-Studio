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


if __name__ == "__main__":
    unittest.main()
