"""Tests for knowledge graph system."""

import pytest
from backend.modules.knowledge_graph.engine import (
    KnowledgeGraphEngine, KnowledgeNode, KnowledgeEdge,
    NodeType, RelationshipType, KnowledgeGraph
)


class TestKnowledgeNode:
    def test_create_node(self):
        node = KnowledgeNode(
            node_type=NodeType.PERSON,
            name="John Doe",
            description="CTO",
            properties={"role": "technical"},
        )
        assert node.node_type == NodeType.PERSON
        assert node.name == "John Doe"
        assert node.is_active is True


class TestKnowledgeGraph:
    def test_create_graph(self):
        graph = KnowledgeGraph(project_id="proj-001")
        assert graph.project_id == "proj-001"
        assert graph.total_nodes == 0


class TestKnowledgeGraphEngine:
    def test_initialization(self):
        engine = KnowledgeGraphEngine(project_id="proj-001")
        assert engine.project_id == "proj-001"

    def test_add_node(self):
        engine = KnowledgeGraphEngine(project_id="proj-001")
        node = engine.add_node(NodeType.PERSON, "Alice", description="CEO")
        assert node.name == "Alice"
        assert engine.graph.total_nodes == 1

    def test_deduplication(self):
        engine = KnowledgeGraphEngine(project_id="proj-001")
        node1 = engine.add_node(NodeType.PERSON, "Alice")
        node2 = engine.add_node(NodeType.PERSON, "Alice")
        assert node1.id == node2.id
        assert engine.graph.total_nodes == 1

    def test_add_edge(self):
        engine = KnowledgeGraphEngine(project_id="proj-001")
        node1 = engine.add_node(NodeType.PERSON, "Alice")
        node2 = engine.add_node(NodeType.PROJECT, "MyApp")
        edge = engine.add_edge(node1.id, node2.id, RelationshipType.WORKS_ON)
        assert edge.source_id == node1.id
        assert engine.graph.total_edges == 1

    def test_get_neighbors(self):
        engine = KnowledgeGraphEngine(project_id="proj-001")
        node1 = engine.add_node(NodeType.PERSON, "Alice")
        node2 = engine.add_node(NodeType.PROJECT, "MyApp")
        engine.add_edge(node1.id, node2.id, RelationshipType.WORKS_ON)
        neighbors = engine.get_neighbors(node1.id)
        assert len(neighbors) == 1
        assert neighbors[0][0].name == "MyApp"

    def test_search(self):
        engine = KnowledgeGraphEngine(project_id="proj-001")
        engine.add_node(NodeType.FEATURE, "User Authentication")
        engine.add_node(NodeType.FEATURE, "Payment Processing")
        results = engine.search("authentication")
        assert len(results) == 1

    def test_get_by_type(self):
        engine = KnowledgeGraphEngine(project_id="proj-001")
        engine.add_node(NodeType.PERSON, "Alice")
        engine.add_node(NodeType.PERSON, "Bob")
        engine.add_node(NodeType.FEATURE, "Auth")
        people = engine.get_by_type(NodeType.PERSON)
        assert len(people) == 2

    def test_update_from_meeting(self):
        engine = KnowledgeGraphEngine(project_id="proj-001")
        nodes = engine.update_from_meeting(
            meeting_id="m1",
            people=["Alice", "Bob"],
            features=["Auth", "Payments"],
            technologies=["React", "PostgreSQL"],
            competitors=["Google"],
            customers=[],
            decisions=[],
            risks=[],
            goals=[],
            action_items=[],
        )
        assert len(nodes) >= 5
        assert engine.graph.total_nodes >= 5

    def test_to_dict(self):
        engine = KnowledgeGraphEngine(project_id="proj-001")
        engine.add_node(NodeType.PERSON, "Alice")
        data = engine.to_dict()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 1
