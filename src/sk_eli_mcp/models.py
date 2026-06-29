"""Pydantic v2 models for the Slovak Slov-lex connector + sk-eli-mcp."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

DATASET_NOTE = (
    "The Slovak Collection of Laws (Zbierka zakonov) is served on static.slov-lex.sk, a "
    "JavaScript-free static mirror of the Slov-lex portal. Acts are addressed by year + number "
    "(e.g. 18/2018); each act has consolidated versions over time (sk_get_versions). Full text is "
    "the official HTML rendering of a version. There is no free-text search. Language: Slovak."
)

ELI_NOTE = (
    "Slovakia implements ELI (Pillar I) but the static pages carry no machine-readable ELI "
    "metadata; eli_uri is the canonical Slov-lex ELI-style URL "
    "(slov-lex.sk/pravne-predpisy/SK/ZZ/{year}/{number}), the stable national identifier. The "
    "text is served from the static.slov-lex.sk mirror (source_url)."
)


class _Tolerant(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Version(_Tolerant):
    """One consolidated version of a Slovak act."""

    version_id: str | None = None
    label: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    in_force: bool = False
    is_promulgated: bool = False
    amended_by: str | None = None
    source_url: str | None = None


class Act(_Tolerant):
    """A Slovak act (metadata + current version pointer)."""

    year: int | None = None
    number: int | None = None
    citation: str | None = None
    current_version_id: str | None = None
    current_effective_from: str | None = None
    version_count: int | None = None

    # Citation contract (Art. 4 CONSTITUTION).
    eli_uri: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None
    eli_note: str = ELI_NOTE
    dataset_note: str = DATASET_NOTE


class LawText(_Tolerant):
    """Result of ``sk_get_text`` (official HTML rendering of a version, as plain text)."""

    year: int | None = None
    number: int | None = None
    version_id: str | None = None
    citation: str | None = None
    eli_uri: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None
    format: str = "text/plain (extracted from the official Slov-lex HTML)"
    content: str | None = None
    byte_size: int | None = None
    eli_note: str = ELI_NOTE
    dataset_note: str = DATASET_NOTE


class VersionListResult(_Tolerant):
    """Result of ``sk_get_versions``."""

    year: int
    number: int
    citation: str | None = None
    eli_uri: str | None = None
    total: int = 0
    items: list[Version] = Field(default_factory=list)
    dataset_note: str = DATASET_NOTE
