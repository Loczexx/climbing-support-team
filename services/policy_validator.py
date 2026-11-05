"""
Policy Validator — 3rd layer of enforcement (deterministic Python rules).

Enforces:
1. Schema conformity.
2. Restriction violation checks (e.g. blocking restricted_actions like crimp_grip or hangboard when finger injury is active).
3. Plan modification authorization (APPLIED requires ACCEPTED status).
4. Data access validation (Least Privilege Matrix & Task-scoped access tokens).
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from services.contracts import ProposalPayload, ProposalStatus, SafetyLevel


class PolicyValidationError(Exception):
    """Raised when an agent action or proposal violates safety or access policy."""
    pass


class PolicyValidator:
    """
    Deterministic rule engine validating agent outputs, proposals, and data accesses.
    """

    @staticmethod
    def validate_training_proposal(
        proposal: ProposalPayload,
        active_restrictions: List[Dict[str, Any]],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates that a proposed training change does not violate any active restrictions.
        Checks proposed_change against restricted_actions in active RESTRICTION or CRITICAL_ESCALATION items.
        """
        proposed_str = json.dumps(proposal.proposed_change).lower()

        for restr in active_restrictions:
            severity = restr.get("severity", "")
            if severity in [SafetyLevel.RESTRICTION.value, SafetyLevel.CRITICAL_ESCALATION.value]:
                restricted_actions = restr.get("restricted_actions", [])
                for action in restricted_actions:
                    action_lower = action.lower().replace("_", " ")
                    action_token = action.lower()
                    if action_token in proposed_str or action_lower in proposed_str:
                        return (
                            False,
                            f"Safety violation: Proposed training includes restricted action '{action}' "
                            f"prohibited by restriction '{restr.get('description', '')}' (area: {restr.get('affected_area', 'unspecified')}).",
                        )

        return True, None

    @staticmethod
    def validate_nutrition_proposal(
        proposal: ProposalPayload,
        active_restrictions: List[Dict[str, Any]],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates that a proposed nutrition change does not violate dietary or energy availability safety gates.
        Prevents caloric deficit if RED-S, acute injury recovery, or energy deficit restrictions are active.
        """
        proposed_change = proposal.proposed_change
        proposed_calories = proposed_change.get("target_calories") or proposed_change.get("calories")

        current_calories = proposal.current_state.get("target_calories") or proposal.current_state.get("calories")

        for restr in active_restrictions:
            severity = restr.get("severity", "")
            desc = restr.get("description", "").lower()
            if severity in [SafetyLevel.RESTRICTION.value, SafetyLevel.CRITICAL_ESCALATION.value]:
                # Check for low energy availability / RED-S / recovery flags
                if any(k in desc for k in ["red-s", "niska dostępność energii", "energy availability", "kontuzja", "uraz"]):
                    if proposed_calories is not None and current_calories is not None:
                        if proposed_calories < current_calories:
                            return (
                                False,
                                f"Safety violation: Cannot reduce calories when restriction '{restr.get('description')}' is active.",
                            )

        return True, None

    @staticmethod
    def validate_plan_authorization(status: ProposalStatus) -> Tuple[bool, Optional[str]]:
        """
        Enforces that plans can only enter APPLIED state if previously ACCEPTED by user.
        """
        if status != ProposalStatus.ACCEPTED:
            return (
                False,
                f"Authorization error: Cannot apply plan modifications with status '{status}'. User approval (ACCEPTED) is required.",
            )
        return True, None

    @staticmethod
    def validate_data_access(
        agent_role: str,
        data_category: str,
        granted_scopes: Optional[List[str]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates data access requests against the Least Privilege Matrix (Section 2)
        and Dynamic Access Control (Section 3).
        """
        scopes = granted_scopes or []

        # Strict rules
        if agent_role == "nutritionist" and data_category == "raw_climbing_logs":
            return False, "Access Denied: General Nutritionist cannot access raw climbing session logs."

        if agent_role == "climbing_coach" and data_category == "raw_nutrition_logs":
            return False, "Access Denied: Climbing Coach cannot access raw nutrition meal logs."

        if agent_role == "nutritionist" and data_category == "injury_restrictions":
            if "active_injury_restrictions_summary" not in scopes and "relevant_injury_restrictions" not in scopes:
                return (
                    False,
                    "Access Denied: General Nutritionist requires Task-scoped access ('active_injury_restrictions_summary') to view injury restrictions.",
                )

        if data_category in ["full_medical_history", "psychological_history"]:
            return False, f"Access Denied: '{data_category}' is strictly inaccessible to all agents."

        return True, None
