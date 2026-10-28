# Sales Analytics — Modello semantico

Tutti gli asset del modello Sales sono in questa cartella. [model.json](model.json) registra le applicazioni e i percorsi locali.

- [ETL1 RAW](scripts/etl1.qvs) → `RawOrders.qvd`.
- [ETL2 TRANSFORM](scripts/etl2.qvs) → `Sales_Clean.qvd`.
- [Script condiviso Presentation](scripts/presentation.qvs).
- [Manifest e dashboard](apps/).
- [Catalogo semantico](catalog/README.md), [Usage & Impact](catalog/USAGE.md).
- [App Lineage](lineage/APP_LINEAGE.md), [grafo JSON](lineage/graph.json).
- [End-to-End Field Lineage](lineage/END_TO_END.md): da campi QVS/QVD a misure e KPI, con [grafo dettagliato JSON](lineage/end_to_end.json).
- [Design System](design/EXECUTIVE_CLEAN.md).
- [App ID](deployment/app-ids.json): gli ID Qlik esistenti restano invariati.

Entrambe le Presentation usano il **[QlikGPT Executive V1](../../ui/README.md)**: header brandizzato, navigazione nativa tra le due app, KPI su card e disposizione su griglia a 24 colonne. La UI è parametrizzata dal manifest `uiTemplate`, mantenendo master item e App ID invariati.

Il framework condiviso risiede in [ci](../../ci/), [tests](../../tests/) e [GitHub Actions](../../.github/workflows/deploy-qlik-cloud.yml). I QVS sono distribuiti senza reload e i reload dati richiedono un comando esplicito.

Il registry supporta l'aggiunta di cartelle sorelle con altri `model.json`, ma il job di deployment corrente lavora su un modello alla volta e resta configurato su `sales`.
