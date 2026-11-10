"""Neo4j operations with session-scoped node keys and relationships."""

import logging
from typing import Dict, List, Optional

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.config import settings

logger = logging.getLogger(__name__)


def _scoped_key(session_id: str, local_id: str) -> str:
    return f"{session_id}:{local_id}"


class Neo4jService:
    """Create/query graph data without sharing nodes across research sessions."""

    def __init__(self):
        self.driver: Optional[AsyncDriver] = None

    async def initialize(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        async with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT unique_paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.paper_id IS UNIQUE",
                "CREATE CONSTRAINT unique_concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
                "CREATE CONSTRAINT unique_author_name IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE",
                "CREATE CONSTRAINT unique_source_key IF NOT EXISTS FOR (s:Source) REQUIRE s.source_key IS UNIQUE",
                "CREATE CONSTRAINT unique_finding_key IF NOT EXISTS FOR (f:Finding) REQUIRE f.finding_key IS UNIQUE",
                "CREATE CONSTRAINT unique_author_key IF NOT EXISTS FOR (a:Author) REQUIRE a.author_key IS UNIQUE",
                "CREATE CONSTRAINT unique_concept_key IF NOT EXISTS FOR (c:Concept) REQUIRE c.concept_key IS UNIQUE",
                "CREATE INDEX finding_session_idx IF NOT EXISTS FOR (f:Finding) ON (f.session_id)",
            ]
            for query in constraints:
                try:
                    await session.run(query)
                except Exception as exc:
                    # Existing databases may run an older Neo4j version; operations
                    # still use scoped keys and do not require a data migration.
                    logger.warning("Neo4j constraint setup failed (%s)", type(exc).__name__)
        logger.info("Neo4j initialized")

    async def close(self):
        if self.driver:
            await self.driver.close()
            self.driver = None

    def _require_driver(self):
        if self.driver is None:
            raise RuntimeError("Neo4j driver is not initialized.")
        return self.driver

    async def create_source_node(
        self, source_id: str, title: str, url: Optional[str],
        source_type: str, session_id: str,
    ):
        query = """
        MERGE (s:Source {source_key: $source_key})
        SET s.source_id = $source_id,
            s.title = $title,
            s.url = $url,
            s.source_type = $source_type,
            s.session_id = $session_id
        """
        async with self._require_driver().session() as session:
            await session.run(
                query,
                source_key=_scoped_key(session_id, source_id),
                source_id=source_id,
                title=title,
                url=url,
                source_type=source_type,
                session_id=session_id,
            )

    async def create_paper_node(
        self,
        paper_id: str,
        title: str,
        year: Optional[int],
        citations: Optional[int],
        url: Optional[str],
        session_id: str,
    ):
        """Store a Paper under a session-scoped key; retained for later phases."""
        query = """
        MERGE (p:Paper {paper_id: $paper_key})
        SET p.source_key = $source_key,
            p.source_id = $paper_id,
            p.title = $title,
            p.year = $year,
            p.citations = $citations,
            p.url = $url,
            p.session_id = $session_id
        """
        async with self._require_driver().session() as session:
            await session.run(
                query,
                paper_key=_scoped_key(session_id, paper_id),
                source_key=_scoped_key(session_id, paper_id),
                paper_id=paper_id,
                title=title,
                year=year,
                citations=citations,
                url=url,
                session_id=session_id,
            )

    async def create_author_and_link(self, author_name: str, paper_id: str, session_id: str):
        query = """
        MERGE (a:Author {author_key: $author_key})
        SET a.display_name = $author_name, a.session_id = $session_id
        WITH a
        MATCH (p:Paper {paper_id: $paper_key, session_id: $session_id})
        MERGE (a)-[:AUTHORED]->(p)
        """
        async with self._require_driver().session() as session:
            await session.run(
                query,
                author_key=_scoped_key(session_id, author_name),
                author_name=author_name,
                paper_key=_scoped_key(session_id, paper_id),
                session_id=session_id,
            )

    async def create_concept_node(self, name: str, concept_type: str, session_id: str):
        query = """
        MERGE (c:Concept {concept_key: $concept_key})
        SET c.display_name = $name, c.type = $concept_type, c.session_id = $session_id
        """
        async with self._require_driver().session() as session:
            await session.run(
                query,
                concept_key=_scoped_key(session_id, name),
                name=name,
                concept_type=concept_type,
                session_id=session_id,
            )

    async def create_finding_node(
        self, finding_id: str, claim: str, confidence: float, session_id: str,
    ):
        query = """
        MERGE (f:Finding {finding_key: $finding_key})
        SET f.finding_id = $finding_id,
            f.claim = $claim,
            f.confidence = $confidence,
            f.session_id = $session_id
        """
        async with self._require_driver().session() as session:
            await session.run(
                query,
                finding_key=_scoped_key(session_id, finding_id),
                finding_id=finding_id,
                claim=claim,
                confidence=confidence,
                session_id=session_id,
            )

    async def link_finding_to_source(
        self, finding_id: str, source_id: str, session_id: str,
    ):
        query = """
        MATCH (f:Finding {finding_key: $finding_key, session_id: $session_id})
        MATCH (s)
        WHERE (s:Source OR s:Paper)
          AND s.source_key = $source_key
          AND s.session_id = $session_id
        MERGE (f)-[:EXTRACTED_FROM]->(s)
        """
        async with self._require_driver().session() as session:
            await session.run(
                query,
                finding_key=_scoped_key(session_id, finding_id),
                source_key=_scoped_key(session_id, source_id),
                session_id=session_id,
            )

    async def link_paper_proposes_concept(
        self, paper_id: str, concept_name: str, session_id: str,
    ):
        query = """
        MATCH (p:Paper {paper_id: $paper_key, session_id: $session_id})
        MERGE (c:Concept {concept_key: $concept_key})
        ON CREATE SET c.display_name = $concept_name, c.session_id = $session_id
        MERGE (p)-[:PROPOSES]->(c)
        """
        async with self._require_driver().session() as session:
            await session.run(
                query,
                paper_key=_scoped_key(session_id, paper_id),
                concept_key=_scoped_key(session_id, concept_name),
                concept_name=concept_name,
                session_id=session_id,
            )

    async def get_session_graph(self, session_id: str) -> Dict[str, List]:
        query = """
        MATCH (n)
        WHERE n.session_id = $session_id
        OPTIONAL MATCH (n)-[r]-(m)
        WHERE m.session_id = $session_id
        RETURN collect(DISTINCT {
            id: elementId(n),
            label: labels(n)[0],
            properties: properties(n)
        }) AS nodes,
        collect(DISTINCT CASE WHEN r IS NULL THEN NULL ELSE {
            source: elementId(startNode(r)),
            target: elementId(endNode(r)),
            type: type(r)
        } END) AS links
        """
        async with self._require_driver().session() as session:
            result = await session.run(query, session_id=session_id)
            record = await result.single()
        if record:
            return {
                "nodes": record["nodes"] or [],
                "links": [link for link in (record["links"] or []) if link],
            }
        return {"nodes": [], "links": []}


neo4j_service = Neo4jService()
