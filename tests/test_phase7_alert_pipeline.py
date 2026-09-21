"""Tests for Alert Pipeline (Phase 7)."""

import pytest
from httpx import AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio

async def test_alert_webhook_ingestion():
    """Test webhook ingestion queues a task."""
    from app.dependencies.providers import get_alert_pipeline_service
    
    class MockService:
        async def process_alert(self, payload):
            return [{"user_id": "test_user", "action": "Irrigate"}]
            
    app.dependency_overrides[get_alert_pipeline_service] = lambda: MockService()
    
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/alerts/webhook", json={
            "hazard_type": "Heavy Rain",
            "headline": "Severe Thunderstorm Warning",
            "wkt_polygon": "POLYGON((77.0 28.0, 78.0 28.0, 78.0 29.0, 77.0 29.0, 77.0 28.0))",
            "warning_level": "Red",
            "prescribed_action": "Stay indoors"
        })
        
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    
    app.dependency_overrides.clear()
