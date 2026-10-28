# Sales — QlikGPT Executive V1 (Frontend Native)

Questa cartella descrive l'applicazione del **[Design System globale](../../../ui/README.md)** alle due Presentation Sales; la Source of Truth della UI è [ui/design-tokens.json](../../../ui/design-tokens.json). Il Semantic Catalog [formatting.json](../catalog/formatting.json) continua a governare la **formattazione delle misure** (non la palette e le superfici dell'interfaccia).

## Palette attuale

| Ruolo | Token | Valore |
| --- | --- | --- |
| Header / brand ink | `navy` | `#142B49` |
| Primary data accent | `teal` | `#0E7490` |
| Primary interaction | `blue` | `#2563EB` |
| KPI / filter card | `card` | `#F5F8FC` |
| Chart surface | `surface` | `#FFFFFF` |
| App canvas (theme, optional) | `canvas` | `#F3F6FB` |
| Secondary labels | `muted` | `#64748B` |

## Presentation 1 — Sales Overview

La [sorgente JSON](../apps/presentation1-objects.json) riutilizza i KPI con gli ID originali, i due grafici `qlikgpt_chart_month` e `qlikgpt_chart_market` e i filtri Qlik native. L'header `qlikgpt_brand_header` usa navy e il nuovo pulsante `qlikgpt_nav_shared_kpis` apre l'altra app, senza reload. Il nuovo blocco breadcrumb `qlikgpt_navigation_hint` distingue il contesto.

## Presentation 2 — Shared KPI

La [sorgente JSON](../apps/presentation2-objects.json) mantiene i due KPI originali, ma introduce header `qlikgpt_p2_header`, sezione KPI, nota di governance e pulsante `qlikgpt_p2_nav_overview` per tornare a Sales Overview. L'azione di navigazione è un `openWebsite` nativo Qlik che punta all'altra app, non a uno sheet inesistente.

## Controlli e accettazione

- La CI con `python3 ci/ui_template.py --check` controlla che entrambe le Presentation rispettino il template, senza grid overlap o child orphan.
- `ci/deploy_visuals.py` e `ci/semantic_catalog.py` continuano a verificare master IDs, oggetti QIX e componenti nativi senza ricaricare i dati.
- **La verifica tecnica non equivale alla verifica visiva**: font, spaziature e comportamento responsive vanno controllati nel browser Qlik Cloud prima di approvare il design come standard per clienti.
- Il [Qlik Custom Theme](../../../ui/themes/qlikgpt-executive-v1/theme.json) è pronto come sorgente versionata ma non è stato importato o attivato automaticamente sul tenant.

## Nuova Presentation

Il generatore `python3 ci/ui_template.py` può preparare manifest e JSON Qlik con un unico comando di anteprima, sottoscrivendo le master measures del modello Sales via `qLibraryId`. Per un nuovo modello semantico si riutilizza lo stesso sistema di token, mentre ciascun modello mantiene i propri cataloghi, script e App ID.
