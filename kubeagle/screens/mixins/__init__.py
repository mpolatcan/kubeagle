"""Screen mixins package for KubEagle TUI."""

from kubeagle.models.types.loading import LoadingProgress, LoadResult
from kubeagle.screens.mixins.main_navigation_tabs_mixin import (
    MAIN_NAV_TAB_CHARTS,
    MAIN_NAV_TAB_CLUSTER,
    MAIN_NAV_TAB_EXPORT,
    MAIN_NAV_TAB_SETTINGS,
    MainNavigationTabsMixin,
)
from kubeagle.screens.mixins.screen_data_loader import (
    DataLoadCompleted,
    DataLoaderMixin,
    DataLoadError,
    DataLoadStarted,
    ScreenDataLoader,
)
from kubeagle.screens.mixins.tabbed_view_mixin import (
    FilterableTableMixin,
    TabbedViewMixin,
)
from kubeagle.screens.mixins.worker_mixin import (
    DataLoaded,
    DataLoadFailed,
    DataLoadMixin,
    LoadingOverlay,
    WorkerMixin,
)

__all__ = [
    "TabbedViewMixin",
    "FilterableTableMixin",
    "DataLoadMixin",
    "WorkerMixin",
    "DataLoaded",
    "DataLoadFailed",
    "LoadingOverlay",
    "ScreenDataLoader",
    "DataLoaderMixin",
    "LoadingProgress",
    "LoadResult",
    "DataLoadStarted",
    "DataLoadCompleted",
    "DataLoadError",
    "MainNavigationTabsMixin",
    "MAIN_NAV_TAB_CLUSTER",
    "MAIN_NAV_TAB_CHARTS",
    "MAIN_NAV_TAB_EXPORT",
    "MAIN_NAV_TAB_SETTINGS",
]
