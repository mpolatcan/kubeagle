# AGENTS.md

## Environment Rules (All Agents)

- `VIRTUAL ENVIRONMENT`: `source venv/bin/activate` (never `.venv`)
- `TYPE CHECKER`: `ty check` (never `pyright`)
- `CHARTS PATH`: `--charts-path ../web-helm-repository` (mandatory for visual-analysis)

## Documentation Rules (All Agents)

- `CONTEXT7 MCP`: Always use Context7 MCP first when reading official library/framework docs.
- `OFFICIAL DOC SOURCES`: Use Context7 MCP for Textual, `asyncio`, and similar core dependencies before any fallback source.

## Project Context

- `Goal`: Build a TUI for the `eks_helm_reporter` CLI tool.
- `CLI (source)`: `eks_helm_reporter/` (read only)
- `TUI (target)`: `kubeagle/` (implementation target)
- `Spec`: `EKS_UNIFIED_HELM_REPORT.md` (table formats, columns)
- `Projects`: `docs/projects/` (project reports: impl, test, ux)

## Architecture Rules

- `Screens glob`: `kubeagle/screens/**/*_screen.py`

## Codex Skills

- `code-conventions`: `.codex/skills/code-conventions/SKILL.md`
- `code-quality`: `.codex/skills/code-quality/SKILL.md`
- `textual-cli`: `.codex/skills/textual-cli/SKILL.md`
- `tui-test`: `.codex/skills/tui-test/SKILL.md`
- `visual-analysis`: `.codex/skills/visual-analysis/SKILL.md`

### Project Structure

```text
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

### Keybindings Architecture

| Module | Contains |
|--------|----------|
| `keyboard/app.py` | `GLOBAL_BINDINGS`, `NAV_BINDINGS`, `HELP_BINDINGS`, `REFRESH_BINDINGS`, `APP_BINDINGS` |
| `keyboard/navigation.py` | All `*_SCREEN_BINDINGS` (12 screen binding lists) |
| `keyboard/tables.py` | `DATA_TABLE_BINDINGS` |
| `keyboard/__init__.py` | Re-exports all bindings |

Import example: `from kubeagle.keyboard import CLUSTER_SCREEN_BINDINGS`
