# QlikGPT — Qlik Sense SaaS as Code

**Semantic Catalog 2.0** centralizza master measures, master dimensions e variabili Qlik, con una matrice GitHub consultabile delle applicazioni e dei grafici che le utilizzano.

### Consulta uso e impatti

- **[Usage & Impact Report](catalog/USAGE.md)**: matrice misure, dimensioni e variabili per Presentation, e oggetti visuali collegati tramite `qLibraryId`.
- **[Report machine-readable](catalog/usage.json)**: dipendenze disponibili per automazioni e controlli.
- **[Master dimensions](catalog/dimensions.json)** e **[variabili Qlik](catalog/variables.json)**: definizioni versionate con ID stabili, anche quando non ancora assegnate a un'app.
- **[Semantic Catalog 2.0](catalog/README.md)**: istruzioni di governance e promozione.

Il report fotografa le **dipendenze dichiarate nei JSON GitHub**, non gli oggetti aggiunti a mano nel tenant né gli accessi degli utenti. I grafici con dimensioni inline sono segnalati separatamente.

**Unico Semantic Catalog per tutte le master measures**: GitHub è la fonte di verità, ogni Presentation sceglie le misure tramite il proprio manifest. Nessuna master measure è definita in file app-specifici.

## Architettura

```
GitHub  catalog/measures.json              ← TUTTE le misure, anche inutilizzate
        apps/presentation1.json             ← solo ID delle misure da utilizzare
        apps/presentation2.json             ← solo ID delle misure da utilizzare
            ↓ commit su main
        GitHub Actions (runner cloud, senza PC)
            ├─ analisi dipendenze per ID e subscription
            ├─ verifica JSON / test / contract
            ├─ QIX CreateMeasure / SetProperties per le sole app interessate
            ├─ QA qLibraryId di KPI, chart e valori; GetProperties + eval
            └─ pulizia controllata di sole misure gestite e non referenziate
                        ↓
        Qlik Sense Cloud — native app master items
```

### Misure catalogate e sottoscrizioni

| Master measure (ID stabile) | Presentation 1 | Presentation 2 |
| --- | :---: | :---: |
| `qlikgpt_shared_revenue` — Fatturato | ✔ | ✔ |
| `qlikgpt_shared_orders` — Numero ordini | ✔ | — |
| `qlikgpt_shared_margin` — Margine lordo | ✔ | — |
| `qlikgpt_shared_margin_pct` — Margine % | ✔ | ✔ |
| `qlikgpt_shared_average_order` — Valore medio ordine | — | — |

La quinta misura è **definita ma non distribuita**: per utilizzarla in futuro aggiungi soltanto l'ID a `catalogMeasures` nel manifest dell'app. Il medesimo processo funziona per una nuova Presentation.

- [Catalogo misure](catalog/measures.json)
- [Manifest Presentation 1](apps/presentation1.json) / [sorgenti foglio e oggetti](apps/presentation1-objects.json)
- [Manifest Presentation 2](apps/presentation2.json) / [sorgenti foglio e oggetti](apps/presentation2-objects.json)
- [Guida per creare una nuova Presentation](catalog/README.md)
- [Unit test](tests/test_semantic_catalog.py) · [Deployment](ci/deploy.py) · [Orchestratore semantico](ci/semantic_catalog.py)

### Applicazioni cloud

Le app del PoC rimangono distinte:
- **ETL1**: [QlikGPT - 01 ETL RAW](https://sdggroup-it.eu.qlikcloud.com/sense/app/932480d2-415d-4535-9267-c699f44c55c6), generazione e store del QVD raw;
- **ETL2**: [QlikGPT - 02 ETL TRANSFORM](https://sdggroup-it.eu.qlikcloud.com/sense/app/70ba9d05-24b7-46ec-8b8c-560e8169c3d1), trasformazione e store del QVD curated;
- **Presentation 1**: [Sales Overview](https://sdggroup-it.eu.qlikcloud.com/sense/app/07dfa926-4895-4fb2-af4c-eac90e9eb2cb);
- **Presentation 2**: [Shared Semantic Measures](https://sdggroup-it.eu.qlikcloud.com/sense/app/04280b14-6ba5-4fe9-90d6-2ff8fa1c994f).

Ogni modifica a `catalog/measures.json` avvia un **frontend-only deployment**, senza reload ETL1/ETL2. L'analisi Git identifica le sole app sottoscritte alla misura modificata. Una modifica agli script ETL provoca il reload completo; la creazione di una nuova Presentation include il caricamento iniziale.

### Convenzioni

- **Catalogo unico**: non creare `frontend/measures.json` o file analoghi sotto una singola app.
- **ID immutabili**: per aggiornare formula, nome o formato, mantenere lo stesso `id`.
- **Master item usati davvero**: nelle definizioni dei grafici Qlik, `qLibraryId` deve puntare a una misura sottoscritta; non utilizzare formule inline.
- **Metadati e data contract**: `requiredFields` elenca i campi necessari; il deployment verifica la loro disponibilità nell'app.
- **Nessun delete implicito del catalogo**: la rimozione della definizione globale è bloccata dalla validazione delle dipendenze; quando si toglie una sottoscrizione, un vecchio master item può essere rimosso solo se QIX non rileva oggetti collegati.
- **Rollback**: compensazione *best effort*; non esiste una transazione atomica tra app Qlik diverse.
- **Sicurezza**: nessuna API key nel repository; conservare `QLIK_API_KEY` soltanto come GitHub Actions secret. Per uso aziendale, repository privato, PR, approvazioni e promozione verso produzione.

## Ripetere i test

Con Python 3.12 e dipendenza `websocket-client`:

```bash
python -m unittest discover -s tests -v
```

Il workflow li esegue automaticamente prima dell'accesso a Qlik Cloud.
