# Constitution of sk-eli-mcp

Version: 0.1.0
Date: 2026-06-29
Licence: Apache-2.0

`sk-eli-mcp` is an MCP server for the Slovak Collection of Laws (Zbierka zákonov) via
static.slov-lex.sk. It lists an act's consolidated versions and fetches full text with verifiable
citations. Case law is not in this MVP.

The 4 principles below are inherited from the `eu-legal-mcp` line Constitution (Article IV).

---

## Art. 1. Public data only

The Slov-lex static mirror is the official, public source of Slovak legislation (Open Government
Data, keyless). The server is read-only and sends nothing beyond the requested coordinates.

## Art. 2. Mandatory audit log

Every tool call MUST append one JSON line to `~/.matematic/audit/sk-eli-mcp.jsonl`
(ts / tool / input_hash SHA-256 / output_count_or_size / duration_ms / status). Inability to write =
the tool returns an error, it does not silently skip.

## Art. 3. Vendor neutrality

No tool hardcodes an LLM provider, assumes a model, or adds commercial telemetry. The server talks
only to `static.slov-lex.sk` and the local filesystem. Authentication: none; own backoff + cache.

## Art. 4. ELI citations and a human-readable citation are mandatory

Every response MUST carry three fields:
- `eli_uri`: the canonical Slov-lex URL, built from year + number
  (`https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/{year}/{number}`). NEVER invented. Slovakia
  implements ELI (Pillar I); the static pages expose no machine ELI metadata, so this national URL
  is the stable identifier - every response carries an `eli_note`.
- `human_readable_citation`: the Slovak convention (e.g. "č. 18/2018 Z. z.").
- `source_url`: the `static.slov-lex.sk` page actually served.

---

## Open points

1. **National vs European ELI** - Slov-lex implements ELI Pillar I; no `data.europa.eu`-resolvable
   form, no machine ELI metadata in the static HTML. Flagged via `eli_note`.
2. **Text extraction** - the consolidated text is extracted from the Slov-lex HTML container; there
   is no structured XML manifestation in the static mirror.
3. **Versioning** - an act has many consolidated versions; `sk_get_text` defaults to the in-force
   one and accepts an explicit `version_id`.
4. **Case law** - Slovak court decisions (Constitutional / Supreme) are a later feature.

## Ewolucja konstytucji

Changes to art. 1-4 follow SEMVER + an entry in `CHANGELOG.md` + a `pyproject.toml` bump.

First version: 2026-06-29. Author: Wieslaw Mazur / MateMatic.
