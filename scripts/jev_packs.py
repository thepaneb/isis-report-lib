#!/usr/bin/env python3
"""Jev packs, questions and report text for isis-report-lib."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SEVERITY_LABELS = ("nenhuma", "baixa", "média", "alta", "crítica")
SEVERITY_LABELS_EN = ("none", "low", "medium", "high", "critical")
RECOMMENDATION_RANK = {"approve": 0, "comment": 1, "block": 2}

# Dimensions, thresholds, and the local action to take when one fires.
CORE_DIMENSIONS: tuple[tuple[str, str, float, str], ...] = (
    (
        "security",
        "Segurança",
        0.70,
        "Revise escaping, data URI, quotas e logs; veja docs/STANDARDS.md §3.5.",
    ),
    (
        "correctness",
        "Correção",
        0.70,
        "Rode a suíte e revise contratos de dados, exports e recursos liberados.",
    ),
    (
        "event_loop",
        "Event loop / browser",
        # A missed cross-loop bug is catastrophic; the free model lands around
        # 0.68 on the Windows policy regression while the clean control stays
        # near 0.07, so 0.65 keeps the signal without flagging the control.
        0.65,
        "Revise pdf.py e _run: nada de policy global, await cross-loop ou close de outro loop.",
    ),
    (
        "tests",
        "Testes",
        0.60,
        "Adicione teste/regressão e rode pytest -m 'not browser'.",
    ),
    (
        "docs",
        "Docs / CHANGELOG",
        0.50,
        "Rode scripts/gen_api_docs.py --check e atualize CHANGELOG/README no mesmo PR.",
    ),
    (
        "api_parity",
        "Paridade sync/async",
        0.70,
        "Adicione a... + wrapper _run e export em __all__ quando for API pública.",
    ),
    (
        "dependencies",
        "Dependências",
        0.70,
        "Justifique o extra/opt-in e rode dependency-review/pip-audit no CI.",
    ),
)
# Extra dimensions for the opt-in "quality" pack. They target issues the
# default questionnaire deliberately leaves to ruff/pytest: dead branches,
# test hygiene, typing at public boundaries, resource cleanup, and API breaks.
QUALITY_DIMENSIONS: tuple[tuple[str, str, float, str], ...] = (
    (
        "dead_code",
        "Código morto/duplicado",
        0.60,
        "Remova branch/except duplicado, código inalcançável ou import sem uso; rode ruff.",
    ),
    (
        "test_hygiene",
        "Higiene dos testes",
        0.60,
        "Use tmp_path, feche handles e isole estado global/ordem entre testes.",
    ),
    (
        "type_safety",
        "Tipagem",
        0.60,
        "Evite `Any`/casts inseguros no boundary público; `dict[str, Any]` de payload é aceito.",
    ),
    (
        "resource_cleanup",
        "Fechamento de recursos",
        0.65,
        "Garanta close/finally em arquivos, browsers, contextos e diretórios temporários.",
    ),
    (
        "backward_compat",
        "Compatibilidade",
        0.70,
        "Deprecie/migre mudanças de API pública, defaults e formato de saída.",
    ),
)
DOCS_DIMENSIONS: tuple[tuple[str, str, float, str], ...] = (
    (
        "docs_api",
        "Docs da API",
        0.70,
        "Rode `python scripts/gen_api_docs.py` e inclua `docs/api.md`.",
    ),
    (
        "docs_changelog",
        "CHANGELOG",
        0.55,
        "Adicione a entrada correspondente em `CHANGELOG.md`.",
    ),
    (
        "docs_readme",
        "README/CLI",
        0.50,
        "Atualize `README.md` e o `--help` para parâmetros/CLI.",
    ),
    (
        "docs_guides",
        "Guias/nav",
        0.50,
        "Atualize `docs/` e a navegação quando o comportamento/feature muda.",
    ),
)
SECURITY_DIMENSIONS: tuple[tuple[str, str, float, str], ...] = (
    (
        "sec_escaping",
        "Escaping/HTML",
        0.65,
        "Revise autoescape/escape e export de strings não confiáveis (§3.2).",
    ),
    (
        "sec_runtime",
        "Runtime/rede/browser",
        0.70,
        "Nenhum fetch de rede no render; JS/plugins/downloads desabilitados.",
    ),
    (
        "sec_media",
        "Imagens/data URI",
        0.70,
        "Aceite apenas data URI raster; rejeite paths/URLs/SVG e limite o tamanho.",
    ),
    (
        "sec_quota",
        "Quotas/limites",
        0.65,
        "Quotas são do operador; payload só pode apertar. Evite recurso sem limite.",
    ),
    (
        "sec_log_leak",
        "Logs/erros",
        0.65,
        "Use `log_value`/redaction; não ecoe payload, segredo, token ou PII.",
    ),
    (
        "sec_trust_contract",
        "Contrato de confiança",
        0.70,
        "`verify_*` retorna veredito; parser falha com ValueError; chaves >=32 bytes.",
    ),
    (
        "sec_supply_chain",
        "Supply chain",
        0.65,
        "Justifique dependência/system package e evite ampliar a instalação padrão.",
    ),
)
RELEASE_DIMENSIONS: tuple[tuple[str, str, float, str], ...] = (
    (
        "rel_version",
        "Versão/tag",
        0.65,
        "Confirme tag/hatch-vcs; `rc` vai para TestPyPI.",
    ),
    (
        "rel_changelog",
        "CHANGELOG de release",
        0.65,
        "Feche `Unreleased` e adicione `[X.Y.Z] - data`.",
    ),
    (
        "rel_notes",
        "Release notes",
        0.60,
        "Crie `release-notes/X.Y.Z.md`; anexe assets antes de publicar.",
    ),
    (
        "rel_publish",
        "Publicação/artefatos",
        0.65,
        "Revise `publish.yml`: Trusted Publishing, TestPyPI rc, SBOM/provenance e assets antes de publicar.",
    ),
    (
        "rel_docker",
        "Docker/GHCR",
        0.60,
        "Compare o pin `docker/requirements.in/.txt` e as tags GHCR/`latest` com a versão/tag do release.",
    ),
    (
        "rel_post",
        "Pós-release",
        0.65,
        "Verifique PyPI/GHCR/docs/Release e atualize roadmap/promo/`security.txt`.",
    ),
)
ALL_DIMENSIONS = CORE_DIMENSIONS + QUALITY_DIMENSIONS + DOCS_DIMENSIONS + SECURITY_DIMENSIONS + RELEASE_DIMENSIONS
ALL_DIMENSION_BY_KEY = {key: (label, threshold, hint) for key, label, threshold, hint in ALL_DIMENSIONS}

EN_TEXT: dict[str, tuple[str, str]] = {
    "security": ("Security", "Review escaping, data URI, quotas and logs; see docs/STANDARDS.md §3.5."),
    "correctness": ("Correctness", "Run the suite and review data contracts, exports and released resources."),
    "event_loop": (
        "Event loop / browser",
        "Review pdf.py and _run: no global policy, cross-loop await, or closing another loop.",
    ),
    "tests": ("Tests", "Add a test/regression and run pytest -m 'not browser'."),
    "docs": ("Docs / CHANGELOG", "Run scripts/gen_api_docs.py --check and update CHANGELOG/README in the same PR."),
    "api_parity": ("Sync/async parity", "Add a... + _run wrapper and export in __all__ for public API."),
    "dependencies": ("Dependencies", "Justify the extra/opt-in and run dependency-review/pip-audit in CI."),
    "dead_code": ("Dead/duplicate code", "Remove duplicate branch/except, unreachable code or unused imports; run ruff."),
    "test_hygiene": ("Test hygiene", "Use tmp_path, close handles and isolate global state/order between tests."),
    "type_safety": (
        "Typing",
        "Avoid `str | Path | Any`, unsafe casts and new type: ignore; `dict[str, Any]` payloads are fine.",
    ),
    "resource_cleanup": ("Resource cleanup", "Ensure close/finally for files, browsers, contexts and temp dirs."),
    "backward_compat": ("Compatibility", "Deprecate/migrate public API, defaults and output format changes."),
    "docs_api": ("API docs", "Run python scripts/gen_api_docs.py and include docs/api.md."),
    "docs_changelog": ("CHANGELOG", "Add the matching entry to CHANGELOG.md."),
    "docs_readme": ("README/CLI", "Update README.md and --help for parameters/CLI."),
    "docs_guides": ("Guides/nav", "Update docs/ and navigation when behavior/feature changes."),
    "sec_escaping": ("Escaping/HTML", "Review autoescape/escaping and exports of untrusted strings (§3.2)."),
    "sec_runtime": ("Runtime/network/browser", "No network fetch at render; JS/plugins/downloads disabled."),
    "sec_media": ("Images/data URI", "Accept only raster data URIs; reject paths/URLs/SVG and enforce size."),
    "sec_quota": ("Quotas/limits", "Operator quotas; payload may only tighten; avoid unbounded resources."),
    "sec_log_leak": ("Logs/errors", "Use log_value/redaction; do not echo payload, secret, token or PII."),
    "sec_trust_contract": (
        "Trust contract",
        "verify_* returns a verdict; parser fails with ValueError; keys >=32 bytes.",
    ),
    "sec_supply_chain": ("Supply chain", "Justify dependency/system package and avoid widening the default install."),
    "rel_version": ("Version/tag", "Confirm tag/hatch-vcs; rc goes to TestPyPI."),
    "rel_changelog": ("Release CHANGELOG", "Close Unreleased and add [X.Y.Z] - date."),
    "rel_notes": ("Release notes", "Create release-notes/X.Y.Z.md; attach assets before publishing."),
    "rel_publish": (
        "Publish/artifacts",
        "Review publish.yml: Trusted Publishing, TestPyPI rc, SBOM/provenance and assets before publish.",
    ),
    "rel_docker": ("Docker/GHCR", "Compare docker/requirements pin and GHCR/latest tags with the release version/tag."),
    "rel_post": ("Post-release", "Check PyPI/GHCR/docs/Release and update roadmap/promo/security.txt."),
}

CHECK_EN: dict[str, str] = {
    "Teste sync e async em loop novo; revise `pdf.py`/`_run` (sem policy global, sem await cross-loop).": (
        "Test sync and async on a fresh loop; review `pdf.py`/`_run` (no global policy, no cross-loop await)."
    ),
    "Atualize `CHANGELOG.md` e `README.md`; rode `python scripts/gen_api_docs.py`.": (
        "Update `CHANGELOG.md` and `README.md`; run `python scripts/gen_api_docs.py`."
    ),
    "Regenere `docs/api.md` com `python scripts/gen_api_docs.py`.": ("Regenerate `docs/api.md` with `python scripts/gen_api_docs.py`."),
    "Adicione a entrada em `CHANGELOG.md` (seção `Unreleased` ou versão).": (
        "Add the entry to `CHANGELOG.md` (`Unreleased` or version section)."
    ),
    "Atualize `README.md` e o `--help` para o parâmetro/CLI novo.": ("Update `README.md` and `--help` for the new parameter/CLI."),
    "Atualize o guia/nav em `docs/` para o comportamento novo.": ("Update the guide/nav in `docs/` for the new behavior."),
    "Adicione `a...` + wrapper `_run` e export em `__all__`.": ("Add `a...` + `_run` wrapper and export in `__all__`."),
    "Adicione teste/regressão no arquivo correspondente.": "Add a test/regression in the matching file.",
    "Passe pelo checklist de `docs/STANDARDS.md` §3.5.": "Go through the `docs/STANDARDS.md` §3.5 checklist.",
    "Revise autoescape/escape em HTML/CSV/XLSX/email; veja `docs/STANDARDS.md` §3.2.": (
        "Review autoescape/escaping in HTML/CSV/XLSX/email; see `docs/STANDARDS.md` §3.2."
    ),
    "Nenhum fetch de rede no render; mantenha JS/plugins/downloads desabilitados.": (
        "No network fetch at render; keep JS/plugins/downloads disabled."
    ),
    "Valide data URI raster; rejeite path/URL/SVG e o limite de 2 MiB.": (
        "Validate raster data URI; reject path/URL/SVG and the 2 MiB limit."
    ),
    "Quotas do operador; payload só aperta; limite linhas/imagens/páginas/chars.": (
        "Operator quotas; payload may only tighten; limit rows/images/pages/chars."
    ),
    "Use `log_value`/redaction; não ecoe payload, segredo, token ou PII.": (
        "Use `log_value`/redaction; do not echo payload, secret, token or PII."
    ),
    "Revise `verify_*` (veredito, não raise), parsers (ValueError) e HMAC >=32 bytes.": (
        "Review `verify_*` (verdict, not raise), parsers (ValueError) and HMAC >=32 bytes."
    ),
    "Justifique a dependência/system package e valide `dependency-review`/`pip-audit`.": (
        "Justify the dependency/system package and validate `dependency-review`/`pip-audit`."
    ),
    "Confirme tag `vX.Y.Z` + hatch-vcs; `rc` vai para TestPyPI.": ("Confirm tag `vX.Y.Z` + hatch-vcs; `rc` goes to TestPyPI."),
    "Feche `Unreleased` e adicione `[X.Y.Z] - data` no `CHANGELOG.md`.": ("Close `Unreleased` and add `[X.Y.Z] - date` to `CHANGELOG.md`."),
    "Crie/atualize `release-notes/X.Y.Z.md` e reuse o draft release.": (
        "Create/update `release-notes/X.Y.Z.md` and reuse the draft release."
    ),
    "Revise `publish.yml`: Trusted Publishing, TestPyPI rc, SBOM/provenance e assets antes de publicar.": (
        "Review `publish.yml`: Trusted Publishing, TestPyPI rc, SBOM/provenance and assets before publishing."
    ),
    "Atualize `docker/requirements.in/.txt` e as tags GHCR/`latest`.": ("Update `docker/requirements.in/.txt` and GHCR/`latest` tags."),
    "Verifique PyPI/GHCR/docs/Release e atualize roadmap/promo/`security.txt`.": (
        "Check PyPI/GHCR/docs/Release and update roadmap/promo/`security.txt`."
    ),
    "Justifique a dependência e valide `dependency-review`/`pip-audit` no CI.": (
        "Justify the dependency and validate `dependency-review`/`pip-audit` in CI."
    ),
    "Rode `ruff check` e remova branch/except/import sem uso.": ("Run `ruff check` and remove unused branch/except/import."),
    "Use `tmp_path`, feche handles e isole estado global/ordem entre testes.": (
        "Use `tmp_path`, close handles and isolate global state/order between tests."
    ),
    "Remova `Any`/casts inseguros do boundary público; rode `mypy`.": ("Remove `Any`/unsafe casts from the public boundary; run `mypy`."),
    "Garanta `finally`/`close` em arquivos, browsers, contextos e diretórios temporários.": (
        "Ensure `finally`/`close` for files, browsers, contexts and temporary directories."
    ),
    "Deprecie/migre a mudança de API/default antes de remover o comportamento antigo.": (
        "Deprecate/migrate the API/default change before removing the old behavior."
    ),
}


def _t(lang: str, pt: str, en: str) -> str:
    return en if lang == "en" else pt


def _dim_text(key: str, label: str, hint: str, lang: str) -> tuple[str, str]:
    if lang == "en":
        return EN_TEXT.get(key, (label, hint))
    return label, hint


QUESTIONS: dict[str, dict[str, Any]] = {
    "security": {
        "type": "noul",
        "instructions": (
            "Does the diff introduce an exploitable vulnerability (unescaped HTML/XSS, path traversal, SSRF, "
            "exposed secret, data URI/quota bypass, logging caller data)?"
        ),
    },
    "correctness": {
        "type": "noul",
        "instructions": ("Does the diff introduce a likely logic, type, data-contract, formatting, export, or resource-leak bug?"),
    },
    "event_loop": {
        "type": "noul",
        "instructions": (
            "Does the diff introduce or worsen an event-loop/browser-pool issue (global policy change, cross-loop "
            "await, singleton reused on another loop, closing a browser from another loop)?"
        ),
    },
    "tests": {
        "type": "noul",
        "instructions": "Does the diff change public behavior or fix a bug without a corresponding test/regression?",
    },
    "docs": {
        "type": "noul",
        "instructions": (
            "Does the diff change public API, CLI, parameter, or behavior without updating README, CHANGELOG, or "
            "docs/api.md (generated by scripts/gen_api_docs.py)?"
        ),
    },
    "api_parity": {
        "type": "noul",
        "instructions": (
            "Does the diff add/change a public feature without the async `a...` version and the sync `_run` "
            "wrapper, or without an `__init__.__all__` export when applicable?"
        ),
    },
    "dependencies": {
        "type": "noul",
        "instructions": ("Does the diff add a runtime dependency, widen the default install, or remove an opt-in without justification?"),
    },
    "severity": {
        "type": "score",
        "instructions": "How severe is the most relevant issue in the diff?",
        "criteria": ["none", "low", "medium", "high", "critical"],
    },
    "recommendation": {
        "type": "choice",
        "instructions": "What should be done with this diff?",
        "criteria": {
            "approve": "Approve without reservations",
            "comment": "Comment asking for changes",
            "block": "Block the merge",
        },
    },
    "focus": {
        "type": "choice",
        "instructions": "What is the main area of attention?",
        "criteria": {
            "none": "None",
            "security": "Security",
            "correctness": "Correctness",
            "event_loop": "Event loop/browser",
            "tests": "Tests",
            "docs": "Docs/CHANGELOG",
            "api_parity": "Sync/async parity",
            "dependencies": "Dependencies",
        },
    },
}

QUALITY_QUESTIONS: dict[str, dict[str, Any]] = {
    "dead_code": {
        "type": "noul",
        "instructions": (
            "Does the diff introduce dead/unreachable code, duplicate branch/except, unused import, or an effectless variable?"
        ),
    },
    "test_hygiene": {
        "type": "noul",
        "instructions": (
            "Do the diff's tests leak temp files/handles, depend on order/global state, not use tmp_path, or fail to isolate effects?"
        ),
    },
    "type_safety": {
        "type": "noul",
        "instructions": (
            "Does the diff use `str | Path | Any`, an unsafe cast, a new `# type: ignore`, or lose relevant typing "
            "at a public boundary (excluding the standard `dict[str, Any]` payload shape)?"
        ),
    },
    "resource_cleanup": {
        "type": "noul",
        "instructions": ("Are files, handles, browsers, contexts, or temporary directories closed on every path, including exceptions?"),
    },
    "backward_compat": {
        "type": "noul",
        "instructions": ("Does the diff break public API, defaults, output format, or semantics without deprecation/migration?"),
    },
}
DOCS_QUESTIONS: dict[str, dict[str, Any]] = {
    "docs_api": {
        "type": "noul",
        "instructions": (
            "Does the diff change a public Python signature, export, CLI, or documented API behavior (excluding "
            "release notes, version bumps, roadmap or changelog text) without regenerating `docs/api.md` with "
            "`scripts/gen_api_docs.py`?"
        ),
    },
    "docs_changelog": {
        "type": "noul",
        "instructions": ("Does the diff change public behavior, fix a bug, or add a feature without a matching `CHANGELOG.md` entry?"),
    },
    "docs_readme": {
        "type": "noul",
        "instructions": "Does the diff add/change a parameter, CLI, example, or quickstart without updating `README.md`?",
    },
    "docs_guides": {
        "type": "noul",
        "instructions": (
            "Does the diff change behavior/features covered by `docs/` (guide, security, roadmap) without updating the text or navigation?"
        ),
    },
}
SECURITY_QUESTIONS: dict[str, dict[str, Any]] = {
    "sec_escaping": {
        "type": "noul",
        "instructions": (
            "Does the diff compile untrusted text as a template (`Template(...)`, `render_template_string`) or "
            "interpolate untrusted data into HTML/CSV/XLSX/email without escaping/autoescape (XSS/injection)?"
        ),
    },
    "sec_runtime": {
        "type": "noul",
        "instructions": (
            "Does the diff add a network fetch/SSRF at render/generate time or enable JavaScript, plugins, or downloads in the browser?"
        ),
    },
    "sec_media": {
        "type": "noul",
        "instructions": "Does the diff allow a path/URL/SVG or bypass the raster data-URI gate and the 2 MiB limit?",
    },
    "sec_quota": {
        "type": "noul",
        "instructions": ("Does the diff accept a quota/limit from the payload or remove a limit on rows, images, pages, or chars?"),
    },
    "sec_log_leak": {
        "type": "noul",
        "instructions": ("Does the diff make an error/log echo payload, secret, token, or PII without `log_value`/redaction?"),
    },
    "sec_trust_contract": {
        "type": "noul",
        "instructions": (
            "Does the diff break the trust contract (`verify_*` raises instead of returning a verdict, parser "
            "swallows an error, HMAC <32 bytes, weak algorithm)?"
        ),
    },
    "sec_supply_chain": {
        "type": "noul",
        "instructions": (
            "Does the diff add a runtime dependency/system package or widen the default install without justification/review?"
        ),
    },
}
RELEASE_QUESTIONS: dict[str, dict[str, Any]] = {
    "rel_version": {
        "type": "noul",
        "instructions": (
            "Does the release diff introduce an inconsistent version/tag (hatch-vcs, rc vs final, tag without "
            "commit) or publish a version without a changelog?"
        ),
    },
    "rel_changelog": {
        "type": "noul",
        "instructions": (
            "Does the release diff leave `Unreleased` open, miss `[X.Y.Z] - date`, or use a version that does not match the tag?"
        ),
    },
    "rel_notes": {
        "type": "noul",
        "instructions": (
            "Does the release diff lack curated release notes (`release-notes/X.Y.Z.md`), reuse the wrong draft, or "
            "allow publishing before assets?"
        ),
    },
    "rel_publish": {
        "type": "noul",
        "instructions": (
            "Does the release diff change `publish.yml` in a way that breaks Trusted Publishing, TestPyPI for `rc`, "
            "wheel/sdist/SBOM/provenance attachment, or immutability (assets before publish)?"
        ),
    },
    "rel_docker": {
        "type": "noul",
        "instructions": (
            "Does the release diff leave the `docker/requirements` pin or GHCR/`latest` tags on a different version "
            "than the release, or not update them to `X.Y.Z`?"
        ),
    },
    "rel_post": {
        "type": "noul",
        "instructions": ("Does the release diff skip verifying published PyPI/GHCR/docs/Release or updating roadmap/promo/`security.txt`?"),
    },
}


@dataclass(frozen=True)
class QuestionPack:
    """A self-contained questionnaire, run as its own API pass."""

    id: str
    title: str
    description: str
    questions: dict[str, dict[str, Any]]
    dimensions: tuple[tuple[str, str, float, str], ...]
    supersedes: tuple[str, ...] = ()


CORE_PACK = QuestionPack(
    id="core",
    title="Core",
    description="Default triage: security, correctness, event loop, tests, docs, parity and dependencies.",
    questions=QUESTIONS,
    dimensions=CORE_DIMENSIONS,
)
QUALITY_PACK = QuestionPack(
    id="quality",
    title="Quality",
    description="Deep code review: dead code, test hygiene, typing, resources and compatibility.",
    questions=QUALITY_QUESTIONS,
    dimensions=QUALITY_DIMENSIONS,
)
DOCS_PACK = QuestionPack(
    id="docs",
    title="Docs",
    description="Detailed API, CHANGELOG, README/CLI and guides/nav drift.",
    questions=DOCS_QUESTIONS,
    dimensions=DOCS_DIMENSIONS,
    supersedes=("docs",),
)
SECURITY_PACK = QuestionPack(
    id="security",
    title="Security",
    description="§3.5 checklist: escaping, runtime/network/browser, media, quotas, logs, trust and supply chain.",
    questions=SECURITY_QUESTIONS,
    dimensions=SECURITY_DIMENSIONS,
    supersedes=("security", "dependencies"),
)
RELEASE_PACK = QuestionPack(
    id="release",
    title="Release",
    description="Release flow: version/tag, CHANGELOG, notes, Trusted Publishing/artifacts, Docker/GHCR and post-release.",
    questions=RELEASE_QUESTIONS,
    dimensions=RELEASE_DIMENSIONS,
    supersedes=("docs_changelog",),
)
PACKS = {pack.id: pack for pack in (CORE_PACK, QUALITY_PACK, DOCS_PACK, SECURITY_PACK, RELEASE_PACK)}
PROFILE_PACKS: dict[str, tuple[str, ...]] = {
    "default": ("core",),
    "strict": ("core", "quality"),
    "docs": ("core", "docs"),
    "security": ("core", "security"),
    "release": ("core", "docs", "release"),
    "all": ("core", "quality", "docs", "security", "release"),
}
AUTO_PACK_RULES: dict[str, tuple[str, ...]] = {
    "quality": ("src/", "tests/"),
    "docs": ("docs/", "README.md", "CHANGELOG.md", "AGENTS.md", "release-notes/"),
    "security": (
        "src/isis_report_lib/media.py",
        "src/isis_report_lib/rendering.py",
        "src/isis_report_lib/templates/",
        "src/isis_report_lib/signing.py",
        "src/isis_report_lib/inputs.py",
        "src/isis_report_lib/export.py",
        "src/isis_report_lib/service.py",
    ),
    "release": (
        "release-notes/",
        "docker/",
        ".github/workflows/publish.yml",
        "pyproject.toml",
    ),
}
