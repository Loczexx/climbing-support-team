"""
Unit tests for PolicyValidator (3rd layer of enforcement).

Verifies:
1. Rejection of training proposals containing restricted actions (e.g. hangboard with finger injury).
2. Rejection of calorie cuts during RED-S / acute injury recovery.
3. Enforcement of PROPOSAL authorization (APPLIED requires ACCEPTED).
4. Enforcement of Least Privilege Matrix and Task-scoped access tokens.
"""

from services.contracts import ProposalPayload, ProposalStatus, SafetyLevel
from services.policy_validator import PolicyValidator


def test_reject_training_proposal_with_restricted_action():
    """Policy Validator blocks a training proposal if it suggests an action from restricted_actions."""
    proposal = ProposalPayload(
        proposal_id="prop_01",
        domain="training",
        status=ProposalStatus.PENDING_REVIEW,
        current_state={"exercises": ["pullups", "fingerboard"]},
        proposed_change={
            "exercises": ["hangboard_max_hangs", "core_tension"],
            "intensity": "high",
        },
        reason="Targeting finger strength",
        requires_user_confirmation=True,
    )

    active_restrictions = [
        {
            "restriction_id": "res_01",
            "category": "movement",
            "severity": SafetyLevel.RESTRICTION.value,
            "affected_area": "right_ring_finger_a2",
            "restricted_actions": ["hangboard", "campus_board", "crimp_grip"],
            "description": "Naciągnięcie troczka A2",
        }
    ]

    is_valid, error_msg = PolicyValidator.validate_training_proposal(proposal, active_restrictions)
    assert is_valid is False
    assert "restricted action 'hangboard'" in error_msg


def test_allow_safe_training_proposal_during_restriction():
    """Policy Validator allows a training proposal if restricted actions are avoided."""
    proposal = ProposalPayload(
        proposal_id="prop_02",
        domain="training",
        status=ProposalStatus.PENDING_REVIEW,
        current_state={"exercises": ["bouldering"]},
        proposed_change={
            "exercises": ["core_plank", "antagonist_pushups", "hip_mobility"],
            "intensity": "moderate",
        },
        reason="Safe training during finger deload",
        requires_user_confirmation=True,
    )

    active_restrictions = [
        {
            "restriction_id": "res_01",
            "category": "movement",
            "severity": SafetyLevel.RESTRICTION.value,
            "affected_area": "right_ring_finger_a2",
            "restricted_actions": ["hangboard", "campus_board", "crimp_grip"],
            "description": "Naciągnięcie troczka A2",
        }
    ]

    is_valid, error_msg = PolicyValidator.validate_training_proposal(proposal, active_restrictions)
    assert is_valid is True
    assert error_msg is None


def test_reject_nutrition_deficit_during_red_s_restriction():
    """Policy Validator blocks caloric reduction when RED-S / recovery restriction is active."""
    proposal = ProposalPayload(
        proposal_id="prop_03",
        domain="nutrition",
        status=ProposalStatus.PENDING_REVIEW,
        current_state={"target_calories": 2500},
        proposed_change={"target_calories": 2000},
        reason="Rapid weight cut",
        requires_user_confirmation=True,
    )

    active_restrictions = [
        {
            "restriction_id": "res_reds_01",
            "category": "dietary",
            "severity": SafetyLevel.RESTRICTION.value,
            "description": "Ryzyko RED-S i niska dostępność energii",
        }
    ]

    is_valid, error_msg = PolicyValidator.validate_nutrition_proposal(proposal, active_restrictions)
    assert is_valid is False
    assert "Cannot reduce calories" in error_msg


def test_enforce_proposal_plan_authorization():
    """Cannot apply plan changes unless status is ACCEPTED."""
    # ACCEPTED passes
    ok, err = PolicyValidator.validate_plan_authorization(ProposalStatus.ACCEPTED)
    assert ok is True
    assert err is None

    # PENDING_REVIEW or REJECTED fails
    for bad_status in [ProposalStatus.PENDING_REVIEW, ProposalStatus.REJECTED, ProposalStatus.CREATED]:
        ok, err = PolicyValidator.validate_plan_authorization(bad_status)
        assert ok is False
        assert "User approval (ACCEPTED) is required" in err


def test_validate_data_access_least_privilege_matrix():
    """Verifies matrix access enforcement and Task-scoped access tokens."""
    # Nutritionist accessing raw climb logs -> DENIED
    ok, err = PolicyValidator.validate_data_access("nutritionist", "raw_climbing_logs")
    assert ok is False
    assert "Access Denied" in err

    # Coach accessing raw meal logs -> DENIED
    ok, err = PolicyValidator.validate_data_access("climbing_coach", "raw_nutrition_logs")
    assert ok is False
    assert "Access Denied" in err

    # Nutritionist accessing injury restrictions without scope -> DENIED
    ok, err = PolicyValidator.validate_data_access("nutritionist", "injury_restrictions")
    assert ok is False
    assert "Task-scoped access" in err

    # Nutritionist accessing injury restrictions WITH scope -> ALLOWED
    ok, err = PolicyValidator.validate_data_access(
        "nutritionist",
        "injury_restrictions",
        granted_scopes=["active_injury_restrictions_summary"],
    )
    assert ok is True
    assert err is None
