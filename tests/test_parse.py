"""Offline parse tests - version-table + text extraction against committed fixtures."""

from __future__ import annotations

from pathlib import Path

from sk_eli_mcp.citations import (
    build_act_record,
    current_version,
    eli_uri,
    extract_text,
    parse_versions,
)

FIX = Path(__file__).parent / "fixtures"


def _index() -> str:
    return (FIX / "index_2018_18.html").read_text(encoding="utf-8")


def test_eli_uri():
    assert eli_uri(2018, 18) == "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2018/18/"


def test_parse_versions_from_index():
    versions = parse_versions(_index())
    assert len(versions) >= 5
    ids = [v["version_id"] for v in versions]
    assert "vyhlasene_znenie" in ids
    assert "20240701" in ids  # the latest dated version present
    promulgated = [v for v in versions if v["is_promulgated"]]
    assert promulgated and promulgated[0]["version_id"] == "vyhlasene_znenie"


def test_current_version_is_in_force():
    versions = parse_versions(_index())
    cur = current_version(versions)
    assert cur is not None
    # The in-force version has no effective_to.
    assert cur["effective_to"] is None
    assert not cur["is_promulgated"]


def test_build_act_record_citation():
    rec = build_act_record(2018, 18, parse_versions(_index()))
    assert rec["citation"] == "č. 18/2018 Z. z."
    assert rec["eli_uri"] == "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2018/18/"
    assert rec["version_count"] >= 5
    assert rec["current_version_id"]


def test_extract_text_from_predpis():
    html = (
        '<div id="banner">nav junk</div>'
        '<div id="predpis"><h1>§ 1</h1><p>Tento z&aacute;kon upravuje ochranu '
        'osobn&yacute;ch&nbsp;&uacute;dajov.</p><p>§ 2 Vymedzenie pojmov</p></div>'
        '<div id="footer">Kontakt</div>'
    )
    text = extract_text(html)
    assert "§ 1" in text
    assert "ochranu osobných údajov." in text
    assert "nav junk" not in text
    assert "Kontakt" not in text
