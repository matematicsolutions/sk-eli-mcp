"""FastMCP entry point - Slovak Slov-lex tools.

Run:

    python -m sk_eli_mcp.server

Configuration via env:

- ``SK_ELI_CACHE_DIR`` (default ``~/.matematic/cache/sk-eli``)
- ``SK_ELI_AUDIT_DIR`` (default ``~/.matematic/audit``)
- ``SK_ELI_BASE_URL`` (default ``https://static.slov-lex.sk``)
"""

from __future__ import annotations

import os
import re

import httpx
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .audit import AuditLogger, hash_input, timer
from .citations import build_act_record, current_version, extract_text, parse_versions, version_url
from . import runtime
from .client import DEFAULT_BASE_URL, SlovLexClient
from .models import Act, LawText, Version, VersionListResult

INSTRUCTIONS = """\
This MCP server exposes the Slovak Collection of Laws (Zbierka zakonov) via static.slov-lex.sk, the JavaScript-free static mirror of the Slov-lex portal. Acts are addressed by year + number (e.g. `year=2018, number=18`). Slovakia implements ELI (Pillar I). Every response carries a stable `eli_uri`, a `human_readable_citation` and a `source_url` (the citation contract).

## Call order

1. `sk_get_versions` - list the consolidated versions of an act by `year` + `number` (each with its effective dates and the amending act). Use this to see the consolidation timeline and pick a `version_id`.
2. `sk_get_act` - metadata for an act: citation (e.g. "č. 18/2018 Z. z."), `eli_uri`, and the current in-force version.
3. `sk_get_text` - the full text of an act by `year` + `number`. By default it returns the current in-force version; pass `version_id` (a date like "20240701" or "vyhlasene_znenie" for the as-promulgated text) for a specific one.

## Hard constraints

- **No free-text search** - addressed by year + number, not keywords. A Slovak citation gives them (e.g. "18/2018 Z. z."). Relay the `dataset_note`.
- **ELI is national (Pillar I), not data.europa.eu** - the static pages carry no machine ELI metadata; `eli_uri` is the canonical Slov-lex URL (`slov-lex.sk/pravne-predpisy/SK/ZZ/{year}/{number}`). Relay the `eli_note`. Do not invent it.
- **Text is extracted from the official HTML** - `sk_get_text` extracts the act text from the Slov-lex version page; do not paraphrase it as the law.
- **Consolidated versions** - an act has many versions over time; be explicit which `version_id` (effective date) a quotation comes from.
- **Every response has `human_readable_citation` + `source_url`** - cite both to the user.
- **Audit log JSONL** - every tool call appends to `~/.matematic/audit/sk-eli-mcp.jsonl`.

## Error iteration

Tools return a structured error with a `[code]` prefix:
- `invalid_arg` - a parameter is missing or invalid (e.g. bad year, non-positive number).
- `not_found` - no act/version exists for those coordinates.
- `upstream_error` - a Slov-lex error (HTTP, timeout). Retry once before surfacing.

## Response style

- Cite as `human_readable_citation` with the ELI URL: "č. 18/2018 Z. z., https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2018/18/".
- NEVER invent an ELI, a number, a year or a version date - take each from the tool output.
"""


class ToolError(Exception):
    """Structured error for sk-eli MCP tools - visible to the LLM with a [code] prefix."""

    VALID_CODES = frozenset({"invalid_arg", "not_found", "upstream_error"})

    def __init__(self, code: str, message: str):
        if code not in self.VALID_CODES:
            raise ValueError(f"Unknown ToolError code: {code}. Valid: {sorted(self.VALID_CODES)}")
        self.code = code
        super().__init__(f"[{code}] {message}")


READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    destructiveHint=False,
    openWorldHint=True,
)

mcp: FastMCP = FastMCP(name="sk-eli-mcp", instructions=INSTRUCTIONS)


def _base_url() -> str:
    return os.environ.get("SK_ELI_BASE_URL", runtime.base_url("eli", DEFAULT_BASE_URL)).rstrip("/")


def _audit() -> AuditLogger:
    return AuditLogger()


def _map_upstream(exc: Exception) -> Exception:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
        return ToolError("not_found", "No act/version found in Slov-lex for those coordinates.")
    if isinstance(exc, (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException)):
        return ToolError("upstream_error", f"Slov-lex error: {type(exc).__name__}: {exc}")
    return exc


def _check(year: int, number: int) -> None:
    if not 1918 <= year <= 2100:
        raise ToolError("invalid_arg", f"year={year} is out of range (1918..2100).")
    if number <= 0:
        raise ToolError("invalid_arg", f"number={number} must be positive.")


