import pytest
from graph_service import GraphService
from filters import StartPublicFilter, EndSinkFilter, HasVulnFilter


@pytest.fixture
def graph_service():
    return GraphService()


def test_start_public_filter_filter_starts(graph_service):
    filter_obj = StartPublicFilter()
    all_starts = graph_service.get_all_nodes()
    filtered = filter_obj.filter_starts(graph_service, all_starts)
    # Assuming there are public nodes, check that all filtered are public
    for node in filtered:
        assert graph_service.get_node_data(node).get('publicExposed', False) == True


def test_start_public_filter_filter_ends(graph_service):
    filter_obj = StartPublicFilter()
    all_ends = graph_service.get_all_nodes()
    filtered = filter_obj.filter_ends(graph_service, all_ends)
    assert filtered == all_ends  # Should not filter ends


def test_start_public_filter_filter_paths(graph_service):
    filter_obj = StartPublicFilter()
    paths = [['node1', 'node2'], ['node3', 'node4']]
    filtered = filter_obj.filter_paths(graph_service, paths)
    assert filtered == paths  # Should not filter paths


def test_end_sink_filter_filter_ends(graph_service):
    filter_obj = EndSinkFilter()
    all_ends = graph_service.get_all_nodes()
    filtered = filter_obj.filter_ends(graph_service, all_ends)
    for node in filtered:
        assert graph_service.get_node_data(node).get('kind') in ['rds', 'sqs']


def test_end_sink_filter_filter_starts(graph_service):
    filter_obj = EndSinkFilter()
    all_starts = graph_service.get_all_nodes()
    filtered = filter_obj.filter_starts(graph_service, all_starts)
    assert filtered == all_starts


def test_end_sink_filter_filter_paths(graph_service):
    filter_obj = EndSinkFilter()
    paths = [['node1', 'node2'], ['node3', 'node4']]
    filtered = filter_obj.filter_paths(graph_service, paths)
    assert filtered == paths


def test_has_vuln_filter_filter_paths(graph_service):
    filter_obj = HasVulnFilter()
    # Find paths with and without vuln
    vuln_paths = []
    no_vuln_paths = []
    for node in graph_service.get_all_nodes():
        if 'vulnerabilities' in graph_service.get_node_data(node):
            vuln_paths.append([node])
        else:
            no_vuln_paths.append([node])
    all_paths = vuln_paths + no_vuln_paths
    filtered = filter_obj.filter_paths(graph_service, all_paths)
    assert len(filtered) == len(vuln_paths)
    for path in filtered:
        assert any('vulnerabilities' in graph_service.get_node_data(n) for n in path)


def test_has_vuln_filter_filter_starts(graph_service):
    filter_obj = HasVulnFilter()
    all_starts = graph_service.get_all_nodes()
    filtered = filter_obj.filter_starts(graph_service, all_starts)
    assert filtered == all_starts


def test_has_vuln_filter_filter_ends(graph_service):
    filter_obj = HasVulnFilter()
    all_ends = graph_service.get_all_nodes()
    filtered = filter_obj.filter_ends(graph_service, all_ends)
    assert filtered == all_ends