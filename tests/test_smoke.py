"""Smoke tests - require internet, hit the live Slovak Slov-lex static mirror.

Run manually:

    pytest tests/test_smoke.py -v
"""

from __future__ import annotations

import pytest

from sk_eli_mcp.server import sk_get_act, sk_get_text, sk_get_versions

# Zákon č. 18/2018 Z. z. - the Slovak data protection act (o ochrane osobných údajov).
YEAR, NUMBER = 2018, 18


@pytest.mark.asyncio
async def test_smoke_get_versions() -> None:
    res = await sk_get_versions(YEAR, NUMBER)
    assert res.total >= 5
    assert res.eli_uri == "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2018/18/"
    ids = [v.version_id for v in res.items]
    assert "vyhlasene_znenie" in ids
    in_force = [v for v in res.items if v.in_force]
    assert len(in_force) >= 1


@pytest.mark.asyncio
async def test_smoke_get_act() -> None:
    act = await sk_get_act(YEAR, NUMBER)
    assert act.citation == "č. 18/2018 Z. z."
    assert act.eli_uri == "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2018/18/"
    assert act.current_version_id
    assert act.version_count and act.version_count >= 5


@pytest.mark.asyncio
async def test_smoke_get_text_current() -> None:
    text = await sk_get_text(YEAR, NUMBER)
    assert text.content and "osobných údajov" in text.content.lower()
    assert text.version_id
    assert text.byte_size and text.byte_size > 5000
    assert text.source_url and text.source_url.startswith("https://static.slov-lex.sk/")


@pytest.mark.asyncio
async def test_smoke_get_text_promulgated() -> None:
    text = await sk_get_text(YEAR, NUMBER, version_id="vyhlasene_znenie")
    assert text.version_id == "vyhlasene_znenie"
    assert text.content and len(text.content) > 5000
