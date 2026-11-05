"""
Tests for MemoryManager and Least Privilege data isolation (Agent Decision Policy v0.2).

Verifies:
1. get_coach_context returns training logs, movement restrictions, weight trend, but ZERO nutrition logs.
2. get_nutritionist_context returns meal logs, dietary restrictions, enriched training overview, but ZERO raw climb logs.
3. Task-scoped access allows Nutritionist to see injury restrictions ONLY when explicitly granted.
4. Supervisor context gets high-level summaries and safety flags.
"""

import pytest
from services.memory import MemoryManager


@pytest.fixture
def seeded_memory():
    """Initializes in-memory SQLite and populates it with test user and activities."""
    mem = MemoryManager(db_path=":memory:")

    # 1. Create User
    mem.create_user(
        user_id="usr_test_01",
        name="Aleksander",
        age=25,
        gender="M",
        height_cm=180.0,
        weight_kg=72.5,
        experience_level="advanced",
    )

    # 2. Add Goals
    mem.add_goal(
        goal_id="goal_01",
        user_id="usr_test_01",
        title="RP 7c na Frankenjurze",
        target_grade="7c",
        deadline="2026-06-30",
    )

    # 3. Add Restrictions (one movement, one dietary)
    mem.add_restriction(
        restriction_id="restr_01",
        user_id="usr_test_01",
        category="movement",
        description="Lekkie naciągnięcie troczka A2 palca serdecznego prawej dłoni",
        severity="RESTRICTION",
        affected_area="right_ring_finger_a2",
        restricted_actions=["crimp_grip", "hangboard", "campus_board"],
        status="active",
        source="user_reported",
        verification_status="unverified_medical",
    )
    mem.add_restriction(
        restriction_id="restr_02",
        user_id="usr_test_01",
        category="dietary",
        description="Nietolerancja laktozy",
        severity="WARNING",
        status="active",
        source="user_reported",
    )

    # 4. Add Training Log
    mem.add_training_log(
        log_id="train_01",
        user_id="usr_test_01",
        session_date="2026-11-03",
        session_type="bouldering",
        details={"problems_sent": ["7A", "7B", "7A+"], "hardest_flash": "7A"},
        rpe=8.5,
        duration_min=105,
    )

    # 5. Add Nutrition Log
    mem.add_nutrition_log(
        log_id="nutr_01",
        user_id="usr_test_01",
        log_date="2026-11-03",
        meal_type="breakfast",
        description="Owsianka z borówkami, orzechami i odżywką roślinną",
        calories=650.0,
        protein_g=35.0,
        carbs_g=85.0,
        fat_g=18.0,
        is_complete=True,
    )

    # 6. Add Weight Log
    mem.add_weight_log(
        log_id="w_01",
        user_id="usr_test_01",
        log_date="2026-11-03",
        weight_kg=72.5,
        body_fat_pct=11.2,
        measurement_method="dxa",
    )

    return mem


def test_coach_context_least_privilege(seeded_memory):
    """
    Verification:
    Calling get_coach_context must return climbing history, movement restrictions with actions,
    and weight trend (Policy v0.2 Section 2), and must NOT contain any meal/nutrition records.
    """
    ctx = seeded_memory.get_coach_context("usr_test_01")

    # 1. Must contain profile and goals
    assert ctx["profile"]["weight_kg"] == 72.5
    assert len(ctx["goals"]) == 1
    assert ctx["goals"][0]["target_grade"] == "7c"

    # 2. Must contain movement restrictions with structured actions
    assert len(ctx["movement_restrictions"]) == 1
    restr = ctx["movement_restrictions"][0]
    assert restr["affected_area"] == "right_ring_finger_a2"
    assert "hangboard" in restr["restricted_actions"]

    # 3. Must contain training logs
    assert len(ctx["training_logs"]) == 1
    assert ctx["training_logs"][0]["session_type"] == "bouldering"
    assert ctx["training_logs"][0]["details"]["hardest_flash"] == "7A"

    # 4. Must contain weight trend (Policy v0.2 Section 2)
    assert len(ctx["weight_trend"]) >= 1
    assert ctx["weight_trend"][0]["weight_kg"] == 72.5

    # 5. CRITICAL: Absolute absence of nutrition data
    assert "nutrition_logs" not in ctx
    assert "dietary_restrictions" not in ctx
    serialized = str(ctx)
    assert "Owsianka" not in serialized
    assert "laktozy" not in serialized


def test_nutritionist_context_least_privilege(seeded_memory):
    """
    Verification:
    Calling get_nutritionist_context returns nutrition logs, dietary restrictions,
    and enriched training load summary (type, duration, rpe), but NO raw climb routes.
    """
    ctx = seeded_memory.get_nutritionist_context("usr_test_01")

    # 1. Contains dietary restriction, NOT movement restriction
    assert len(ctx["dietary_restrictions"]) == 1
    assert "Nietolerancja laktozy" in ctx["dietary_restrictions"][0]["description"]
    assert "movement_restrictions" not in ctx

    # 2. Contains nutrition logs
    assert len(ctx["nutrition_logs"]) == 1
    assert ctx["nutrition_logs"][0]["calories"] == 650.0
    assert "Owsianka" in ctx["nutrition_logs"][0]["description"]

    # 3. Contains enriched load summary (counts + recent session overviews)
    assert ctx["training_load_summary"]["session_count"] == 1
    assert ctx["training_load_summary"]["avg_rpe"] == 8.5
    overview = ctx["training_load_summary"]["recent_sessions_overview"]
    assert len(overview) == 1
    assert overview[0]["type"] == "bouldering"
    assert overview[0]["duration_min"] == 105
    # Does NOT contain raw routes or boulder problems
    assert "problems_sent" not in str(overview)

    # 4. Without granted scopes, does NOT have injury restrictions
    assert "task_scoped_injury_restrictions" not in ctx


def test_nutritionist_task_scoped_access(seeded_memory):
    """
    Verification:
    When granted_scopes includes 'active_injury_restrictions_summary',
    Nutritionist receives the injury restriction summary (Policy v0.2 Section 3).
    """
    ctx = seeded_memory.get_nutritionist_context(
        "usr_test_01",
        granted_scopes=["active_injury_restrictions_summary"],
    )

    assert "task_scoped_injury_restrictions" in ctx
    injuries = ctx["task_scoped_injury_restrictions"]
    assert len(injuries) == 1
    assert injuries[0]["affected_area"] == "right_ring_finger_a2"
    assert "hangboard" in injuries[0]["restricted_actions"]


def test_supervisor_context_least_privilege(seeded_memory):
    """
    Verification:
    Supervisor gets high-level status, all active safety flags, but NO raw set-by-set or meal logs.
    """
    ctx = seeded_memory.get_supervisor_context("usr_test_01")

    # Has all restrictions (both movement and dietary)
    assert len(ctx["active_restrictions"]) == 2

    # Has last workout high-level summary
    assert ctx["last_workout_summary"]["session_type"] == "bouldering"

    # Does NOT have full raw logs
    assert "training_logs" not in ctx
    assert "nutrition_logs" not in ctx
