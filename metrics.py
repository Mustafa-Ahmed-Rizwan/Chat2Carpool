# metrics.py
from prometheus_client import Counter, Histogram, start_http_server

# 1. COUNTERS (Things that go up)
# Counts total intents classified (request vs offer)
INTENT_COUNTER = Counter(
    "chat2carpool_intent_total", 
    "Total intents classified", 
    ["intent_type"] # Label: 'ride_request', 'ride_offer', 'other'
)

# Counts database operations
DB_OPERATION_COUNTER = Counter(
    "chat2carpool_db_ops_total",
    "Total database operations",
    ["operation", "status"] # e.g. op="save_request", status="success"
)

# Counts matching results
MATCH_COUNTER = Counter(
    "chat2carpool_matches_found_total",
    "Total matches found",
    ["type"] # 'exact', 'partial'
)

# 2. HISTOGRAMS (Things we measure duration for)
# Measures how long LLM takes to respond
LLM_LATENCY = Histogram(
    "chat2carpool_llm_duration_seconds",
    "Time taken for LLM operations",
    ["operation"] # 'classify', 'extract', 'confirm'
)

def init_metrics(port=8000):
    """
    Start a separate HTTP server just for metrics.
    Prometheus will scrape http://localhost:8000/metrics
    """
    # We use a different port than FastAPI (8002) to keep traffic separate
    start_http_server(port)
    print(f"📊 Metrics server started on port {port}")