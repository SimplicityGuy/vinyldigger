"""Item matching service for cross-platform item identification."""

import hashlib
import re
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.item_match import ItemMatch, ItemMatchResult, MatchConfidence

logger = get_logger(__name__)


class ItemMatchingService:
    """Service for matching items across platforms with fuzzy matching."""

    # Condition ranking for comparison
    CONDITION_RANKS = {
        "M": 10,
        "MINT": 10,
        "NM": 9,
        "NEAR MINT": 9,
        "NM/M": 9,
        "EX+": 8,
        "EXCELLENT PLUS": 8,
        "EX": 7,
        "EXCELLENT": 7,
        "VG+": 6,
        "VERY GOOD PLUS": 6,
        "VG": 5,
        "VERY GOOD": 5,
        "G+": 4,
        "GOOD PLUS": 4,
        "G": 3,
        "GOOD": 3,
        "F": 2,
        "FAIR": 2,
        "P": 1,
        "POOR": 1,
    }

    # Common format variations
    FORMAT_ALIASES = {
        "LP": ["LP", "ALBUM", '12"', "12 INCH"],
        "EP": ["EP", '7"', "7 INCH", "45 RPM"],
        "SINGLE": ["SINGLE", '7"', "7 INCH", "45 RPM"],
        "CD": ["CD", "COMPACT DISC"],
        "CASSETTE": ["CASSETTE", "TAPE", "MC"],
        "VINYL": ["VINYL", "LP", "EP", "SINGLE"],
    }

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""

        # Convert to lowercase and remove extra whitespace
        text = re.sub(r"\s+", " ", text.lower().strip())

        # Remove common punctuation and special characters
        text = re.sub(r"[^\w\s]", " ", text)

        # Remove common words that don't help with matching
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        words = [w for w in text.split() if w not in stop_words]

        return " ".join(words)

    @staticmethod
    def generate_fingerprint(
        title: str, artist: str, year: int | None = None, catalog_number: str | None = None
    ) -> str:
        """Generate a unique fingerprint for item matching."""
        normalized_title = ItemMatchingService.normalize_text(title)
        normalized_artist = ItemMatchingService.normalize_text(artist)

        # Create fingerprint components
        components = [normalized_artist, normalized_title]

        if year:
            components.append(str(year))

        if catalog_number:
            normalized_catalog = ItemMatchingService.normalize_text(catalog_number)
            if normalized_catalog:
                components.append(normalized_catalog)

        fingerprint_text = "|".join(components)

        # Generate SHA256 hash for consistent fingerprinting
        return hashlib.sha256(fingerprint_text.encode()).hexdigest()[:32]

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Calculate similarity between two text strings (0-100)."""
        if not text1 or not text2:
            return 0.0

        norm1 = ItemMatchingService.normalize_text(text1)
        norm2 = ItemMatchingService.normalize_text(text2)

        if norm1 == norm2:
            return 100.0

        # Use SequenceMatcher for fuzzy matching
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity * 100.0

    @staticmethod
    def extract_item_info(item_data: dict[str, Any], platform: str) -> dict[str, Any]:
        """Extract normalized item information from platform-specific data."""
        if platform.lower() == "discogs":
            return ItemMatchingService._extract_discogs_info(item_data)
        elif platform.lower() == "ebay":
            return ItemMatchingService._extract_ebay_info(item_data)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

    @staticmethod
    def _extract_discogs_info(item_data: dict[str, Any]) -> dict[str, Any]:
        """Extract item info from Discogs API response."""
        # Handle both search results and release data formats
        if "basic_information" in item_data:
            basic_info = item_data["basic_information"]
            title = basic_info.get("title", "")
            artists = basic_info.get("artists", [])
            year = basic_info.get("year")
            formats = basic_info.get("formats", [])
            labels = basic_info.get("labels", [])
        else:
            title = item_data.get("title", "")
            artists = item_data.get("artists", [])
            year = item_data.get("year")
            formats = item_data.get("formats", [])
            labels = item_data.get("labels", [])

        # Extract artist names
        artist_names = []
        for artist in artists:
            if isinstance(artist, dict):
                artist_names.append(artist.get("name", ""))
            else:
                artist_names.append(str(artist))

        # Extract format information
        format_names = []
        for fmt in formats:
            if isinstance(fmt, dict):
                format_names.append(fmt.get("name", ""))
            else:
                format_names.append(str(fmt))

        # Extract catalog number
        catalog_number = None
        for label in labels:
            if isinstance(label, dict) and label.get("catno"):
                catalog_number = label["catno"]
                break

        return {
            "title": title,
            "artist": ", ".join(artist_names),
            "year": year,
            "format": ", ".join(format_names),
            "catalog_number": catalog_number,
            "price": item_data.get("price"),
            "condition": item_data.get("condition"),
        }

    @staticmethod
    def _extract_ebay_info(item_data: dict[str, Any]) -> dict[str, Any]:
        """Extract item info from eBay API response."""
        title = item_data.get("title", "")

        # Try to parse artist from title (common pattern: "Artist - Title")
        artist = ""
        if " - " in title:
            parts = title.split(" - ", 1)
            artist = parts[0].strip()
            title = parts[1].strip()

        # Extract price information
        price = None
        if "price" in item_data:
            price_info = item_data["price"]
            if isinstance(price_info, dict):
                price = price_info.get("value")
            else:
                price = price_info

        return {
            "title": title,
            "artist": artist,
            "year": item_data.get("year"),
            "format": item_data.get("format"),
            "catalog_number": item_data.get("catalog_number"),
            "price": price,
            "condition": item_data.get("condition"),
        }

    async def find_or_create_item_match(self, db: AsyncSession, item_info: dict[str, Any]) -> ItemMatch:
        """Find existing item match or create new one."""
        fingerprint = self.generate_fingerprint(
            item_info["title"], item_info["artist"], item_info.get("year"), item_info.get("catalog_number")
        )

        # Try to find existing match
        result = await db.execute(select(ItemMatch).where(ItemMatch.match_fingerprint == fingerprint))
        existing_match = result.scalar_one_or_none()

        if existing_match:
            return existing_match

        # Create new match
        new_match = ItemMatch(
            canonical_title=item_info["title"],
            canonical_artist=item_info["artist"],
            canonical_year=item_info.get("year"),
            canonical_format=item_info.get("format"),
            catalog_number=item_info.get("catalog_number"),
            match_fingerprint=fingerprint,
            total_matches=0,
            avg_confidence_score=0.0,
        )

        db.add(new_match)
        await db.flush()
        return new_match

    async def calculate_match_confidence(
        self, item_match: ItemMatch, item_info: dict[str, Any]
    ) -> tuple[MatchConfidence, float, dict[str, Any]]:
        """Calculate match confidence and detailed scoring."""

        # Calculate individual similarity scores
        title_similarity = self.calculate_similarity(item_match.canonical_title, item_info["title"])
        artist_similarity = self.calculate_similarity(item_match.canonical_artist, item_info["artist"])

        # Year matching
        year_match = False
        if item_match.canonical_year and item_info.get("year"):
            year_match = abs(item_match.canonical_year - item_info["year"]) <= 1  # Allow 1 year difference
        elif not item_match.canonical_year and not item_info.get("year"):
            year_match = True  # Both missing year is neutral

        # Catalog number matching
        catalog_match = False
        if item_match.catalog_number and item_info.get("catalog_number"):
            catalog_similarity = self.calculate_similarity(item_match.catalog_number, item_info["catalog_number"])
            catalog_match = catalog_similarity > 80.0

        # Format matching
        format_match = False
        if item_match.canonical_format and item_info.get("format"):
            format_similarity = self.calculate_similarity(item_match.canonical_format, item_info["format"])
            format_match = format_similarity > 70.0

        # Calculate overall confidence score
        base_score = (title_similarity * 0.4) + (artist_similarity * 0.4)

        # Bonuses for additional matches
        if year_match:
            base_score += 10.0
        if catalog_match:
            base_score += 15.0  # Catalog number is very strong indicator
        if format_match:
            base_score += 5.0

        # Cap at 100
        confidence_score = min(base_score, 100.0)

        # Determine confidence level
        if confidence_score >= 95.0:
            confidence = MatchConfidence.EXACT
        elif confidence_score >= 85.0:
            confidence = MatchConfidence.HIGH
        elif confidence_score >= 70.0:
            confidence = MatchConfidence.MEDIUM
        elif confidence_score >= 50.0:
            confidence = MatchConfidence.LOW
        else:
            confidence = MatchConfidence.UNCERTAIN

        # Detailed match metadata
        match_metadata = {
            "title_similarity": title_similarity,
            "artist_similarity": artist_similarity,
            "year_match": year_match,
            "catalog_match": catalog_match,
            "format_match": format_match,
            "base_score": base_score,
            "bonuses_applied": {
                "year": year_match,
                "catalog": catalog_match,
                "format": format_match,
            },
        }

        return confidence, confidence_score, match_metadata

    async def match_search_result(
        self, db: AsyncSession, search_result_id: str, item_data: dict[str, Any], platform: str
    ) -> ItemMatchResult | None:
        """Match a search result to an item match."""
        try:
            # Extract item information
            item_info = self.extract_item_info(item_data, platform)

            # Find or create item match
            item_match = await self.find_or_create_item_match(db, item_info)

            # Calculate confidence
            confidence, confidence_score, match_metadata = await self.calculate_match_confidence(item_match, item_info)

            # Create match result
            match_result = ItemMatchResult(
                item_match_id=item_match.id,
                search_result_id=search_result_id,
                confidence=confidence,
                confidence_score=confidence_score,
                title_similarity=match_metadata["title_similarity"],
                artist_similarity=match_metadata["artist_similarity"],
                year_match=match_metadata["year_match"],
                catalog_match=match_metadata["catalog_match"],
                format_match=match_metadata["format_match"],
                requires_review=confidence in [MatchConfidence.LOW, MatchConfidence.UNCERTAIN],
                match_metadata=match_metadata,
            )

            db.add(match_result)

            # Update item match statistics
            item_match.total_matches += 1

            # Recalculate average confidence (simplified - could be more sophisticated)
            current_avg = float(item_match.avg_confidence_score or 0.0)
            new_avg = (
                (current_avg * (item_match.total_matches - 1)) + float(confidence_score)
            ) / item_match.total_matches
            item_match.avg_confidence_score = Decimal(str(new_avg))

            await db.flush()

            logger.info(
                f"Matched search result {search_result_id} to item {item_match.id} "
                f"with {confidence.value} confidence ({confidence_score:.1f}%)"
            )

            return match_result

        except Exception as e:
            logger.error(f"Error matching search result {search_result_id}: {str(e)}")
            return None
