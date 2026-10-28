# QlikGPT — Executive Premium (visual system 1.1)

**Global design system, independent of Sales.** The stable template identifier remains `qlikgpt-executive-v1` for backward compatibility. Version **1.1.0** introduces a more pronounced visual hierarchy while preserving all Qlik master-item contracts.

## Design tokens and visual hierarchy

| Role | Token | Color |
| --- | --- | --- |
| Branding and navigation | navy | `#142840` |
| Main chart/interactive accent | blue | `#3365D5` |
| Secondary chart/selection accent | teal | `#16A39A` |
| Sheet canvas | canvas | `#F5F7FB` |
| Card surfaces | surface, card | `#FFFFFF` |
| Borders | border | `#E3E9F1` |
| Positive states | success | `#16A34A` |

Sources of truth:
- [design-tokens.json](design-tokens.json): reusable palette, KPI rules, grid contract and semantic colors.
- [theme.json](themes/qlikgpt-executive-v1/theme.json) and [QEXT](themes/qlikgpt-executive-v1/qlikgpt-executive-v1.qext): official custom Qlik theme package source.
- [ci/ui_template.py](../ci/ui_template.py): Qlik-native generator and consistency checks for future Presentation apps.
- [Sales application example](../semantic-models/sales/apps/presentation1-objects.json): production demo layout to validate visually.

## Sheet archetype — Executive Overview

The main overview uses a **24-column / 18-row** grid. From top to bottom: 2-row hero with cross-app native navigation; contextual rail; 2-row filter strip; KPI section heading; four 3-row KPI cards; insights section heading; two 8-row charts (15/9 split). No sample values and no invented deltas. All KPIs and charts continue to reference governed measures by `qLibraryId`; filters use master dimensions.

The header is a native `text-image` visualization with Qlik rich-text markup (`%[...](4)^[...](inherit)`), replacing raw `##` Markdown that previously appeared as literal text. The two chart geometries and the original identifiers remain intact. Qlik buttons use the supported native `openWebsite` navigation action, with real app URLs.

## Important deployment distinction

There are **two independent layers**:

1. **Native object properties and grid** are deployed by the existing QIX/GitHub workflow on `main`. This path is **deploy-only**: it never initiates a data reload. The branch/PR itself does not deploy to Qlik Cloud.
2. **The custom global theme** must be uploaded to Qlik Cloud as a ZIP and explicitly selected in the app (Settings > Appearance > Application theme). A commit alone does not import, upgrade or activate a theme. Qlik native styling, chart rounding, shadow and responsive spacing need an actual browser QA; JSON tests alone cannot prove visual rendering.

Package only these two files in the ZIP root: `theme.json` and `qlikgpt-executive-v1.qext`. Have an administrator upload it under the tenant's theme management. Then select the theme on each Presentation using app settings. If the theme is already installed with the same ID, coordinate an update rather than creating duplicate names.

## Checks and rollout

```bash
python3 ci/ui_template.py --check
python3 -m unittest discover -s tests -v
python3 ci/catalog_report.py --check
python3 ci/app_lineage.py --check
```

Review in the Qlik Cloud browser at desktop and laptop width. Confirm header text rendering, filter usability, navigation target, KPI number formatting, 12-month chronology, bar ranking, appearance of selected states and no overflow. **Do not claim WOW is complete without the browser visual pass.**

## New app scaffold

```bash
python3 ci/ui_template.py --new-key presentation3 --app-name "QlikGPT - PRODUCT PERFORMANCE" --measures qlikgpt_shared_revenue,qlikgpt_shared_orders
```

The command prints a non-persistent preview. Pass `--write` only to intentionally generate files for a new app. New apps must subscribe to real catalog measures/dimensions and be assigned their own Qlik ID; no reusable frontend makes a new semantic model by itself. Avoid CSS selectors into undocumented Qlik DOM internals.
