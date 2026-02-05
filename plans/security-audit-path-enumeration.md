# Optimized Strategy for Complete Path Enumeration (Security Audit)

## The Challenge

Finding ALL paths from public services to sinks is fundamentally expensive because:
- Graph can have exponential number of paths
- Networks with cycles can have infinite paths (handled by `simple_paths` constraint)
- Large microservices graphs can have thousands of paths

**Key Insight:** You cannot avoid enumeration if you truly need ALL paths, but you can:

1. **Optimize the enumeration algorithm**
2. **Add strict limits and timeouts**
3. **Use streaming/pagination**
4. **Leverage parallelism**
5. **Use incremental computation**

---

## Optimization Strategies for Complete Path Enumeration

### 1. Early Filtering Before Path Finding

**Current approach (inefficient):**
```python
# graph_query_service.py:24-29
for start in all_starts:
    for end in all_ends:
        paths = get_simple_paths(start, end)  # Enumerate all, then filter
```

**Optimized approach:**
```python
# Filter early - only find paths that CAN reach a sink
for start in all_starts:
    # Pre-compute reachable nodes from start
    reachable = nx.descendants(G, start)
    valid_ends = [end for end in all_ends if end in reachable]
    
    for end in valid_ends:
        paths = get_simple_paths(start, end)
```

**Even better - Pre-compute sink reachability once:**
```python
def precompute_sink_reachability(G, sink_nodes):
    """Compute which public nodes can reach any sink."""
    # Reverse the graph for efficient backward reachability
    reverse_G = G.reverse()
    
    sink_reachable = {}
    for sink in sink_nodes:
        # Find all nodes that can reach this sink
        ancestors = nx.ancestors(reverse_G, sink)
        for node in ancestors:
            if node not in sink_reachable:
                sink_reachable[node] = []
            sink_reachable[node].append(sink)
    
    return sink_reachable

# Usage
sink_reachable = precompute_sink_reachability(G, sink_nodes)
for start in all_starts:
    valid_ends = sink_reachable.get(start, [])
    for end in valid_ends:
        paths = get_simple_paths(start, end)
```

---

### 2. Parallel Path Enumeration

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

def find_paths_for_pair(args):
    """Find all paths for a single start-end pair."""
    start, end, G, cutoff = args
    try:
        return (start, end, list(nx.all_simple_paths(G, start, end, cutoff=cutoff)))
    except nx.NetworkXNoPath:
        return (start, end, [])

def find_all_paths_parallel(G, starts, ends, cutoff=10, max_workers=None):
    """Find all paths using parallel processing."""
    if max_workers is None:
        max_workers = multiprocessing.cpu_count()
    
    # Pre-filter to only valid start-end pairs
    valid_pairs = []
    for start in starts:
        for end in ends:
            if start != end and nx.has_path(G, start, end):
                valid_pairs.append((start, end, G, cutoff))
    
    all_paths = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(find_paths_for_pair, pair): pair for pair in valid_pairs}
        
        for future in as_completed(futures):
            start, end, paths = future.result()
            all_paths[(start, end)] = paths
    
    return all_paths
```

---

### 3. Streaming Path Results

```python
import asyncio
from typing import Generator, List, Tuple

def stream_all_paths(G, starts, ends, cutoff=10, batch_size=100) -> Generator[List[Tuple], None, None]:
    """
    Stream all paths in batches to avoid memory exhaustion.
    
    Yields:
        List of (start, end, path) tuples in batches
    """
    batch = []
    path_count = 0
    
    for start in starts:
        for end in ends:
            if start == end:
                continue
            
            try:
                for path in nx.all_simple_paths(G, start, end, cutoff=cutoff):
                    batch.append((start, end, list(path)))
                    path_count += 1
                    
                    if len(batch) >= batch_size:
                        yield batch
                        batch = []
                        
            except nx.NetworkXNoPath:
                continue
    
    # Yield remaining paths
    if batch:
        yield batch

# Usage in API
@app.get("/graph/audit")
def get_all_paths_audit(
    start_public: bool = True, 
    end_sink: bool = True,
    cutoff: int = 10,
    batch_size: int = 100
):
    """Get all paths for security audit with streaming."""
    filters = []
    if start_public:
        filters.append(StartPublicFilter())
    if end_sink:
        filters.append(EndSinkFilter())
    
    # Get filtered nodes
    gs = graph_query_service.graph_service
    all_starts = gs.get_all_nodes()
    all_ends = gs.get_all_nodes()
    
    for filter_obj in filters:
        all_starts = filter_obj.filter_starts(gs, all_starts)
        all_ends = filter_obj.filter_ends(gs, all_ends)
    
    # Stream results
    def generate():
        for batch in stream_all_paths(gs.graph, all_starts, all_ends, cutoff, batch_size):
            yield format_batch_for_json(batch)
    
    return StreamingResponse(generate(), media_type="application/json")
