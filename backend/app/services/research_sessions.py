"""Application-wide in-memory research session manager."""

from langgraph.types import Command

from app.graph.workflow import research_graph
from app.services.session_manager import ResearchSessionManager

session_manager = ResearchSessionManager(
    research_graph,
    lambda decision: Command(resume=decision),
)
