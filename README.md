# sk-eli-mcp

An MCP server for the Slovak **Collection of Laws** (Zbierka zákonov) via **static.slov-lex.sk**,
the JavaScript-free static mirror of the Slov-lex portal. It fetches Slovak legislation and its
consolidated versions, with verifiable citations.

Part of the MateMatic `eu-legal-mcp` production line - after PL, DE, AT, ES, FI, IE, NL, SE, FR,
LU, DK, CZ, HR and LT. Same citation contract, Slov-lex source. Slovakia implements ELI (Pillar I).

> **Scope.** This MVP lists an act's consolidated versions, returns metadata, and fetches the full
> text of a version. Acts are addressed by year + number; the portal is path-based, not keyword
> search. Coverage 1918-present. Language: Slovak. Every response carries a `dataset_note`.
>
> **ELI is national (Pillar I), not data.europa.eu.** The static pages carry no machine-readable
> ELI metadata, so `eli_uri` is the canonical Slov-lex URL
> (`slov-lex.sk/pravne-predpisy/SK/ZZ/{year}/{number}`), the stable national identifier. Full text
> is served from the `static.slov-lex.sk` mirror (`source_url`). Every response carries an
> `eli_note`.
>
> **Text is extracted from the official HTML.** Slov-lex serves the consolidated text as HTML;
> `sk_get_text` extracts the plain text from the act container.

## The tools

| Tool | What it does |
|---|---|
| `sk_get_versions` | List an act's consolidated versions (effective dates, amending act). |
| `sk_get_act` | Metadata for an act by year + number, plus the current in-force version. |
| `sk_get_text` | Full text of an act version (default: the current in-force version). |

Every response carries the contract: `eli_uri` (the Slov-lex URL, e.g.
`https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2018/18/`), `human_readable_citation`
(e.g. `č. 18/2018 Z. z.`), and `source_url`.

## Install

Run it with no install step (once published to PyPI):

```bash
uvx sk-eli-mcp
```

Or from source:

```bash
cd sk-eli-mcp
pip install -e .
```

## Configure (Claude Code / any MCP client)

```json
{
  "mcpServers": {
    "sk-eli-mcp": { "command": "sk-eli-mcp" }
  }
}
```

Environment:

- `SK_ELI_BASE_URL` - default `https://static.slov-lex.sk`
- `SK_ELI_CACHE_DIR` - default `~/.matematic/cache/sk-eli`
- `SK_ELI_AUDIT_DIR` - default `~/.matematic/audit`

No API key. The Slov-lex static mirror is keyless.

## Governance

- **Public data only** - read-only against Slov-lex; no client data leaves the machine.
- **Audit log** - every tool call appends one JSON line to `~/.matematic/audit/sk-eli-mcp.jsonl`.
- **Vendor-neutral** - talks only to `static.slov-lex.sk`; no LLM provider, no telemetry.
- **Verifiable citations** - every response is independently checkable via `source_url`.

See `CONSTITUTION.md` and `DISCOVERY.md`.

## Tests

```bash
pip install -e ".[dev]"
pytest tests/test_instructions_drift.py tests/test_parse.py -v   # offline
pytest tests/test_smoke.py -v                                    # hits live Slov-lex
```

## Licence

Apache-2.0. © Matematic Solutions / Wieslaw Mazur.