```

---

### 4. Incremental Computation with Checkpoints

```python
import hashlib
import json
from pathlib import Path
from datetime import datetime

class IncrementalPathComputer:
    """Compute paths incrementally with checkpointing."""
    
    def __init__(self, cache_dir="path_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_cache_key(self, starts, ends, cutoff):
        """Generate cache key from parameters."""
        key_data = f"{sorted(starts)}_{sorted(ends)}_{cutoff}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def save_checkpoint(self, key, state):
        """Save computation state."""
        checkpoint_file = self.cache_dir / f"{key}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump({
                'timestamp': datetime.utcnow().isoformat(),
                'state': state
            }, f)
    
    def load_checkpoint(self, key):
        """Load computation state."""
        checkpoint_file = self.cache_dir / f"{key}.json"
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r') as f:
                return json.load(f)['state']
        return None
    
    def compute_paths_incremental(self, G, starts, ends, cutoff=10, resume=True):
        """
        Compute paths incrementally with checkpoint support.
        
        Returns:
            Dict of (start, end) -> List of paths
        """
        key = self.get_cache_key(starts, ends, cutoff)
        
        # Try to resume from checkpoint
        if resume:
            checkpoint = self.load_checkpoint(key)
            if checkpoint:
                completed_pairs = checkpoint['completed_pairs']
                all_paths = checkpoint['all_paths']
            else:
                completed_pairs = set()
                all_paths = {}
        else:
            completed_pairs = set()
            all_paths = {}
        
        # Continue computation
        for start in starts:
            for end in ends:
                if start == end:
                    continue
                    
                pair_key = (start, end)
                if pair_key in completed_pairs:
                    continue
                
                if not nx.has_path(G, start, end):
                    completed_pairs.add(pair_key)
                    continue
                
                # Compute paths for this pair
                paths = list(nx.all_simple_paths(G, start, end, cutoff=cutoff))
                all_paths[pair_key] = paths
                completed_pairs.add(pair_key)
                
                # Checkpoint every 10 pairs
                if len(completed_pairs) % 10 == 0:
                    self.save_checkpoint(key, {
                        'completed_pairs': list(completed_pairs),
                        'all_paths': all_paths
                    })
        
        # Final save
        self.save_checkpoint(key, {
            'completed_pairs': list(completed_pairs),
            'all_paths': all_paths
        })
        
        return all_paths
```

---

### 5. Bounded Path Finding with Completeness Guarantee

```python
from collections import defaultdict
from typing import Dict, List, Set, Tuple

def find_all_paths_bounded(
    G, 
    starts: Set[str], 
    ends: Set[str], 
    cutoff: int = 10,
    max_paths_per_pair: int = 10000,
    timeout_seconds: float = 30
) -> Tuple[Dict[Tuple[str, str], List[List[str]]], Dict]:
    """
    Find all paths with bounds and timeout.
    
    Returns:
        - paths: Dict of (start, end) -> List of paths
        - metadata: Info about limits hit, counts, etc.
    """
    import signal
    import time
    
    start_time = time.time()
    paths = defaultdict(list)
    metadata = {
        'total_paths': 0,
        'pairs_completed': 0,
        'pairs_timed_out': set(),
        'pairs_maxed': set(),
        'timed_out': False
    }
    
    def timeout_handler(signum, frame):
        metadata['timed_out'] = True
        raise TimeoutError("Path enumeration timed out")
    
    # Set up timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        for start in starts:
            for end in ends:
                if start == end:
                    continue
                
                pair_key = (start, end)
                
                try:
                    for path in nx.all_simple_paths(G, start, end, cutoff=cutoff):
                        if time.time() - start_time > timeout_seconds:
                            metadata['timed_out'] = True
                            break
                        
                        if len(paths[pair_key]) >= max_paths_per_pair:
                            metadata['pairs_maxed'].add(pair_key)
                            break
                        
                        paths[pair_key].append(list(path))
                        metadata['total_paths'] += 1
                    
                    metadata['pairs_completed'] += 1
                    
                except nx.NetworkXNoPath:
                    metadata['pairs_completed'] += 1
                    continue
                
                if metadata['timed_out']:
                    metadata['pairs_timed_out'].add(pair_key)
                    break
            
            if metadata['timed_out']:
                break
    
    finally:
        signal.alarm(0)  # Cancel alarm
    
    return dict(paths), metadata
