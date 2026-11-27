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

It is local and read-only. It does not call the network, does not need an API
key, and does not create tags, releases or images.

Usage::

    python scripts/release_preflight.py --version 0.17.0
    python scripts/release_preflight.py --tag v0.17.0 --require-tag
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
        raise PreflightError(f"versão inválida: {raw!r} (use X.Y.Z ou X.Y.ZrcN)")
    return value


def _run_git(repo: Path, *args: str) -> str:
    git = shutil.which("git")
    if git is None:
        raise PreflightError("git não encontrado no PATH.")
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
        return "fail", "Expires ausente"
    days = (expires - today).days
    if days < 0:
        return "fail", f"expirado em {expires.isoformat()}"
    if days < 30:
        return "warn", f"expira em {expires.isoformat()} ({days} dias)"
    return "pass", f"Expires {expires.isoformat()} ({days} dias)"


def _check_version(version: str) -> Check:
    return Check("version", "pass", f"versão {version}")


def _check_pyproject(repo: Path, version: str) -> Check:
    path = repo / "pyproject.toml"
    if not path.exists():
        return Check("pyproject", "fail", "pyproject.toml ausente")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        return Check("pyproject", "fail", "seção [project] ausente")
    dynamic = project.get("dynamic", [])
    if isinstance(dynamic, list) and "version" in dynamic:
        return Check("pyproject", "pass", "version via hatch-vcs (dynamic)")
    hardcoded = project.get("version")
    if isinstance(hardcoded, str):
        if hardcoded == version:
            return Check("pyproject", "pass", f"version = {version}")
        return Check("pyproject", "fail", f"version = {hardcoded}, esperado {version}")
    return Check("pyproject", "fail", "sem version nem dynamic version")


def _check_changelog(repo: Path, version: str, today: date) -> list[Check]:
    path = repo / "CHANGELOG.md"
    if not path.exists():
        return [Check("changelog", "fail", "CHANGELOG.md ausente")]
    text = path.read_text(encoding="utf-8")
    date_text, unreleased = _parse_changelog(text, version)
    if date_text is None:
        return [Check("changelog", "fail", f"falta '## [{version}] - YYYY-MM-DD'")]
    checks = [Check("changelog", "pass", f"[{version}] - {date_text}")]
    try:
        released_on = date.fromisoformat(date_text)
    except ValueError:
        checks.append(Check("changelog_date", "fail", f"data inválida: {date_text}"))
        return checks
    if released_on > today:
        checks.append(Check("changelog_date", "warn", f"data futura: {date_text}"))
    else:
        checks.append(Check("changelog_date", "pass", date_text))
    meaningful = [line for line in (unreleased or "").splitlines() if line.strip() and not line.strip().startswith("###")]
    if meaningful:
        checks.append(Check("unreleased", "warn", "Unreleased ainda tem conteúdo; mova para a versão"))
    else:
        checks.append(Check("unreleased", "pass", "Unreleased vazio"))
    return checks


def _check_release_notes(repo: Path, version: str) -> Check:
    path = repo / "release-notes" / f"{version}.md"
    if not path.exists():
        return Check("release_notes", "fail", f"release-notes/{version}.md ausente")
    text = path.read_text(encoding="utf-8").strip()
    if len(text) < 80:
        return Check("release_notes", "warn", f"release-notes/{version}.md muito curto")
    if PLACEHOLDER_RE.search(text):
        return Check("release_notes", "fail", f"release-notes/{version}.md contém TODO/TBD")
    return Check("release_notes", "pass", f"release-notes/{version}.md")


def _check_docker(repo: Path, version: str) -> list[Check]:
    checks: list[Check] = []
    for relative in ("docker/requirements.in", "docker/requirements.txt"):
        path = repo / relative
        if not path.exists():
            checks.append(Check("docker_pin", "fail", f"{relative} ausente"))
            continue
        pins = _parse_pins(path.read_text(encoding="utf-8"))
        if not pins:
            checks.append(Check("docker_pin", "fail", f"{relative} sem pin de isis-report-lib"))
        elif any(pin != version for pin in pins):
            bad = ", ".join(sorted(set(pins)))
            checks.append(Check("docker_pin", "fail", f"{relative}: {bad}, esperado {version}"))
        else:
            checks.append(Check("docker_pin", "pass", f"{relative}: {version}"))
    return checks


