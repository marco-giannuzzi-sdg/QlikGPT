# Sales — End-to-End Field Lineage

**Lineage statico con evidenze file/riga:** QVS → QVD → campi associativi → Semantic Catalog → manifest applicativi → grafici e filtri.

**Copertura:** 4 app, 62 campi tabella, 19 campi QVD, 5 misure, 6 dimensioni, 10 visualizzazioni, 3 filtri.

[Grafo JSON dettagliato](end_to_end.json) · [App Lineage](APP_LINEAGE.md) · [Semantic Usage](../catalog/USAGE.md)

## Misure: origini e utilizzo

| Misura | Campi Presentation | Origini upstream | App e KPI/grafici | Definizione |
| --- | --- | --- | --- | --- |
| `qlikgpt_shared_average_order` | OrderID, Revenue | `etl1.RawOrders.OrderID`, `etl1.RawOrders.Quantity`, `etl1.RawOrders.UnitPrice` | **Non utilizzata** | [semantic-models/sales/catalog/measures.json#L81](../../../semantic-models/sales/catalog/measures.json#L81) |
| `qlikgpt_shared_margin` | Margin | `etl1.RawOrders.CostRatio`, `etl1.RawOrders.Quantity`, `etl1.RawOrders.UnitPrice` | `presentation/qlikgpt_kpi_margin` | [semantic-models/sales/catalog/measures.json#L45](../../../semantic-models/sales/catalog/measures.json#L45) |
| `qlikgpt_shared_margin_pct` | Margin, Revenue | `etl1.RawOrders.CostRatio`, `etl1.RawOrders.Quantity`, `etl1.RawOrders.UnitPrice` | `presentation/qlikgpt_kpi_margin_pct`, `presentation2/qlikgpt_p2_kpi_marginpct` | [semantic-models/sales/catalog/measures.json#L63](../../../semantic-models/sales/catalog/measures.json#L63) |
| `qlikgpt_shared_orders` | OrderID | `etl1.RawOrders.OrderID` | `presentation/qlikgpt_kpi_orders` | [semantic-models/sales/catalog/measures.json#L28](../../../semantic-models/sales/catalog/measures.json#L28) |
| `qlikgpt_shared_revenue` | Revenue | `etl1.RawOrders.Quantity`, `etl1.RawOrders.UnitPrice` | `presentation/qlikgpt_chart_market`, `presentation/qlikgpt_chart_month`, `presentation/qlikgpt_kpi_revenue`, `presentation2/qlikgpt_p2_kpi_revenue` | [semantic-models/sales/catalog/measures.json#L10](../../../semantic-models/sales/catalog/measures.json#L10) |

## Dimensioni e filtri

| Dimensione | Campo | Visualizzazioni/filtri | Definizione |
| --- | --- | --- | --- |
| `qlikgpt_d_category` | ProductCategory | Non utilizzata | [semantic-models/sales/catalog/dimensions.json#L43](../../../semantic-models/sales/catalog/dimensions.json#L43) |
| `qlikgpt_d_channel` | Channel | `presentation/qlikgpt_list_channel` | [semantic-models/sales/catalog/dimensions.json#L77](../../../semantic-models/sales/catalog/dimensions.json#L77) |
| `qlikgpt_d_market` | Market | `presentation/qlikgpt_chart_market`, `presentation/qlikgpt_list_market` | [semantic-models/sales/catalog/dimensions.json#L9](../../../semantic-models/sales/catalog/dimensions.json#L9) |
| `qlikgpt_d_quarter` | YearQuarter | Non utilizzata | [semantic-models/sales/catalog/dimensions.json#L94](../../../semantic-models/sales/catalog/dimensions.json#L94) |
| `qlikgpt_d_year` | SalesYear | `presentation/qlikgpt_list_year` | [semantic-models/sales/catalog/dimensions.json#L60](../../../semantic-models/sales/catalog/dimensions.json#L60) |
| `qlikgpt_d_yearmonth` | YearMonth | `presentation/qlikgpt_chart_month` | [semantic-models/sales/catalog/dimensions.json#L26](../../../semantic-models/sales/catalog/dimensions.json#L26) |

## Variabili

Le variabili del catalogo sono versionate e possono essere sottoscritte; non risultano referenziate da espressioni dei visual attuali. Non si inventano utilizzi.

| Variabile | App sottoscritte |
| --- | --- |
| `qlikgpt_v_currency_label` | Nessuna |
| `qlikgpt_v_target_margin` | presentation, presentation2 |

## Esempi di impact analysis

- `python3 ci/field_lineage.py --impact source:etl1.RawOrders.Quantity` — include la propagazione dei WHERE che filtrano le righe.
- `python3 ci/field_lineage.py --impact field:Revenue` — misure, KPI, grafici e ordinamenti.
- `python3 ci/field_lineage.py --impact measure:qlikgpt_shared_margin_pct` — app e oggetti a valle, fonti a monte.
- `python3 ci/field_lineage.py --check` — controlla i report generati.

## Tipi di arco e limiti

- **value**: dipendenza di calcolo; **row_filter**: influisce sul numero delle righe (WHERE), non necessariamente sul valore; **inline_sort**: influenza l'ordinamento.
- **store_qvd / field_binding**: percorso QVD e campo logico Qlik.
- **semantic_dependency / subscribed_by / visual_use / filter_use**: catalogo, sottoscrizione e oggetto versionato.
- Dati ETL1 sintetici generati da AUTOGENERATE/Rand(), non sorgenti aziendali reali.
- Non rappresenta il Qlik runtime, dati aggiornati, oggetti manuali, SQL, join, mapping, campi dinamici o spazi Qlik non condivisi.
- Qualunque collegamento non dimostrato dai file viene omesso e segnalato.

## Avvisi del parser

Nessuna anomalia rilevata nel subset supportato.
