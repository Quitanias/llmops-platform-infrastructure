# SRE Runbook - PostgreSQL Database

## Incident: Connections Exhausted (Timeout / Connection Refused)
If the backend services (like FastAPI) are throwing 500 Internal Server Errors accompanied by logs showing "asyncpg.exceptions.TooManyConnectionsError" or database connection timeouts:

**Standard Diagnosis:**
The PostgreSQL database has reached its maximum connection limit (`max_connections`). This is typically caused by a sudden spike in traffic, a deployed bug where connection pools are not being closed properly, or a misconfiguration in `asyncpg`.

**Mitigation Action (Level 1):**
1. Identify the recent deployment to verify if the connection pool settings in `app/main.py` were inadvertently altered (e.g., `asyncpg.create_pool` with unlimited max size).
2. Manually restart the application pods to immediately flush lingering zombie connections: `kubectl rollout restart deployment fastapi-agent`.
3. Increase `max_connections` parameter in the RDS parameter group to provide temporary headroom while the engineering team investigates the leak.
4. Scale up the PgBouncer deployment if connection pooling proxy is being used.
