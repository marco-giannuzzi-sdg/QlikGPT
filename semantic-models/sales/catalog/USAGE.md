# QlikGPT — Semantic Catalog 2.0 | Usage & Impact

> Report **generato dai manifest e dagli oggetti versionati su GitHub**. Le sottoscrizioni rappresentano master item attesi nelle app; le visualizzazioni sono ricavate dai riferimenti `qLibraryId` dichiarati, non da telemetria QIX runtime.

## Applicazioni

| Applicazione | Qlik Cloud | Manifest |
| --- | --- | --- |
| QlikGPT - 03 PRESENTATION | [Apri app](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb) | [Manifest](../../../semantic-models/sales/apps/presentation1.json) |
| QlikGPT - 04 PRESENTATION SHARED | [Apri app](https://sdggroup-it.eu.qlikcloud.com/sense/app/04280b14-6ba5-4fe9-90d6-2ff8fa1c994f) | [Manifest](../../../semantic-models/sales/apps/presentation2.json) |

## Matrice delle dipendenze

**✓** = master item sottoscritto, **—** = assente. Il numero di grafici che lo referenziano è mostrato separatamente.

| Tipo | Elemento | presentation | presentation2 | Grafici collegati |
| --- | --- | :---: | :---: | ---: |
| measure | `qlikgpt_shared_revenue` — Fatturato | ✓ | ✓ | 4 |
| measure | `qlikgpt_shared_orders` — Numero ordini | ✓ | — | 1 |
| measure | `qlikgpt_shared_margin` — Margine lordo | ✓ | — | 1 |
| measure | `qlikgpt_shared_margin_pct` — Margine % | ✓ | ✓ | 2 |
| measure | `qlikgpt_shared_average_order` — Valore medio ordine | — | — | 0 |
| dimension | `qlikgpt_d_market` — Mercato | ✓ | ✓ | 2 |
| dimension | `qlikgpt_d_yearmonth` — Anno / Mese | ✓ | ✓ | 1 |
| dimension | `qlikgpt_d_category` — Categoria | ✓ | — | 0 |
| dimension | `qlikgpt_d_year` — Anno | ✓ | — | 1 |
| dimension | `qlikgpt_d_channel` — Canale | ✓ | — | 1 |
| dimension | `qlikgpt_d_quarter` — Trimestre | — | — | 0 |
| variable | `qlikgpt_v_target_margin` — vQlikGPTTargetMargin | ✓ | ✓ | 0 |
| variable | `qlikgpt_v_currency_label` — vQlikGPTCurrencyLabel | — | — | 0 |

## Impatto per oggetto

In caso di modifica, il deployment sincronizza **solo le app sottoscritte**. Le visualizzazioni che usano `qLibraryId` ereditano la definizione aggiornata.

### Fatturato · `qlikgpt_shared_revenue`
**Tipo:** measure · **Versione:** 1.0.2
**Applicazioni:** [presentation](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb), [presentation2](https://sdggroup-it.eu.qlikcloud.com/sense/app/04280b14-6ba5-4fe9-90d6-2ff8fa1c994f)
**Visualizzazioni collegate:** `presentation/qlikgpt_kpi_revenue`, `presentation/qlikgpt_chart_month`, `presentation/qlikgpt_chart_market`, `presentation2/qlikgpt_p2_kpi_revenue`

### Numero ordini · `qlikgpt_shared_orders`
**Tipo:** measure · **Versione:** 1.0.0
**Applicazioni:** [presentation](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb)
**Visualizzazioni collegate:** `presentation/qlikgpt_kpi_orders`

### Margine lordo · `qlikgpt_shared_margin`
**Tipo:** measure · **Versione:** 1.0.0
**Applicazioni:** [presentation](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb)
**Visualizzazioni collegate:** `presentation/qlikgpt_kpi_margin`

### Margine % · `qlikgpt_shared_margin_pct`
**Tipo:** measure · **Versione:** 1.0.1
**Applicazioni:** [presentation](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb), [presentation2](https://sdggroup-it.eu.qlikcloud.com/sense/app/04280b14-6ba5-4fe9-90d6-2ff8fa1c994f)
**Visualizzazioni collegate:** `presentation/qlikgpt_kpi_margin_pct`, `presentation2/qlikgpt_p2_kpi_marginpct`

### Valore medio ordine · `qlikgpt_shared_average_order`
**Tipo:** measure · **Versione:** 1.0.0
**Applicazioni:** Nessuna (disponibile per uso futuro)
**Visualizzazioni collegate:** Nessuna referenza diretta

### Mercato · `qlikgpt_d_market`
**Tipo:** dimension · **Versione:** 1.0.0
**Applicazioni:** [presentation](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb), [presentation2](https://sdggroup-it.eu.qlikcloud.com/sense/app/04280b14-6ba5-4fe9-90d6-2ff8fa1c994f)
**Visualizzazioni collegate:** `presentation/qlikgpt_chart_market`, `presentation/qlikgpt_list_market`

### Anno / Mese · `qlikgpt_d_yearmonth`
**Tipo:** dimension · **Versione:** 1.0.0
**Applicazioni:** [presentation](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb), [presentation2](https://sdggroup-it.eu.qlikcloud.com/sense/app/04280b14-6ba5-4fe9-90d6-2ff8fa1c994f)
**Visualizzazioni collegate:** `presentation/qlikgpt_chart_month`

### Categoria · `qlikgpt_d_category`
**Tipo:** dimension · **Versione:** 1.0.0
**Applicazioni:** [presentation](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb)
**Visualizzazioni collegate:** Nessuna referenza diretta

### Anno · `qlikgpt_d_year`
**Tipo:** dimension · **Versione:** 1.0.0
**Applicazioni:** [presentation](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb)
**Visualizzazioni collegate:** `presentation/qlikgpt_list_year`

### Canale · `qlikgpt_d_channel`
**Tipo:** dimension · **Versione:** 1.0.0
**Applicazioni:** [presentation](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb)
**Visualizzazioni collegate:** `presentation/qlikgpt_list_channel`

### Trimestre · `qlikgpt_d_quarter`
**Tipo:** dimension · **Versione:** 1.0.0
**Applicazioni:** Nessuna (disponibile per uso futuro)
**Visualizzazioni collegate:** Nessuna referenza diretta

### vQlikGPTTargetMargin · `qlikgpt_v_target_margin`
**Tipo:** variable · **Versione:** 1.0.0
**Applicazioni:** [presentation](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb), [presentation2](https://sdggroup-it.eu.qlikcloud.com/sense/app/04280b14-6ba5-4fe9-90d6-2ff8fa1c994f)
**Visualizzazioni collegate:** Nessuna referenza diretta

### vQlikGPTCurrencyLabel · `qlikgpt_v_currency_label`
**Tipo:** variable · **Versione:** 1.0.0
**Applicazioni:** Nessuna (disponibile per uso futuro)
**Visualizzazioni collegate:** Nessuna referenza diretta

## Come si usa

Modifica **[measures.json](measures.json)**, **[dimensions.json](dimensions.json)** oppure **[variables.json](variables.json)**; associa gli ID alle app nei rispettivi manifest. Il report è aggiornato dal workflow GitHub Actions senza usare il computer dell'autore.

Per i dettagli strutturati e per altri strumenti, usa **[usage.json](usage.json)**.
