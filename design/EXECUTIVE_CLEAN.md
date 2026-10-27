# QlikGPT — Executive Clean v2

## Why

Use a coherent BI design system rather than Qlik's default color on every metric. The dashboard remains **100% native Qlik Cloud** (no HTML mashup or local client).

## Palette

| Semantic role | Color |
| --- | --- |
| Brand ink / Revenue KPI | `#142B49` (navy) |
| Trend and Margin KPI | `#0E7490` (teal) |
| Positive margin rate | `#15803D` (green) |
| Primary accent | `#2563EB` |
| Supporting text | `#64748B` |
| KPI card background | `#F5F9FC` |

## Chart definitions

The Sales Overview dashboard is stored in [apps/presentation1-objects.json](../apps/presentation1-objects.json).

- **Revenue trend:** 20 chronological `YearMonth` values, native Qlik linechart, 3px solid teal line, discrete date axis, no legend, data points enabled, currency value format.
- **Revenue by market:** native Qlik barchart, horizontal orientation, sorted by `Sum(Revenue)` descending, value labels enabled, matching teal hue.
- **KPI cards:** compact EUR millions with `M` suffix, 5,000 order count, percentage with one decimal, restrained color coding and responsive type.
- **Filters:** SalesYear, Market and Channel remain native Qlik associative selections.

## Validation

The Qlik Engine hypercubes must return nonzero data rows. QlikGPT CI also verifies that 20 expected native objects exist after a Qlik CLI export and that Presentation holds 5,000 orders. **A QIX hypercube with data is not visual proof that the Qlik client drew the chart.** Final acceptance requires viewing the actual sheet in the browser.

## Continuous delivery

Any commit modifying only `frontend/**` runs a **frontend-only** deploy, leaving all three apps and their loaded data unchanged. Changes to `scripts/**`, `ci/**` or workflow files deploy all three stages sequentially. Manual workflow runs default to full.

## Next level

A tenant-level Qlik custom theme can extend margins, typography, background and chart palettes. This is deliberately not imported without checking tenant permissions and the rendered native dashboard first.

## Central measure governance

All four KPI measures and both Revenue charts use `qLibraryId` references to master measures in `catalog/measures.json`. No inline measure formulas or app-specific master-measure files. Display formatting is controlled by the corresponding catalog measure. The second Presentation uses the same contract.
