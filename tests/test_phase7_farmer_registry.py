"""Tests for Farmer Registry API (Phase 7)."""

import pytest
from httpx import AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio

async def test_register_farmer_plot_success():
    """Test successful plot registration via API."""
    # We test the API structure, mocking out the repository dependency
    from app.dependencies.providers import get_farmer_plot_repository
    
    class MockRepo:
        async def create_plot(self, **kwargs):
            from app.db.models.farmer import FarmerPlot
            return FarmerPlot(
                plot_id="f53b53f0-4df2-4d22-b5f7-646e7f781ea3",
                user_id=kwargs["user_id"],
                plot_name=kwargs["plot_name"],
                crop_name=kwargs["crop_name"],
                centroid_lat=kwargs["centroid_lat"],
                centroid_lon=kwargs["centroid_lon"],
                area_acres=kwargs.get("area_acres")
            )
            
    app.dependency_overrides[get_farmer_plot_repository] = lambda: MockRepo()
    
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/farmer/plots", json={
            "user_id": "test_user_1",
            "plot_name": "North Field",
            "crop_name": "Wheat",
            "centroid_lat": 28.6139,
            "centroid_lon": 77.2090,
            "area_acres": 5.0
        })
        
    assert response.status_code == 201
    data = response.json()
    assert data["plot_name"] == "North Field"
    assert data["user_id"] == "test_user_1"
    
    app.dependency_overrides.clear()


async def test_get_farmer_plots_success():
    """Test retrieving plots for a user."""
    from app.dependencies.providers import get_farmer_plot_repository
    
    class MockRepo:
        async def get_by_user(self, user_id: str):
            from app.db.models.farmer import FarmerPlot
            return [
                FarmerPlot(
                    plot_id="f53b53f0-4df2-4d22-b5f7-646e7f781ea3",
                    user_id=user_id,
                    plot_name="North Field",
                    crop_name="Wheat",
                    centroid_lat=28.6,
                    centroid_lon=77.2,
                    area_acres=5.0
                )
            ]
            
    app.dependency_overrides[get_farmer_plot_repository] = lambda: MockRepo()
    
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/farmer/plots/test_user_1")
        
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["plot_name"] == "North Field"
    
    app.dependency_overrides.clear()
