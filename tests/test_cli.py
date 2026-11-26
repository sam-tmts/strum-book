"""Observable CLI behaviour, not implementation details."""

import subprocess
import sys
import tomllib
from importlib.metadata import version
from pathlib import Path

import pytest

from strumbook.cli import main


def test_help_describes_current_capability(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    output = capsys.readouterr()
    assert "usage: strumbook" in output.out
    assert "--version" in output.out
    assert "build" in output.out
    assert "not implemented yet" not in output.out
    assert output.err == ""


def test_version_comes_from_package_metadata(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"strumbook {version('strumbook')}"


def test_installed_metadata_matches_project_version() -> None:
    project = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with project.open("rb") as stream:
        expected = tomllib.load(stream)["project"]["version"]
    assert version("strumbook") == expected


def test_no_arguments_shows_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "usage: strumbook" in capsys.readouterr().out


def test_unknown_arguments_fail(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--not-a-real-option"])
    assert exc.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        ["build"],
        ["build", "songs"],
        ["build", "songs", "-o", "book.pdf", "--mid-word-chords", "sideways"],
        ["build", "songs", "-o", "book.pdf", "--pdf-tags", "maybe"],
    ],
)
def test_build_usage_errors(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2
    assert "usage:" in capsys.readouterr().err


@pytest.mark.parametrize("argument", ["--help", "--version"])
def test_module_entry_point_runs_from_another_directory(
    argument: str, tmp_path: Path
) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "strumbook", argument],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "strumbook" in result.stdout
    assert result.stderr == ""
