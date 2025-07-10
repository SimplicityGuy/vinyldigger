from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# Define the docs directory
DOCS_DIR = Path(__file__).parent.parent.parent.parent.parent / "docs"


@router.get("/{doc_name}")
async def get_documentation(doc_name: str) -> FileResponse:
    """Serve documentation files."""
    # Sanitize the filename to prevent directory traversal
    if ".." in doc_name or "/" in doc_name or "\\" in doc_name:
        raise HTTPException(status_code=400, detail="Invalid document name")

    # Only allow .md files
    if not doc_name.endswith(".md"):
        doc_name += ".md"

    file_path = DOCS_DIR / doc_name

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Documentation not found")

    return FileResponse(
        path=file_path,
        media_type="text/markdown",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/")
async def list_documentation() -> dict[str, list[str]]:
    """List available documentation files."""
    if not DOCS_DIR.exists():
        return {"documents": []}

    docs = [f.name for f in DOCS_DIR.glob("*.md")]
    return {"documents": sorted(docs)}
