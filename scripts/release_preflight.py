#!/usr/bin/env python3
"""Local release preflight for isis-report-lib.

This is the repo-state companion to the Jev ``release`` pack. The pack reviews a
diff; this script checks the files that must agree before a tag is pushed:

- version/tag format and hatch-vcs configuration;
- CHANGELOG version heading, date and empty ``Unreleased``;
- curated ``release-notes/X.Y.Z.md``;
- ``docker/requirements.in``/``.txt`` pins;
- generated ``docs/api.md``;
- ``docs/security.txt`` expiry;
- roadmap mention and git state.

It is local and read-only. By default it does not call the network or need an
API key; ``--remote`` adds post-release checks for PyPI, the GitHub Release,
the docs site and GHCR (when Docker is available).

Usage::

    python scripts/release_preflight.py --version 0.17.0
    python scripts/release_preflight.py --tag v0.17.0 --require-tag
    python scripts/release_preflight.py --version 0.17.0 --remote
    python scripts/release_preflight.py --version 0.18.0 --allow-dirty
    python scripts/release_preflight.py --self-test
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?P<pre>rc\d+)?$")
EXPIRES_RE = re.compile(r"(?m)^Expires:\s*(\d{4}-\d{2}-\d{2})(?:[T ][0-9:.]+Z?)?\s*$")
CHANGELOG_HEADING_RE = re.compile(r"(?m)^## \[(?P<version>[^\]]+)\] - (?P<date>\d{4}-\d{2}-\d{2})\s*$")
UNRELEASED_RE = re.compile(r"(?ms)^## \[Unreleased\]\s*(.*?)(?=^## \[|\Z)")
PIN_RE = re.compile(r"(?m)^\s*isis-report-lib==(?P<version>[^\s\\]+)")
DEFAULT_GITHUB_REPO = "thepaneb/isis-report-lib"
DOCS_URL = "https://thepaneb.github.io/isis-report-lib"
GHCR_IMAGE = "ghcr.io/thepaneb/isis-report-lib"
PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|notes not ready|placeholder)\b", re.IGNORECASE)


class PreflightError(RuntimeError):
    """A user-facing preflight error."""


@dataclass(frozen=True)
class Check:
    name: str
    status: str  # pass | warn | fail
    message: str
    hint: str = ""


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _normalize_version(raw: str) -> str:
    value = raw.strip()
    if value.startswith("v"):
        value = value[1:]
    if not VERSION_RE.fullmatch(value):
        raise PreflightError(f"invalid version: {raw!r} (use X.Y.Z or X.Y.ZrcN)")
    return value


def _run_git(repo: Path, *args: str) -> str:
    git = shutil.which("git")
    if git is None:
        raise PreflightError("git not found on PATH.")
    completed = subprocess.run(  # noqa: S603
        [git, "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise PreflightError(completed.stderr.strip() or f"git {' '.join(args)} falhou")
    return completed.stdout.strip()


def _parse_changelog(text: str, version: str) -> tuple[str | None, str | None]:
    """Return (date, unreleased_content) for a version, or (None, ...)."""
    match = CHANGELOG_HEADING_RE.search(text)
    if match is None or match.group("version") != version:
        # Search specifically for the requested version, not just the first heading.
        for candidate in CHANGELOG_HEADING_RE.finditer(text):
            if candidate.group("version") == version:
                match = candidate
                break
        else:
            return None, None
    unreleased = UNRELEASED_RE.search(text)
    content = unreleased.group(1) if unreleased else ""
    return match.group("date"), content


def _parse_pins(text: str) -> list[str]:
    return [match.group("version") for match in PIN_RE.finditer(text)]


def _parse_expires(text: str) -> date | None:
    match = EXPIRES_RE.search(text)
    if match is None:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _expiry_status(expires: date | None, today: date) -> tuple[str, str]:
    if expires is None:
        return "fail", "Expires missing"
    days = (expires - today).days
    if days < 0:
        return "fail", f"expired on {expires.isoformat()}"
    if days < 30:
        return "warn", f"expires on {expires.isoformat()} ({days} days)"
    return "pass", f"Expires {expires.isoformat()} ({days} days)"


def _check_version(version: str) -> Check:
    return Check("version", "pass", f"version {version}")


def _check_pyproject(repo: Path, version: str) -> Check:
    path = repo / "pyproject.toml"
    if not path.exists():
        return Check("pyproject", "fail", "pyproject.toml missing")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        return Check("pyproject", "fail", "[project] section missing")
    dynamic = project.get("dynamic", [])
    if isinstance(dynamic, list) and "version" in dynamic:
        return Check("pyproject", "pass", "version via hatch-vcs (dynamic)")
    hardcoded = project.get("version")
    if isinstance(hardcoded, str):
        if hardcoded == version:
            return Check("pyproject", "pass", f"version = {version}")
        return Check("pyproject", "fail", f"version = {hardcoded}, expected {version}")
    return Check("pyproject", "fail", "no version or dynamic version")


def _check_changelog(repo: Path, version: str, today: date) -> list[Check]:
    path = repo / "CHANGELOG.md"
    if not path.exists():
        return [Check("changelog", "fail", "CHANGELOG.md missing")]
    text = path.read_text(encoding="utf-8")
    date_text, unreleased = _parse_changelog(text, version)
    if date_text is None:
        return [Check("changelog", "fail", f"missing '## [{version}] - YYYY-MM-DD'")]
    checks = [Check("changelog", "pass", f"[{version}] - {date_text}")]
    try:
        released_on = date.fromisoformat(date_text)
    except ValueError:
        checks.append(Check("changelog_date", "fail", f"invalid date: {date_text}"))
        return checks
    if released_on > today:
        checks.append(Check("changelog_date", "warn", f"future date: {date_text}"))
    else:
        checks.append(Check("changelog_date", "pass", date_text))
    meaningful = [line for line in (unreleased or "").splitlines() if line.strip() and not line.strip().startswith("###")]
    if meaningful:
        checks.append(Check("unreleased", "warn", "Unreleased still has content; move it into the version"))
    else:
        checks.append(Check("unreleased", "pass", "Unreleased empty"))
    return checks


def _check_release_notes(repo: Path, version: str) -> Check:
    path = repo / "release-notes" / f"{version}.md"
    if not path.exists():
        return Check("release_notes", "fail", f"release-notes/{version}.md missing")
    text = path.read_text(encoding="utf-8").strip()
    if len(text) < 80:
        return Check("release_notes", "warn", f"release-notes/{version}.md is very short")
    if PLACEHOLDER_RE.search(text):
        return Check("release_notes", "fail", f"release-notes/{version}.md contains TODO/TBD")
    return Check("release_notes", "pass", f"release-notes/{version}.md")


def _check_docker(repo: Path, version: str) -> list[Check]:
    checks: list[Check] = []
    for relative in ("docker/requirements.in", "docker/requirements.txt"):
        path = repo / relative
        if not path.exists():
            checks.append(Check("docker_pin", "fail", f"{relative} missing"))
            continue
        pins = _parse_pins(path.read_text(encoding="utf-8"))
        if not pins:
            checks.append(Check("docker_pin", "fail", f"{relative} has no isis-report-lib pin"))
        elif any(pin != version for pin in pins):
            bad = ", ".join(sorted(set(pins)))
            checks.append(Check("docker_pin", "fail", f"{relative}: {bad}, expected {version}"))
        else:
            checks.append(Check("docker_pin", "pass", f"{relative}: {version}"))
    return checks


def _check_docs_api(repo: Path) -> Check:
    script = repo / "scripts" / "gen_api_docs.py"
    if not script.exists():
        return Check("docs_api", "warn", "scripts/gen_api_docs.py missing")
    completed = subprocess.run(  # noqa: S603
        [sys.executable, str(script), "--check"],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode == 0:
        return Check("docs_api", "pass", "docs/api.md is up to date")
    return Check("docs_api", "fail", output[:300] or "docs/api.md is out of date")


def _check_security_txt(repo: Path, today: date) -> Check:
    path = repo / "docs" / "security.txt"
    if not path.exists():
        return Check("security_txt", "fail", "docs/security.txt missing")
    status, message = _expiry_status(_parse_expires(path.read_text(encoding="utf-8")), today)
    return Check("security_txt", status, message)


def _check_roadmap(repo: Path, version: str) -> Check:
    path = repo / "docs" / "ROADMAP.md"
    if not path.exists():
        return Check("roadmap", "warn", "docs/ROADMAP.md missing")
    if version in path.read_text(encoding="utf-8"):
        return Check("roadmap", "pass", f"roadmap mentions {version}")
    return Check("roadmap", "warn", f"roadmap does not mention {version}")


def _check_git(repo: Path, allow_dirty: bool) -> list[Check]:
    checks: list[Check] = []
    try:
        status = _run_git(repo, "status", "--porcelain")
    except PreflightError as exc:
        return [Check("git", "fail", str(exc))]
    if status:
        checks.append(Check("worktree", "warn" if allow_dirty else "fail", "working tree is dirty"))
    else:
        checks.append(Check("worktree", "pass", "working tree is clean"))
    try:
        branch = _run_git(repo, "branch", "--show-current") or "(detached)"
    except PreflightError:
        branch = "(unknown)"
    checks.append(Check("branch", "pass" if branch == "main" else "warn", f"branch: {branch}"))
    try:
        upstream = _run_git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        if upstream:
            counts = _run_git(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}")
            ahead, behind = (int(part) for part in counts.split())
            if ahead or behind:
                checks.append(Check("upstream", "warn", f"{ahead} ahead / {behind} behind {upstream}"))
            else:
                checks.append(Check("upstream", "pass", f"up to date with {upstream}"))
    except PreflightError:
        checks.append(Check("upstream", "warn", "branch has no upstream; could not compare"))
    return checks


def _check_tag(repo: Path, version: str, tag_arg: str | None, require_tag: bool) -> Check:
    tag = tag_arg or f"v{version}"
    if tag_arg is not None and _normalize_version(tag_arg) != version:
        return Check("tag", "fail", f"tag {tag_arg} does not match {version}")
    try:
        tag_commit = _run_git(repo, "rev-list", "-n", "1", tag)
    except PreflightError:
        return Check("tag", "fail" if require_tag else "warn", f"tag {tag} does not exist yet")
    try:
        head = _run_git(repo, "rev-parse", "HEAD")
    except PreflightError:
        return Check("tag", "warn", f"tag {tag} exists; HEAD unknown")
    if tag_commit == head:
        return Check("tag", "pass", f"tag {tag} points to HEAD")
    return Check("tag", "warn", f"tag {tag} exists but does not point to HEAD")


def _http_get(url: str, timeout: float) -> tuple[int, bytes]:
    if not url.startswith("https://"):
        raise PreflightError(f"remote check requires https://: {url}")
    request = urllib.request.Request(  # noqa: S310  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        url, headers={"User-Agent": "isis-report-lib-preflight/1.0"}
    )
    try:
        # URLs are fixed https:// constants or the validated version/slug.
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return getattr(response, "status", 200), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        return 0, str(exc.reason).encode("utf-8", "replace")


def _repo_slug(repo: Path) -> str:
    try:
        remote = _run_git(repo, "remote", "get-url", "origin")
    except PreflightError:
        return DEFAULT_GITHUB_REPO
    match = re.search(r"github\.com[:/](?P<slug>[^/]+/[^/]+?)(?:\.git)?$", remote)
    return match.group("slug") if match else DEFAULT_GITHUB_REPO


def _missing_release_assets(names: Sequence[str]) -> list[str]:
    missing: list[str] = []
    if not any(name.endswith(".whl") for name in names):
        missing.append("*.whl")
    if not any(name.endswith(".tar.gz") for name in names):
        missing.append("*.tar.gz")
    for required in ("sbom.json", "provenance.intoto.jsonl"):
        if required not in names:
            missing.append(required)
    return missing


def _remote_pypi(version: str, timeout: float) -> Check:
    status, body = _http_get(f"https://pypi.org/pypi/isis-report-lib/{version}/json", timeout)
    if status != 200:
        return Check("remote_pypi", "fail", f"PyPI {version}: HTTP {status}")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return Check("remote_pypi", "fail", "PyPI response is not JSON")
    info = data.get("info") if isinstance(data, dict) else None
    published = info.get("version") if isinstance(info, dict) else None
    if published != version:
        return Check("remote_pypi", "fail", f"PyPI has {published!r}, expected {version}")
    return Check("remote_pypi", "pass", f"PyPI {version}")


def _remote_github(repo: Path, version: str, timeout: float, github_repo: str | None) -> Check:
    slug = github_repo or _repo_slug(repo)
    status, body = _http_get(f"https://api.github.com/repos/{slug}/releases/tags/v{version}", timeout)
    if status != 200:
        return Check("remote_github", "fail", f"GitHub release v{version}: HTTP {status}")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return Check("remote_github", "fail", "GitHub release response is not JSON")
    if not isinstance(data, dict):
        return Check("remote_github", "fail", "GitHub release response is not an object")
    if data.get("draft"):
        return Check("remote_github", "fail", f"GitHub release v{version} is still a draft")
    assets = [asset.get("name") for asset in data.get("assets", []) if isinstance(asset, dict)]
    names = [name for name in assets if isinstance(name, str)]
    missing = _missing_release_assets(names)
    if missing:
        return Check("remote_github", "fail", f"GitHub release v{version} missing: {', '.join(missing)}")
    return Check("remote_github", "pass", f"GitHub release v{version} with assets")


def _remote_docs(timeout: float) -> list[Check]:
    checks: list[Check] = []
    for name, url in (("remote_docs", DOCS_URL + "/"), ("remote_security_txt", DOCS_URL + "/security.txt")):
        status, _body = _http_get(url, timeout)
        checks.append(Check(name, "pass" if status == 200 else "fail", f"{url}: HTTP {status}"))
    return checks


def _remote_ghcr(version: str, timeout: float) -> Check:
    docker = shutil.which("docker")
    if docker is None:
        return Check("remote_ghcr", "warn", "docker not found; GHCR manifest not checked")
    try:
        completed = subprocess.run(  # noqa: S603
            [docker, "manifest", "inspect", f"{GHCR_IMAGE}:{version}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return Check("remote_ghcr", "warn", f"docker manifest inspect failed: {exc}")
    if completed.returncode == 0:
        return Check("remote_ghcr", "pass", f"GHCR {GHCR_IMAGE}:{version}")
    message = (completed.stderr or completed.stdout).strip()
    lowered = message.lower()
    if "manifest unknown" in lowered or "no such manifest" in lowered or "not found" in lowered:
        return Check("remote_ghcr", "fail", f"GHCR {version}: {message[:200]}")
    return Check("remote_ghcr", "warn", f"docker/daemon issue: {message[:200]}")


def _remote_checks(repo: Path, version: str, timeout: float, github_repo: str | None) -> list[Check]:
    checks = [
        _remote_pypi(version, timeout),
        _remote_github(repo, version, timeout, github_repo),
        _remote_ghcr(version, timeout),
    ]
    checks += _remote_docs(timeout)
    return checks


def _checks(repo: Path, version: str, tag: str | None, allow_dirty: bool, require_tag: bool, today: date) -> list[Check]:
    checks = [_check_version(version), _check_pyproject(repo, version)]
    checks += _check_changelog(repo, version, today)
    checks.append(_check_release_notes(repo, version))
    checks += _check_docker(repo, version)
    checks.append(_check_docs_api(repo))
    checks.append(_check_security_txt(repo, today))
    checks.append(_check_roadmap(repo, version))
    checks += _check_git(repo, allow_dirty)
    checks.append(_check_tag(repo, version, tag, require_tag))
    return checks


def _summary(checks: list[Check]) -> dict[str, int]:
    return {
        "pass": sum(1 for check in checks if check.status == "pass"),
        "warn": sum(1 for check in checks if check.status == "warn"),
        "fail": sum(1 for check in checks if check.status == "fail"),
    }


def _render_text(version: str, repo: Path, checks: list[Check], summary: dict[str, int]) -> str:
    lines = [f"Release preflight: {version}", f"Repo: {repo}", ""]
    for check in checks:
        marker = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[check.status]
        lines.append(f"[{marker}] {check.name}: {check.message}")
        if check.hint:
            lines.append(f"       {check.hint}")
    lines += ["", f"Summary: {summary['pass']} pass, {summary['warn']} warn, {summary['fail']} fail"]
    return "\n".join(lines) + "\n"


def _resolve_version(args: argparse.Namespace, repo: Path) -> str:
    if args.version:
        return _normalize_version(args.version)
    if args.tag:
        return _normalize_version(args.tag)
    try:
        latest = _run_git(repo, "describe", "--tags", "--abbrev=0")
    except PreflightError as exc:
        raise PreflightError("no tags; pass --version X.Y.Z") from exc
    return _normalize_version(latest)


def _run_self_test() -> int:
    _check(_normalize_version("v0.17.0") == "0.17.0", "v prefix")
    _check(_normalize_version("0.18.0rc1") == "0.18.0rc1", "rc version")
    text = "# Changelog\n\n## [Unreleased]\n\n## [0.17.0] - 2026-11-27\n\n### Added\n- x\n"
    released, unreleased = _parse_changelog(text, "0.17.0")
    _check(released == "2026-11-27", "changelog date")
    _check(not (unreleased or "").strip(), "unreleased content")
    _check(_parse_pins("isis-report-lib==0.17.0\nisis-report-lib==0.17.0 \\\n") == ["0.17.0", "0.17.0"], "pins")
    _check(_parse_expires("Contact: x\nExpires: 2027-11-27\n") == date(2027, 11, 27), "expires")
    _check(_expiry_status(date(2027, 11, 27), date(2026, 11, 27))[0] == "pass", "expiry pass")
    _check(_expiry_status(date(2026, 1, 1), date(2026, 11, 27))[0] == "fail", "expiry fail")
    complete = ["x.whl", "x.tar.gz", "sbom.json", "provenance.intoto.jsonl"]
    _check(_missing_release_assets(complete) == [], "release assets complete")
    _check("sbom.json" in _missing_release_assets(["x.whl", "x.tar.gz"]), "release assets missing")
    print("self-test OK")
    return 0


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=ROOT, help="repository root (default: this repo)")
    parser.add_argument("--version", help="version to check (X.Y.Z or X.Y.ZrcN)")
    parser.add_argument("--tag", help="tag to check (default: vVERSION)")
    parser.add_argument("--allow-dirty", action="store_true", help="warn instead of failing on a dirty tree")
    parser.add_argument("--require-tag", action="store_true", help="fail when the tag does not exist")
    parser.add_argument(
        "--remote",
        action="store_true",
        help="also check PyPI, GitHub Release, docs and GHCR (network)",
    )
    parser.add_argument("--timeout", type=float, default=15.0, help="remote HTTP/docker timeout in seconds")
    parser.add_argument("--github-repo", help="owner/repo for the GitHub Release check")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--self-test", action="store_true", help="run local parser checks")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdio()
    args = _parse_args(argv)
    if args.self_test:
        return _run_self_test()
    try:
        repo = args.repo.resolve()
        if not (repo / "pyproject.toml").exists():
            raise PreflightError(f"does not look like the project repository: {repo}")
        version = _resolve_version(args, repo)
        checks = _checks(repo, version, args.tag, args.allow_dirty, args.require_tag, date.today())
        if args.remote:
            checks += _remote_checks(repo, version, args.timeout, args.github_repo)
        summary = _summary(checks)
        if args.json:
            print(
                json.dumps(
                    {
                        "schema": "isis-report-lib.release-preflight.v1",
                        "version": version,
                        "repo": str(repo),
                        "checks": [asdict(check) for check in checks],
                        "summary": summary,
                        "ok": summary["fail"] == 0 and (not args.strict or summary["warn"] == 0),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(_render_text(version, repo, checks, summary), end="")
        failed = summary["fail"] > 0 or (args.strict and summary["warn"] > 0)
        return 1 if failed else 0
    except PreflightError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
