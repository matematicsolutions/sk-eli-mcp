"""Slovak Slov-lex (static HTML) parsing + citation helpers.

The Slovak Collection of Laws (Zbierka zakonov) is published on static.slov-lex.sk, a
JavaScript-free static mirror of the Slov-lex portal. Each act has a history page listing its
consolidated versions, and each version is a full-text HTML page.

Slovakia implements ELI (Pillar I) but the static pages expose no machine-readable ELI metadata,
so eli_uri carries the canonical Slov-lex ELI-style URL (slov-lex.sk/pravne-predpisy/SK/ZZ/...),
the stable national identifier. The connector flags this via eli_note.

Citation contract:
- eli_uri: the canonical Slov-lex predpis URL (national ELI Pillar I). NEVER invented - built from
  year + number.
- human_readable_citation: the Slovak convention, e.g. "c. 18/2018 Z. z.".
- source_url: the static.slov-lex.sk page actually served.
"""

from __future__ import annotations

import html as _html
import re
from typing import Any

STATIC_BASE = "https://static.slov-lex.sk"
CANONICAL_BASE = "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ"

_ROW_RE = re.compile(r'<tr class="effectivenessHistoryItem"(.*?)</tr>', re.DOTALL)
_ATTR_IRI = re.compile(r'data-iri="([^"]+)"')
_ATTR_VYHL = re.compile(r'data-vyhlasene="([^"]*)"')
_ATTR_OD = re.compile(r'data-ucinnostod="([^"]*)"')
_ATTR_DO = re.compile(r'data-ucinnostdo="([^"]*)"')
_HREF_VERSION = re.compile(r'href="([^"]+\.html)"')
_LABEL = re.compile(r"<span>([^<]+)</span>")
_NOVELA = re.compile(r'href="\.\./\.\./\.\./ZZ/[^"]+">([^<]+)</a>')


def eli_uri(year: int, number: int) -> str:
    """Build the canonical Slov-lex ELI-style URL (national, ELI Pillar I)."""
    return f"{CANONICAL_BASE}/{year}/{number}/"


def index_url(year: int, number: int) -> str:
    """The static history/index page for an act."""
    return f"{STATIC_BASE}/static/SK/ZZ/{year}/{number}/"


def version_url(year: int, number: int, version_id: str) -> str:
    """The static full-text page for a specific version."""
    return f"{STATIC_BASE}/static/SK/ZZ/{year}/{number}/{version_id}.html"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(text.replace("\xa0", " "))).strip()


def parse_versions(index_html: str) -> list[dict[str, Any]]:
    """Parse the history table of an act index page into a list of version dicts."""
    out: list[dict[str, Any]] = []
    for body in _ROW_RE.findall(index_html):
        m_iri = _ATTR_IRI.search(body)
        if not m_iri:
            continue
        version_id = m_iri.group(1).rstrip("/").rsplit("/", 1)[-1]
        vyhl = (_ATTR_VYHL.search(body) or [None, ""])[1] if _ATTR_VYHL.search(body) else ""
        od = (_ATTR_OD.search(body).group(1) if _ATTR_OD.search(body) else "") or None
        do = (_ATTR_DO.search(body).group(1) if _ATTR_DO.search(body) else "") or None
        label_m = _LABEL.search(body)
        novela_m = _NOVELA.search(body)
        is_promulgated = vyhl == "1"
        out.append({
            "version_id": version_id,
            "label": _clean(label_m.group(1)) if label_m else version_id,
            "effective_from": od,
            "effective_to": do,
            "is_promulgated": is_promulgated,
            "in_force": (do is None and not is_promulgated),
            "amended_by": _clean(novela_m.group(1)) if novela_m else None,
        })
    return out


def current_version(versions: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the in-force consolidated version (effective_to empty, not the promulgated text)."""
    for v in versions:
        if v.get("in_force"):
            return v
    dated = [v for v in versions if not v.get("is_promulgated")]
    if dated:
        return dated[-1]
    return versions[-1] if versions else None


def extract_text(version_html: str) -> str:
    """Extract the act's full text from the ``id="predpis"`` container of a version page."""
    start = version_html.find('id="predpis"')
    if start < 0:
        return ""
    end = version_html.find('id="footer"', start)
    if end < 0:
        end = len(version_html)
    chunk = version_html[start:end]
    chunk = re.sub(r"(?is)<(script|style).*?</\1>", " ", chunk)
    chunk = re.sub(r"(?i)<br\s*/?>", "\n", chunk)
    chunk = re.sub(r"(?i)</(p|div|tr|h[1-6]|li)>", "\n", chunk)
    chunk = re.sub(r"<[^>]+>", "", chunk)
    chunk = _html.unescape(chunk).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in chunk.split("\n")]
    text = "\n".join(ln for ln in lines if ln)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def build_act_record(
    year: int, number: int, versions: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build a citation-bearing record from an act's parsed version list."""
    cur = current_version(versions)
    citation = f"č. {number}/{year} Z. z."
    return {
        "year": year,
        "number": number,
        "citation": citation,
        "eli_uri": eli_uri(year, number),
        "human_readable_citation": citation,
        "source_url": index_url(year, number),
        "current_version_id": cur.get("version_id") if cur else None,
        "current_effective_from": cur.get("effective_from") if cur else None,
        "version_count": len(versions),
    }
