"""Tests for error handling and edge cases."""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.main import app
from src.models.search import SavedSearch, SearchPlatform
from src.models.user import User


class TestErrorHandling:
    """Test suite for error handling and edge cases."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        return User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    @pytest.fixture
    def authenticated_client(self, client: AsyncClient, mock_user):
        """Create authenticated client with mock user."""

        async def mock_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = mock_get_current_user
        yield client
        app.dependency_overrides.pop(get_current_user, None)

    async def test_get_nonexistent_search(self, authenticated_client: AsyncClient):
        """Test getting a search that doesn't exist."""
        fake_id = str(uuid4())
        response = await authenticated_client.get(f"/api/v1/searches/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    async def test_update_nonexistent_search(self, authenticated_client: AsyncClient):
        """Test updating a search that doesn't exist."""
        fake_id = str(uuid4())
        update_data = {"name": "Updated Name"}
        response = await authenticated_client.put(f"/api/v1/searches/{fake_id}", json=update_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_nonexistent_search(self, authenticated_client: AsyncClient):
        """Test deleting a search that doesn't exist."""
        fake_id = str(uuid4())
        response = await authenticated_client.delete(f"/api/v1/searches/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_invalid_uuid_format(self, authenticated_client: AsyncClient):
        """Test endpoints with invalid UUID format."""
        invalid_id = "not-a-uuid"

        # Test GET
        response = await authenticated_client.get(f"/api/v1/searches/{invalid_id}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test PUT
        response = await authenticated_client.put(f"/api/v1/searches/{invalid_id}", json={"name": "Test"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test DELETE
        response = await authenticated_client.delete(f"/api/v1/searches/{invalid_id}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_search_invalid_platform(self, authenticated_client: AsyncClient):
        """Test creating a search with invalid platform."""
        search_data = {
            "name": "Test Search",
            "query": "test",
            "platforms": ["invalid_platform"],
            "check_interval_hours": 24,
        }
        response = await authenticated_client.post("/api/v1/searches", json=search_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_search_empty_platforms(self, authenticated_client: AsyncClient):
        """Test creating a search with empty platforms list."""
        search_data = {
            "name": "Test Search",
            "query": "test",
            "platforms": [],
            "check_interval_hours": 24,
        }
        response = await authenticated_client.post("/api/v1/searches", json=search_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_search_invalid_interval(self, authenticated_client: AsyncClient):
        """Test creating a search with invalid check interval."""
        # Negative interval
        search_data = {
            "name": "Test Search",
            "query": "test",
            "platforms": ["discogs"],
            "check_interval_hours": -1,
        }
        response = await authenticated_client.post("/api/v1/searches", json=search_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Zero interval
        search_data["check_interval_hours"] = 0
        response = await authenticated_client.post("/api/v1/searches", json=search_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_malformed_json_request(self, authenticated_client: AsyncClient):
        """Test sending malformed JSON."""
        response = await authenticated_client.post(
            "/api/v1/searches",
            content='{"invalid json"',
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_missing_required_fields(self, authenticated_client: AsyncClient):
        """Test creating search with missing required fields."""
        # Missing name
        search_data = {
            "query": "test",
            "platforms": ["discogs"],
        }
        response = await authenticated_client.post("/api/v1/searches", json=search_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing query
        search_data = {
            "name": "Test",
            "platforms": ["discogs"],
        }
        response = await authenticated_client.post("/api/v1/searches", json=search_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_search_name_too_long(self, authenticated_client: AsyncClient):
        """Test creating search with name exceeding length limit."""
        search_data = {
            "name": "A" * 256,  # Assuming 255 char limit
            "query": "test",
            "platforms": ["discogs"],
            "check_interval_hours": 24,
        }
        response = await authenticated_client.post("/api/v1/searches", json=search_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_concurrent_updates(self, authenticated_client: AsyncClient, db_session: AsyncSession, mock_user):
        """Test handling concurrent updates to same resource."""
        # Create a search
        search = SavedSearch(
            id=uuid4(),
            user_id=mock_user.id,
            name="Original Name",
            query="test",
            platforms=[SearchPlatform.DISCOGS],
            is_active=True,
        )
        db_session.add(search)
        await db_session.commit()

        # Simulate concurrent update by deleting the search
        await db_session.execute(delete(SavedSearch).where(SavedSearch.id == search.id))
        await db_session.commit()

        # Try to update the now-deleted search
        update_data = {"name": "Updated Name"}
        response = await authenticated_client.put(f"/api/v1/searches/{search.id}", json=update_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_database_connection_error(self, authenticated_client: AsyncClient, monkeypatch):
        """Test handling database connection errors."""

        # Mock database error
        async def mock_execute(*args, **kwargs):
            raise Exception("Database connection lost")

        monkeypatch.setattr("sqlalchemy.ext.asyncio.AsyncSession.execute", mock_execute)

        response = await authenticated_client.get("/api/v1/searches")

        # Should return 500 Internal Server Error
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    async def test_null_values_handling(self, authenticated_client: AsyncClient):
        """Test handling of null values in requests."""
        search_data = {
            "name": None,  # Null name
            "query": "test",
            "platforms": ["discogs"],
            "check_interval_hours": 24,
        }
        response = await authenticated_client.post("/api/v1/searches", json=search_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_special_characters_in_search(self, authenticated_client: AsyncClient):
        """Test creating search with special characters."""
        search_data = {
            "name": "Test <script>alert('xss')</script>",
            "query": "'; DROP TABLE searches; --",
            "platforms": ["discogs"],
            "check_interval_hours": 24,
        }
        response = await authenticated_client.post("/api/v1/searches", json=search_data)

        # Should handle special characters safely
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        # Verify data is stored as-is (escaped by the database)
        assert "<script>" in data["name"]
        assert "DROP TABLE" in data["query"]
