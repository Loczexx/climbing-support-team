"""
Unified Pydantic contracts for the Multi-Agent Climbing Support Team.

Defines the common message envelope (AgentMessage) and specific payloads:
- TASK
- RECOMMENDATION
- PROPOSAL
- TASK_RESULT
- RESTRICTION
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


class MessageType(str, Enum):
    TASK = "TASK"
    TASK_RESULT = "TASK_RESULT"
    RECOMMENDATION = "RECOMMENDATION"
    PROPOSAL = "PROPOSAL"
    MESSAGE = "MESSAGE"
    ESCALATION = "ESCALATION"
    CONTEXT_REQUEST = "CONTEXT_REQUEST"


class ProposalStatus(str, Enum):
    CREATED = "CREATED"
    PENDING_REVIEW = "PENDING_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"
    APPLIED = "APPLIED"
    CANCELLED = "CANCELLED"


class SafetyLevel(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    RESTRICTION = "RESTRICTION"
    CRITICAL_ESCALATION = "CRITICAL_ESCALATION"


class RestrictionPayload(BaseModel):
    """Structured restriction and safety flag schema as defined in Agent Decision Policy v0.2."""
    restriction_id: str
    category: Literal["training", "dietary", "medical", "movement"]
    severity: SafetyLevel = SafetyLevel.RESTRICTION
    affected_area: Optional[str] = None
    restricted_actions: List[str] = Field(default_factory=list)
    status: Literal["active", "resolved", "archived"] = "active"
    source: Literal["user_reported", "agent_detected", "confirmed_specialist"] = "user_reported"
    verification_status: Literal["unverified_medical", "verified_medical", "self_reported"] = "unverified_medical"
    description: str


class TaskPayload(BaseModel):
    """Payload for TASK messages dispatched by Supervisor."""
    intent: str
    user_query: str
    relevant_context: Dict[str, Any] = Field(default_factory=dict)
    granted_scopes: List[str] = Field(
        default_factory=list,
        description="Task-scoped access tokens temporarily elevating data access (e.g. relevant_injury_restrictions)"
    )


class RecommendationPayload(BaseModel):
    """Payload for inter-agent RECOMMENDATION messages (e.g. Coach -> Nutritionist)."""
    topic: str
    context_summary: str
    recommendation: str
    reason: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)
    confidence: Optional[str] = "medium"
    priority: str = "medium"
    requires_user_confirmation: bool = True
    required_data: List[str] = Field(default_factory=list)


class ProposalPayload(BaseModel):
    """Payload for PROPOSAL messages requiring user confirmation."""
    proposal_id: str
    domain: Literal["training", "nutrition", "recovery", "general"]
    status: ProposalStatus = ProposalStatus.PENDING_REVIEW
    current_state: Dict[str, Any]
    proposed_change: Dict[str, Any]
    reason: str
    evidence: List[str] = Field(default_factory=list)
    risk: Optional[str] = None
    requires_user_confirmation: Literal[True] = True


class TaskResultPayload(BaseModel):
    """Payload for TASK_RESULT messages returned by specialist agents."""
    status: Literal["SUCCESS", "FAILED", "PARTIAL", "RESTRICTION", "CRITICAL_ESCALATION"] = "SUCCESS"
    analysis: str
    recommendation: Optional[str] = None
    proposal: Optional[ProposalPayload] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(default_factory=list)
    safety_level: SafetyLevel = SafetyLevel.NORMAL


ContentPayload = Union[
    TaskPayload,
    RecommendationPayload,
    ProposalPayload,
    TaskResultPayload,
    RestrictionPayload,
    Dict[str, Any],
]


class AgentMessage(BaseModel):
    """
    Common message envelope for all agent-to-agent and supervisor communication.
    user_id is strictly required.
    """
    message_id: str
    sender: str
    receiver: str
    user_id: str = Field(..., min_length=1, description="Unique user identifier is strictly required")
    type: MessageType
    task_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content: ContentPayload
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty or whitespace")
        return v.strip()
