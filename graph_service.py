import json
import networkx as nx


class GraphService:
    def __init__(self, data_file: str = 'train-ticket.json'):
        self.data_file = data_file
        self.nodes = {}
        self.graph = nx.DiGraph()
        self._load_data()

    def _load_data(self):
        with open(self.data_file, 'r') as f:
            data = json.load(f)

        self.nodes = {n['name']: n for n in data['nodes']}
        all_node_names = set(n['name'] for n in data['nodes'])
        for e in data['edges']:
            all_node_names.add(e['from'])
            to_list = e['to'] if isinstance(e['to'], list) else [e['to']]
            for to in to_list:
                all_node_names.add(to)

        # Add default attributes for missing nodes
        for name in all_node_names:
            if name not in self.nodes:
                self.nodes[name] = {'name': name, 'kind': 'service', 'publicExposed': False}
            self.graph.add_node(name, **self.nodes[name])

        for e in data['edges']:
            from_ = e['from']
            to_list = e['to'] if isinstance(e['to'], list) else [e['to']]
            for to in to_list:
                self.graph.add_edge(from_, to)

    def get_all_nodes(self):
        return list(self.graph.nodes())

    def get_node_data(self, node):
        return self.nodes.get(node, {})

    def get_simple_paths(self, start, end, cutoff=10):
        try:
            return list(nx.all_simple_paths(self.graph, start, end, cutoff=cutoff))
        except nx.NetworkXNoPath:
            return []

    def create_subgraph_from_paths(self, paths):
        subgraph = nx.DiGraph()
        for path in paths:
            for i in range(len(path) - 1):
                subgraph.add_edge(path[i], path[i + 1])
            for node in path:
                subgraph.add_node(node, **self.nodes[node])
        return subgraph