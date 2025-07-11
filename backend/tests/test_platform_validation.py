import pytest
from pydantic import ValidationError

from src.api.v1.endpoints.searches import SavedSearchCreate
from src.models.search import SearchPlatform


def test_platform_accepts_lowercase():
    """Test that lowercase platform values are accepted and converted to uppercase."""
    # Test lowercase values
    search_data = {
        "name": "Test Search",
        "query": "Beatles",
        "platform": "ebay",
    }
    search = SavedSearchCreate(**search_data)
    assert search.platform == SearchPlatform.EBAY

    # Test 'discogs'
    search_data["platform"] = "discogs"
    search = SavedSearchCreate(**search_data)
    assert search.platform == SearchPlatform.DISCOGS

    # Test 'both'
    search_data["platform"] = "both"
    search = SavedSearchCreate(**search_data)
    assert search.platform == SearchPlatform.BOTH


def test_platform_accepts_uppercase():
    """Test that uppercase platform values still work."""
    search_data = {
        "name": "Test Search",
        "query": "Beatles",
        "platform": "EBAY",
    }
    search = SavedSearchCreate(**search_data)
    assert search.platform == SearchPlatform.EBAY


def test_platform_rejects_invalid_values():
    """Test that invalid platform values are rejected."""
    search_data = {
        "name": "Test Search",
        "query": "Beatles",
        "platform": "invalid",
    }
    with pytest.raises(ValidationError):
        SavedSearchCreate(**search_data)
