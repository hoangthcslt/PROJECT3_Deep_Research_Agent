"""
Neo4j Graph Database Service
Manages Knowledge Graph operations: creating nodes, relationships, and queries.

Maps from brainstorm: tool_api_data_contracts.md (Neo4j Schema).
"""

import logging
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import settings

logger = logging.getLogger(__name__)


class Neo4jService:
    """Manages Neo4j Knowledge Graph operations."""

    def __init__(self):
        self.driver: Optional[AsyncDriver] = None

    async def initialize(self):
        """Initialize Neo4j driver and create constraints/indexes."""
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

        # Create constraints and indexes
        async with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT unique_paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.paper_id IS UNIQUE",
                "CREATE CONSTRAINT unique_concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
                "CREATE CONSTRAINT unique_author_name IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE",
                "CREATE INDEX finding_session_idx IF NOT EXISTS FOR (f:Finding) ON (f.session_id)",
            ]
            for cypher in constraints:
                try:
                    await session.run(cypher)
                except Exception as e:
                    logger.warning(f"⚠️ Constraint/index creation: {e}")

        logger.info("✅ Neo4j initialized with constraints and indexes")

    async def close(self):
        """Close the Neo4j driver."""
        if self.driver:
            await self.driver.close()

    # ── Node Creation ──

    async def create_paper_node(
        self,
        paper_id: str,
        title: str,
        year: Optional[int],
        citations: Optional[int],
        url: Optional[str],
        session_id: str,
    ):
        """Create or merge a Paper node."""
        query = """
        MERGE (p:Paper {paper_id: $paper_id})
        SET p.title = $title,
            p.year = $year,
            p.citations = $citations,
            p.url = $url,
            p.session_id = $session_id
        """
        async with self.driver.session() as session:
            await session.run(
                query,
                paper_id=paper_id,
                title=title,
                year=year,
                citations=citations,
                url=url,
                session_id=session_id,
            )

    async def create_author_and_link(self, author_name: str, paper_id: str):
        """Create Author node and AUTHORED relationship to Paper."""
        query = """
        MERGE (a:Author {name: $author_name})
        WITH a
        MATCH (p:Paper {paper_id: $paper_id})
        MERGE (a)-[:AUTHORED]->(p)
        """
        async with self.driver.session() as session:
            await session.run(
                query,
                author_name=author_name,
                paper_id=paper_id,
            )

    async def create_concept_node(self, name: str, concept_type: str):
        """Create or merge a Concept node."""
        query = """
        MERGE (c:Concept {name: $name})
        SET c.type = $concept_type
        """
        async with self.driver.session() as session:
            await session.run(query, name=name, concept_type=concept_type)

    async def create_finding_node(
        self,
        finding_id: str,
        claim: str,
        confidence: float,
        session_id: str,
    ):
        """Create a Finding node."""
        query = """
        MERGE (f:Finding {finding_id: $finding_id})
        SET f.claim = $claim,
            f.confidence = $confidence,
            f.session_id = $session_id
        """
        async with self.driver.session() as session:
            await session.run(
                query,
                finding_id=finding_id,
                claim=claim,
                confidence=confidence,
                session_id=session_id,
            )

    async def link_finding_to_source(self, finding_id: str, source_id: str):
        """Create EXTRACTED_FROM relationship between Finding and Paper."""
        query = """
        MATCH (f:Finding {finding_id: $finding_id})
        MATCH (p:Paper {paper_id: $source_id})
        MERGE (f)-[:EXTRACTED_FROM]->(p)
        """
        async with self.driver.session() as session:
            await session.run(
                query,
                finding_id=finding_id,
                source_id=source_id,
            )

    async def link_paper_proposes_concept(self, paper_id: str, concept_name: str):
        """Create PROPOSES relationship between Paper and Concept."""
        query = """
        MATCH (p:Paper {paper_id: $paper_id})
        MERGE (c:Concept {name: $concept_name})
        MERGE (p)-[:PROPOSES]->(c)
        """
        async with self.driver.session() as session:
            await session.run(
                query,
                paper_id=paper_id,
                concept_name=concept_name,
            )

    # ── Query Operations ──

    async def get_session_graph(self, session_id: str) -> Dict[str, List]:
        """
        Retrieve all nodes and relationships for a session (for UI visualization).
        
        Returns:
            Dict with "nodes" and "links" arrays for react-force-graph-2d.
        """
        query = """
        MATCH (n)
        WHERE n.session_id = $session_id OR
              EXISTS { MATCH (n)-[]-(m) WHERE m.session_id = $session_id }
        OPTIONAL MATCH (n)-[r]-(m)
        WHERE m.session_id = $session_id OR n.session_id = $session_id
        RETURN collect(DISTINCT {
            id: elementId(n),
            label: labels(n)[0],
            properties: properties(n)
        }) as nodes,
        collect(DISTINCT {
            source: elementId(startNode(r)),
            target: elementId(endNode(r)),
            type: type(r)
        }) as links
        """
        async with self.driver.session() as session:
            result = await session.run(query, session_id=session_id)
            record = await result.single()

            if record:
                return {
                    "nodes": record["nodes"] or [],
                    "links": record["links"] or [],
                }

        return {"nodes": [], "links": []}


# Singleton instance
neo4j_service = Neo4jService()
