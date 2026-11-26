"""The README thanks every project StrumBook depends on."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _thanks_section() -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    match = re.search(r"^## Thanks\n(.*?)(?=^## |\Z)", readme, re.MULTILINE | re.DOTALL)
    assert match, "README.md has no '## Thanks' section"
    return match.group(1).lower()


def _dependencies() -> list[str]:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)
    specs = project["project"]["dependencies"]
    for group in project.get("dependency-groups", {}).values():
        specs += group
    return [re.match(r"[A-Za-z0-9._-]+", spec).group() for spec in specs]


def test_readme_thanks_every_dependency() -> None:
    thanks = _thanks_section()
    missing = [name for name in _dependencies() if name.lower() not in thanks]
    assert not missing, f"add these to the README's Thanks table: {missing}"
