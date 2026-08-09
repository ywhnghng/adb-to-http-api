"""Online documentation endpoint.

Exposes ``GET /doc`` which returns the agent API guide (``docs/AGENT_API_GUIDE.md``)
as raw ``text/markdown`` so that any program (or the browser) can fetch the latest
calling instructions after the service has started.

Path resolution must work in both run modes:

* **Frozen (PyInstaller onefile)**: the document lives under ``sys._MEIPASS``.
* **Source tree**: derived from this file (``app/routes/doc.py`` -> two levels up
  is the project root) -> ``docs/AGENT_API_GUIDE.md``.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import List, Optional

from flask import Blueprint, Response

from app.routes import common

logger = logging.getLogger(__name__)

bp = Blueprint("doc", __name__)

# Optional explicit override, set at registration time.
_DOC_PATH: Optional[str] = None

DOC_FILENAME = "AGENT_API_GUIDE.md"
DOC_DIR = "docs"


def _resolve_doc_path(explicit: Optional[str] = None) -> Optional[str]:
    """Locate the agent API guide markdown document.

    Resolution order:
        1. ``explicit`` path when provided and it exists.
        2. PyInstaller onefile bundle: ``<sys._MEIPASS>/docs/AGENT_API_GUIDE.md``.
        3. Source layout: ``app/routes/doc.py`` -> two levels up (project root)
           -> ``docs/AGENT_API_GUIDE.md``.

    Args:
        explicit: Optional absolute override path.

    Returns:
        An existing absolute path to the document, or ``None`` if no candidate
        could be found.
    """
    candidates: List[str] = []
    if explicit:
        candidates.append(explicit)

    # Frozen / bundled by PyInstaller (onefile).
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        candidates.append(os.path.join(base, DOC_DIR, DOC_FILENAME))

    # Source layout: app/routes/doc.py -> ../.. -> project root.
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(here))
    candidates.append(os.path.join(project_root, DOC_DIR, DOC_FILENAME))

    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def register(app, doc_path: Optional[str] = None) -> None:  # noqa: ANN001
    """Register the documentation blueprint onto ``app``.

    Args:
        app: The Flask application.
        doc_path: Optional explicit path to the markdown document. When omitted
            (or ``None``) the path is auto-detected per the run mode.
    """
    global _DOC_PATH
    _DOC_PATH = doc_path
    app.register_blueprint(bp)


@bp.route("/doc", methods=["GET"])
def doc():
    """Return the agent API guide as raw markdown text.

    The response ``Content-Type`` is ``text/markdown; charset=utf-8`` so the
    body can be both parsed by programs and rendered directly in a browser.
    When the document cannot be located a 404 JSON error is returned.
    """
    path = _DOC_PATH or _resolve_doc_path()
    if path is None or not os.path.isfile(path):
        return common.fail("DOC_NOT_FOUND", "文档未找到", http=404)

    try:
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError as exc:
        logger.exception("Failed to read doc file %s", path)
        return common.fail("INTERNAL", f"读取文档失败: {exc}", http=500)

    return Response(content, content_type="text/markdown; charset=utf-8")
