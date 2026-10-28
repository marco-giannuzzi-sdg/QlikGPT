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

## Passaggi intermedi verificati per ciascuna misura

Ogni arco qui sotto è un collegamento documentato: campo sorgente, trasformazione ETL, QVD, campo del modello associativo, definizione semantica, sottoscrizione e oggetto Qlik.
Le relazioni **row_filter** sono escluse da questi percorsi di valore e riportate nella sezione successiva.

### Valore medio ordine (`qlikgpt_shared_average_order`)

| Da | A | Relazione | Evidenza nel repository |
| --- | --- | --- | --- |
| `presentation2.OrderID` | `Valore medio ordine` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L81](../../../semantic-models/sales/catalog/measures.json#L81) |
| `presentation2.Revenue` | `Valore medio ordine` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L81](../../../semantic-models/sales/catalog/measures.json#L81) |
| `presentation.OrderID` | `Valore medio ordine` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L81](../../../semantic-models/sales/catalog/measures.json#L81) |
| `presentation.Revenue` | `Valore medio ordine` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L81](../../../semantic-models/sales/catalog/measures.json#L81) |
| `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#OrderID` | `etl2.RawOrders.OrderID` | `value` | [semantic-models/sales/scripts/etl2.qvs#L15](../../../semantic-models/sales/scripts/etl2.qvs#L15) |
| `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#Quantity` | `etl2.RawOrders.Quantity` | `value` | [semantic-models/sales/scripts/etl2.qvs#L15](../../../semantic-models/sales/scripts/etl2.qvs#L15) |
| `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#UnitPrice` | `etl2.RawOrders.UnitPrice` | `value` | [semantic-models/sales/scripts/etl2.qvs#L15](../../../semantic-models/sales/scripts/etl2.qvs#L15) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#OrderID` | `presentation2.FactSales.OrderID` | `value` | [semantic-models/sales/scripts/presentation.qvs#L15](../../../semantic-models/sales/scripts/presentation.qvs#L15) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#OrderID` | `presentation.FactSales.OrderID` | `value` | [semantic-models/sales/scripts/presentation.qvs#L15](../../../semantic-models/sales/scripts/presentation.qvs#L15) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `presentation2.FactSales.Revenue` | `value` | [semantic-models/sales/scripts/presentation.qvs#L23](../../../semantic-models/sales/scripts/presentation.qvs#L23) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `presentation.FactSales.Revenue` | `value` | [semantic-models/sales/scripts/presentation.qvs#L23](../../../semantic-models/sales/scripts/presentation.qvs#L23) |
| `etl1.RawOrders.OrderID` | `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#OrderID` | `store_qvd` | [semantic-models/sales/scripts/etl1.qvs#L31](../../../semantic-models/sales/scripts/etl1.qvs#L31) |
| `etl1.RawOrders.Quantity` | `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#Quantity` | `store_qvd` | [semantic-models/sales/scripts/etl1.qvs#L31](../../../semantic-models/sales/scripts/etl1.qvs#L31) |
| `etl1.RawOrders.UnitPrice` | `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#UnitPrice` | `store_qvd` | [semantic-models/sales/scripts/etl1.qvs#L31](../../../semantic-models/sales/scripts/etl1.qvs#L31) |
| `etl2.RawOrders.OrderID` | `etl2.SalesClean.OrderID` | `value` | [semantic-models/sales/scripts/etl2.qvs#L21](../../../semantic-models/sales/scripts/etl2.qvs#L21) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.Revenue` | `value` | [semantic-models/sales/scripts/etl2.qvs#L29](../../../semantic-models/sales/scripts/etl2.qvs#L29) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.Revenue` | `value` | [semantic-models/sales/scripts/etl2.qvs#L29](../../../semantic-models/sales/scripts/etl2.qvs#L29) |
| `etl2.SalesClean.OrderID` | `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#OrderID` | `store_qvd` | [semantic-models/sales/scripts/etl2.qvs#L38](../../../semantic-models/sales/scripts/etl2.qvs#L38) |
| `etl2.SalesClean.Revenue` | `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `store_qvd` | [semantic-models/sales/scripts/etl2.qvs#L38](../../../semantic-models/sales/scripts/etl2.qvs#L38) |
| `presentation2.FactSales.OrderID` | `presentation2.OrderID` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L15](../../../semantic-models/sales/scripts/presentation.qvs#L15) |
| `presentation2.FactSales.Revenue` | `presentation2.Revenue` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L23](../../../semantic-models/sales/scripts/presentation.qvs#L23) |
| `presentation.FactSales.OrderID` | `presentation.OrderID` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L15](../../../semantic-models/sales/scripts/presentation.qvs#L15) |
| `presentation.FactSales.Revenue` | `presentation.Revenue` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L23](../../../semantic-models/sales/scripts/presentation.qvs#L23) |

### Margine lordo (`qlikgpt_shared_margin`)

| Da | A | Relazione | Evidenza nel repository |
| --- | --- | --- | --- |
| `presentation2.Margin` | `Margine lordo` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L45](../../../semantic-models/sales/catalog/measures.json#L45) |
| `presentation.Margin` | `Margine lordo` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L45](../../../semantic-models/sales/catalog/measures.json#L45) |
| `Margine lordo` | `presentation: qlikgpt_shared_margin` | `subscribed_by` | [semantic-models/sales/apps/presentation1.json#L8](../../../semantic-models/sales/apps/presentation1.json#L8) |
| `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#CostRatio` | `etl2.RawOrders.CostRatio` | `value` | [semantic-models/sales/scripts/etl2.qvs#L15](../../../semantic-models/sales/scripts/etl2.qvs#L15) |
| `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#Quantity` | `etl2.RawOrders.Quantity` | `value` | [semantic-models/sales/scripts/etl2.qvs#L15](../../../semantic-models/sales/scripts/etl2.qvs#L15) |
| `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#UnitPrice` | `etl2.RawOrders.UnitPrice` | `value` | [semantic-models/sales/scripts/etl2.qvs#L15](../../../semantic-models/sales/scripts/etl2.qvs#L15) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Cost` | `presentation2.FactSales.Margin` | `value` | [semantic-models/sales/scripts/presentation.qvs#L25](../../../semantic-models/sales/scripts/presentation.qvs#L25) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Cost` | `presentation.FactSales.Margin` | `value` | [semantic-models/sales/scripts/presentation.qvs#L25](../../../semantic-models/sales/scripts/presentation.qvs#L25) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `presentation2.FactSales.Margin` | `value` | [semantic-models/sales/scripts/presentation.qvs#L25](../../../semantic-models/sales/scripts/presentation.qvs#L25) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `presentation.FactSales.Margin` | `value` | [semantic-models/sales/scripts/presentation.qvs#L25](../../../semantic-models/sales/scripts/presentation.qvs#L25) |
| `presentation: qlikgpt_shared_margin` | `Margine lordo` | `visual_use` | [semantic-models/sales/apps/presentation1-objects.json#L290](../../../semantic-models/sales/apps/presentation1-objects.json#L290) |
| `etl1.RawOrders.CostRatio` | `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#CostRatio` | `store_qvd` | [semantic-models/sales/scripts/etl1.qvs#L31](../../../semantic-models/sales/scripts/etl1.qvs#L31) |
| `etl1.RawOrders.Quantity` | `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#Quantity` | `store_qvd` | [semantic-models/sales/scripts/etl1.qvs#L31](../../../semantic-models/sales/scripts/etl1.qvs#L31) |
| `etl1.RawOrders.UnitPrice` | `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#UnitPrice` | `store_qvd` | [semantic-models/sales/scripts/etl1.qvs#L31](../../../semantic-models/sales/scripts/etl1.qvs#L31) |
| `etl2.RawOrders.CostRatio` | `etl2.SalesClean.Cost` | `value` | [semantic-models/sales/scripts/etl2.qvs#L30](../../../semantic-models/sales/scripts/etl2.qvs#L30) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.Cost` | `value` | [semantic-models/sales/scripts/etl2.qvs#L30](../../../semantic-models/sales/scripts/etl2.qvs#L30) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.Revenue` | `value` | [semantic-models/sales/scripts/etl2.qvs#L29](../../../semantic-models/sales/scripts/etl2.qvs#L29) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.Cost` | `value` | [semantic-models/sales/scripts/etl2.qvs#L30](../../../semantic-models/sales/scripts/etl2.qvs#L30) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.Revenue` | `value` | [semantic-models/sales/scripts/etl2.qvs#L29](../../../semantic-models/sales/scripts/etl2.qvs#L29) |
| `etl2.SalesClean.Cost` | `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Cost` | `store_qvd` | [semantic-models/sales/scripts/etl2.qvs#L38](../../../semantic-models/sales/scripts/etl2.qvs#L38) |
| `etl2.SalesClean.Revenue` | `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `store_qvd` | [semantic-models/sales/scripts/etl2.qvs#L38](../../../semantic-models/sales/scripts/etl2.qvs#L38) |
| `presentation2.FactSales.Margin` | `presentation2.Margin` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L25](../../../semantic-models/sales/scripts/presentation.qvs#L25) |
| `presentation.FactSales.Margin` | `presentation.Margin` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L25](../../../semantic-models/sales/scripts/presentation.qvs#L25) |

### Margine % (`qlikgpt_shared_margin_pct`)

| Da | A | Relazione | Evidenza nel repository |
| --- | --- | --- | --- |
| `presentation2.Margin` | `Margine %` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L63](../../../semantic-models/sales/catalog/measures.json#L63) |
| `presentation2.Revenue` | `Margine %` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L63](../../../semantic-models/sales/catalog/measures.json#L63) |
| `presentation.Margin` | `Margine %` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L63](../../../semantic-models/sales/catalog/measures.json#L63) |
| `presentation.Revenue` | `Margine %` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L63](../../../semantic-models/sales/catalog/measures.json#L63) |
| `Margine %` | `presentation2: qlikgpt_shared_margin_pct` | `subscribed_by` | [semantic-models/sales/apps/presentation2.json#L7](../../../semantic-models/sales/apps/presentation2.json#L7) |
| `Margine %` | `presentation: qlikgpt_shared_margin_pct` | `subscribed_by` | [semantic-models/sales/apps/presentation1.json#L9](../../../semantic-models/sales/apps/presentation1.json#L9) |
| `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#CostRatio` | `etl2.RawOrders.CostRatio` | `value` | [semantic-models/sales/scripts/etl2.qvs#L15](../../../semantic-models/sales/scripts/etl2.qvs#L15) |
| `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#Quantity` | `etl2.RawOrders.Quantity` | `value` | [semantic-models/sales/scripts/etl2.qvs#L15](../../../semantic-models/sales/scripts/etl2.qvs#L15) |
| `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#UnitPrice` | `etl2.RawOrders.UnitPrice` | `value` | [semantic-models/sales/scripts/etl2.qvs#L15](../../../semantic-models/sales/scripts/etl2.qvs#L15) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Cost` | `presentation2.FactSales.Margin` | `value` | [semantic-models/sales/scripts/presentation.qvs#L25](../../../semantic-models/sales/scripts/presentation.qvs#L25) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Cost` | `presentation.FactSales.Margin` | `value` | [semantic-models/sales/scripts/presentation.qvs#L25](../../../semantic-models/sales/scripts/presentation.qvs#L25) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `presentation2.FactSales.Margin` | `value` | [semantic-models/sales/scripts/presentation.qvs#L25](../../../semantic-models/sales/scripts/presentation.qvs#L25) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `presentation2.FactSales.Revenue` | `value` | [semantic-models/sales/scripts/presentation.qvs#L23](../../../semantic-models/sales/scripts/presentation.qvs#L23) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `presentation.FactSales.Margin` | `value` | [semantic-models/sales/scripts/presentation.qvs#L25](../../../semantic-models/sales/scripts/presentation.qvs#L25) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `presentation.FactSales.Revenue` | `value` | [semantic-models/sales/scripts/presentation.qvs#L23](../../../semantic-models/sales/scripts/presentation.qvs#L23) |
| `presentation2: qlikgpt_shared_margin_pct` | `MARGINE % GOVERNATO` | `visual_use` | [semantic-models/sales/apps/presentation2-objects.json#L103](../../../semantic-models/sales/apps/presentation2-objects.json#L103) |
| `presentation: qlikgpt_shared_margin_pct` | `Margine %` | `visual_use` | [semantic-models/sales/apps/presentation1-objects.json#L337](../../../semantic-models/sales/apps/presentation1-objects.json#L337) |
| `etl1.RawOrders.CostRatio` | `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#CostRatio` | `store_qvd` | [semantic-models/sales/scripts/etl1.qvs#L31](../../../semantic-models/sales/scripts/etl1.qvs#L31) |
| `etl1.RawOrders.Quantity` | `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#Quantity` | `store_qvd` | [semantic-models/sales/scripts/etl1.qvs#L31](../../../semantic-models/sales/scripts/etl1.qvs#L31) |
| `etl1.RawOrders.UnitPrice` | `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#UnitPrice` | `store_qvd` | [semantic-models/sales/scripts/etl1.qvs#L31](../../../semantic-models/sales/scripts/etl1.qvs#L31) |
| `etl2.RawOrders.CostRatio` | `etl2.SalesClean.Cost` | `value` | [semantic-models/sales/scripts/etl2.qvs#L30](../../../semantic-models/sales/scripts/etl2.qvs#L30) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.Cost` | `value` | [semantic-models/sales/scripts/etl2.qvs#L30](../../../semantic-models/sales/scripts/etl2.qvs#L30) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.Revenue` | `value` | [semantic-models/sales/scripts/etl2.qvs#L29](../../../semantic-models/sales/scripts/etl2.qvs#L29) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.Cost` | `value` | [semantic-models/sales/scripts/etl2.qvs#L30](../../../semantic-models/sales/scripts/etl2.qvs#L30) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.Revenue` | `value` | [semantic-models/sales/scripts/etl2.qvs#L29](../../../semantic-models/sales/scripts/etl2.qvs#L29) |
| `etl2.SalesClean.Cost` | `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Cost` | `store_qvd` | [semantic-models/sales/scripts/etl2.qvs#L38](../../../semantic-models/sales/scripts/etl2.qvs#L38) |
| `etl2.SalesClean.Revenue` | `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `store_qvd` | [semantic-models/sales/scripts/etl2.qvs#L38](../../../semantic-models/sales/scripts/etl2.qvs#L38) |
| `presentation2.FactSales.Margin` | `presentation2.Margin` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L25](../../../semantic-models/sales/scripts/presentation.qvs#L25) |
| `presentation2.FactSales.Revenue` | `presentation2.Revenue` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L23](../../../semantic-models/sales/scripts/presentation.qvs#L23) |
| `presentation.FactSales.Margin` | `presentation.Margin` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L25](../../../semantic-models/sales/scripts/presentation.qvs#L25) |
| `presentation.FactSales.Revenue` | `presentation.Revenue` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L23](../../../semantic-models/sales/scripts/presentation.qvs#L23) |

### Numero ordini (`qlikgpt_shared_orders`)

| Da | A | Relazione | Evidenza nel repository |
| --- | --- | --- | --- |
| `presentation2.OrderID` | `Numero ordini` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L28](../../../semantic-models/sales/catalog/measures.json#L28) |
| `presentation.OrderID` | `Numero ordini` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L28](../../../semantic-models/sales/catalog/measures.json#L28) |
| `Numero ordini` | `presentation: qlikgpt_shared_orders` | `subscribed_by` | [semantic-models/sales/apps/presentation1.json#L7](../../../semantic-models/sales/apps/presentation1.json#L7) |
| `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#OrderID` | `etl2.RawOrders.OrderID` | `value` | [semantic-models/sales/scripts/etl2.qvs#L15](../../../semantic-models/sales/scripts/etl2.qvs#L15) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#OrderID` | `presentation2.FactSales.OrderID` | `value` | [semantic-models/sales/scripts/presentation.qvs#L15](../../../semantic-models/sales/scripts/presentation.qvs#L15) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#OrderID` | `presentation.FactSales.OrderID` | `value` | [semantic-models/sales/scripts/presentation.qvs#L15](../../../semantic-models/sales/scripts/presentation.qvs#L15) |
| `presentation: qlikgpt_shared_orders` | `Ordini` | `visual_use` | [semantic-models/sales/apps/presentation1-objects.json#L243](../../../semantic-models/sales/apps/presentation1-objects.json#L243) |
| `etl1.RawOrders.OrderID` | `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#OrderID` | `store_qvd` | [semantic-models/sales/scripts/etl1.qvs#L31](../../../semantic-models/sales/scripts/etl1.qvs#L31) |
| `etl2.RawOrders.OrderID` | `etl2.SalesClean.OrderID` | `value` | [semantic-models/sales/scripts/etl2.qvs#L21](../../../semantic-models/sales/scripts/etl2.qvs#L21) |
| `etl2.SalesClean.OrderID` | `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#OrderID` | `store_qvd` | [semantic-models/sales/scripts/etl2.qvs#L38](../../../semantic-models/sales/scripts/etl2.qvs#L38) |
| `presentation2.FactSales.OrderID` | `presentation2.OrderID` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L15](../../../semantic-models/sales/scripts/presentation.qvs#L15) |
| `presentation.FactSales.OrderID` | `presentation.OrderID` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L15](../../../semantic-models/sales/scripts/presentation.qvs#L15) |

### Fatturato (`qlikgpt_shared_revenue`)

| Da | A | Relazione | Evidenza nel repository |
| --- | --- | --- | --- |
| `presentation2.Revenue` | `Fatturato` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L10](../../../semantic-models/sales/catalog/measures.json#L10) |
| `presentation.Revenue` | `Fatturato` | `semantic_dependency` | [semantic-models/sales/catalog/measures.json#L10](../../../semantic-models/sales/catalog/measures.json#L10) |
| `Fatturato` | `presentation2: qlikgpt_shared_revenue` | `subscribed_by` | [semantic-models/sales/apps/presentation2.json#L6](../../../semantic-models/sales/apps/presentation2.json#L6) |
| `Fatturato` | `presentation: qlikgpt_shared_revenue` | `subscribed_by` | [semantic-models/sales/apps/presentation1.json#L6](../../../semantic-models/sales/apps/presentation1.json#L6) |
| `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#Quantity` | `etl2.RawOrders.Quantity` | `value` | [semantic-models/sales/scripts/etl2.qvs#L15](../../../semantic-models/sales/scripts/etl2.qvs#L15) |
| `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#UnitPrice` | `etl2.RawOrders.UnitPrice` | `value` | [semantic-models/sales/scripts/etl2.qvs#L15](../../../semantic-models/sales/scripts/etl2.qvs#L15) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `presentation2.FactSales.Revenue` | `value` | [semantic-models/sales/scripts/presentation.qvs#L23](../../../semantic-models/sales/scripts/presentation.qvs#L23) |
| `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `presentation.FactSales.Revenue` | `value` | [semantic-models/sales/scripts/presentation.qvs#L23](../../../semantic-models/sales/scripts/presentation.qvs#L23) |
| `presentation2: qlikgpt_shared_revenue` | `RICAVI GOVERNATI` | `visual_use` | [semantic-models/sales/apps/presentation2-objects.json#L73](../../../semantic-models/sales/apps/presentation2-objects.json#L73) |
| `presentation: qlikgpt_shared_revenue` | `RICAVI PER MERCATO` | `visual_use` | [semantic-models/sales/apps/presentation1-objects.json#L196](../../../semantic-models/sales/apps/presentation1-objects.json#L196) |
| `presentation: qlikgpt_shared_revenue` | `TREND DEL FATTURATO` | `visual_use` | [semantic-models/sales/apps/presentation1-objects.json#L196](../../../semantic-models/sales/apps/presentation1-objects.json#L196) |
| `presentation: qlikgpt_shared_revenue` | `Fatturato` | `visual_use` | [semantic-models/sales/apps/presentation1-objects.json#L196](../../../semantic-models/sales/apps/presentation1-objects.json#L196) |
| `etl1.RawOrders.Quantity` | `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#Quantity` | `store_qvd` | [semantic-models/sales/scripts/etl1.qvs#L31](../../../semantic-models/sales/scripts/etl1.qvs#L31) |
| `etl1.RawOrders.UnitPrice` | `lib://DataFiles/QlikGPT/01_RAW/RawOrders.qvd#UnitPrice` | `store_qvd` | [semantic-models/sales/scripts/etl1.qvs#L31](../../../semantic-models/sales/scripts/etl1.qvs#L31) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.Revenue` | `value` | [semantic-models/sales/scripts/etl2.qvs#L29](../../../semantic-models/sales/scripts/etl2.qvs#L29) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.Revenue` | `value` | [semantic-models/sales/scripts/etl2.qvs#L29](../../../semantic-models/sales/scripts/etl2.qvs#L29) |
| `etl2.SalesClean.Revenue` | `lib://DataFiles/QlikGPT/02_TRANSFORM/Sales_Clean.qvd#Revenue` | `store_qvd` | [semantic-models/sales/scripts/etl2.qvs#L38](../../../semantic-models/sales/scripts/etl2.qvs#L38) |
| `presentation2.FactSales.Revenue` | `presentation2.Revenue` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L23](../../../semantic-models/sales/scripts/presentation.qvs#L23) |
| `presentation.FactSales.Revenue` | `presentation.Revenue` | `field_binding` | [semantic-models/sales/scripts/presentation.qvs#L23](../../../semantic-models/sales/scripts/presentation.qvs#L23) |

## Dipendenze che filtrano le righe

Un campo utilizzato da un WHERE può cambiare i risultati dei KPI anche senza entrare nell'espressione di calcolo. Gli archi di questo tipo vengono mantenuti separati nel JSON e nella impact analysis.

| Input | Output filtrato | Dove |
| --- | --- | --- |
| `etl2.RawOrders.OrderID` | `etl2.SalesClean.Channel` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.OrderID` | `etl2.SalesClean.Cost` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.OrderID` | `etl2.SalesClean.CustomerID` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.OrderID` | `etl2.SalesClean.Market` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.OrderID` | `etl2.SalesClean.OrderDate` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.OrderID` | `etl2.SalesClean.OrderID` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.OrderID` | `etl2.SalesClean.ProductCategory` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.OrderID` | `etl2.SalesClean.Quantity` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.OrderID` | `etl2.SalesClean.Revenue` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.OrderID` | `etl2.SalesClean.UnitPrice` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.Channel` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.Cost` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.CustomerID` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.Market` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.OrderDate` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.OrderID` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.ProductCategory` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.Quantity` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.Revenue` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.Quantity` | `etl2.SalesClean.UnitPrice` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.Channel` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.Cost` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.CustomerID` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.Market` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.OrderDate` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.OrderID` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.ProductCategory` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.Quantity` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.Revenue` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |
| `etl2.RawOrders.UnitPrice` | `etl2.SalesClean.UnitPrice` | [semantic-models/sales/scripts/etl2.qvs#L18](../../../semantic-models/sales/scripts/etl2.qvs#L18) |


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
