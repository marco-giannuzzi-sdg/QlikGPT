# Overview dichiarativo: modifica diretta del JSON

Il foglio esistente **Sales Intelligence | Overview**, ID `qlikgpt_sales_overview`,
continua a essere definito da
[`presentation1-objects.json`](../semantic-models/sales/apps/presentation1-objects.json).
Questo file è scritto e versionato direttamente: il deploy non lo rigenera da
`ui/native-overview/generate.py`.

La struttura resta quella originale: proprietà del foglio, `cells` con posizioni
e dimensioni e `qChildren` con le proprietà dei grafici. I filtri continuano a
usare [`presentation1-filters.json`](../semantic-models/sales/apps/presentation1-filters.json).

## Oggetti principali

| ID nel JSON | Oggetto |
| --- | --- |
| qlikgpt_kpi_revenue | KPI fatturato |
| qlikgpt_kpi_orders | KPI ordini |
| qlikgpt_kpi_margin | KPI margine lordo |
| qlikgpt_kpi_margin_pct | KPI margine percentuale |
| qlikgpt_chart_month | Trend mensile ad area |
| qlikgpt_chart_market | Barre del fatturato per mercato |
| qlikgpt_table_sales | Tabella per mercato e canale con quattro misure |
| qlikgpt_chart_channel | Ciambella del fatturato per canale |
| qlikgpt_filter_panel | Contenitore compatto dei tre filtri |

Gli ID preesistenti di foglio, KPI, trend, mercato e filtri sono conservati.
Il blocco header duplicato e il button non valido sono rimossi dalla composizione.
KPI, grafici, filtri e tabella sono nativi; le icone SVG sono solo decorazioni.

## Aggiungere una colonna alla tabella

1. Cerca `"qId": "qlikgpt_table_sales"` dentro `qChildren`.
2. Aggiungi il master ID a `qHyperCubeDef.qMeasures` oppure
   `qHyperCubeDef.qDimensions`. Usa `qLibraryId`; lascia vuote le formule inline.
3. Verifica che il master esista nel catalogo e sia sottoscritto in
   `presentation1.json`. Per un nuovo master, completa prima il provisioning
   semantico, poi distribuisci la modifica visuale.
4. Aggiorna, all'interno dello stesso `qHyperCubeDef`:
   - `qColumnOrder` e `columnOrder`: tutti gli indici delle colonne, da zero.
   - `columnWidths`: un elemento per colonna; `-1` indica larghezza automatica.
   - `qInitialDataFetch[0].qWidth`: numero totale di dimensioni e misure.
   - `qInterColumnSortOrder`: indici coerenti con le nuove colonne.
5. Per una nuova misura aggiunta in fondo, le colonne passano da sei a sette.
   Le due dimensioni restano agli indici 0 e 1 e il fatturato all'indice 2:
   `qInterColumnSortOrder` può diventare `[2, 0, 1, 3, 4, 5, 6]`.
6. Apri una PR. La validazione statica controlla gerarchia, griglia e master.
   Il merge su main avvia il deploy governato con Qlik CLI e gli audit.

## Come viene applicato

`ci/deploy_visuals.py` legge il JSON e adatta solamente il contenitore al
formato **GenericObjectEntry** richiesto da `qlik app object set`.
Non calcola layout, non riscrive le proprietà dei grafici e non modifica il
file sorgente. Il contenitore dei filtri riceve le tre listbox definite nel
file filtri originale.

QIX serve per leggere stato e risultati: gerarchia, master, dati, stili,
riconciliazione del fatturato e timestamp del reload. Il deploy CLI verifica
anche che gli altri fogli siano invariati. Un figlio sconosciuto blocca la
sostituzione; i soli oggetti precedenti ammessi al ritiro sono il vecchio header
e il vecchio button identificati esplicitamente.

Per modifiche a visualizzazioni basate sui dati già caricati non serve un reload.
Le modifiche al modello dati seguono il flusso separato del progetto.

## Verifica del 28 ottobre 2026

Il vecchio foglio [Sales Intelligence | Overview](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb/sheet/qlikgpt_sales_overview/state/analysis)
è stato aggiornato e verificato nel browser in modalità analisi: quattro KPI centrati,
tre filtri compatti, area chart blu, barre teal, tabella con 12 righe per mercato/canale
e ciambella con palette blu/teal/navy. Il browser è stato usato solo per la verifica visiva.

- [PR di implementazione #8](https://github.com/marco-giannuzzi-sdg/QlikGPT/pull/8), integrata.
- [CI statica finale](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40713627775): verde.
- [Deploy governato finale e import Qlik CLI](https://github.com/marco-giannuzzi-sdg/QlikGPT/actions/runs/40713627736): verde.
- 102 test passati; 18 oggetti nativi nel full property tree.
- Dati e master verificati per tutti i grafici e i filtri.
- Fatturato di trend, mercato, tabella e ciambella riconciliato con il KPI.
- Script, quattro master measures, cinque master dimensions e timestamp del reload invariati durante l'import visuale.
- Proprietà complete degli altri fogli verificate invariate.
- Nessun reload dati.

Il primo tentativo di deploy si è fermato su un timeout di connessione prima
dell'import dell'Overview. La revisione finale introduce un retry limitato
all'apertura della connessione, senza ripetere RPC o scritture Engine.

I fogli Native e Premium restano separati. Questo Overview ora si modifica
direttamente in presentation1-objects.json, senza dipendere dal generatore Native.
