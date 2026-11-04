"""
Tests for MemoryManager and Least Privilege data isolation.

Verifies:
1. get_coach_context returns training logs and movement restrictions, but ZERO nutrition logs.
2. get_nutritionist_context returns meal logs and dietary restrictions, but ZERO raw climb logs.
3. Supervisor context gets high-level summaries and safety flags.
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
    )
    mem.add_restriction(
        restriction_id="restr_02",
        user_id="usr_test_01",
        category="dietary",
        description="Nietolerancja laktozy",
        severity="WARNING",
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

    return mem


def test_coach_context_least_privilege(seeded_memory):
    """
    Verification:
    Calling get_coach_context must return climbing history and movement restrictions,
    and must NOT contain any meal/nutrition records.
    """
    ctx = seeded_memory.get_coach_context("usr_test_01")

    # 1. Must contain profile and goals
    assert ctx["profile"]["weight_kg"] == 72.5
    assert len(ctx["goals"]) == 1
    assert ctx["goals"][0]["target_grade"] == "7c"

    # 2. Must contain movement restrictions ONLY
    assert len(ctx["movement_restrictions"]) == 1
    assert "troczka A2" in ctx["movement_restrictions"][0]["description"]

    # 3. Must contain training logs
    assert len(ctx["training_logs"]) == 1
    assert ctx["training_logs"][0]["session_type"] == "bouldering"
    assert ctx["training_logs"][0]["details"]["hardest_flash"] == "7A"

    # 4. CRITICAL: Absolute absence of nutrition data
    assert "nutrition_logs" not in ctx
    assert "dietary_restrictions" not in ctx
    # Double check that no nutrition logs leak into training logs
    serialized = str(ctx)
    assert "Owsianka" not in serialized
    assert "laktozy" not in serialized


def test_nutritionist_context_least_privilege(seeded_memory):
    """
    Verification:
    Calling get_nutritionist_context returns nutrition logs and dietary restrictions,
    and training volume summary, but NO raw climb routes or raw bouldering logs.
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

    # 3. Contains aggregated load summary, NOT raw boulders
    assert ctx["training_load_summary"]["session_count"] == 1
    assert ctx["training_load_summary"]["avg_rpe"] == 8.5
    assert "training_logs" not in ctx

    serialized = str(ctx)
    assert "troczka A2" not in serialized
    assert "7B" not in serialized


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
