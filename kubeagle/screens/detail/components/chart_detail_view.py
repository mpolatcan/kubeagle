"""Chart detail view component for detail screen."""

from __future__ import annotations


class ChartDetailViewComponent:
    """Component for displaying chart detail information."""

    def __init__(self, widget_id: str = "chart-detail-view") -> None:
        """Initialize chart detail view component.

        Args:
            widget_id: ID for the view widget
        """
        self.widget_id = widget_id

    def update_view(self, parent, chart_info: dict) -> None:
        """Update the view with chart information.

        Args:
            parent: Parent widget
            chart_info: Chart information dictionary
        """
        if parent is None:
            return

        chart_name = str(chart_info.get("name", "Unknown chart"))
        summary_text = f"Chart: {chart_name}"

        try:
            update_fn = getattr(parent, "update", None)
            if callable(update_fn):
                update_fn(summary_text)
                return

            if hasattr(parent, "content"):
                parent.content = summary_text
        except Exception:
            # This helper is best-effort and should never break screen rendering.
            return
