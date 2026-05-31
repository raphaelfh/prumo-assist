"""End-to-end tests pros orquestradores `propagate` e `diff_against_last_adr`."""

from __future__ import annotations

from pathlib import Path

import pytest

from prumo_assist.domains.protocol.ops import (
    PropagateReport,
    diff_against_last_adr,
    propagate,
)
from prumo_assist.domains.protocol.picot_io import write_picot
from prumo_assist.domains.protocol.schemas.v1 import Hypothesis, PicotSpec


def _spec(version: int = 1, population: str = "TCGA") -> PicotSpec:
    return PicotSpec(
        type="clinical",
        created_at="2026-05-03",
        last_updated="2026-05-03",
        version=version,
        population=population,
        intervention="HEALNet",
        comparison="best unimodal",
        outcome="AUROC ≥ 0.85",
        time="retrospectivo",
        hypothesis=Hypothesis(
            statement="multimodal supera unimodal",
            rationale="PID",
            metrics=["AUROC"],
        ),
    )


def _bootstrap_pj(tmp_path: Path) -> Path:
    pj = tmp_path / "pj_demo"
    (pj / "docs").mkdir(parents=True)
    (pj / "docs" / "protocol.md").write_text(
        "# Protocolo do estudo\n\n## Contexto da pesquisa\n\nProse humana inicial.\n"
    )
    (pj / "docs" / "project_guide.md").write_text(
        "---\ntitle: Projeto\n---\n\n# Projeto\n\nIntro.\n"
    )
    (pj / "docs" / "decisions").mkdir()
    return pj


def test_propagate_inserts_blocks_when_absent(tmp_path: Path) -> None:
    pj = _bootstrap_pj(tmp_path)
    write_picot(pj, _spec())
    report = propagate(pj)
    assert isinstance(report, PropagateReport)
    assert report.protocol_status == "inserted"
    assert report.project_status == "inserted"
    protocol_text = (pj / "docs" / "protocol.md").read_text()
    project_text = (pj / "docs" / "project_guide.md").read_text()
    assert "<!-- picot:begin" in protocol_text
    assert "<!-- picot:begin" in project_text
    assert "TCGA" in protocol_text
    assert "Pergunta de pesquisa" in project_text


def test_propagate_replaces_blocks_when_present(tmp_path: Path) -> None:
    pj = _bootstrap_pj(tmp_path)
    write_picot(pj, _spec(population="TCGA"))
    propagate(pj)
    write_picot(pj, _spec(population="TCGA + CPTAC"))
    propagate(pj)
    text = (pj / "docs" / "protocol.md").read_text()
    assert "TCGA + CPTAC" in text
    assert text.count("<!-- picot:begin") == 1


def test_propagate_unchanged_when_hash_matches(tmp_path: Path) -> None:
    pj = _bootstrap_pj(tmp_path)
    write_picot(pj, _spec())
    propagate(pj)
    report = propagate(pj)
    assert report.protocol_status == "unchanged"
    assert report.project_status == "unchanged"


def test_propagate_raises_when_picot_missing(tmp_path: Path) -> None:
    pj = _bootstrap_pj(tmp_path)
    with pytest.raises(FileNotFoundError):
        propagate(pj)


def test_diff_against_last_adr_no_baseline_returns_diff_with_no_changes(
    tmp_path: Path,
) -> None:
    pj = _bootstrap_pj(tmp_path)
    write_picot(pj, _spec())
    out = diff_against_last_adr(pj)
    assert out is not None
    assert out.changes == []
    assert out.has_structural is False


def test_diff_against_last_adr_detects_structural_change(tmp_path: Path) -> None:
    """Após ADR inicial, mudar campo estrutural produz diff structural."""
    from prumo_assist.domains.protocol.adr import compose_adr, next_adr_number
    from prumo_assist.domains.protocol.diff import PicotDiff

    pj = _bootstrap_pj(tmp_path)
    spec_v1 = _spec(version=1, population="TCGA")
    write_picot(pj, spec_v1)
    decisions = pj / "docs" / "decisions"
    body = compose_adr(
        adr_number=next_adr_number(pj),
        spec=spec_v1,
        diff=PicotDiff(changes=[]),
        motivation="versão inicial",
        supersedes_path=None,
        date="2026-05-03",
    )
    (decisions / "adr-0001-picot-v1-versao-inicial.md").write_text(body)

    spec_v2 = _spec(version=2, population="TCGA + CPTAC")
    write_picot(pj, spec_v2)
    diff = diff_against_last_adr(pj)
    assert diff is not None
    assert diff.has_structural is True
    assert any(c.field == "population" for c in diff.changes)
