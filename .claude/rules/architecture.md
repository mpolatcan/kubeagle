# Architecture

**Screens glob**: `Glob(pattern="kubeagle/screens/**/*_screen.py")`

## Project Structure

```
kubeagle/
├── app.py, main.py
├── keyboard/           # app.py, navigation.py, tables.py
├── screens/
│   ├── base_screen.py
│   ├── charts/         # Each module: *_screen.py, config.py, presenter.py, components/
│   ├── cluster/
│   ├── teams/
│   ├── detail/
│   ├── settings/
│   ├── reports/
│   └── mixins/         # screen_data_loader, tabbed_view_mixin, worker_mixin
├── widgets/            # _base.py, _config.py
│   ├── containers/     # custom_card, custom_containers
│   ├── data/           # indicators/, kpi/, tables/ (custom_data_table, custom_table, etc.)
│   ├── display/        # custom_digits, custom_markdown, custom_rich_log, custom_static
│   ├── feedback/       # custom_button, custom_dialog, custom_loading_indicator
│   ├── filter/         # custom_filter_bar, custom_search_bar, etc.
│   ├── input/          # custom_checkbox, custom_input, custom_text_area
│   ├── selection/      # custom_option_list, custom_radio_set, custom_switch, etc.
│   ├── special/        # custom_content_switcher, custom_tree, etc.
│   ├── structure/      # custom_footer, custom_header, custom_rule
│   └── tabs/           # custom_tab_pane, custom_tabbed_content, custom_tabs
├── controllers/        # base/, charts/, cluster/, team/, analyzers/
│   │                   # Each module has fetchers/, parsers/, mappers/ sub-dirs
├── models/             # analysis/, cache/, charts/, core/, events/, optimization/,
│                       # pdb/, reports/, state/, teams/, types/
├── constants/          # enums.py, defaults.py, limits.py, tables.py, timeouts.py,
│                       # values.py, ui.py, optimizer.py, patterns.py,
│                       # screens/ (charts, cluster, common, detail, settings, teams)
├── optimizer/          # analyzer.py, fixer.py, rules.py
├── utils/              # resource_parser, concurrent, cache_manager, report_generator
├── css/                # app.tcss, screens/*.tcss, widgets/*.tcss
├── tests/tui/          # smoke/, unit/
└── docs/

docs/
├── templates/          # Project document templates
└── projects/           # PRD-{slug}/ project folders with reports
```

## Keybindings Architecture

| Module | Contains |
|--------|----------|
| `keyboard/app.py` | `GLOBAL_BINDINGS`, `NAV_BINDINGS`, `HELP_BINDINGS`, `REFRESH_BINDINGS`, `APP_BINDINGS` |
| `keyboard/navigation.py` | All `*_SCREEN_BINDINGS` (12 screen binding lists) |
| `keyboard/tables.py` | `DATA_TABLE_BINDINGS` |
| `keyboard/__init__.py` | Re-exports all bindings |

Import: `from kubeagle.keyboard import CLUSTER_SCREEN_BINDINGS`
