"""Song collections from git: cloned into the user's cache with the system's `git`.

A StrumBook file is someone else's text, so only https and ssh addresses reach `git`,
always after `--`, and a StrumBook file can never add `git` options.
"""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

from strumbook.book import BuildError

# https://host/…, ssh://[user@]host/…, or scp-like user@host:path. The user and host
# can't start with "-", which git or ssh could read as an option.
_GIT_URL = re.compile(
    r"(?:https|ssh)://(?:\w[\w.-]*@)?\w[^\s@]*|\w[\w.-]*@\w[\w.-]*:\S+"
)
_SIGN_IN = re.compile(r"https://[^/]*@")
_PIN = re.compile(r"[\w.][\w./-]*")


def check_git_url(url: str) -> None:
    if _SIGN_IN.match(url):  # don't print it: it may hold a password or token
        raise BuildError(
            "a git address can't hold sign-in details: leave them to git's own sign-in"
        )
    if not _GIT_URL.fullmatch(url):
        raise BuildError(
            f"git address {url!r} isn't allowed: use https://… or ssh (git@host:…)"
        )


def check_pin(pin: str) -> None:
    if not _PIN.fullmatch(pin):
        raise BuildError(f"pin {pin!r} isn't a commit or tag")


def cache_folder() -> Path:
    """The platform's user cache folder for StrumBook. Deleting it is always safe."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "strumbook"
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
        return Path(local) / "strumbook" / "cache"
    xdg = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(xdg) / "strumbook"


def fetch(name: str, url: str, pin: str | None) -> tuple[Path, list[str]]:
    """A checkout of `url` at `pin`, or at the latest commit, and any warnings."""
    check_git_url(url)
    if pin is not None:
        check_pin(pin)
    stem = re.sub(r"[^\w.-]+", "-", url.rstrip("/").rsplit("/", 1)[-1]).strip("-.")
    digest = hashlib.sha256(url.encode()).hexdigest()[:12]
    clone = cache_folder() / "git" / f"{stem or 'repo'}-{digest}"
    warnings: list[str] = []

    if not (clone / ".git").is_dir():
        try:
            clone.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise BuildError(
                f"can't make the cache folder {clone.parent}: {e}"
            ) from None
        # Links arrive as plain files, so a collection can't point a song at a file
        # elsewhere on this computer.
        ok, why = _git(
            "clone", "-c", "core.symlinks=false", "--quiet", "--no-checkout",
            "--", url, str(clone),
        )  # fmt: skip
        if not ok:
            raise BuildError(f"can't download source {name!r} from {url}: {why}")
    elif (
        pin is None
        or not _git("-C", str(clone), "cat-file", "-e", pin + "^{commit}")[0]
    ):
        # The latest is wanted, or the pin isn't in the cache yet.
        ok, why = _git("-C", str(clone), "fetch", "--quiet", "--tags", "origin")
        if not ok:
            warnings.append(
                f"can't update source {name!r} from {url} ({why}); "
                "using the copy from the last build, which may be out of date"
            )

    ref = pin if pin is not None else "origin/HEAD"
    ok, why = _git(
        "-C", str(clone), "checkout", "--quiet", "--force", "--detach", ref, "--"
    )
    if not ok:
        what = f"pin {pin!r}" if pin is not None else "the latest commit"
        raise BuildError(f"can't check out {what} of source {name!r}: {why}")
    return clone, warnings


def _git(*args: str) -> tuple[bool, str]:
    """Run git; return whether it worked and, if not, its last line of error."""
    try:
        done = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        raise BuildError("git sources need git: https://git-scm.com") from None
    lines = done.stderr.strip().splitlines() or [f"git exit code {done.returncode}"]
    return done.returncode == 0, lines[-1]
