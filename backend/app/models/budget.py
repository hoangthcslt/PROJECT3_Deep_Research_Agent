"""
Session budget tracker — enforces hard limits on API calls, loops, and token usage
to prevent runaway costs. Maps from brainstorm: guardrails_HITL.md (Trụ cột 2).
"""

from pydantic import BaseModel, Field

from app.config import settings


class SessionBudget(BaseModel):
    """
    Tracks and enforces resource consumption limits for a single research session.
    All limits are configurable via environment variables.
    """

    # ── API Call Limits (Per Session) ──
    max_tavily_calls: int = Field(default_factory=lambda: settings.max_tavily_calls)
    current_tavily_calls: int = 0

    max_scholar_calls: int = Field(default_factory=lambda: settings.max_scholar_calls)
    current_scholar_calls: int = 0

    # ── Loop & Document Limits ──
    max_loop_iterations: int = Field(default_factory=lambda: settings.max_loops)
    current_loop: int = 0

    max_documents_to_read: int = Field(default_factory=lambda: settings.max_documents_to_read)
    current_documents_read: int = 0

    # ── Token Budget ──
    max_total_input_tokens: int = Field(default_factory=lambda: settings.max_total_input_tokens)
    current_total_input_tokens: int = 0

    def can_search(self, provider: str) -> bool:
        """Check if there's remaining budget for a search call."""
        if provider == "tavily":
            return self.current_tavily_calls < self.max_tavily_calls
        elif provider == "scholar":
            return self.current_scholar_calls < self.max_scholar_calls
        return False

    def increment_search(self, provider: str) -> None:
        """Record a search API call."""
        if provider == "tavily":
            if self.current_tavily_calls >= self.max_tavily_calls:
                raise BudgetExhaustedError(
                    f"Tavily budget exhausted: {self.current_tavily_calls}/{self.max_tavily_calls}"
                )
            self.current_tavily_calls += 1
        elif provider == "scholar":
            if self.current_scholar_calls >= self.max_scholar_calls:
                raise BudgetExhaustedError(
                    f"Scholar budget exhausted: {self.current_scholar_calls}/{self.max_scholar_calls}"
                )
            self.current_scholar_calls += 1

    def can_loop(self) -> bool:
        """Check if there's remaining loop budget (circuit breaker)."""
        return self.current_loop < self.max_loop_iterations

    def increment_loop(self) -> None:
        """Record a loop iteration."""
        self.current_loop += 1

    def can_read_document(self) -> bool:
        """Check if there's remaining document read budget."""
        return self.current_documents_read < self.max_documents_to_read

    def increment_document_read(self) -> None:
        """Record a document read."""
        self.current_documents_read += 1

    def get_usage_summary(self) -> dict:
        """Return a summary of current resource usage."""
        return {
            "tavily_calls": f"{self.current_tavily_calls}/{self.max_tavily_calls}",
            "scholar_calls": f"{self.current_scholar_calls}/{self.max_scholar_calls}",
            "loops": f"{self.current_loop}/{self.max_loop_iterations}",
            "documents_read": f"{self.current_documents_read}/{self.max_documents_to_read}",
            "input_tokens": f"{self.current_total_input_tokens}/{self.max_total_input_tokens}",
        }


class BudgetExhaustedError(Exception):
    """Raised when a session budget limit is reached."""
    pass
