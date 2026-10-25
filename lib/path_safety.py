"""Safe path resolution under a base directory (prevents path traversal)."""

import os


def safe_resolve(base_dir, relative_path):
    """Resolve relative_path under base_dir; return absolute path or None if unsafe."""
    if not relative_path:
        return None
    base = os.path.realpath(base_dir)
    # Normalize separators and strip leading slashes
    rel = relative_path.replace("\\", "/").lstrip("/")
    candidate = os.path.realpath(os.path.join(base, rel))
    if candidate == base:
        return None
    if not candidate.startswith(base + os.sep):
        return None
    return candidate
