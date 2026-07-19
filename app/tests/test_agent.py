import os
import pytest
from fastapi.testclient import TestClient

# Mock environmental variables before importing the main app to avoid validation failures
os.environ["GROQ_API_KEY"] = "mock-groq-key-gsk-12345"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PASSWORD"] = "mock-password"

from main import app

client = TestClient(app)

def test_health_check_unhealthy_when_db_down():
    """
    SRE Test Case: Verifies that the health check endpoint properly returns 503
    if the database is unreachable or missing.
    """
    response = client.get("/health")
    # Should fail or return 503 because 'localhost' db won't be up in a clean CI environment
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"

def test_ask_endpoint_requires_payload():
    """
    Input Guardrail Test Case: Verifies that Pydantic properly blocks incoming requests
    missing the required valid JSON structure.
    """
    response = client.post("/ask", json={})
    assert response.status_code == 422 # Unprocessable Entity

def test_ask_endpoint_invalid_json():
    """
    Input Guardrail Test Case: Verifies that sending corrupted text string data
    instead of structured JSON fields crashes gracefully at the framework gate.
    """
    response = client.post("/ask", data="corrupted string format")
    assert response.status_code == 422