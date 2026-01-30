from typing import List, Dict, Any
import networkx as nx
from graph_service import GraphService
from filters import Filter


class GraphQueryService:
    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service

    def get_filtered_graph(self, filters: List[Filter]) -> Dict[str, Any]:
        all_starts = self.graph_service.get_all_nodes()
        all_ends = self.graph_service.get_all_nodes()

        # Apply start filters
        for filter_obj in filters:
            all_starts = filter_obj.filter_starts(self.graph_service, all_starts)

        # Apply end filters
        for filter_obj in filters:
            all_ends = filter_obj.filter_ends(self.graph_service, all_ends)

        matching_paths = []
        for start in all_starts:
            for end in all_ends:
                if start == end:
                    continue
                paths = self.graph_service.get_simple_paths(start, end)
                matching_paths.extend(paths)

        # Apply path filters
        for filter_obj in filters:
            matching_paths = filter_obj.filter_paths(self.graph_service, matching_paths)

        # If no filters, return full graph
        if not filters:
            subgraph = self.graph_service.graph.copy()
        else:
            subgraph = self.graph_service.create_subgraph_from_paths(matching_paths)

        # Build response
        nodes_list = [{"name": n, **attr} for n, attr in subgraph.nodes(data=True)]
        edges_list = [{"from": u, "to": v} for u, v in subgraph.edges()]

        # Mermaid
        mermaid = "graph TD\n"
        for n in subgraph.nodes():
            label = n.replace('-', '_')
            mermaid += f"{label}[{n}]\n"
        for u, v in subgraph.edges():
            u_label = u.replace('-', '_')
            v_label = v.replace('-', '_')
            mermaid += f"{u_label} --> {v_label}\n"

        # Add class definitions for coloring by rules
        mermaid += "classDef publicExposed fill:#00ff00\n"
        mermaid += "classDef vulnerable fill:#ff0000\n"
        mermaid += "classDef nonService fill:#ffff00\n"
        mermaid += "classDef service fill:#add8e6\n"

        # Assign classes to nodes
        for n in subgraph.nodes():
            node_data = self.graph_service.get_node_data(n)
            label = n.replace('-', '_')
            if node_data.get('publicExposed', False):
                class_name = 'publicExposed'
            elif 'vulnerabilities' in node_data and node_data['vulnerabilities']:
                class_name = 'vulnerable'
            elif node_data.get('kind', 'service') != 'service':
                class_name = 'nonService'
            else:
                class_name = 'service'
            mermaid += f"class {label} {class_name}\n"

        return {
            "nodes": nodes_list,
            "edges": edges_list,
            "mermaid": mermaid
        }