# Sales Intelligence — Executive Premium pilot

This is the **first visual pilot** of the [global Executive Premium UI Kit](../../../ui/README.md), version 1.1.0. No ETL, metric formulas, field lineage or existing visualization identifiers are changed.

## First Presentation — Sales Overview

- [Governed native sheet](../apps/presentation1-objects.json): 24 columns x 18 rows, refreshed hero and navigation rail, dedicated filter control strip, four KPI cards, section separators, and dual-chart insight area.
- Visual master measures remain: `qlikgpt_shared_revenue`, `qlikgpt_shared_orders`, `qlikgpt_shared_margin`, `qlikgpt_shared_margin_pct`.
- The two existing charts retain their `qLibraryId`-based dimensions and measure subscriptions, including the monthly revenue trend and market comparison.
- Native button opens the already provisioned [Shared KPI Presentation](https://sdggroup-it.eu.qlikcloud.com/sense/app/04280b14-6ba5-4fe9-90d6-2ff8fa1c994f).
- The header uses native Qlik text-image rich-text markup rather than raw Markdown. A browser visual check is still required to confirm it renders as intended.

## Companion Presentation — Shared KPI

The [second native sheet](../apps/presentation2-objects.json) adopts the same palette and has a native navigation button back to Sales Overview. Original KPI and master measure identifiers stay unchanged.

## How to complete the visual rollout

1. Review and merge the Executive Premium PR to `main`, after the static checks. With `QLIK_CICD_ENABLED=true`, the existing GitHub workflow can synchronize the native QIX frontend **without reloading data**.
2. The guarded GitHub workflow publishes the versioned theme through `ci/deploy_theme.py` (Qlik CLI create/patch), then saves `appprops.theme` on the first Presentation via QIX. Check the job result and theme management permission. If the workflow is skipped, an administrator can still upload the ZIP manually and choose it under **App settings > Appearance > Application theme**.
3. Open [Sales Overview](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb) and verify header readability, filter alignment, KPI layout, navigation, title styles, line chart and market sorting.
4. Only after visual approval roll out to client-facing apps. The source Qlik objects and the custom theme are separate layers.

## Acceptance criteria

- No blank or orphan QIX objects and no overlapping grid cells.
- No inline metric expressions: every KPI/chart keeps governed `qLibraryId` references.
- No fake KPIs/deltas or fabricated selection counts.
- `qlikgpt_brand_header` displays properly formatted text, not literal `##`.
- The browser matches the design tokens sufficiently, or deviations are documented before approval.
