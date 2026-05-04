"""Tests para PicotSpec/v1."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from prumo_assist.domains.protocol.schemas.v1 import Hypothesis, PicotSpec


def _valid_clinical() -> dict[str, Any]:
    return {
        "type": "clinical",
        "created_at": "2026-05-03",
        "last_updated": "2026-05-03",
        "version": 1,
        "population": "TCGA-BRCA + CPTAC",
        "intervention": "fusão multimodal HEALNet",
        "comparison": "melhor unimodal por modalidade",
        "outcome": "AUROC ≥ 0.85",
        "time": "retrospectivo, sem janela",
        "hypothesis": {
            "statement": "multimodal supera unimodal em ≥5 pontos AUC",
            "rationale": "decomposição PID indica sinergia sob cobertura ≥60%",
            "metrics": ["AUROC", "ECE"],
        },
    }


def test_clinical_picot_valid() -> None:
    spec = PicotSpec.model_validate(_valid_clinical())
    assert spec.type == "clinical"
    assert spec.version == 1
    assert spec.hypothesis.statement.startswith("multimodal")


def test_clinical_picot_requires_picot_fields() -> None:
    data = _valid_clinical()
    data["population"] = ""
    with pytest.raises(ValidationError) as exc:
        PicotSpec.model_validate(data)
    assert "population" in str(exc.value)


def test_methodological_picot_valid() -> None:
    data = {
        "type": "methodological",
        "created_at": "2026-05-03",
        "last_updated": "2026-05-03",
        "version": 1,
        "contribution": "predição conformal sensível à modalidade com IPW",
        "hypothesis_validity_condition": "exchangeability quebra sob MNAR",
        "hypothesis": {
            "statement": "cobertura empírica permanece próxima ao nível nominal sob MNAR",
            "rationale": "IPW corrige amostragem da calibração",
            "metrics": ["coverage", "set-size"],
        },
    }
    spec = PicotSpec.model_validate(data)
    assert spec.type == "methodological"
    assert spec.population is None
    assert spec.contribution is not None


def test_methodological_picot_requires_contribution() -> None:
    data = {
        "type": "methodological",
        "created_at": "2026-05-03",
        "last_updated": "2026-05-03",
        "version": 1,
        "contribution": "",
        "hypothesis_validity_condition": "X",
        "hypothesis": {
            "statement": "Y",
            "rationale": "Z",
            "metrics": ["m"],
        },
    }
    with pytest.raises(ValidationError) as exc:
        PicotSpec.model_validate(data)
    assert "contribution" in str(exc.value)


def test_hypothesis_metrics_must_be_non_empty() -> None:
    data = _valid_clinical()
    data["hypothesis"]["metrics"] = []
    with pytest.raises(ValidationError):
        PicotSpec.model_validate(data)


def test_version_must_be_positive() -> None:
    data = _valid_clinical()
    data["version"] = 0
    with pytest.raises(ValidationError):
        PicotSpec.model_validate(data)


def test_schema_version_constant() -> None:
    spec = PicotSpec.model_validate(_valid_clinical())
    assert spec.schema_version == "PicotSpec/v1"


def test_hypothesis_statement_required() -> None:
    h = {"statement": "", "rationale": "x", "metrics": ["m"]}
    with pytest.raises(ValidationError):
        Hypothesis.model_validate(h)
