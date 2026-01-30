from abc import ABC, abstractmethod
from typing import List


class Filter(ABC):
    @abstractmethod
    def filter_starts(self, graph_service, all_starts: List[str]) -> List[str]:
        """Filter the list of possible start nodes."""
        pass

    @abstractmethod
    def filter_ends(self, graph_service, all_ends: List[str]) -> List[str]:
        """Filter the list of possible end nodes."""
        pass

    @abstractmethod
    def filter_paths(self, graph_service, paths: List[List[str]]) -> List[List[str]]:
        """Filter the list of paths."""
        pass


class StartPublicFilter(Filter):
    def filter_starts(self, graph_service, all_starts: List[str]) -> List[str]:
        return [node for node in all_starts if graph_service.get_node_data(node).get('publicExposed', False)]

    def filter_ends(self, graph_service, all_ends: List[str]) -> List[str]:
        return all_ends

    def filter_paths(self, graph_service, paths: List[List[str]]) -> List[List[str]]:
        return paths


class EndSinkFilter(Filter):
    def filter_starts(self, graph_service, all_starts: List[str]) -> List[str]:
        return all_starts

    def filter_ends(self, graph_service, all_ends: List[str]) -> List[str]:
        return [node for node in all_ends if graph_service.get_node_data(node).get('kind') in ['rds', 'sqs']]

    def filter_paths(self, graph_service, paths: List[List[str]]) -> List[List[str]]:
        return paths


class HasVulnFilter(Filter):
    def filter_starts(self, graph_service, all_starts: List[str]) -> List[str]:
        return all_starts

    def filter_ends(self, graph_service, all_ends: List[str]) -> List[str]:
        return all_ends

    def filter_paths(self, graph_service, paths: List[List[str]]) -> List[List[str]]:
        return [path for path in paths if any('vulnerabilities' in graph_service.get_node_data(node) for node in path)]