def _check_docs_api(repo: Path) -> Check:
    script = repo / "scripts" / "gen_api_docs.py"
    if not script.exists():
        return Check("docs_api", "warn", "scripts/gen_api_docs.py ausente")
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
        return Check("docs_api", "pass", "docs/api.md atualizado")
    return Check("docs_api", "fail", output[:300] or "docs/api.md desatualizado")


def _check_security_txt(repo: Path, today: date) -> Check:
    path = repo / "docs" / "security.txt"
    if not path.exists():
        return Check("security_txt", "fail", "docs/security.txt ausente")
    status, message = _expiry_status(_parse_expires(path.read_text(encoding="utf-8")), today)
    return Check("security_txt", status, message)


def _check_roadmap(repo: Path, version: str) -> Check:
    path = repo / "docs" / "ROADMAP.md"
    if not path.exists():
        return Check("roadmap", "warn", "docs/ROADMAP.md ausente")
    if version in path.read_text(encoding="utf-8"):
        return Check("roadmap", "pass", f"roadmap menciona {version}")
    return Check("roadmap", "warn", f"roadmap não menciona {version}")


def _check_git(repo: Path, allow_dirty: bool) -> list[Check]:
    checks: list[Check] = []
    try:
        status = _run_git(repo, "status", "--porcelain")
    except PreflightError as exc:
        return [Check("git", "fail", str(exc))]
    if status:
        checks.append(Check("worktree", "warn" if allow_dirty else "fail", "working tree sujo"))
    else:
        checks.append(Check("worktree", "pass", "working tree limpo"))
    try:
        branch = _run_git(repo, "branch", "--show-current") or "(detached)"
    except PreflightError:
        branch = "(desconhecida)"
    checks.append(Check("branch", "pass" if branch == "main" else "warn", f"branch: {branch}"))
    try:
        upstream = _run_git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        if upstream:
            counts = _run_git(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}")
            ahead, behind = (int(part) for part in counts.split())
            if ahead or behind:
                checks.append(Check("upstream", "warn", f"{ahead} ahead / {behind} behind {upstream}"))
            else:
                checks.append(Check("upstream", "pass", f"em dia com {upstream}"))
    except PreflightError:
        checks.append(Check("upstream", "warn", "branch sem upstream; não foi possível comparar"))
    return checks


def _check_tag(repo: Path, version: str, tag_arg: str | None, require_tag: bool) -> Check:
    tag = tag_arg or f"v{version}"
    if tag_arg is not None and _normalize_version(tag_arg) != version:
        return Check("tag", "fail", f"tag {tag_arg} não corresponde a {version}")
    try:
        tag_commit = _run_git(repo, "rev-list", "-n", "1", tag)
    except PreflightError:
        return Check("tag", "fail" if require_tag else "warn", f"tag {tag} ainda não existe")
    try:
        head = _run_git(repo, "rev-parse", "HEAD")
    except PreflightError:
        return Check("tag", "warn", f"tag {tag} existe; HEAD desconhecido")
    if tag_commit == head:
        return Check("tag", "pass", f"tag {tag} aponta para HEAD")
    return Check("tag", "warn", f"tag {tag} existe, mas não aponta para HEAD")


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
    lines += ["", f"Resumo: {summary['pass']} pass, {summary['warn']} warn, {summary['fail']} fail"]
    return "\n".join(lines) + "\n"


def _resolve_version(args: argparse.Namespace, repo: Path) -> str:
    if args.version:
        return _normalize_version(args.version)
    if args.tag:
        return _normalize_version(args.tag)
    try:
        latest = _run_git(repo, "describe", "--tags", "--abbrev=0")
    except PreflightError as exc:
        raise PreflightError("sem tags; informe --version X.Y.Z") from exc
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
            raise PreflightError(f"não parece um repositório do projeto: {repo}")
        version = _resolve_version(args, repo)
        checks = _checks(repo, version, args.tag, args.allow_dirty, args.require_tag, date.today())
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
