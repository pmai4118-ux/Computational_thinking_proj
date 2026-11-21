"""Acceptance checks for E02 deterministic fixture provider and demo-mode label."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from source.Model.evaluation import CriterionStatus
from source.Model.ids import CriterionId, QuestionId, RubricId, SkillId, SourceId, VersionedRef
from source.Model.question import Criterion, CriterionLevel, Question, Rubric
from source.service.providers.fixture_provider import DEMO_MODE_LABEL, FixtureProvider
from source.service.providers.interfaces import EvidenceInterpreter, ProviderFailureError

FIXTURE_OUTPUTS_PATH = Path(__file__).resolve().parents[1] / 'fixtures' / 'provider_outputs.json'


def test_e02_fixture_provider_returns_offline_observations_with_demo_label_and_errors() -> None:
    provider = FixtureProvider.from_json_file(FIXTURE_OUTPUTS_PATH)
    assert isinstance(provider, EvidenceInterpreter)
    raw = json.loads(FIXTURE_OUTPUTS_PATH.read_text(encoding='utf-8'))['records']
    rubric = Rubric(
        id=RubricId('rubric.c03.inventory_race.v1'),
        version=1,
        criteria=tuple(
            Criterion(
                id=CriterionId(cid),
                label=cid,
                expected_evidence=('A', 'B'),
                levels=(CriterionLevel(0, '0'), CriterionLevel(1, '1'), CriterionLevel(2, '2')),
            )
            for cid in ('c03.race', 'c03.atomicity', 'c03.concurrent_tests')
        ),
    )
    question = Question(
        id=QuestionId('case.c03.inventory_race.v1'),
        version=1,
        category='technical_case',
        language='vi',
        prompt='Kho con mot san pham...',
        skill_ids=(SkillId('skill.backend.data_consistency'),),
        rubric_ref=VersionedRef(rubric.id, rubric.version),
        source_id=SourceId('source.c03.concurrent_inventory'),
    )
    batch = provider.interpret(
        question=question,
        rubric=rubric,
        answer_text=raw['case.c03.inventory_race.v1::correct']['answer_text'],
    )
    assert batch.demo_mode_label == DEMO_MODE_LABEL
    assert all(obs.status is CriterionStatus.MET for obs in batch.observations)

    unresolved = provider.interpret(
        question=question,
        rubric=rubric,
        answer_text=raw['case.c03.inventory_race.v1::insufficient_evidence']['answer_text'],
    )
    assert all(obs.status is CriterionStatus.INSUFFICIENT_EVIDENCE for obs in unresolved.observations)

    with pytest.raises(ProviderFailureError) as err:
        provider.interpret(question=question, rubric=rubric, answer_text='x', fixture_key='provider_timeout')
    assert err.value.code == 'PROVIDER_TIMEOUT'
