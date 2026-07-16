from scripts.dev import commands_for


def test_commands_are_shell_independent() -> None:
    commands = commands_for("all", python="python", npm="npm")

    assert commands == [
        [
            "python",
            "-m",
            "uvicorn",
            "essentia_studio.main:create_app",
            "--factory",
            "--reload",
            "--port",
            "8000",
        ],
        ["npm", "--prefix", "frontend", "run", "dev"],
    ]


def test_frontend_command_accepts_windows_npm_executable() -> None:
    assert commands_for("frontend", npm="npm.cmd") == [
        ["npm.cmd", "--prefix", "frontend", "run", "dev"]
    ]
