# DISCOVERY - sk-eli-mcp (Slovakia / Slov-lex)

Date: 2026-06-29. Source selection driven by Legal Data Hunter coverage data
(`worldwidelaw/legal-sources`): Slovakia's `SK/CollectionOfLaws` source is the Slov-lex static
mirror, confirmed clean by live probes.

## Why Slovakia, why the static mirror

The live Slov-lex portal (`www.slov-lex.sk`) is a JavaScript SPA. The Ministry of Justice also
publishes a **JavaScript-free static mirror** at `static.slov-lex.sk` ("statická verzia portálu")
that server-renders the full text. We read the static mirror - no headless browser, no scraping of
a SPA.

## Endpoints (keyless, Open Government Data)

| Purpose | Endpoint | Format |
|---|---|---|
| Act history / versions | `/static/SK/ZZ/{year}/{number}/` | HTML (history table) |
| Version full text | `/static/SK/ZZ/{year}/{number}/{version}.html` | HTML |
| As-promulgated text | `/static/SK/ZZ/{year}/{number}/vyhlasene_znenie.html` | HTML |
| (also) PDF | `/static/pdf/SK/ZZ/{year}/{number}/...pdf` | PDF |

- `ZZ` = Zbierka zákonov. `{version}` is a date `YYYYMMDD` (effective-from) or `vyhlasene_znenie`.
- 404 for a non-existent coordinate is clean.

## Page shape (probed)

- The index page carries a history table; each row is
  `<tr class="effectivenessHistoryItem" data-iri="/SK/ZZ/{year}/{number}/{version}"
  data-vyhlasene="0|1" data-ucinnostod="YYYY-MM-DD" data-ucinnostdo="YYYY-MM-DD">` with a link to
  `{version}.html`, a label span (the effective range), and the amending act (Novela) when any.
  The in-force version has an empty `data-ucinnostdo`.
- A version page carries the full text in `<div id="predpis">` (articles `§`, `ČASŤ`, `HLAVA`,
  ~250 KB for a large act). The page `<title>` is generic; the law is cited by its number.

Example probed: 18/2018 Z. z. (the data protection act) - 7 versions from `vyhlasene_znenie` to
the 2024-07-01 in-force text.

## Citation contract (Art. 4)

- `eli_uri` = `https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/{year}/{number}/` (Slov-lex ELI URL).
- `human_readable_citation` = the Slovak convention "č. {number}/{year} Z. z.".
- `source_url` = the `static.slov-lex.sk` version page actually served.

## Tools (MVP)

- `sk_get_versions(year, number)` - the consolidation timeline (effective dates + amending act).
- `sk_get_act(year, number)` - metadata + the current in-force version pointer.
- `sk_get_text(year, number, version_id?)` - extracted full text (default: in-force version).

## Deficiencies flagged (per WM's "some connectors may be deficient" steer)

- **National ELI (Pillar I), not European** - no `data.europa.eu` form, no machine ELI metadata.
- **Text extracted from HTML** - no structured XML manifestation in the static mirror.
- **No descriptive title cheaply** - the act is cited by number (`č. N/YYYY Z. z.`); the
  descriptive title lives inside the text body.

## Deferred

- **Case law** - Constitutional Court / Supreme Court (separate sources).
- **PDF manifestation** - the MVP returns extracted HTML text; the PDF could be added.
- **Year listing** (`/static/SK/ZZ/{year}/`) - browsing all acts of a year is out of MVP scope.

## Licence / re-use

Slovak legislation is official public information; Slov-lex publishes it as Open Government Data.
Read-only relay with attribution + `source_url`. No key, no ToS gate for the static mirror.
Distribution as a public connector is in line with the keyless tier.
