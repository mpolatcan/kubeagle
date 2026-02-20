# CLAUDE.md

## Environment Rules (ALL Agents)

```
VIRTUAL ENVIRONMENT: source venv/bin/activate  (NEVER .venv)
TYPE CHECKER:        ty check                   (NEVER pyright)
CHARTS PATH:         --charts-path ../web-helm-repository  (MANDATORY for visual-analysis)
```

---

## Project Context

**Goal**: Build a TUI for the `eks_helm_reporter` CLI tool.

| Component | Path | Purpose |
|-----------|------|---------|
| CLI (source) | `eks_helm_reporter/` | READ ONLY |
| TUI (target) | `kubeagle/` | Implementation target |
| Spec | `EKS_UNIFIED_HELM_REPORT.md` | Table formats, columns |
| Projects | `docs/projects/` | Project reports (impl, test, ux) |
