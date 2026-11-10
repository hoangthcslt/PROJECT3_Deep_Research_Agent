import pytest

from app.models.budget import BudgetExhaustedError, SessionBudget, estimate_input_tokens


def test_zero_limits_reject_every_resource_without_changing_counters():
    budget = SessionBudget(
        max_tavily_calls=0,
        max_scholar_calls=0,
        max_loop_iterations=0,
        max_documents_to_read=0,
        max_total_input_tokens=0,
    )

    assert not budget.can_search("tavily")
    assert not budget.can_search("scholar")
    assert not budget.can_loop()
    assert not budget.can_read_document()
    with pytest.raises(BudgetExhaustedError):
        budget.increment_search("tavily")
    with pytest.raises(BudgetExhaustedError):
        budget.increment_search("scholar")
    with pytest.raises(BudgetExhaustedError):
        budget.increment_loop()
    with pytest.raises(BudgetExhaustedError):
        budget.increment_document_read()
    with pytest.raises(BudgetExhaustedError):
        budget.reserve_input("x")

    assert budget.current_tavily_calls == 0
    assert budget.current_scholar_calls == 0
    assert budget.current_loop == 0
    assert budget.current_documents_read == 0
    assert budget.current_total_input_tokens == 0


def test_limits_allow_exact_boundary_then_reject_without_overshooting():
    budget = SessionBudget(
        max_tavily_calls=1,
        max_scholar_calls=1,
        max_loop_iterations=1,
        max_documents_to_read=1,
        max_total_input_tokens=3,
    )

    for provider in ("tavily", "scholar"):
        assert budget.can_search(provider)
        budget.increment_search(provider)
        assert not budget.can_search(provider)
        with pytest.raises(BudgetExhaustedError):
            budget.increment_search(provider)

    assert budget.can_loop()
    budget.increment_loop()
    assert not budget.can_loop()
    with pytest.raises(BudgetExhaustedError):
        budget.increment_loop()

    assert budget.can_read_document()
    budget.increment_document_read()
    assert not budget.can_read_document()
    with pytest.raises(BudgetExhaustedError):
        budget.increment_document_read()

    assert estimate_input_tokens("é") == 2
    assert budget.reserve_input("é") == 2
    assert budget.reserve_input("x") == 1
    with pytest.raises(BudgetExhaustedError):
        budget.reserve_input("x")

    assert budget.current_tavily_calls == 1
    assert budget.current_scholar_calls == 1
    assert budget.current_loop == 1
    assert budget.current_documents_read == 1
    assert budget.current_total_input_tokens == 3


def test_usage_round_trips_across_checkpoint_serialization():
    budget = SessionBudget(
        max_tavily_calls=2,
        max_scholar_calls=1,
        max_loop_iterations=2,
        max_documents_to_read=2,
        max_total_input_tokens=5,
    )
    budget.increment_search("tavily")
    budget.increment_search("scholar")
    budget.increment_loop()
    budget.increment_document_read()
    budget.reserve_input("é")

    checkpoint = budget.model_dump()
    resumed = SessionBudget.model_validate(checkpoint)
    assert resumed.model_dump() == checkpoint

    resumed.increment_search("tavily")
    resumed.increment_loop()
    resumed.increment_document_read()
    resumed.reserve_input("abc")
    next_checkpoint = resumed.model_dump()
    resumed_again = SessionBudget.model_validate(next_checkpoint)

    assert resumed_again.current_tavily_calls == 2
    assert resumed_again.current_scholar_calls == 1
    assert resumed_again.current_loop == 2
    assert resumed_again.current_documents_read == 2
    assert resumed_again.current_total_input_tokens == 5
    assert resumed_again.model_dump() == next_checkpoint


def test_independent_session_budgets_do_not_share_counters():
    template = SessionBudget(
        max_tavily_calls=2,
        max_scholar_calls=2,
        max_loop_iterations=2,
        max_documents_to_read=2,
        max_total_input_tokens=10,
    ).model_dump()
    sessions = {
        "session-a": SessionBudget.model_validate(template),
        "session-b": SessionBudget.model_validate(template),
    }

    sessions["session-a"].increment_search("tavily")
    sessions["session-a"].increment_loop()
    sessions["session-a"].increment_document_read()
    sessions["session-a"].reserve_input("one")

    assert sessions["session-b"].current_tavily_calls == 0
    assert sessions["session-b"].current_loop == 0
    assert sessions["session-b"].current_documents_read == 0
    assert sessions["session-b"].current_total_input_tokens == 0

    sessions["session-b"].increment_search("scholar")
    assert sessions["session-a"].current_scholar_calls == 0
    assert sessions["session-b"].current_scholar_calls == 1
