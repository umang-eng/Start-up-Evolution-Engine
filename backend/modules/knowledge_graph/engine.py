"""Founder Knowledge Graph — links people, projects, features, technologies,
customers, competitors, decisions, risks, goals, and action items.
Continuously evolves from meeting discussions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    PERSON = "person"
    PROJECT = "project"
    FEATURE = "feature"
    TECHNOLOGY = "technology"
    CUSTOMER = "customer"
    COMPETITOR = "competitor"
    DECISION = "decision"
    RISK = "risk"
    GOAL = "goal"
    ACTION = "action"
    COMPANY = "company"
    MARKET = "market"
    INVESTOR = "investor"
    MEETING = "meeting"
    DOCUMENT = "document"


class RelationshipType(str, Enum):
    WORKS_ON = "works_on"
    OWNS = "owns"
    DEPENDS_ON = "depends_on"
    COMPETES_WITH = "competes_with"
    DECIDED_IN = "decided_in"
    ASSIGNED_TO = "assigned_to"
    CREATED_IN = "created_in"
    AFFECTS = "affects"
    MENTIONS = "mentions"
    FOLLOWS = "follows"
    BLOCKS = "blocks"
    RELATED_TO = "related_to"
    REPORTS_TO = "reports_to"
    INVESTED_IN = "invested_in"
    USES = "uses"
    REPLACES = "replaces"
    SUPERSEDES = "supersedes"


class KnowledgeNode(BaseModel):
    """A node in the knowledge graph."""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    node_type: NodeType
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=1000)
    properties: dict[str, Any] = Field(default_factory=dict)
    source_meetings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    is_active: bool = True


class KnowledgeEdge(BaseModel):
    """A relationship between two nodes."""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    source_id: str
    target_id: str
    relationship: RelationshipType
    weight: float = Field(ge=0.0, le=1.0, default=0.5)
    properties: dict[str, Any] = Field(default_factory=dict)
    source_meeting_id: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_active: bool = True


class KnowledgeGraph(BaseModel):
    """Complete knowledge graph state."""
    project_id: str
    nodes: list[KnowledgeNode] = Field(default_factory=list)
    edges: list[KnowledgeEdge] = Field(default_factory=list)
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_nodes: int = 0
    total_edges: int = 0


class GraphQuery(BaseModel):
    """A semantic query against the knowledge graph."""
    query: str
    node_types: list[NodeType] = Field(default_factory=list)
    max_results: int = 10
    include_relationships: bool = True


class GraphQueryResult(BaseModel):
    """Result of a knowledge graph query."""
    nodes: list[KnowledgeNode]
    relationships: list[dict[str, Any]]
    summary: str
    confidence: float


class KnowledgeGraphEngine:
    """Builds and queries the founder knowledge graph."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.graph = KnowledgeGraph(project_id=project_id)

    def add_node(self, node_type: NodeType, name: str, **kwargs) -> KnowledgeNode:
        """Add a node to the graph, deduplicating by name+type."""
        existing = self._find_node(node_type, name)
        if existing:
            existing.updated_at = datetime.now(timezone.utc).isoformat()
            existing.properties.update(kwargs.get("properties", {}))
            if kwargs.get("source_meeting_id"):
                existing.source_meetings.append(kwargs["source_meeting_id"])
            return existing

        node = KnowledgeNode(
            node_type=node_type,
            name=name,
            description=kwargs.get("description", ""),
            properties=kwargs.get("properties", {}),
            source_meetings=[kwargs.get("source_meeting_id", "")] if kwargs.get("source_meeting_id") else [],
            confidence=kwargs.get("confidence", 0.8),
        )
        self.graph.nodes.append(node)
        self.graph.total_nodes = len(self.graph.nodes)
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: RelationshipType,
        **kwargs,
    ) -> KnowledgeEdge:
        """Add an edge between two nodes."""
        existing = self._find_edge(source_id, target_id, relationship)
        if existing:
            existing.weight = max(existing.weight, kwargs.get("weight", 0.5))
            return existing

        edge = KnowledgeEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            weight=kwargs.get("weight", 0.5),
            properties=kwargs.get("properties", {}),
            source_meeting_id=kwargs.get("source_meeting_id", ""),
        )
        self.graph.edges.append(edge)
        self.graph.total_edges = len(self.graph.edges)
        return edge

    def _find_node(self, node_type: NodeType, name: str) -> KnowledgeNode | None:
        """Find existing node by type and name."""
        name_lower = name.lower()
        for node in self.graph.nodes:
            if node.node_type == node_type and node.name.lower() == name_lower and node.is_active:
                return node
        return None

    def _find_edge(self, source_id: str, target_id: str, relationship: RelationshipType) -> KnowledgeEdge | None:
        """Find existing edge."""
        for edge in self.graph.edges:
            if (edge.source_id == source_id and edge.target_id == target_id
                    and edge.relationship == relationship and edge.is_active):
                return edge
        return None

    def get_node(self, node_id: str) -> KnowledgeNode | None:
        """Get a node by ID."""
        for node in self.graph.nodes:
            if node.id == node_id and node.is_active:
                return node
        return None

    def get_neighbors(self, node_id: str, relationship: RelationshipType | None = None) -> list[tuple[KnowledgeNode, RelationshipType]]:
        """Get neighboring nodes."""
        neighbors = []
        for edge in self.graph.edges:
            if not edge.is_active:
                continue
            if relationship and edge.relationship != relationship:
                continue
            if edge.source_id == node_id:
                target = self.get_node(edge.target_id)
                if target:
                    neighbors.append((target, edge.relationship))
            elif edge.target_id == node_id:
                source = self.get_node(edge.source_id)
                if source:
                    neighbors.append((source, edge.relationship))
        return neighbors

    def search(self, query: str) -> list[KnowledgeNode]:
        """Search nodes by name or description."""
        q = query.lower()
        return [
            node for node in self.graph.nodes
            if node.is_active and (q in node.name.lower() or q in node.description.lower())
        ]

    def get_by_type(self, node_type: NodeType) -> list[KnowledgeNode]:
        """Get all nodes of a type."""
        return [n for n in self.graph.nodes if n.node_type == node_type and n.is_active]

    def update_from_meeting(
        self,
        meeting_id: str,
        people: list[str],
        features: list[str],
        technologies: list[str],
        competitors: list[str],
        customers: list[str],
        decisions: list[str],
        risks: list[str],
        goals: list[str],
        action_items: list[str],
    ) -> list[KnowledgeNode]:
        """Update graph from meeting extraction."""
        nodes = []

        for p in people:
            node = self.add_node(NodeType.PERSON, p, source_meeting_id=meeting_id)
            nodes.append(node)

        for f in features:
            node = self.add_node(NodeType.FEATURE, f, source_meeting_id=meeting_id)
            nodes.append(node)

        for t in technologies:
            node = self.add_node(NodeType.TECHNOLOGY, t, source_meeting_id=meeting_id)
            nodes.append(node)

        for c in competitors:
            node = self.add_node(NodeType.COMPETITOR, c, source_meeting_id=meeting_id)
            nodes.append(node)

        for c in customers:
            node = self.add_node(NodeType.CUSTOMER, c, source_meeting_id=meeting_id)
            nodes.append(node)

        for d in decisions:
            node = self.add_node(NodeType.DECISION, d, source_meeting_id=meeting_id)
            nodes.append(node)

        for r in risks:
            node = self.add_node(NodeType.RISK, r, source_meeting_id=meeting_id)
            nodes.append(node)

        for g in goals:
            node = self.add_node(NodeType.GOAL, g, source_meeting_id=meeting_id)
            nodes.append(node)

        for a in action_items:
            node = self.add_node(NodeType.ACTION, a, source_meeting_id=meeting_id)
            nodes.append(node)

        # Create edges: people work on the project
        project_node = self.add_node(NodeType.PROJECT, self.project_id, source_meeting_id=meeting_id)
        for p_node in [n for n in nodes if n.node_type == NodeType.PERSON]:
            self.add_edge(p_node.id, project_node.id, RelationshipType.WORKS_ON, source_meeting_id=meeting_id)

        # Create edges: decisions related to features
        decision_nodes = [n for n in nodes if n.node_type == NodeType.DECISION]
        feature_nodes = [n for n in nodes if n.node_type == NodeType.FEATURE]
        for d_node in decision_nodes:
            for f_node in feature_nodes:
                self.add_edge(d_node.id, f_node.id, RelationshipType.RELATED_TO, source_meeting_id=meeting_id)

        return nodes

    def to_dict(self) -> dict[str, Any]:
        """Export graph as dictionary."""
        return {
            "nodes": [n.model_dump() for n in self.graph.nodes if n.is_active],
            "edges": [e.model_dump() for e in self.graph.edges if e.is_active],
            "stats": {
                "total_nodes": self.graph.total_nodes,
                "total_edges": self.graph.total_edges,
            },
        }
