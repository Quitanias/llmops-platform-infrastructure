# SRE Runbook - FastAPI Services

## Incident: CPU Spike and HPA Drop (OOMKilled)
If the FastAPI application experiences repeated crashes with "OOMKilled" accompanied by CPU spikes close to 98%, and the new pod is failing the startupProbe for more than 2 minutes:

**Standard Diagnosis:**
Loading large AI models (such as SentenceTransformers) into RAM during startup exceeds the configured memory limits in Kubernetes, additionally causing timeouts on the initialization probe (startupProbe).

**Mitigation Action (Level 1):**
1. Increase `startupProbe.failureThreshold` from 30 to 60 seconds in the Deployment manifest.
2. Change the HPA strategy to be based on request concurrency rather than raw CPU/Memory metrics, since loading the model causes an artificial spike.
3. If the error persists, contact the MLOps team to move the model (SentenceTransformers) to an isolated sidecar container or external service (e.g., vLLM).
