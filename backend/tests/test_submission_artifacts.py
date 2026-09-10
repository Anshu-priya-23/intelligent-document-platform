"""Regression checks for installability and the supplied submission snapshots."""
import json
from pathlib import Path

import pytest
from packaging.requirements import Requirement

from backend.app.schemas.document import Result

ROOT = Path(__file__).resolve().parents[2]


def test_runtime_requirements_are_individually_installable_specs():
    lines = (ROOT / "backend/requirements.txt").read_text().splitlines()
    requirements = [Requirement(line) for line in lines if line.strip() and not line.startswith("#")]
    names = {requirement.name.lower() for requirement in requirements}
    assert {"python-dotenv", "jinja2", "psycopg"} <= names
    assert len(names) == len(requirements)


@pytest.mark.parametrize("script", ["render-build.sh", "render-start.sh"])
def test_render_scripts_use_unix_line_endings(script):
    content = (ROOT / "scripts" / script).read_bytes()
    assert content.startswith(b"#!/usr/bin/env bash\n")
    assert b"\r" not in content


@pytest.mark.parametrize("kind", ["invoice", "balance_sheet", "profit_and_loss", "cash_flow_statement"])
def test_stored_sample_matches_public_contract(kind):
    payload = json.loads((ROOT / "sample_outputs" / f"{kind}_stored_result.json").read_text(encoding="utf-8"))
    result = Result.model_validate(payload)
    assert result.document_type == kind
    assert result.processing_metadata
    assert result.validation.checks
