"""Research graph schema.

Import the workflow explicitly from ``app.graph.workflow`` so tooling that only
needs the state type does not eagerly load every provider and database client.
"""

from app.graph.state import DeepResearchState

__all__ = ["DeepResearchState"]
