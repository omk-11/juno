"""Top-level package marker for the application source.

Making `src` a package allows package-relative imports (e.g. `from .scraper ...`) to work
when the app is imported as `src.main` by Uvicorn or other runners.
"""

__all__ = []
