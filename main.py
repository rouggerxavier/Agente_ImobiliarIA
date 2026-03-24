"""Compatibility entrypoint that re-exports ``app.main``."""

import os
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.main import app

__all__ = ["app"]


class SPAStaticFiles(StaticFiles):
    """Static files with fallback to index.html for client-side routing."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


_BASE_DIR = Path(__file__).resolve().parent
_dist_path = _BASE_DIR / "dist"
_has_root_static_mount = any(
    getattr(route, "path", None) == "/" and route.__class__.__name__ == "Mount"
    for route in app.router.routes
)
if _dist_path.is_dir() and not _has_root_static_mount:
    app.mount("/", SPAStaticFiles(directory=str(_dist_path), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
