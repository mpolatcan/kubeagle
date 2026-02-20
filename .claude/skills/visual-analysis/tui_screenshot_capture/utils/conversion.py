"""SVG to PNG conversion for TUI screenshots."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from tui_screenshot_capture.constants import PNG_WRITE_ERRNOS

# Optional dependency for PNG conversion
try:
    import cairosvg

    CAIROSVG_AVAILABLE = True
except ImportError:
    cairosvg = None  # type: ignore[assignment]
    CAIROSVG_AVAILABLE = False


def convert_svg_to_png(
    svg_path: Path,
    scale: float = 1.0,
    keep_svg: bool = False,
) -> Path | None:
    """Convert SVG to PNG using cairosvg.

    Args:
        svg_path: Path to the SVG file.
        scale: Scaling factor for PNG conversion.
        keep_svg: If False, delete SVG after successful PNG conversion.

    Returns:
        Path to the PNG file, or None if conversion fails or cairosvg is not installed.

    """
    if not CAIROSVG_AVAILABLE:
        logger.warning("cairosvg not installed, skipping PNG conversion")
        logger.info("To enable PNG conversion, run: pip install cairosvg")
        return None

    png_path = svg_path.with_suffix(".png")

    try:
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(png_path),
            scale=scale,
        )
        logger.info(f"Converted: {png_path.name} (scale={scale}x)")

        # Delete SVG after successful PNG conversion (default behavior)
        if not keep_svg:
            svg_path.unlink()
            logger.info(f"Removed: {svg_path.name}")

        return png_path
    except OSError as e:
        if e.errno in PNG_WRITE_ERRNOS:
            logger.error(f"Permission denied writing PNG file: {e}")
            return None
        else:
            logger.warning(f"File I/O error during PNG conversion: {e}")
            return None