```

---

## Recommended Architecture for Security Audit API

```mermaid
graph TB
    subgraph "API Layer"
        A[POST /audit/paths] --> B[Validate Parameters]
        B --> C{Cache Hit?}
    end
    
    subgraph "Cache Layer"
        C -->|Yes| D[Return Cached Result]
        C -->|No| E[Create Job]
    end
    
    subgraph "Background Processing"
        E --> F[Job Queue]
        F --> G[Worker Process]
        G --> H[Path Computer]
        H --> I[Stream Results]
        I --> J[Checkpoint Storage]
    end
    
    subgraph "Result Delivery"
        J --> K[Polling: GET /audit/job/{id}]
        J --> L[WebSocket Push]
        D --> M[Return Immediately]
    end
    
    subgraph "Limits & Safety"
        H --> N[Max Paths Per Pair]
        H --> O[Timeout Guard]
        H --> P[Memory Monitor]
        N --> Q[Partial Results Flag]
        O --> Q
        P --> Q
    end
```

---

## API Endpoint Design

```python
@app.post("/graph/audit/paths")
def create_audit_job(
    start_public: bool = True,
    end_sink: bool = True,
    cutoff: int = 10,
    max_paths_per_pair: int = 10000,
    timeout_seconds: int = 300,
    priority: str = "normal"
):
    """
    Create background job for complete path enumeration.
    
    Returns job ID immediately.
    Poll /audit/job/{id} for status and results.
    """
    job_id = job_queue.enqueue(
        compute_audit_paths,
        start_public=start_public,
        end_sink=end_sink,
        cutoff=cutoff,
        max_paths_per_pair=max_paths_per_pair,
        timeout_seconds=timeout_seconds,
        priority=priority
    )
    
    return {"job_id": job_id, "status": "queued"}

@app.get("/audit/job/{job_id}")
def get_job_status(job_id: str):
    """Get job status and partial results."""
    job = job_queue.get_job(job_id)
    
    if job.is_complete:
        return {
            "status": "complete",
            "result_url": f"/audit/job/{job_id}/result",
            "metadata": job.metadata
        }
    elif job.has_partial:
        return {
            "status": "in_progress",
            "progress": job.progress,
            "partial_results": job.partial_results,
            "metadata": job.metadata
        }
    else:
        return {
            "status": "queued",
            "position_in_queue": job.queue_position
        }

@app.get("/audit/job/{job_id}/result")
def download_results(job_id: str, format: str = "json"):
    """Download complete results."""
    job = job_queue.get_job(job_id)
    
    if format == "json":
        return job.result
    elif format == "csv":
        return convert_to_csv(job.result)
    elif format == "gzip":
        return compress_result(job.result)
```

---

## Summary of Recommendations

| Priority | Optimization | Impact | Implementation Effort |
|----------|--------------|--------|----------------------|
| 1 | Pre-filter start/end pairs | High | Low |
| 2 | Add strict limits (max_paths, timeout) | High | Low |
| 3 | Streaming response | High | Medium |
| 4 | Parallel processing | Medium | Medium |
| 5 | Incremental computation | Medium | High |
| 6 | Background jobs with polling | High | High |

---

## Quick Wins to Implement Now

1. **Add `max_paths` parameter** to `get_simple_paths()`:
   ```python
   def get_simple_paths(self, start, end, cutoff=10, max_paths=10000):
       paths = []
       for path in nx.all_simple_paths(self.graph, start, end, cutoff=cutoff):
           if len(paths) >= max_paths:
               break
           paths.append(path)
       return paths
   ```

2. **Add timeout wrapper**:
   ```python
   import signal
   
   def timeout_handler(signum, frame):
       raise TimeoutError("Path enumeration timed out")
   
   signal.signal(signal.SIGALRM, timeout_handler)
   signal.alarm(30)  # 30 second timeout
   ```

3. **Pre-filter valid pairs**:
   ```python
   # Only call get_simple_paths if path exists
   if nx.has_path(G, start, end):
       paths = get_simple_paths(start, end)
   ```
