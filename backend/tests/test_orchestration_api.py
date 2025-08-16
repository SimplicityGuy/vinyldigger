"""API tests for search orchestration endpoints."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_headers(async_client: AsyncClient, test_user_credentials: dict[str, str]) -> dict[str, str]:
    """Get authentication headers."""
    response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user_credentials["email"],
            "password": test_user_credentials["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestBudgetAPI:
    """Test budget management API endpoints."""

    async def test_create_budget(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test creating a search budget."""
        response = await async_client.post(
            "/api/v1/budgets",
            headers=auth_headers,
            json={
                "monthly_limit": 100.00,
                "alert_threshold": 80,
                "alert_enabled": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["monthly_limit"] == 100.00
        assert data["current_spent"] == 0.00
        assert data["alert_threshold"] == 80
        assert data["is_active"] is True

    async def test_get_budget(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test getting user's budget."""
        # Create budget first
        create_response = await async_client.post(
            "/api/v1/budgets",
            headers=auth_headers,
            json={"monthly_limit": 50.00},
        )
        assert create_response.status_code == 200

        # Get budget
        response = await async_client.get("/api/v1/budgets/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["monthly_limit"] == 50.00

    async def test_update_budget(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test updating a budget."""
        # Create budget first
        create_response = await async_client.post(
            "/api/v1/budgets",
            headers=auth_headers,
            json={"monthly_limit": 50.00},
        )
        budget_id = create_response.json()["id"]

        # Update budget
        response = await async_client.put(
            f"/api/v1/budgets/{budget_id}",
            headers=auth_headers,
            json={
                "monthly_limit": 75.00,
                "alert_threshold": 90,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["monthly_limit"] == 75.00
        assert data["alert_threshold"] == 90

    async def test_get_budget_usage(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test getting budget usage statistics."""
        # Create budget
        await async_client.post(
            "/api/v1/budgets",
            headers=auth_headers,
            json={"monthly_limit": 100.00},
        )

        # Get usage
        response = await async_client.get("/api/v1/budgets/usage", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "current_spent" in data
        assert "monthly_limit" in data
        assert "percentage_used" in data
        assert "days_remaining" in data


class TestTemplateAPI:
    """Test template management API endpoints."""

    async def test_create_template(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test creating a search template."""
        response = await async_client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json={
                "name": "Jazz Records",
                "description": "Search for jazz vinyl",
                "category": "Jazz",
                "is_public": True,
                "template_data": {
                    "query": "{artist} {album} jazz",
                    "platform": "both",
                    "min_price": 10,
                    "max_price": 100,
                    "check_interval_hours": 24,
                },
                "parameters": {
                    "artist": {
                        "type": "string",
                        "required": True,
                        "description": "Artist name",
                    },
                    "album": {
                        "type": "string",
                        "required": False,
                        "default": "",
                    },
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Jazz Records"
        assert data["category"] == "Jazz"
        assert "artist" in data["parameters"]

    async def test_list_templates(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test listing templates."""
        # Create a template
        await async_client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json={
                "name": "Rock Template",
                "category": "Rock",
                "template_data": {"query": "rock vinyl", "platform": "both"},
            },
        )

        # List templates
        response = await async_client.get("/api/v1/templates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(t["name"] == "Rock Template" for t in data)

    async def test_use_template(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test using a template to create a search."""
        # Create template
        template_response = await async_client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json={
                "name": "Artist Search",
                "category": "General",
                "template_data": {
                    "query": "{artist} vinyl",
                    "platform": "both",
                },
                "parameters": {
                    "artist": {"type": "string", "required": True},
                },
            },
        )
        template_id = template_response.json()["id"]

        # Use template
        response = await async_client.post(
            f"/api/v1/templates/{template_id}/use",
            headers=auth_headers,
            json={
                "name": "Miles Davis Search",
                "parameters": {"artist": "Miles Davis"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "search_id" in data

    async def test_validate_template_parameters(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test validating template parameters."""
        # Create template with validation
        template_response = await async_client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json={
                "name": "Price Range Search",
                "category": "General",
                "template_data": {
                    "query": "vinyl",
                    "platform": "both",
                    "min_price": "{min_price}",
                    "max_price": "{max_price}",
                },
                "parameters": {
                    "min_price": {"type": "number", "required": True},
                    "max_price": {"type": "number", "required": True},
                },
            },
        )
        template_id = template_response.json()["id"]

        # Validate valid parameters
        response = await async_client.post(
            f"/api/v1/templates/{template_id}/validate",
            headers=auth_headers,
            json={"min_price": 10, "max_price": 50},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

        # Validate invalid parameters (missing required)
        response = await async_client.post(
            f"/api/v1/templates/{template_id}/validate",
            headers=auth_headers,
            json={"min_price": 10},  # Missing max_price
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["issues"]) > 0


class TestChainAPI:
    """Test search chain API endpoints."""

    async def test_create_chain(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test creating a search chain."""
        # Create searches first
        search1_response = await async_client.post(
            "/api/v1/searches",
            headers=auth_headers,
            json={
                "name": "Search 1",
                "query": "test 1",
                "platform": "both",
            },
        )
        search2_response = await async_client.post(
            "/api/v1/searches",
            headers=auth_headers,
            json={
                "name": "Search 2",
                "query": "test 2",
                "platform": "both",
            },
        )
        search1_id = search1_response.json()["id"]
        search2_id = search2_response.json()["id"]

        # Create chain
        response = await async_client.post(
            "/api/v1/chains",
            headers=auth_headers,
            json={
                "name": "Test Chain",
                "description": "Chain for testing",
                "searches": [
                    {
                        "search_id": search1_id,
                        "order_index": 1,
                        "trigger_condition": {},
                    },
                    {
                        "search_id": search2_id,
                        "order_index": 2,
                        "trigger_condition": {"min_results": 5},
                    },
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Chain"
        assert len(data["links"]) == 2

    async def test_list_chains(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test listing user's chains."""
        response = await async_client.get("/api/v1/chains", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_toggle_chain(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test toggling chain active status."""
        # Create a chain
        search_response = await async_client.post(
            "/api/v1/searches",
            headers=auth_headers,
            json={"name": "Test", "query": "test", "platform": "both"},
        )
        search_id = search_response.json()["id"]

        chain_response = await async_client.post(
            "/api/v1/chains",
            headers=auth_headers,
            json={
                "name": "Toggle Test",
                "searches": [{"search_id": search_id, "order_index": 1}],
            },
        )
        chain_id = chain_response.json()["id"]

        # Toggle off
        response = await async_client.post(
            f"/api/v1/chains/{chain_id}/toggle",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

        # Toggle on
        response = await async_client.post(
            f"/api/v1/chains/{chain_id}/toggle",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True


class TestOrchestrationIntegration:
    """Test orchestration features in search endpoints."""

    async def test_search_with_orchestration_fields(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test creating a search with orchestration fields."""
        response = await async_client.post(
            "/api/v1/searches",
            headers=auth_headers,
            json={
                "name": "Orchestrated Search",
                "query": "test query",
                "platform": "both",
                "check_interval_hours": 12,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Check orchestration fields are included
        assert "status" in data
        assert "results_count" in data
        assert "chain_id" in data
        assert "template_id" in data
        assert "budget_id" in data
        assert "estimated_cost_per_result" in data
        assert "depends_on_search" in data
        assert "trigger_conditions" in data
        assert "optimal_run_times" in data
        assert "avoid_run_times" in data
        assert "priority_level" in data

    async def test_update_search_orchestration(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test updating search orchestration settings."""
        # Create search
        search_response = await async_client.post(
            "/api/v1/searches",
            headers=auth_headers,
            json={
                "name": "Update Test",
                "query": "test",
                "platform": "both",
            },
        )
        search_id = search_response.json()["id"]

        # Update orchestration settings
        response = await async_client.put(
            f"/api/v1/searches/{search_id}/orchestration",
            headers=auth_headers,
            json={
                "estimated_cost_per_result": 0.15,
                "priority_level": 8,
                "optimal_run_times": [9, 14, 20],
                "avoid_run_times": [0, 1, 2, 3],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estimated_cost_per_result"] == 0.15
        assert data["priority_level"] == 8
        assert data["optimal_run_times"] == [9, 14, 20]

    async def test_get_search_dependencies(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        """Test getting search dependencies."""
        # Create parent search
        parent_response = await async_client.post(
            "/api/v1/searches",
            headers=auth_headers,
            json={
                "name": "Parent Search",
                "query": "parent",
                "platform": "both",
            },
        )
        parent_id = parent_response.json()["id"]

        # Create dependent search
        await async_client.post(
            "/api/v1/searches",
            headers=auth_headers,
            json={
                "name": "Dependent Search",
                "query": "dependent",
                "platform": "both",
            },
        )

        # Update to add dependency
        # Note: This would require implementing dependency update endpoint

        # Get dependencies
        response = await async_client.get(
            f"/api/v1/searches/{parent_id}/dependencies",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
