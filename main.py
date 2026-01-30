from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
from graph_service import GraphService
from graph_query_service import GraphQueryService
from filters import StartPublicFilter, EndSinkFilter, HasVulnFilter

app = FastAPI(title="Train Ticket Graph API", description="API for querying the train ticket microservices graph")

# Dependency injection: Instantiate services
graph_service = GraphService()
graph_query_service = GraphQueryService(graph_service)

@app.get("/graph")
def get_graph(start_public: bool = False, end_sink: bool = False, has_vuln_filter: bool = False):
    """
    Get filtered graph based on criteria.
    - start_public: Include routes starting from public services
    - end_sink: Include routes ending in sinks (rds/sqs)
    - has_vuln_filter: Include routes that have at least one vulnerable node
    If no filters are enabled, returns the full graph.
    """
    filters = []
    if start_public:
        filters.append(StartPublicFilter())
    if end_sink:
        filters.append(EndSinkFilter())
    if has_vuln_filter:
        filters.append(HasVulnFilter())

    return graph_query_service.get_filtered_graph(filters)

@app.get("/graph/html")
def get_graph_html(start_public: bool = False, end_sink: bool = False, has_vuln_filter: bool = False):
    """
    Get the graph as an HTML page with Mermaid diagram.
    """
    graph_data = get_graph(start_public, end_sink, has_vuln_filter)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Train Ticket Graph</title>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true }});
        </script>
    </head>
    <body>
        <h1>Filtered Graph</h1>
        <div class="mermaid">
{graph_data['mermaid']}
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)