import pytest
from graph_service import GraphService


def test_graph_service_loads_data():
    gs = GraphService()
    assert len(gs.nodes) > 0
    assert len(gs.graph.nodes) > 0
    assert len(gs.graph.edges) > 0


def test_get_all_nodes():
    gs = GraphService()
    nodes = gs.get_all_nodes()
    assert isinstance(nodes, list)
    assert len(nodes) > 0


def test_get_node_data():
    gs = GraphService()
    node = gs.get_all_nodes()[0]
    data = gs.get_node_data(node)
    assert isinstance(data, dict)
    assert 'name' in data


def test_get_simple_paths():
    gs = GraphService()
    nodes = gs.get_all_nodes()
    if len(nodes) >= 2:
        start = nodes[0]
        end = nodes[1]
        paths = gs.get_simple_paths(start, end)
        assert isinstance(paths, list)
        for path in paths:
            assert isinstance(path, list)
            assert path[0] == start
            assert path[-1] == end


def test_create_subgraph_from_paths():
    gs = GraphService()
    nodes = gs.get_all_nodes()
    if len(nodes) >= 3:
        path1 = [nodes[0], nodes[1]]
        path2 = [nodes[1], nodes[2]]
        paths = [path1, path2]
        subgraph = gs.create_subgraph_from_paths(paths)
        assert len(subgraph.nodes) >= 2
        assert len(subgraph.edges) >= 1
    else:
        # If not enough nodes, skip or use available
        paths = [[nodes[0], nodes[1]]] if len(nodes) >= 2 else []
        subgraph = gs.create_subgraph_from_paths(paths)
        assert len(subgraph.nodes) >= len(paths)