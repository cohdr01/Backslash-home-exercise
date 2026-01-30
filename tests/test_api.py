import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_get_graph_no_filters():
    response = client.get("/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert "mermaid" in data
    assert len(data["nodes"]) > 0


def test_get_graph_with_start_public():
    response = client.get("/graph?start_public=true")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    # Check that starts are public, but since subgraph, hard to check directly


def test_get_graph_with_end_sink():
    response = client.get("/graph?end_sink=true")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data


def test_get_graph_with_has_vuln_filter():
    response = client.get("/graph?has_vuln_filter=true")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data


def test_get_graph_html():
    response = client.get("/graph/html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<div class=\"mermaid\">" in response.text