# ---------------------------------------------------------------------------
# sk_get_versions
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def sk_get_versions(year: int, number: int) -> VersionListResult:
    """List the consolidated versions of a Slovak act.

    Args:
        year: e.g. ``2018``.
        number: e.g. ``18``.

    Returns:
        ``VersionListResult`` with ``items: list[Version]`` (effective dates, amending act, links).
    """
    audit = _audit()
    _check(year, number)
    input_hash = hash_input({"year": year, "number": number})

    with timer() as t:
        try:
            async with SlovLexClient(base_url=_base_url()) as client:
                index_html = await client.get_index(year, number)
        except Exception as exc:
            audit.log(tool="sk_get_versions", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    versions = parse_versions(index_html)
    if not versions:
        raise ToolError("not_found", f"No versions found for {number}/{year} in Slov-lex.")
    rec = build_act_record(year, number, versions)
    items = [
        Version(
            version_id=v["version_id"], label=v.get("label"),
            effective_from=v.get("effective_from"), effective_to=v.get("effective_to"),
            in_force=v.get("in_force", False), is_promulgated=v.get("is_promulgated", False),
            amended_by=v.get("amended_by"),
            source_url=version_url(year, number, v["version_id"]),
        )
        for v in versions
    ]
    result = VersionListResult(
        year=year, number=number, citation=rec["citation"], eli_uri=rec["eli_uri"],
        total=len(items), items=items,
    )
    audit.log(tool="sk_get_versions", input_hash=input_hash, output_count_or_size=len(items),
              duration_ms=t.duration_ms, status="ok")
    return result


# ---------------------------------------------------------------------------
# sk_get_act
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def sk_get_act(year: int, number: int) -> Act:
    """Fetch Slovak act metadata by year and number.

    Args:
        year: e.g. ``2018``.
        number: e.g. ``18``.

    Returns:
        ``Act`` with ``eli_uri``, ``human_readable_citation``, ``source_url`` and the current
        in-force version pointer.
    """
    audit = _audit()
    _check(year, number)
    input_hash = hash_input({"year": year, "number": number})

    with timer() as t:
        try:
            async with SlovLexClient(base_url=_base_url()) as client:
                index_html = await client.get_index(year, number)
        except Exception as exc:
            audit.log(tool="sk_get_act", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    versions = parse_versions(index_html)
    if not versions:
        raise ToolError("not_found", f"No versions found for {number}/{year} in Slov-lex.")
    act = Act.model_validate(build_act_record(year, number, versions))
    audit.log(tool="sk_get_act", input_hash=input_hash, output_count_or_size=1,
              duration_ms=t.duration_ms, status="ok")
    return act


# ---------------------------------------------------------------------------
# sk_get_text
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def sk_get_text(year: int, number: int, version_id: str | None = None) -> LawText:
    """Fetch the full text of a Slovak act (a consolidated version).

    Args:
        year: e.g. ``2018``.
        number: e.g. ``18``.
        version_id: optional - a date like ``"20240701"`` or ``"vyhlasene_znenie"`` (as-promulgated).
            Default: the current in-force version.

    Returns:
        ``LawText`` with the citation contract and ``content`` (extracted text).
    """
    audit = _audit()
    _check(year, number)
    if version_id is not None:
        version_id = version_id.strip()
        if not re.fullmatch(r"\d{8}|vyhlasene_znenie", version_id):
            raise ToolError("invalid_arg", "version_id must be 'YYYYMMDD' or 'vyhlasene_znenie'.")
    input_hash = hash_input({"year": year, "number": number, "version_id": version_id})

    with timer() as t:
        try:
            async with SlovLexClient(base_url=_base_url()) as client:
                index_html = await client.get_index(year, number)
                versions = parse_versions(index_html)
                if not versions:
                    raise ToolError("not_found", f"No versions found for {number}/{year}.")
                if version_id is None:
                    cur = current_version(versions)
                    version_id = cur["version_id"] if cur else versions[-1]["version_id"]
                html_text = await client.get_version_html(year, number, version_id)
        except ToolError:
            audit.log(tool="sk_get_text", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error="not_found")
            raise
        except Exception as exc:
            audit.log(tool="sk_get_text", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    rec = build_act_record(year, number, versions)
    text = extract_text(html_text)
    if not text:
        raise ToolError("not_found", f"Version {version_id} of {number}/{year} has no extractable text.")
    result = LawText(
        year=year,
        number=number,
        version_id=version_id,
        citation=rec["citation"],
        eli_uri=rec["eli_uri"],
        human_readable_citation=rec["human_readable_citation"],
        source_url=version_url(year, number, version_id),
        content=text,
        byte_size=len(text.encode("utf-8")),
    )
    audit.log(tool="sk_get_text", input_hash=input_hash, output_count_or_size=result.byte_size or 0,
              duration_ms=t.duration_ms, status="ok")
    return result


def main() -> None:
    """Run the MCP server over stdio (default for Claude Code)."""
    mcp.run()


if __name__ == "__main__":
    main()
