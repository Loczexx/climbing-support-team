"""
Tests for unified Pydantic contracts.

Verifies:
1. All JSON examples from Supervisor Specification v0.2 validate cleanly.
2. Missing or blank user_id is rejected with ValidationError.
3. Envelope and payload typing integrity.
"""

import pytest
from pydantic import ValidationError

from services.contracts import (
    AgentMessage,
    MessageType,
    ProposalPayload,
    ProposalStatus,
    RecommendationPayload,
    TaskPayload,
    TaskResultPayload,
)


def test_validate_task_example_from_supervisor_spec():
    """Verify TASK JSON example from Supervisor SPEC section 11.1."""
    raw_task = {
        "message_id": "msg_sup_101",
        "sender": "supervisor",
        "receiver": "climbing_coach",
        "user_id": "usr_12345",
        "type": "TASK",
        "task_id": "task_20261104_01",
        "timestamp": "2026-11-04T14:30:00Z",
        "content": {
            "intent": "evaluate_workout_readiness",
            "user_query": "Czy mogę dzisiaj zrobić mocny trening na hangboardzie?",
            "relevant_context": {
                "target_goal": "Lead 7c RP",
                "last_climbing_sessions_summary": "2026-11-02: Bouldering (RPE 8, 2h)",
                "skin_condition": "good",
                "active_restrictions": [],
            },
        },
    }

    msg = AgentMessage.model_validate(raw_task)
    assert msg.message_id == "msg_sup_101"
    assert msg.user_id == "usr_12345"
    assert msg.type == MessageType.TASK
    payload = TaskPayload.model_validate(msg.content)
    assert payload.intent == "evaluate_workout_readiness"
    assert payload.relevant_context["target_goal"] == "Lead 7c RP"


def test_validate_recommendation_example_from_supervisor_spec():
    """Verify RECOMMENDATION JSON example from Supervisor SPEC section 11.2."""
    raw_rec = {
        "message_id": "msg_rec_201",
        "sender": "climbing_coach",
        "receiver": "nutritionist",
        "user_id": "usr_12345",
        "type": "RECOMMENDATION",
        "task_id": "task_20261104_02",
        "timestamp": "2026-11-04T14:32:00Z",
        "content": {
            "topic": "energy_expenditure_increase",
            "context_summary": "Zwiększono częstotliwość jednostek o wysokiej intensywności z 3 do 4 w tygodniu.",
            "recommendation": "Dostosowanie podaży energii i węglowodanów w dniach okołotreningowych.",
            "priority": "medium",
            "requires_user_confirmation": True,
        },
    }

    msg = AgentMessage.model_validate(raw_rec)
    assert msg.type == MessageType.RECOMMENDATION
    payload = RecommendationPayload.model_validate(msg.content)
    assert payload.topic == "energy_expenditure_increase"
    assert payload.requires_user_confirmation is True


def test_validate_proposal_example_from_supervisor_spec():
    """Verify PROPOSAL JSON example from Supervisor SPEC section 11.3."""
    raw_proposal = {
        "proposal_id": "prop_20261104_01",
        "domain": "training",
        "status": "PENDING_REVIEW",
        "current_state": {
            "weekly_sessions": 3,
            "focus": "hypertrophy",
        },
        "proposed_change": {
            "weekly_sessions": 4,
            "focus": "finger_strength_max_hangs",
        },
        "reason": "Zakończenie bloku adaptacji anatomicznej, przejście do fazy siły maksymalnej przed projektem RP.",
        "evidence": ["Schoenfeld 2020", "Bechtel 2019"],
        "risk": "Zwiększone obciążenie aparatu więzadłowo-ścięgnistego palców; wymagany deload po 4 tygodniach.",
        "requires_user_confirmation": True,
    }

    proposal = ProposalPayload.model_validate(raw_proposal)
    assert proposal.proposal_id == "prop_20261104_01"
    assert proposal.status == ProposalStatus.PENDING_REVIEW
    assert proposal.domain == "training"
    assert proposal.requires_user_confirmation is True

    # Check proposal inside an AgentMessage envelope
    envelope = {
        "message_id": "msg_prop_001",
        "sender": "climbing_coach",
        "receiver": "supervisor",
        "user_id": "usr_12345",
        "type": "PROPOSAL",
        "task_id": "task_20261104_01",
        "timestamp": "2026-11-04T14:35:00Z",
        "content": raw_proposal,
    }
    msg = AgentMessage.model_validate(envelope)
    assert msg.type == MessageType.PROPOSAL
    assert ProposalPayload.model_validate(msg.content).proposal_id == "prop_20261104_01"


def test_validate_task_result_example_from_supervisor_spec():
    """Verify TASK_RESULT JSON example from Supervisor SPEC section 11.4."""
    raw_result = {
        "message_id": "msg_resp_301",
        "sender": "climbing_coach",
        "receiver": "supervisor",
        "user_id": "usr_12345",
        "type": "TASK_RESULT",
        "task_id": "task_20261104_01",
        "timestamp": "2026-11-04T14:30:45Z",
        "content": {
            "status": "SUCCESS",
            "analysis": "Palce są zregenerowane po 48h przerwy od sesji boulderingowej.",
            "recommendation": "Możesz wykonać sesję Max Hangs (5x10s przy 85% masy maks.), z 3-minutową przerwą.",
            "confidence": 0.9,
            "evidence_ids": ["ev_hangboard_01"],
        },
    }

    msg = AgentMessage.model_validate(raw_result)
    assert msg.type == MessageType.TASK_RESULT
    payload = TaskResultPayload.model_validate(msg.content)
    assert payload.status == "SUCCESS"
    assert payload.confidence == 0.9


def test_reject_message_with_missing_user_id():
    """Verification requirement: reject message if user_id is missing."""
    invalid_data = {
        "message_id": "msg_invalid_01",
        "sender": "supervisor",
        "receiver": "climbing_coach",
        # user_id is deliberately omitted
        "type": "TASK",
        "task_id": "task_01",
        "timestamp": "2026-11-04T14:30:00Z",
        "content": {
            "intent": "test",
            "user_query": "hello",
        },
    }

    with pytest.raises(ValidationError) as excinfo:
        AgentMessage.model_validate(invalid_data)

    errors = excinfo.value.errors()
    assert any(err["loc"] == ("user_id",) for err in errors)


def test_reject_message_with_empty_or_whitespace_user_id():
    """Verification requirement: reject message if user_id is empty or whitespace."""
    for empty_val in ["", "   "]:
        invalid_data = {
            "message_id": "msg_invalid_02",
            "sender": "supervisor",
            "receiver": "climbing_coach",
            "user_id": empty_val,
            "type": "TASK",
            "task_id": "task_01",
            "timestamp": "2026-11-04T14:30:00Z",
            "content": {
                "intent": "test",
                "user_query": "hello",
            },
        }

        with pytest.raises(ValidationError) as excinfo:
            AgentMessage.model_validate(invalid_data)

        errors = excinfo.value.errors()
        assert any(err["loc"] == ("user_id",) for err in errors)
