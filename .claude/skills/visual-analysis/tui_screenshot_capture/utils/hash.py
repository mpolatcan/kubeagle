"""Hash utilities for stable widget identification."""

from __future__ import annotations

import zlib


def generate_stable_hash(*components: str) -> str:
    """Generate a stable hash from string components.

    Uses zlib.adler32 for fast non-cryptographic hashing.
    This provides stable IDs that survive widget recompose.

    Args:
        *components: String components to hash (joined with ':').

    Returns:
        Hex string hash (8 characters).
    """
    props_str = ":".join(components)
    try:
        widget_hash = zlib.adler32(props_str.encode("utf-8")) & 0xFFFFFFFF
    except UnicodeEncodeError:
        props_str_ascii = props_str.encode("ascii", errors="replace").decode("ascii")
        widget_hash = zlib.adler32(props_str_ascii.encode()) & 0xFFFFFFFF
    return f"{widget_hash:08x}"


__all__ = ["generate_stable_hash"]
