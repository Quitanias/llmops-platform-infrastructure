import time
import random
import requests
import datetime
from prometheus_client import start_http_server, Gauge

# Metric simulating CPU usage of the FastAPI pod
# Gauge allows values to go up and down
CPU_USAGE = Gauge('fastapi_cpu_usage_percent', 'CPU usage of the FastAPI pod', ['pod', 'namespace'])

LOKI_URL = "http://loki:3100/loki/api/v1/push"

def push_log_to_loki(message, level="info"):
    """Manually push a log message to Loki API."""
    # Current timestamp in nanoseconds (Loki requirement)
    ts = str(int(time.time() * 1e9))
    payload = {
        "streams": [
            {
                "stream": {
                    "app": "fastapi-agent",
                    "level": level,
                    "namespace": "production"
                },
                "values": [
                    [ts, message]
                ]
            }
        ]
    }
    try:
        requests.post(LOKI_URL, json=payload, timeout=2)
    except Exception as e:
        print(f"Loki unavailable: {e}")

if __name__ == '__main__':
    # Start the Prometheus metrics server on port 8001
    start_http_server(8001)
    print("Mock Prometheus and Loki server started on port 8001")
    
    cycle = 0
    # Infinite loop generating repeating anomalies (OOM every 2 minutes)
    while True:
        cycle += 1
        
        # Normal operation
        print(f"Cycle {cycle}: Normal operation...")
        CPU_USAGE.labels(pod="fastapi-app-pod-1234", namespace="production").set(0.20 + random.uniform(0, 0.1))
        push_log_to_loki("[INFO] FastAPI Agent running normally.", "info")
        time.sleep(30)
        
        # Traffic spike
        print(f"Cycle {cycle}: Traffic spike (CPU rising)...")
        CPU_USAGE.labels(pod="fastapi-app-pod-1234", namespace="production").set(0.65 + random.uniform(0, 0.1))
        push_log_to_loki("[WARN] High latency detected in embedding endpoint.", "warn")
        time.sleep(30)
        
        # Crisis (OOM and Restart)
        print(f"Cycle {cycle}: Crisis (CPU capping and OOM)...")
        CPU_USAGE.labels(pod="fastapi-app-pod-1234", namespace="production").set(0.98 + random.uniform(0, 0.02))
        push_log_to_loki("[ERROR] Pod fastapi-app-pod-1234 terminated unexpectedly (OOMKilled).", "error")
        time.sleep(15)
        
        # Startup attempt and delay
        print(f"Cycle {cycle}: Startup delay...")
        CPU_USAGE.labels(pod="fastapi-app-pod-1234", namespace="production").set(0.0)
        push_log_to_loki("[INFO] Starting new container fastapi-app-pod-5678...", "info")
        push_log_to_loki("[INFO] Loading SentenceTransformer model 'paraphrase-multilingual-MiniLM-L12-v2' into memory...", "info")
        time.sleep(15)
        
        push_log_to_loki("[WARN] startupProbe failed: connection refused.", "warn")
        time.sleep(30)
        
        push_log_to_loki("[INFO] SentenceTransformer model loaded successfully (took 180s).", "info")
        push_log_to_loki("[INFO] Application startup complete.", "info")
